import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from .momentum_engine import MomentumEngine
from .price_service import PriceService
from ..config.portfolio_config import PORTFOLIO_CATEGORIES, SORT_COLUMN_MAP

logger = logging.getLogger(__name__)

class PortfolioService:
    """Service for portfolio analysis and management"""

    def __init__(self, momentum_engine: Optional[MomentumEngine] = None,
                 price_service: Optional[PriceService] = None,
                 db_config=None,
                 momentum_cache_service=None) -> None:
        self.momentum_engine: MomentumEngine = momentum_engine or MomentumEngine()
        self.price_service: PriceService = price_service or PriceService()
        self.db_config = db_config
        self.momentum_cache_service = momentum_cache_service
        self.portfolio_categories: Dict[str, Dict[str, Any]] = PORTFOLIO_CATEGORIES

    def _batch_scores(self, tickers: List[str]) -> Tuple[Dict[str, Dict], List[str]]:
        """Batch-fetch momentum scores from Tier 1 + Tier 2 (no yfinance).

        Returns (found_map, missing_list). When momentum_cache_service is not
        configured, returns ({}, tickers) so callers fall back to per-ticker.
        """
        if self.momentum_cache_service:
            return self.momentum_cache_service.get_scores_from_db(tickers)
        return {}, list(tickers)

    def _fetch_position_values(self, portfolio: Dict[str, int]) -> Tuple[Dict[str, float], Dict[str, float], float]:
        """Fetch prices and compute market values for all positions.

        PriceService handles DB-first lookup internally when db_config is set.

        Returns:
        - prices_data: ticker -> current price (0 if unavailable)
        - position_values: ticker -> market value (shares * price)
        - total_value: sum of all market values
        """
        tickers = list(portfolio.keys())
        fetched = self.price_service.get_current_prices(tickers)

        prices_data: Dict[str, float] = {}
        position_values: Dict[str, float] = {}
        total_value = 0.0

        for ticker, shares in portfolio.items():
            price = fetched.get(ticker) or 0
            market_value = shares * price
            prices_data[ticker] = price
            position_values[ticker] = market_value
            total_value += market_value

        return prices_data, position_values, total_value

    @staticmethod
    def dataframe_to_holdings(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Convert analyze_portfolio() DataFrame to list of holding dicts."""
        holdings = []
        for _, row in df.iterrows():
            holdings.append({
                'ticker': row['Ticker'],
                'shares': row['Shares'],
                'price': row['Price'],
                'market_value': row['Market_Value'],
                'portfolio_percent': row['Portfolio_%'],
                'momentum_score': row['Momentum_Score'],
                'rating': row['Rating'],
                'price_momentum': row['Price_Momentum'],
                'technical_momentum': row['Technical_Momentum'],
            })
        return holdings

    def get_category_tickers(self, category_name: str) -> List[str]:
        """Get tickers for a specific category"""
        category = self.portfolio_categories.get(category_name)
        return category['tickers'] if category else []

    def get_all_categories(self) -> Dict[str, Dict[str, Any]]:
        """Get all portfolio categories"""
        return self.portfolio_categories

    def analyze_portfolio(self, portfolio: Dict[str, int]) -> Tuple[pd.DataFrame, float, float]:
        """
        Analyze portfolio with position sizes, percentages, and momentum signals

        Parameters:
        - portfolio: dict with ticker: shares mapping

        Returns:
        - DataFrame with analysis results
        - Total portfolio value
        - Average momentum score
        """
        prices_data, position_values, total_value = self._fetch_position_values(portfolio)

        # Batch-fetch momentum scores from DB when available
        tickers = list(portfolio.keys())
        scores_map: Dict[str, Dict] = {}
        if self.momentum_cache_service:
            scores_map, missing = self.momentum_cache_service.get_scores_from_db(tickers)
        else:
            missing = tickers

        # Fall back to per-ticker yfinance only for missing tickers
        for ticker in missing:
            try:
                scores_map[ticker] = self.momentum_engine.calculate_momentum_score(ticker)
            except Exception:
                scores_map[ticker] = {
                    'composite_score': 0, 'rating': 'No Data',
                    'price_momentum': 0, 'technical_momentum': 0,
                }

        # Calculate percentages and build results
        results = []
        for ticker, shares in portfolio.items():
            price = prices_data[ticker]
            market_value = position_values[ticker]
            percentage = (market_value / total_value * 100) if total_value > 0 else 0
            momentum_result = scores_map.get(ticker, {
                'composite_score': 0, 'rating': 'No Data',
                'price_momentum': 0, 'technical_momentum': 0,
            })

            results.append({
                'Ticker': ticker,
                'Shares': shares,
                'Price': f"${price:.2f}",
                'Market_Value': f"${market_value:,.2f}",
                'Portfolio_%': f"{percentage:.1f}%",
                'Momentum_Score': momentum_result.get('composite_score', 0),
                'Rating': momentum_result.get('rating', 'No Data'),
                'Price_Momentum': momentum_result.get('price_momentum', 0),
                'Technical_Momentum': momentum_result.get('technical_momentum', 0)
            })

        # Create DataFrame and sort by momentum score
        df = pd.DataFrame(results)
        df = df.sort_values('Momentum_Score', ascending=False)

        avg_momentum_score = df['Momentum_Score'].mean()

        return df, total_value, avg_momentum_score

    def get_category_analysis(self, category_name: str) -> Dict[str, Any]:
        """Analyze a specific portfolio category"""
        category = self.portfolio_categories.get(category_name)
        if not category:
            return {'error': f'Category {category_name} not found'}

        tickers = category['tickers']

        # Batch DB lookup when available
        scores_map, missing = self._batch_scores(tickers)

        for ticker in missing:
            try:
                scores_map[ticker] = self.momentum_engine.calculate_momentum_score(ticker)
            except Exception:
                scores_map[ticker] = {'composite_score': 0, 'rating': 'No Data',
                                       'ticker': ticker}

        scores = [scores_map.get(t, {'composite_score': 0, 'rating': 'No Data', 'ticker': t})
                  for t in tickers]

        return {
            'category': category_name,
            'target_allocation': category['target_allocation'],
            'benchmark': category['benchmark'],
            'tickers': tickers,
            'momentum_scores': scores,
            'average_score': sum(score['composite_score'] for score in scores) / len(scores) if scores else 0
        }

    def get_top_momentum_stocks(self, category_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top momentum stocks, optionally filtered by category"""
        if category_name:
            tickers = self.get_category_tickers(category_name)
        else:
            # Get all tickers from all categories
            tickers = []
            for category in self.portfolio_categories.values():
                tickers.extend(category['tickers'])
            tickers = list(set(tickers))  # Remove duplicates

        # Batch DB lookup when available
        scores_map, missing = self._batch_scores(tickers)

        for ticker in missing:
            try:
                scores_map[ticker] = self.momentum_engine.calculate_momentum_score(ticker)
            except Exception:
                scores_map[ticker] = {'composite_score': 0, 'rating': 'No Data',
                                       'ticker': ticker}

        scores = list(scores_map.values())

        # Sort by composite score and return top N
        scores.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        return scores[:limit]

    def generate_watchlist(self, current_portfolio: Dict[str, int], min_score: float = 70.0) -> Dict[str, Any]:
        """Generate a watchlist of potential portfolio additions"""
        current_tickers = set(current_portfolio.keys())
        watchlist_by_category = {}

        # Get current portfolio allocation by category
        current_allocation = self._calculate_current_allocation(current_portfolio)

        # Collect all available (non-held) tickers across categories for batch lookup
        all_available: List[str] = []
        for category_info in self.portfolio_categories.values():
            available = set(category_info['tickers']) - current_tickers
            all_available.extend(available)
        all_available = list(set(all_available))

        # Batch DB lookup
        all_scores_map, missing = self._batch_scores(all_available)
        for ticker in missing:
            try:
                all_scores_map[ticker] = self.momentum_engine.calculate_momentum_score(ticker)
            except Exception:
                pass  # skip tickers we can't score

        for category_name, category_info in self.portfolio_categories.items():
            category_tickers = set(category_info['tickers'])
            available_tickers = category_tickers - current_tickers

            if not available_tickers:
                continue

            # Filter to tickers meeting min_score
            scores = []
            for ticker in available_tickers:
                result = all_scores_map.get(ticker)
                if result and result.get('composite_score', 0) >= min_score:
                    scores.append(result)

            # Sort by score
            scores.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

            # Calculate category metrics
            target_allocation = category_info['target_allocation']
            current_cat_allocation = current_allocation.get(category_name, 0)
            allocation_gap = target_allocation - current_cat_allocation

            watchlist_by_category[category_name] = {
                'target_allocation': target_allocation,
                'current_allocation': current_cat_allocation,
                'allocation_gap': allocation_gap,
                'priority': 'High' if allocation_gap > 0.02 else 'Medium' if allocation_gap > 0 else 'Low',
                'benchmark': category_info['benchmark'],
                'candidates': scores[:5],  # Top 5 candidates per category
                'total_candidates': len(scores)
            }

        # Overall watchlist summary
        total_candidates = sum(cat['total_candidates'] for cat in watchlist_by_category.values())
        high_priority_categories = [name for name, data in watchlist_by_category.items() if data['priority'] == 'High']

        return {
            'summary': {
                'total_candidates': total_candidates,
                'high_priority_categories': high_priority_categories,
                'min_score_threshold': min_score,
                'current_positions': len(current_portfolio),
                'recommended_additions': len(high_priority_categories) + 2  # Conservative growth
            },
            'categories': watchlist_by_category
        }

    def _calculate_current_allocation(self, portfolio: Dict[str, int]) -> Dict[str, float]:
        """Calculate current allocation percentages by category based on dollar values"""
        _, position_values, total_value = self._fetch_position_values(portfolio)

        category_allocation = {}
        for category_name, category_info in self.portfolio_categories.items():
            category_value = sum(
                position_values.get(ticker, 0) for ticker in portfolio.keys()
                if ticker in category_info['tickers']
            )
            category_allocation[category_name] = category_value / total_value if total_value > 0 else 0

        return category_allocation

    def get_portfolio_by_categories(self, portfolio: Dict[str, int]) -> Dict[str, Any]:
        """
        Group portfolio holdings by category with actual vs target allocation percentages

        Parameters:
        - portfolio: dict with ticker: shares mapping

        Returns:
        - Dict with categories, holdings grouped by category, and allocation info
        """
        prices_data, position_values, total_portfolio_value = self._fetch_position_values(portfolio)

        # Batch-fetch momentum scores for all portfolio tickers
        all_tickers = list(portfolio.keys())
        scores_map, missing = self._batch_scores(all_tickers)
        for ticker in missing:
            try:
                scores_map[ticker] = self.momentum_engine.calculate_momentum_score(ticker)
            except Exception:
                scores_map[ticker] = {'composite_score': 0, 'rating': 'No Data'}

        # Group holdings by category
        categorized_holdings = {}
        category_totals = {}

        for category_name, category_info in self.portfolio_categories.items():
            category_tickers = set(category_info['tickers'])
            category_holdings = []
            category_value = 0

            for ticker, shares in portfolio.items():
                if ticker in category_tickers:
                    price = prices_data.get(ticker, 0)
                    market_value = position_values.get(ticker, 0)
                    percentage = (market_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
                    category_value += market_value

                    momentum_result = scores_map.get(ticker, {'composite_score': 0, 'rating': 'No Data'})

                    category_holdings.append({
                        'ticker': ticker,
                        'shares': shares,
                        'price': f"${price:.2f}",
                        'market_value': f"${market_value:,.2f}",
                        'portfolio_percent': f"{percentage:.1f}%",
                        'momentum_score': momentum_result.get('composite_score', 0),
                        'rating': momentum_result.get('rating', 'No Data')
                    })

            if category_holdings:
                # Sort holdings by momentum score
                category_holdings.sort(key=lambda x: x['momentum_score'], reverse=True)

                actual_allocation = (category_value / total_portfolio_value) if total_portfolio_value > 0 else 0
                target_allocation = category_info['target_allocation']

                categorized_holdings[category_name] = {
                    'name': category_name,
                    'holdings': category_holdings,
                    'target_allocation': target_allocation,
                    'actual_allocation': actual_allocation,
                    'total_value': category_value,
                    'benchmark': category_info.get('benchmark', 'N/A')
                }

                category_totals[category_name] = category_value

        # Calculate overall portfolio stats
        avg_momentum_score = 0
        total_positions = 0
        for cat_data in categorized_holdings.values():
            for holding in cat_data['holdings']:
                avg_momentum_score += holding['momentum_score']
                total_positions += 1

        if total_positions > 0:
            avg_momentum_score /= total_positions

        return {
            'total_value': total_portfolio_value,
            'average_momentum_score': avg_momentum_score,
            'number_of_positions': total_positions,
            'categories': categorized_holdings
        }


# Module-level singleton
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get the global PortfolioService singleton (creates one if not set)."""
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service


def set_portfolio_service(instance: PortfolioService) -> None:
    """Set the global PortfolioService singleton (called at startup)."""
    global _portfolio_service
    _portfolio_service = instance