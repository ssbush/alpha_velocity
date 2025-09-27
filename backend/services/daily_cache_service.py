"""
Daily Cache Service for AlphaVelocity
Handles daily sampling of stock prices and momentum scores for improved performance.
"""

import json
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import pytz


class DailyCacheService:
    """Service for daily caching of stock prices and momentum scores"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.cache_dir = self.data_dir / "daily_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache files
        self.daily_prices_file = self.cache_dir / "daily_prices.json"
        self.daily_momentum_file = self.cache_dir / "daily_momentum.json"
        self.cache_metadata_file = self.cache_dir / "cache_metadata.json"

        # Trading timezone
        self.trading_tz = pytz.timezone('US/Eastern')

        # Initialize files if they don't exist
        self._initialize_cache_files()

    def _initialize_cache_files(self):
        """Initialize cache files if they don't exist"""
        for file_path in [self.daily_prices_file, self.daily_momentum_file, self.cache_metadata_file]:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump({}, f)

    def get_last_trading_date(self) -> str:
        """Get the last trading date (excluding weekends and considering market hours)"""
        now = datetime.now(self.trading_tz)

        # If it's before 4:00 PM ET on a trading day, use previous trading day
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        if now < market_close:
            # Use previous trading day
            current_date = now - timedelta(days=1)
        else:
            current_date = now

        # Find the most recent trading day (Monday-Friday)
        while current_date.weekday() > 4:  # 0=Monday, 6=Sunday
            current_date -= timedelta(days=1)

        return current_date.strftime('%Y-%m-%d')

    def is_cache_current(self, date: str = None) -> bool:
        """Check if cache is current for the given date"""
        if date is None:
            date = self.get_last_trading_date()

        try:
            with open(self.cache_metadata_file, 'r') as f:
                metadata = json.load(f)

            return metadata.get('last_update_date') == date
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def get_cached_prices(self, date: str = None) -> Dict[str, float]:
        """Get cached daily prices for a specific date"""
        if date is None:
            date = self.get_last_trading_date()

        try:
            with open(self.daily_prices_file, 'r') as f:
                prices = json.load(f)

            return prices.get(date, {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_cached_momentum(self, date: str = None) -> Dict[str, Dict]:
        """Get cached momentum scores for a specific date"""
        if date is None:
            date = self.get_last_trading_date()

        try:
            with open(self.daily_momentum_file, 'r') as f:
                momentum = json.load(f)

            return momentum.get(date, {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def fetch_daily_prices(self, tickers: List[str], date: str = None) -> Dict[str, float]:
        """Fetch daily closing prices for given tickers"""
        if date is None:
            date = self.get_last_trading_date()

        prices = {}
        failed_tickers = []

        print(f"Fetching daily prices for {len(tickers)} tickers for {date}...")

        for ticker in tickers:
            try:
                # Get 5 days of data to ensure we have the target date
                end_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)
                start_date = end_date - timedelta(days=7)

                # Download data
                stock_data = yf.download(
                    ticker,
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    interval='1d',
                    auto_adjust=True,
                    progress=False
                )

                if not stock_data.empty:
                    # Get the closing price for the target date or most recent
                    target_date = pd.Timestamp(date)

                    # Find the closest trading day to our target date
                    if target_date in stock_data.index:
                        close_price = stock_data.loc[target_date]['Close']
                    else:
                        # Get the most recent price before or on the target date
                        valid_dates = stock_data.index[stock_data.index <= target_date]
                        if not valid_dates.empty:
                            close_price = stock_data.loc[valid_dates[-1]]['Close']
                        else:
                            close_price = stock_data['Close'].iloc[-1]

                    prices[ticker] = float(close_price)
                    print(f"  ✓ {ticker}: ${close_price:.2f}")
                else:
                    failed_tickers.append(ticker)
                    print(f"  ✗ {ticker}: No data available")

            except Exception as e:
                failed_tickers.append(ticker)
                print(f"  ✗ {ticker}: Error - {e}")

        if failed_tickers:
            print(f"Failed to fetch prices for: {failed_tickers}")

        return prices

    def calculate_daily_momentum(self, tickers: List[str], momentum_engine,
                               date: str = None) -> Dict[str, Dict]:
        """Calculate momentum scores for given tickers using historical data"""
        if date is None:
            date = self.get_last_trading_date()

        momentum_scores = {}
        failed_tickers = []

        print(f"Calculating momentum scores for {len(tickers)} tickers for {date}...")

        for ticker in tickers:
            try:
                # Calculate momentum score using the existing engine
                result = momentum_engine.calculate_momentum_score(ticker)

                # Store the result
                momentum_scores[ticker] = {
                    'composite_score': result['composite_score'],
                    'rating': result['rating'],
                    'price_momentum': result['price_momentum'],
                    'technical_momentum': result['technical_momentum'],
                    'fundamental_momentum': result['fundamental_momentum'],
                    'relative_momentum': result['relative_momentum']
                }

                print(f"  ✓ {ticker}: {result['composite_score']:.1f} ({result['rating']})")

            except Exception as e:
                failed_tickers.append(ticker)
                print(f"  ✗ {ticker}: Error calculating momentum - {e}")

        if failed_tickers:
            print(f"Failed to calculate momentum for: {failed_tickers}")

        return momentum_scores

    def update_daily_cache(self, tickers: List[str], momentum_engine,
                          date: str = None, force_update: bool = False) -> bool:
        """Update daily cache with latest prices and momentum scores"""
        if date is None:
            date = self.get_last_trading_date()

        # Check if cache is already current
        if not force_update and self.is_cache_current(date):
            print(f"Cache is already current for {date}")
            return True

        print(f"Updating daily cache for {date}...")

        try:
            # Fetch daily prices
            daily_prices = self.fetch_daily_prices(tickers, date)

            if not daily_prices:
                print("No prices fetched, cache update failed")
                return False

            # Calculate momentum scores
            daily_momentum = self.calculate_daily_momentum(tickers, momentum_engine, date)

            if not daily_momentum:
                print("No momentum scores calculated, cache update failed")
                return False

            # Load existing cache data
            with open(self.daily_prices_file, 'r') as f:
                all_prices = json.load(f)

            with open(self.daily_momentum_file, 'r') as f:
                all_momentum = json.load(f)

            # Update with new data
            all_prices[date] = daily_prices
            all_momentum[date] = daily_momentum

            # Clean up old data (keep last 365 days)
            cutoff_date = datetime.strptime(date, '%Y-%m-%d') - timedelta(days=365)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')

            all_prices = {d: data for d, data in all_prices.items() if d > cutoff_str}
            all_momentum = {d: data for d, data in all_momentum.items() if d > cutoff_str}

            # Save updated cache
            with open(self.daily_prices_file, 'w') as f:
                json.dump(all_prices, f, indent=2)

            with open(self.daily_momentum_file, 'w') as f:
                json.dump(all_momentum, f, indent=2)

            # Update metadata
            metadata = {
                'last_update_date': date,
                'last_update_timestamp': datetime.now().isoformat(),
                'cached_tickers': list(daily_prices.keys()),
                'successful_tickers': len(daily_prices),
                'total_dates_cached': len(all_prices)
            }

            with open(self.cache_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            print(f"✅ Daily cache updated successfully for {date}")
            print(f"   - Cached {len(daily_prices)} tickers")
            print(f"   - Total historical dates: {len(all_prices)}")

            # Record daily portfolio snapshot using cached data
            self._record_daily_portfolio_snapshot(date)

            return True

        except Exception as e:
            print(f"❌ Failed to update daily cache: {e}")
            return False

    def _record_daily_portfolio_snapshot(self, date: str):
        """Record daily portfolio snapshot using cached data"""
        try:
            # Import here to avoid circular imports
            from .historical_service import HistoricalDataService

            # Get the default portfolio tickers and shares
            # This should match the DEFAULT_PORTFOLIO from main.py
            default_portfolio = {
                'AAPL': 10, 'NVDA': 5, 'TSM': 7, 'GOOGL': 3, 'MSFT': 8, 'META': 4,
                'AMD': 6, 'ASML': 3, 'AVGO': 2, 'TSLA': 3, 'PLTR': 15, 'CSCO': 20,
                'ORCL': 8, 'NOW': 4, 'DLR': 5, 'AMT': 3, 'CCI': 10, 'EQIX': 2,
                'VCIT': 50
            }

            # Get cached prices and momentum for the date
            cached_prices = {}
            cached_momentum = {}

            with open(self.daily_prices_file, 'r') as f:
                all_prices = json.load(f)
                if date in all_prices:
                    cached_prices = all_prices[date]

            with open(self.daily_momentum_file, 'r') as f:
                all_momentum = json.load(f)
                if date in all_momentum:
                    cached_momentum = all_momentum[date]

            # Calculate portfolio totals using cached data
            total_value = 0
            momentum_scores = []
            valid_positions = 0
            holdings = []

            for ticker, shares in default_portfolio.items():
                if ticker in cached_prices and ticker in cached_momentum:
                    price = cached_prices[ticker]
                    momentum = cached_momentum[ticker]

                    market_value = price * shares
                    total_value += market_value
                    momentum_scores.append(momentum['composite_score'])
                    valid_positions += 1

                    holdings.append({
                        'ticker': ticker,
                        'shares': shares,
                        'market_value': market_value,
                        'momentum_score': momentum['composite_score'],
                        'rating': momentum['rating']
                    })

            if valid_positions > 0:
                avg_momentum = sum(momentum_scores) / len(momentum_scores)

                # Calculate portfolio percentages
                for holding in holdings:
                    holding['portfolio_percent'] = (holding['market_value'] / total_value * 100) if total_value > 0 else 0

                portfolio_snapshot = {
                    'total_value': total_value,
                    'average_momentum_score': avg_momentum,
                    'number_of_positions': valid_positions,
                    'holdings': holdings
                }

                # Record the snapshot
                historical_service = HistoricalDataService()
                historical_service.record_portfolio_snapshot('default', portfolio_snapshot)

                print(f"📊 Recorded daily portfolio snapshot for {date}")
                print(f"   - Portfolio value: ${total_value:,.2f}")
                print(f"   - Average momentum: {avg_momentum:.1f}")
                print(f"   - Valid positions: {valid_positions}")

        except Exception as e:
            print(f"Warning: Failed to record daily portfolio snapshot: {e}")

    def get_historical_prices(self, ticker: str, days: int = 30) -> List[Tuple[str, float]]:
        """Get historical prices for a ticker from cache"""
        try:
            with open(self.daily_prices_file, 'r') as f:
                all_prices = json.load(f)

            # Get dates within the specified range
            end_date = datetime.strptime(self.get_last_trading_date(), '%Y-%m-%d')
            start_date = end_date - timedelta(days=days)

            historical_data = []
            for date_str, tickers_data in all_prices.items():
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if start_date <= date_obj <= end_date and ticker in tickers_data:
                    historical_data.append((date_str, tickers_data[ticker]))

            return sorted(historical_data, key=lambda x: x[0])

        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_historical_momentum(self, ticker: str, days: int = 30) -> List[Tuple[str, Dict]]:
        """Get historical momentum scores for a ticker from cache"""
        try:
            with open(self.daily_momentum_file, 'r') as f:
                all_momentum = json.load(f)

            # Get dates within the specified range
            end_date = datetime.strptime(self.get_last_trading_date(), '%Y-%m-%d')
            start_date = end_date - timedelta(days=days)

            historical_data = []
            for date_str, tickers_data in all_momentum.items():
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if start_date <= date_obj <= end_date and ticker in tickers_data:
                    historical_data.append((date_str, tickers_data[ticker]))

            return sorted(historical_data, key=lambda x: x[0])

        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_cache_stats(self) -> Dict:
        """Get statistics about the current cache"""
        try:
            with open(self.cache_metadata_file, 'r') as f:
                metadata = json.load(f)

            with open(self.daily_prices_file, 'r') as f:
                prices = json.load(f)

            with open(self.daily_momentum_file, 'r') as f:
                momentum = json.load(f)

            return {
                'is_current': self.is_cache_current(),
                'last_update': metadata.get('last_update_date', 'Never'),
                'cached_dates': len(prices),
                'cached_tickers': metadata.get('successful_tickers', 0),
                'oldest_date': min(prices.keys()) if prices else None,
                'newest_date': max(prices.keys()) if prices else None,
                'next_trading_date': self.get_last_trading_date()
            }

        except Exception as e:
            return {'error': str(e)}

    def force_refresh_cache(self, momentum_engine, tickers: List[str]) -> bool:
        """Force refresh the cache for today's data"""
        return self.update_daily_cache(tickers, momentum_engine, force_update=True)