"""
Data Migration Script for AlphaVelocity

Migrates data from JSON files to PostgreSQL database
"""

import json
import sys
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
import yfinance as yf

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.config import db_config
from models.database import (
    User, Portfolio, SecurityMaster, Category, Holding, Transaction,
    MomentumScore, PriceHistory, PerformanceSnapshot, Benchmark, BenchmarkPerformance
)
from services.momentum_engine import MomentumEngine

class DatabaseMigration:
    """Handles migration of existing JSON data to PostgreSQL"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.historical_dir = self.data_dir / "historical"

    def run_full_migration(self):
        """Execute complete data migration"""
        print("🚀 Starting AlphaVelocity database migration...")

        # Initialize database
        db_config.initialize_engine()
        db_config.create_all_tables()

        with db_config.get_session_context() as session:
            # Step 1: Create default user
            user = self.create_default_user(session)

            # Step 2: Set up categories
            self.setup_categories(session)

            # Step 3: Set up benchmarks
            self.setup_benchmarks(session)

            # Step 4: Create default portfolio
            portfolio = self.create_default_portfolio(session, user.id)

            # Step 5: Load securities and holdings
            self.load_securities_and_holdings(session, portfolio.id)

            # Step 6: Migrate historical portfolio values
            self.migrate_historical_data(session, portfolio.id)

            # Step 7: Load momentum scores
            self.migrate_momentum_scores(session)

        print("✅ Database migration completed successfully!")

    def create_default_user(self, session) -> User:
        """Create default user account"""
        print("👤 Creating default user...")

        user = User(
            username='admin',
            email='admin@alphavelocity.com',
            password_hash='$2b$12$temporary_hash',  # Should be properly hashed in production
            first_name='Alpha',
            last_name='Velocity',
            is_active=True
        )

        session.add(user)
        session.flush()  # Get the user ID
        print(f"   ✅ Created user: {user.username} (ID: {user.id})")
        return user

    def setup_categories(self, session):
        """Set up investment categories"""
        print("📊 Setting up investment categories...")

        categories = [
            {
                'name': 'Large-Cap Anchors',
                'description': 'Large-cap technology leaders providing portfolio stability',
                'target_allocation_pct': Decimal('20.00'),
                'benchmark_ticker': 'QQQ'
            },
            {
                'name': 'Small-Cap Specialists',
                'description': 'Small-cap technology companies with high growth potential',
                'target_allocation_pct': Decimal('15.00'),
                'benchmark_ticker': 'XLK'
            },
            {
                'name': 'Data Center Infrastructure',
                'description': 'Infrastructure supporting AI and cloud computing',
                'target_allocation_pct': Decimal('15.00'),
                'benchmark_ticker': 'VNQ'
            },
            {
                'name': 'International Tech/Momentum',
                'description': 'International technology exposure and momentum plays',
                'target_allocation_pct': Decimal('12.00'),
                'benchmark_ticker': 'VEA'
            },
            {
                'name': 'Tactical Fixed Income',
                'description': 'Short-term fixed income for portfolio stability',
                'target_allocation_pct': Decimal('8.00'),
                'benchmark_ticker': 'AGG'
            },
            {
                'name': 'Sector Momentum Rotation',
                'description': 'Sector rotation based on momentum signals',
                'target_allocation_pct': Decimal('10.00'),
                'benchmark_ticker': 'SPY'
            },
            {
                'name': 'Critical Metals & Mining',
                'description': 'Critical metals and materials for technology',
                'target_allocation_pct': Decimal('7.00'),
                'benchmark_ticker': 'XLB'
            },
            {
                'name': 'Specialized Materials ETFs',
                'description': 'Specialized materials and commodity ETFs',
                'target_allocation_pct': Decimal('5.00'),
                'benchmark_ticker': 'XLB'
            }
        ]

        for cat_data in categories:
            category = Category(**cat_data)
            session.add(category)

        session.flush()
        print(f"   ✅ Created {len(categories)} categories")

    def setup_benchmarks(self, session):
        """Set up benchmark definitions"""
        print("📈 Setting up benchmarks...")

        benchmarks = [
            {'name': 'QQQ - Nasdaq 100', 'ticker': 'QQQ', 'description': 'Nasdaq 100 Index'},
            {'name': 'SPY - S&P 500', 'ticker': 'SPY', 'description': 'S&P 500 Index'},
            {'name': 'XLK - Technology', 'ticker': 'XLK', 'description': 'Technology Select Sector SPDR Fund'},
            {'name': 'VNQ - Real Estate', 'ticker': 'VNQ', 'description': 'Vanguard Real Estate ETF'},
            {'name': 'VEA - International', 'ticker': 'VEA', 'description': 'Vanguard FTSE Developed Markets ETF'},
            {'name': 'AGG - Aggregate Bond', 'ticker': 'AGG', 'description': 'iShares Core U.S. Aggregate Bond ETF'},
            {'name': 'XLB - Basic Materials', 'ticker': 'XLB', 'description': 'Materials Select Sector SPDR Fund'}
        ]

        for bench_data in benchmarks:
            benchmark = Benchmark(**bench_data)
            session.add(benchmark)

        session.flush()
        print(f"   ✅ Created {len(benchmarks)} benchmarks")

    def create_default_portfolio(self, session, user_id: int) -> Portfolio:
        """Create default portfolio"""
        print("💼 Creating default portfolio...")

        portfolio = Portfolio(
            user_id=user_id,
            name='Default Portfolio',
            description='AlphaVelocity momentum-based AI supply chain portfolio',
            is_active=True
        )

        session.add(portfolio)
        session.flush()
        print(f"   ✅ Created portfolio: {portfolio.name} (ID: {portfolio.id})")
        return portfolio

    def load_securities_and_holdings(self, session, portfolio_id: int):
        """Load securities and create holdings from main.py DEFAULT_PORTFOLIO"""
        print("🏦 Loading securities and holdings...")

        # Import default portfolio from main.py
        from main import DEFAULT_PORTFOLIO

        # Category mapping for holdings
        category_mapping = {
            'NVDA': 'Specialized Materials ETFs',
            'BE': 'Specialized Materials ETFs',
            'AVGO': 'Large-Cap Anchors',
            'MSFT': 'Large-Cap Anchors',
            'META': 'Large-Cap Anchors',
            'NOW': 'Large-Cap Anchors',
            'AAPL': 'Large-Cap Anchors',
            'GOOGL': 'Large-Cap Anchors',
            'VRT': 'Small-Cap Specialists',
            'MOD': 'Small-Cap Specialists',
            'UI': 'Small-Cap Specialists',
            'DLR': 'Data Center Infrastructure',
            'SRVR': 'Data Center Infrastructure',
            'IRM': 'Data Center Infrastructure',
            'CCI': 'Data Center Infrastructure',
            'EWJ': 'International Tech/Momentum',
            'EWT': 'International Tech/Momentum',
            'SHY': 'Tactical Fixed Income',
            'XLI': 'Sector Momentum Rotation',
            'MP': 'Critical Metals & Mining'
        }

        # Get categories for lookup
        categories = {cat.name: cat.id for cat in session.query(Category).all()}

        securities_created = 0
        holdings_created = 0

        for ticker, shares in DEFAULT_PORTFOLIO.items():
            # Create or get security
            security = session.query(SecurityMaster).filter_by(ticker=ticker).first()
            if not security:
                # Try to get company info from yfinance
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    company_name = info.get('longName', ticker)
                    sector = info.get('sector', 'Unknown')
                    industry = info.get('industry', 'Unknown')
                    security_type = 'ETF' if ticker in ['EWJ', 'EWT', 'SHY', 'XLI', 'VRT', 'SRVR'] else 'STOCK'
                except:
                    company_name = ticker
                    sector = 'Unknown'
                    industry = 'Unknown'
                    security_type = 'STOCK'

                security = SecurityMaster(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector,
                    industry=industry,
                    security_type=security_type,
                    exchange='NASDAQ'
                )
                session.add(security)
                session.flush()
                securities_created += 1

            # Create holding
            category_name = category_mapping.get(ticker)
            category_id = categories.get(category_name) if category_name else None

            holding = Holding(
                portfolio_id=portfolio_id,
                security_id=security.id,
                category_id=category_id,
                shares=Decimal(str(shares)),
                average_cost_basis=None,  # Will be populated from transactions
                total_cost_basis=None
            )
            session.add(holding)
            holdings_created += 1

        session.flush()
        print(f"   ✅ Created {securities_created} securities and {holdings_created} holdings")

    def migrate_historical_data(self, session, portfolio_id: int):
        """Migrate historical portfolio values from JSON"""
        print("📊 Migrating historical portfolio data...")

        portfolio_values_file = self.historical_dir / "portfolio_values.json"

        if not portfolio_values_file.exists():
            print("   ⚠️  No historical portfolio data found")
            return

        with open(portfolio_values_file, 'r') as f:
            data = json.load(f)

        default_values = data.get('default', [])
        snapshots_created = 0

        for entry in default_values:
            snapshot_date = datetime.fromisoformat(entry['timestamp']).date()

            # Check if snapshot already exists
            existing = session.query(PerformanceSnapshot).filter_by(
                portfolio_id=portfolio_id,
                snapshot_date=snapshot_date
            ).first()

            if existing:
                continue

            snapshot = PerformanceSnapshot(
                portfolio_id=portfolio_id,
                snapshot_date=snapshot_date,
                total_value=Decimal(str(entry['total_value'])),
                total_cost_basis=None,  # Not available in JSON
                unrealized_gain_loss=None,
                realized_gain_loss=None,
                dividend_income=None,
                average_momentum_score=Decimal(str(entry['average_momentum_score'])),
                number_of_positions=entry['number_of_positions']
            )
            session.add(snapshot)
            snapshots_created += 1

        session.flush()
        print(f"   ✅ Created {snapshots_created} performance snapshots")

    def migrate_momentum_scores(self, session):
        """Migrate momentum scores from historical service"""
        print("📈 Migrating momentum score history...")

        momentum_file = self.historical_dir / "momentum_scores.json"

        if not momentum_file.exists():
            print("   ⚠️  No historical momentum data found")
            return

        try:
            with open(momentum_file, 'r') as f:
                data = json.load(f)
        except:
            print("   ⚠️  Could not read momentum scores file")
            return

        scores_created = 0

        # Get security lookup
        securities = {sec.ticker: sec.id for sec in session.query(SecurityMaster).all()}

        for ticker, score_history in data.items():
            if ticker not in securities:
                continue

            security_id = securities[ticker]

            for score_entry in score_history:
                score_date = datetime.fromisoformat(score_entry['timestamp']).date()

                # Check if score already exists
                existing = session.query(MomentumScore).filter_by(
                    security_id=security_id,
                    score_date=score_date
                ).first()

                if existing:
                    continue

                momentum_score = MomentumScore(
                    security_id=security_id,
                    score_date=score_date,
                    composite_score=Decimal(str(score_entry['composite_score'])),
                    price_momentum=Decimal(str(score_entry.get('price_momentum', 0))),
                    technical_momentum=Decimal(str(score_entry.get('technical_momentum', 0))),
                    fundamental_momentum=Decimal(str(score_entry.get('fundamental_momentum', 0))),
                    relative_momentum=Decimal(str(score_entry.get('relative_momentum', 0))),
                    rating=score_entry.get('rating', 'Hold')
                )
                session.add(momentum_score)
                scores_created += 1

        session.flush()
        print(f"   ✅ Created {scores_created} momentum score entries")

def main():
    """Run the migration"""
    migration = DatabaseMigration()

    # Test database connection first
    if not db_config.test_connection():
        print("❌ Cannot connect to PostgreSQL. Please ensure:")
        print("   - PostgreSQL is running")
        print("   - Database 'alphavelocity' exists")
        print("   - User 'alphavelocity' has access")
        print("   - Environment variables are set correctly")
        return

    migration.run_full_migration()

if __name__ == "__main__":
    main()