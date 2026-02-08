"""
Service for managing portfolio categories and their ticker mappings
"""
import os
import psycopg2
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import momentum engine for scoring
try:
    from .momentum_engine import MomentumEngine
except ImportError:
    from momentum_engine import MomentumEngine


class CategoryService:
    """Service for managing categories and category-ticker relationships"""

    def __init__(self, momentum_engine=None):
        self.conn = None
        self.momentum_engine = momentum_engine or MomentumEngine()

    def _get_connection(self):
        """Get database connection"""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', 5432),
                database=os.getenv('DB_NAME', 'alphavelocity'),
                user=os.getenv('DB_USER', 'alphavelocity'),
                password=os.getenv('DB_PASSWORD', 'alphavelocity_secure_password')
            )
        return self.conn

    def get_all_categories(self) -> List[Dict]:
        """Get all categories with their ticker mappings - optimized with single query"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Single optimized query with JOIN to avoid N+1 problem
            cursor.execute("""
                SELECT
                    c.id, c.name, c.description, c.target_allocation_pct, c.benchmark_ticker,
                    cs.ticker, sm.company_name
                FROM categories c
                LEFT JOIN category_securities cs ON c.id = cs.category_id
                LEFT JOIN security_master sm ON cs.security_id = sm.id
                WHERE c.is_active = true
                ORDER BY c.target_allocation_pct DESC, c.name, cs.ticker
            """)
            rows = cursor.fetchall()

            # Group by category and collect all unique tickers
            categories_map = {}
            all_tickers = set()

            for row in rows:
                cat_id, name, description, target_alloc, benchmark, ticker, company_name = row

                if cat_id not in categories_map:
                    categories_map[cat_id] = {
                        'id': cat_id,
                        'name': name,
                        'description': description,
                        'target_allocation_pct': float(target_alloc) if target_alloc else 0,
                        'benchmark': benchmark,
                        'tickers_list': []
                    }

                if ticker:
                    categories_map[cat_id]['tickers_list'].append((ticker, company_name))
                    all_tickers.add(ticker)

            # Batch-fetch all momentum scores at once (uses 24-hour cache)
            momentum_scores = {}
            for ticker in all_tickers:
                try:
                    momentum_data = self.momentum_engine.calculate_momentum_score(ticker)
                    momentum_scores[ticker] = {
                        'score': momentum_data.get('composite_score', 0),
                        'rating': momentum_data.get('rating', 'N/A')
                    }
                except:
                    momentum_scores[ticker] = {'score': 0, 'rating': 'N/A'}

            # Build final result with pre-fetched scores
            result = []
            for cat_id, cat_data in categories_map.items():
                ticker_details = []
                for ticker, company_name in cat_data['tickers_list']:
                    score_data = momentum_scores.get(ticker, {'score': 0, 'rating': 'N/A'})
                    ticker_details.append({
                        'ticker': ticker,
                        'company_name': company_name,
                        'momentum_score': score_data['score'],
                        'rating': score_data['rating']
                    })

                result.append({
                    'id': cat_data['id'],
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'target_allocation': cat_data['target_allocation_pct'] / 100,
                    'target_allocation_pct': cat_data['target_allocation_pct'],
                    'benchmark': cat_data['benchmark'],
                    'tickers': [t[0] for t in cat_data['tickers_list']],
                    'ticker_details': ticker_details,
                    'ticker_count': len(cat_data['tickers_list'])
                })

            return result

        finally:
            cursor.close()

    def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        """Get a single category by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, description, target_allocation_pct, benchmark_ticker, is_active
                FROM categories
                WHERE id = %s AND is_active = true
            """, (category_id,))

            cat = cursor.fetchone()
            if not cat:
                return None

            category_id, name, description, target_alloc, benchmark, is_active = cat

            # Get tickers for this category
            cursor.execute("""
                SELECT cs.ticker, sm.company_name
                FROM category_securities cs
                LEFT JOIN security_master sm ON cs.security_id = sm.id
                WHERE cs.category_id = %s
                ORDER BY cs.ticker
            """, (category_id,))

            tickers = cursor.fetchall()

            # Build ticker details with momentum scores
            ticker_details = []
            for ticker, company_name in tickers:
                try:
                    momentum_data = self.momentum_engine.calculate_momentum_score(ticker)
                    ticker_details.append({
                        'ticker': ticker,
                        'company_name': company_name,
                        'momentum_score': momentum_data.get('composite_score', 0),
                        'rating': momentum_data.get('rating', 'N/A')
                    })
                except Exception as e:
                    ticker_details.append({
                        'ticker': ticker,
                        'company_name': company_name,
                        'momentum_score': 0,
                        'rating': 'N/A'
                    })

            return {
                'id': category_id,
                'name': name,
                'description': description,
                'target_allocation': float(target_alloc) / 100 if target_alloc else 0,
                'target_allocation_pct': float(target_alloc) if target_alloc else 0,
                'benchmark': benchmark,
                'tickers': [t[0] for t in tickers],
                'ticker_details': ticker_details,
                'ticker_count': len(tickers)
            }

        finally:
            cursor.close()

    def add_ticker_to_category(self, category_id: int, ticker: str) -> Dict:
        """Add a ticker to a category"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Check if category exists
            cursor.execute("SELECT id FROM categories WHERE id = %s", (category_id,))
            if not cursor.fetchone():
                return {'success': False, 'error': 'Category not found'}

            # Get or create security_master entry
            cursor.execute("""
                SELECT id FROM security_master WHERE ticker = %s
            """, (ticker.upper(),))

            result = cursor.fetchone()
            if result:
                security_id = result[0]
            else:
                # Create new security_master entry
                cursor.execute("""
                    INSERT INTO security_master (ticker, security_type, is_active, created_at, updated_at)
                    VALUES (%s, 'STOCK', true, NOW(), NOW())
                    RETURNING id
                """, (ticker.upper(),))
                security_id = cursor.fetchone()[0]

            # Check if mapping already exists
            cursor.execute("""
                SELECT id FROM category_securities
                WHERE category_id = %s AND security_id = %s
            """, (category_id, security_id))

            if cursor.fetchone():
                return {'success': False, 'error': 'Ticker already in category'}

            # Add mapping
            cursor.execute("""
                INSERT INTO category_securities (category_id, security_id, ticker, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
            """, (category_id, security_id, ticker.upper()))

            mapping_id = cursor.fetchone()[0]
            conn.commit()

            return {
                'success': True,
                'message': f'Added {ticker.upper()} to category',
                'mapping_id': mapping_id
            }

        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()

    def remove_ticker_from_category(self, category_id: int, ticker: str) -> Dict:
        """Remove a ticker from a category"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM category_securities
                WHERE category_id = %s AND ticker = %s
                RETURNING id
            """, (category_id, ticker.upper()))

            result = cursor.fetchone()
            if not result:
                return {'success': False, 'error': 'Ticker not found in category'}

            conn.commit()
            return {
                'success': True,
                'message': f'Removed {ticker.upper()} from category'
            }

        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()

    def get_ticker_category(self, ticker: str) -> Optional[Dict]:
        """Get the category for a given ticker"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT c.id, c.name, c.target_allocation_pct
                FROM categories c
                JOIN category_securities cs ON c.id = cs.category_id
                WHERE cs.ticker = %s AND c.is_active = true
                LIMIT 1
            """, (ticker.upper(),))

            result = cursor.fetchone()
            if not result:
                return None

            return {
                'category_id': result[0],
                'category_name': result[1],
                'target_allocation_pct': float(result[2]) if result[2] else 0
            }

        finally:
            cursor.close()

    def create_category(self, name: str, description: str, target_allocation_pct: float,
                       benchmark_ticker: str) -> Dict:
        """Create a new category"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO categories (name, description, target_allocation_pct, benchmark_ticker, is_active, created_at)
                VALUES (%s, %s, %s, %s, true, NOW())
                RETURNING id
            """, (name, description, target_allocation_pct, benchmark_ticker))

            category_id = cursor.fetchone()[0]
            conn.commit()

            return {
                'success': True,
                'message': f'Created category: {name}',
                'category_id': category_id
            }

        except psycopg2.IntegrityError as e:
            conn.rollback()
            if 'unique' in str(e).lower():
                return {'success': False, 'error': 'Category name already exists'}
            return {'success': False, 'error': str(e)}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()

    def update_category(self, category_id: int, name: Optional[str] = None,
                       description: Optional[str] = None, target_allocation_pct: Optional[float] = None,
                       benchmark_ticker: Optional[str] = None) -> Dict:
        """Update a category"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            updates = []
            params = []

            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            if target_allocation_pct is not None:
                updates.append("target_allocation_pct = %s")
                params.append(target_allocation_pct)
            if benchmark_ticker is not None:
                updates.append("benchmark_ticker = %s")
                params.append(benchmark_ticker)

            if not updates:
                return {'success': False, 'error': 'No fields to update'}

            params.append(category_id)
            query = f"UPDATE categories SET {', '.join(updates)} WHERE id = %s RETURNING id"

            cursor.execute(query, params)
            result = cursor.fetchone()

            if not result:
                return {'success': False, 'error': 'Category not found'}

            conn.commit()
            return {
                'success': True,
                'message': 'Category updated successfully'
            }

        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()

    def __del__(self):
        """Close connection when service is destroyed"""
        if self.conn and not self.conn.closed:
            self.conn.close()
