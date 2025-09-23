import pandas as pd
from typing import Dict, List, Optional, Tuple
from .momentum_engine import MomentumEngine
from ..utils.data_providers import DataProvider

class PortfolioService:
    """Service for portfolio analysis and management"""

    def __init__(self, momentum_engine: MomentumEngine = None):
        self.momentum_engine = momentum_engine or MomentumEngine()
        self.data_provider = DataProvider()

        # Portfolio categories with target allocations
        self.portfolio_categories = {
            'Large-Cap Anchors': {
                'tickers': ['NVDA', 'TSM', 'ASML', 'AVGO', 'MSFT', 'META', 'AAPL', 'AMD', 'GOOGL', 'TSLA', 'PLTR', 'CSCO', 'CRWV', 'ORCL', 'DT', 'AUR', 'MBLY', 'NOW'],
                'target_allocation': 0.20,
                'benchmark': 'QQQ'
            },
            'Small-Cap Specialists': {
                'tickers': ['VRT', 'MOD', 'BE', 'CIEN', 'ATKR', 'UI', 'APLD', 'SMCI', 'GDS', 'VNET'],
                'target_allocation': 0.15,
                'benchmark': 'XLK'
            },
            'Data Center Infrastructure': {
                'tickers': ['SRVR', 'DLR', 'EQIX', 'AMT', 'CCI', 'COR', 'IRM', 'ACM', 'JCI', 'IDGT', 'DTCR'],
                'target_allocation': 0.15,
                'benchmark': 'VNQ'
            },
            'International Tech/Momentum': {
                'tickers': ['EWJ', 'EWT', 'INDA', 'EWY'],
                'target_allocation': 0.12,
                'benchmark': 'VEA'
            },
            'Tactical Fixed Income': {
                'tickers': ['SHY', 'VCIT', 'IPE'],
                'target_allocation': 0.08,
                'benchmark': 'AGG'
            },
            'Sector Momentum Rotation': {
                'tickers': ['XLE', 'XLF', 'XLI', 'XLU', 'XLB'],
                'target_allocation': 0.10,
                'benchmark': 'SPY'
            },
            'Critical Metals & Mining': {
                'tickers': ['MP', 'LYC', 'ARA', 'ALB', 'SQM', 'LAC', 'FCX', 'SCCO', 'TECK'],
                'target_allocation': 0.07,
                'benchmark': 'XLB'
            },
            'Specialized Materials ETFs': {
                'tickers': ['REMX', 'LIT', 'XMET'],
                'target_allocation': 0.05,
                'benchmark': 'XLB'
            }
        }

    def get_category_tickers(self, category_name: str) -> List[str]:
        """Get tickers for a specific category"""
        category = self.portfolio_categories.get(category_name)
        return category['tickers'] if category else []

    def get_all_categories(self) -> Dict:
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
        tickers = list(portfolio.keys())
        prices_data = {}

        # Get current prices for all positions
        for ticker in tickers:
            try:
                hist_data, _ = self.data_provider.get_stock_data(ticker, '1d')
                if hist_data is not None and not hist_data.empty:
                    prices_data[ticker] = hist_data['Close'].iloc[-1]
                else:
                    prices_data[ticker] = 0
            except Exception as e:
                print(f"Error fetching price for {ticker}: {e}")
                prices_data[ticker] = 0

        # Calculate portfolio values
        portfolio_data = []
        total_value = 0

        for ticker, shares in portfolio.items():
            price = prices_data.get(ticker, 0)
            market_value = shares * price
            total_value += market_value

            portfolio_data.append({
                'ticker': ticker,
                'shares': shares,
                'price': price,
                'market_value': market_value
            })

        # Calculate percentages and get momentum signals
        results = []

        for data in portfolio_data:
            ticker = data['ticker']
            percentage = (data['market_value'] / total_value * 100) if total_value > 0 else 0

            # Get momentum score
            momentum_result = self.momentum_engine.calculate_momentum_score(ticker)

            results.append({
                'Ticker': ticker,
                'Shares': data['shares'],
                'Price': f"${data['price']:.2f}",
                'Market_Value': f"${data['market_value']:,.2f}",
                'Portfolio_%': f"{percentage:.1f}%",
                'Momentum_Score': momentum_result['composite_score'],
                'Rating': momentum_result['rating'],
                'Price_Momentum': momentum_result['price_momentum'],
                'Technical_Momentum': momentum_result['technical_momentum']
            })

        # Create DataFrame and sort by momentum score
        df = pd.DataFrame(results)
        df = df.sort_values('Momentum_Score', ascending=False)

        # Calculate summary statistics
        total_portfolio_value = sum(data['market_value'] for data in portfolio_data)
        avg_momentum_score = df['Momentum_Score'].mean()

        return df, total_portfolio_value, avg_momentum_score

    def get_category_analysis(self, category_name: str) -> Dict:
        """Analyze a specific portfolio category"""
        category = self.portfolio_categories.get(category_name)
        if not category:
            return {'error': f'Category {category_name} not found'}

        tickers = category['tickers']
        scores = []

        for ticker in tickers:
            momentum_result = self.momentum_engine.calculate_momentum_score(ticker)
            scores.append(momentum_result)

        return {
            'category': category_name,
            'target_allocation': category['target_allocation'],
            'benchmark': category['benchmark'],
            'tickers': tickers,
            'momentum_scores': scores,
            'average_score': sum(score['composite_score'] for score in scores) / len(scores) if scores else 0
        }

    def get_top_momentum_stocks(self, category_name: str = None, limit: int = 10) -> List[Dict]:
        """Get top momentum stocks, optionally filtered by category"""
        if category_name:
            tickers = self.get_category_tickers(category_name)
        else:
            # Get all tickers from all categories
            tickers = []
            for category in self.portfolio_categories.values():
                tickers.extend(category['tickers'])
            tickers = list(set(tickers))  # Remove duplicates

        scores = []
        for ticker in tickers:
            momentum_result = self.momentum_engine.calculate_momentum_score(ticker)
            scores.append(momentum_result)

        # Sort by composite score and return top N
        scores.sort(key=lambda x: x['composite_score'], reverse=True)
        return scores[:limit]

    def generate_watchlist(self, current_portfolio: Dict[str, int], min_score: float = 70.0) -> Dict:
        """Generate a watchlist of potential portfolio additions"""
        current_tickers = set(current_portfolio.keys())
        watchlist_by_category = {}

        # Get current portfolio allocation by category
        current_allocation = self._calculate_current_allocation(current_portfolio)

        for category_name, category_info in self.portfolio_categories.items():
            category_tickers = set(category_info['tickers'])
            available_tickers = category_tickers - current_tickers

            if not available_tickers:
                continue

            # Score available tickers
            scores = []
            for ticker in available_tickers:
                try:
                    momentum_result = self.momentum_engine.calculate_momentum_score(ticker)
                    if momentum_result['composite_score'] >= min_score:
                        scores.append(momentum_result)
                except Exception as e:
                    continue

            # Sort by score
            scores.sort(key=lambda x: x['composite_score'], reverse=True)

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
        """Calculate current allocation percentages by category"""
        # This is a simplified version - in practice you'd use market values
        total_positions = sum(portfolio.values())
        category_allocation = {}

        for category_name, category_info in self.portfolio_categories.items():
            category_positions = sum(
                shares for ticker, shares in portfolio.items()
                if ticker in category_info['tickers']
            )
            category_allocation[category_name] = category_positions / total_positions if total_positions > 0 else 0

        return category_allocation