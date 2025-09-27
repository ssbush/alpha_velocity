import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path
from .daily_cache_service import DailyCacheService

class HistoricalDataService:
    """Service for managing historical momentum scores and portfolio performance"""

    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # File paths for different data types
        self.momentum_scores_file = self.data_dir / "momentum_scores.json"
        self.portfolio_values_file = self.data_dir / "portfolio_values.json"
        self.portfolio_compositions_file = self.data_dir / "portfolio_compositions.json"

        # Daily cache service for improved performance
        self.daily_cache = DailyCacheService()

        # Initialize data files if they don't exist
        self._initialize_data_files()

    def _initialize_data_files(self):
        """Initialize empty data files if they don't exist"""
        for file_path in [self.momentum_scores_file, self.portfolio_values_file, self.portfolio_compositions_file]:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump({}, f)

    def record_momentum_score(self, ticker: str, momentum_data: Dict):
        """Record a momentum score for a ticker at current timestamp"""
        timestamp = datetime.now().isoformat()

        # Load existing data
        with open(self.momentum_scores_file, 'r') as f:
            data = json.load(f)

        # Initialize ticker if not exists
        if ticker not in data:
            data[ticker] = []

        # Add new score with timestamp
        score_entry = {
            'timestamp': timestamp,
            'composite_score': momentum_data['composite_score'],
            'rating': momentum_data['rating'],
            'price_momentum': momentum_data['price_momentum'],
            'technical_momentum': momentum_data['technical_momentum'],
            'fundamental_momentum': momentum_data['fundamental_momentum'],
            'relative_momentum': momentum_data['relative_momentum']
        }

        data[ticker].append(score_entry)

        # Keep only last 90 days of data to manage file size
        cutoff_date = datetime.now() - timedelta(days=90)
        data[ticker] = [
            entry for entry in data[ticker]
            if datetime.fromisoformat(entry['timestamp']) > cutoff_date
        ]

        # Save updated data
        with open(self.momentum_scores_file, 'w') as f:
            json.dump(data, f, indent=2)

    def should_record_daily_data(self) -> bool:
        """Check if we should record daily data (once per trading day)"""
        try:
            # Only record once per trading day after market close
            last_trading_date = self.daily_cache.get_last_trading_date()

            with open(self.portfolio_values_file, 'r') as f:
                values_data = json.load(f)

            # Check if we already have data for today
            default_values = values_data.get('default', [])
            if default_values:
                last_entry = default_values[-1]
                last_entry_date = datetime.fromisoformat(last_entry['timestamp']).strftime('%Y-%m-%d')
                return last_entry_date != last_trading_date

            return True
        except Exception:
            return True

    def record_portfolio_snapshot(self, portfolio_id: str, portfolio_data: Dict):
        """Record a portfolio snapshot (daily only to avoid over-sampling)"""
        # Only record once per trading day to avoid over-sampling
        if not self.should_record_daily_data():
            return

        # Use trading day date instead of current timestamp for consistency
        trading_date = self.daily_cache.get_last_trading_date()
        # Convert to datetime for consistency with existing code
        timestamp = f"{trading_date}T16:00:00"

        # Record portfolio value
        self._record_portfolio_value(portfolio_id, timestamp, portfolio_data)

        # Record portfolio composition
        self._record_portfolio_composition(portfolio_id, timestamp, portfolio_data)

        print(f"📊 Recorded daily portfolio snapshot for {portfolio_id} on {trading_date}")

    def _record_portfolio_value(self, portfolio_id: str, timestamp: str, portfolio_data: Dict):
        """Record portfolio total value and average momentum score"""
        with open(self.portfolio_values_file, 'r') as f:
            data = json.load(f)

        if portfolio_id not in data:
            data[portfolio_id] = []

        value_entry = {
            'timestamp': timestamp,
            'total_value': portfolio_data.get('total_value', 0),
            'average_momentum_score': portfolio_data.get('average_momentum_score', 0),
            'number_of_positions': portfolio_data.get('number_of_positions', 0)
        }

        data[portfolio_id].append(value_entry)

        # Keep only last 365 days for better historical analysis
        cutoff_date = datetime.now() - timedelta(days=365)
        data[portfolio_id] = [
            entry for entry in data[portfolio_id]
            if datetime.fromisoformat(entry['timestamp']) > cutoff_date
        ]

        with open(self.portfolio_values_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _record_portfolio_composition(self, portfolio_id: str, timestamp: str, portfolio_data: Dict):
        """Record detailed portfolio composition"""
        with open(self.portfolio_compositions_file, 'r') as f:
            data = json.load(f)

        if portfolio_id not in data:
            data[portfolio_id] = []

        # Extract holding information
        holdings_summary = []
        if 'holdings' in portfolio_data:
            for holding in portfolio_data['holdings']:
                holdings_summary.append({
                    'ticker': holding.get('ticker'),
                    'shares': holding.get('shares'),
                    'market_value': holding.get('market_value'),
                    'portfolio_percent': holding.get('portfolio_percent'),
                    'momentum_score': holding.get('momentum_score'),
                    'rating': holding.get('rating')
                })

        composition_entry = {
            'timestamp': timestamp,
            'holdings': holdings_summary
        }

        data[portfolio_id].append(composition_entry)

        # Keep only last 30 days for composition (more detailed data)
        cutoff_date = datetime.now() - timedelta(days=30)
        data[portfolio_id] = [
            entry for entry in data[portfolio_id]
            if datetime.fromisoformat(entry['timestamp']) > cutoff_date
        ]

        with open(self.portfolio_compositions_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_momentum_history(self, ticker: str, days: int = 30) -> List[Dict]:
        """Get historical momentum scores for a ticker"""
        try:
            with open(self.momentum_scores_file, 'r') as f:
                data = json.load(f)

            if ticker not in data:
                return []

            # Filter by days
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_data = [
                entry for entry in data[ticker]
                if datetime.fromisoformat(entry['timestamp']) > cutoff_date
            ]

            return sorted(filtered_data, key=lambda x: x['timestamp'])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_portfolio_history(self, portfolio_id: str, days: int = 30) -> Dict:
        """Get historical portfolio performance"""
        try:
            with open(self.portfolio_values_file, 'r') as f:
                values_data = json.load(f)

            with open(self.portfolio_compositions_file, 'r') as f:
                compositions_data = json.load(f)

            # Filter by days
            cutoff_date = datetime.now() - timedelta(days=days)

            values = []
            if portfolio_id in values_data:
                values = [
                    entry for entry in values_data[portfolio_id]
                    if datetime.fromisoformat(entry['timestamp']) > cutoff_date
                ]

            compositions = []
            if portfolio_id in compositions_data:
                compositions = [
                    entry for entry in compositions_data[portfolio_id]
                    if datetime.fromisoformat(entry['timestamp']) > cutoff_date
                ]

            return {
                'values': sorted(values, key=lambda x: x['timestamp']),
                'compositions': sorted(compositions, key=lambda x: x['timestamp'])
            }
        except (FileNotFoundError, json.JSONDecodeError):
            return {'values': [], 'compositions': []}

    def get_performance_analytics(self, portfolio_id: str, days: int = 30) -> Dict:
        """Calculate performance analytics for a portfolio"""
        history = self.get_portfolio_history(portfolio_id, days)
        values = history['values']

        if len(values) < 2:
            return {
                'total_return': 0,
                'daily_return': 0,
                'volatility': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'momentum_trend': 'neutral'
            }

        # Convert to pandas for easier calculations
        df = pd.DataFrame(values)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        df = df.sort_values('timestamp')

        # Calculate returns
        initial_value = df['total_value'].iloc[0]
        final_value = df['total_value'].iloc[-1]
        total_return = ((final_value - initial_value) / initial_value) * 100 if initial_value > 0 else 0

        # Daily returns
        df['daily_return'] = df['total_value'].pct_change()
        avg_daily_return = df['daily_return'].mean() * 100

        # Volatility (standard deviation of daily returns)
        volatility = df['daily_return'].std() * 100 if len(df) > 1 else 0

        # Sharpe ratio (simplified, assuming risk-free rate of 2%)
        risk_free_rate = 0.02 / 365  # Daily risk-free rate
        excess_returns = df['daily_return'] - risk_free_rate
        sharpe_ratio = excess_returns.mean() / excess_returns.std() if excess_returns.std() > 0 else 0

        # Max drawdown
        rolling_max = df['total_value'].cummax()
        drawdown = (df['total_value'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100

        # Momentum trend
        momentum_scores = df['average_momentum_score']
        if len(momentum_scores) >= 2:
            momentum_change = momentum_scores.iloc[-1] - momentum_scores.iloc[0]
            if momentum_change > 2:
                momentum_trend = 'improving'
            elif momentum_change < -2:
                momentum_trend = 'declining'
            else:
                momentum_trend = 'stable'
        else:
            momentum_trend = 'neutral'

        return {
            'total_return': round(total_return, 2),
            'daily_return': round(avg_daily_return, 4),
            'volatility': round(volatility, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'momentum_trend': momentum_trend,
            'data_points': len(df),
            'period_days': (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days
        }

    def get_top_performers(self, days: int = 7) -> List[Dict]:
        """Get top performing stocks by momentum score improvement"""
        try:
            with open(self.momentum_scores_file, 'r') as f:
                data = json.load(f)

            performers = []
            cutoff_date = datetime.now() - timedelta(days=days)

            for ticker, scores in data.items():
                # Filter recent scores
                recent_scores = [
                    entry for entry in scores
                    if datetime.fromisoformat(entry['timestamp']) > cutoff_date
                ]

                if len(recent_scores) >= 2:
                    # Sort by timestamp
                    recent_scores.sort(key=lambda x: x['timestamp'])

                    initial_score = recent_scores[0]['composite_score']
                    latest_score = recent_scores[-1]['composite_score']
                    improvement = latest_score - initial_score

                    performers.append({
                        'ticker': ticker,
                        'initial_score': initial_score,
                        'latest_score': latest_score,
                        'improvement': improvement,
                        'improvement_percent': (improvement / initial_score * 100) if initial_score > 0 else 0,
                        'latest_rating': recent_scores[-1]['rating']
                    })

            # Sort by improvement and return top 10
            performers.sort(key=lambda x: x['improvement'], reverse=True)
            return performers[:10]

        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_cached_momentum_score(self, ticker: str) -> Dict:
        """Get latest cached momentum score for a ticker"""
        try:
            cached_momentum = self.daily_cache.get_cached_momentum()
            if ticker in cached_momentum:
                return cached_momentum[ticker]
        except Exception as e:
            print(f"Failed to get cached momentum for {ticker}: {e}")

        return {}

    def get_cached_price(self, ticker: str) -> float:
        """Get latest cached price for a ticker"""
        try:
            cached_prices = self.daily_cache.get_cached_prices()
            return cached_prices.get(ticker, 0.0)
        except Exception as e:
            print(f"Failed to get cached price for {ticker}: {e}")
            return 0.0

    def get_portfolio_from_cache(self, tickers: Dict[str, int]) -> Dict:
        """Calculate portfolio analysis using cached data"""
        try:
            cached_prices = self.daily_cache.get_cached_prices()
            cached_momentum = self.daily_cache.get_cached_momentum()

            total_value = 0
            momentum_scores = []
            valid_positions = 0

            for ticker, shares in tickers.items():
                if ticker in cached_prices and ticker in cached_momentum:
                    price = cached_prices[ticker]
                    momentum = cached_momentum[ticker]

                    market_value = price * shares
                    total_value += market_value
                    momentum_scores.append(momentum['composite_score'])
                    valid_positions += 1

            avg_momentum = sum(momentum_scores) / len(momentum_scores) if momentum_scores else 0

            return {
                'total_value': total_value,
                'average_momentum_score': avg_momentum,
                'number_of_positions': valid_positions,
                'using_cache': True
            }

        except Exception as e:
            print(f"Failed to get portfolio from cache: {e}")
            return {'using_cache': False}

    def cleanup_old_data(self, days_to_keep: int = 365):
        """Clean up data older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        for file_path in [self.momentum_scores_file, self.portfolio_values_file, self.portfolio_compositions_file]:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                # Clean each ticker/portfolio
                for key in data:
                    if isinstance(data[key], list):
                        data[key] = [
                            entry for entry in data[key]
                            if datetime.fromisoformat(entry['timestamp']) > cutoff_date
                        ]

                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)

            except (FileNotFoundError, json.JSONDecodeError):
                continue