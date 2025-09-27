#!/usr/bin/env python3
"""
Backfill Historical Data Script for AlphaVelocity

This script rebuilds historical portfolio performance data using daily closing prices
for the past several weeks, replacing any existing intraday data.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from services.daily_cache_service import DailyCacheService
from services.momentum_engine import MomentumEngine
from services.historical_service import HistoricalDataService

# Default portfolio from main.py
DEFAULT_PORTFOLIO = {
    "NVDA": 7, "AVGO": 4, "MSFT": 2, "META": 1, "NOW": 1, "AAPL": 4, "GOOGL": 4,
    "VRT": 7, "MOD": 10, "BE": 30, "UI": 3,
    "DLR": 6, "SRVR": 58, "IRM": 10,
    "EWJ": 14, "EWT": 17,
    "SHY": 13,
    "XLI": 7,
    "MP": 16
}

def get_trading_dates(start_date: datetime, end_date: datetime):
    """Get list of trading dates (weekdays) between start and end date"""
    trading_dates = []
    current_date = start_date

    while current_date <= end_date:
        # Only include weekdays (Monday=0, Sunday=6)
        if current_date.weekday() < 5:
            trading_dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    return trading_dates

def backfill_portfolio_data(days_back: int = 21):
    """
    Backfill historical portfolio data for the specified number of days

    Args:
        days_back: Number of days back to fetch data (default 21 = ~3 weeks)
    """
    print(f"🔄 Starting historical data backfill for {days_back} days...")

    # Initialize services
    cache_service = DailyCacheService()
    momentum_engine = MomentumEngine()
    historical_service = HistoricalDataService()

    # Get date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back + 7)  # Add buffer for weekends

    trading_dates = get_trading_dates(start_date, end_date)
    print(f"📅 Found {len(trading_dates)} trading dates to process")

    # Get all tickers from default portfolio
    tickers = list(DEFAULT_PORTFOLIO.keys())
    print(f"📊 Processing {len(tickers)} tickers: {', '.join(tickers)}")

    successful_dates = 0

    for date_str in trading_dates:
        try:
            print(f"\n📈 Processing {date_str}...")

            # Fetch daily prices for this date
            daily_prices = cache_service.fetch_daily_prices(tickers, date_str)

            if not daily_prices:
                print(f"  ❌ No price data available for {date_str}")
                continue

            # Calculate momentum scores
            daily_momentum = cache_service.calculate_daily_momentum(tickers, momentum_engine, date_str)

            if not daily_momentum:
                print(f"  ❌ No momentum data calculated for {date_str}")
                continue

            # Calculate portfolio snapshot using cached data
            total_value = 0
            momentum_scores = []
            valid_positions = 0

            for ticker, shares in DEFAULT_PORTFOLIO.items():
                if ticker in daily_prices and ticker in daily_momentum:
                    price = daily_prices[ticker]
                    momentum = daily_momentum[ticker]

                    market_value = price * shares
                    total_value += market_value
                    momentum_scores.append(momentum['composite_score'])
                    valid_positions += 1

            if valid_positions == 0:
                print(f"  ❌ No valid positions for {date_str}")
                continue

            avg_momentum = sum(momentum_scores) / len(momentum_scores)

            # Create portfolio snapshot
            portfolio_snapshot = {
                'total_value': total_value,
                'average_momentum_score': avg_momentum,
                'number_of_positions': valid_positions,
                'timestamp': f"{date_str}T16:00:00"  # Market close time
            }

            # Record the snapshot directly to avoid duplicate checking
            historical_service._record_portfolio_value('default', f"{date_str}T16:00:00", portfolio_snapshot)

            print(f"  ✅ Recorded portfolio snapshot: ${total_value:,.2f}, momentum: {avg_momentum:.1f}")
            successful_dates += 1

        except Exception as e:
            print(f"  ❌ Error processing {date_str}: {e}")
            continue

    print(f"\n🎉 Backfill completed! Successfully processed {successful_dates}/{len(trading_dates)} trading dates")

    # Show final portfolio values summary
    try:
        with open(historical_service.portfolio_values_file, 'r') as f:
            data = json.load(f)

        default_values = data.get('default', [])
        print(f"📊 Total portfolio entries: {len(default_values)}")

        if default_values:
            latest = max(default_values, key=lambda x: x['timestamp'])
            oldest = min(default_values, key=lambda x: x['timestamp'])
            print(f"📅 Date range: {oldest['timestamp'][:10]} to {latest['timestamp'][:10]}")
            print(f"💰 Latest value: ${latest['total_value']:,.2f}")

    except Exception as e:
        print(f"⚠️  Could not read final summary: {e}")

if __name__ == "__main__":
    # Default to 3 weeks of data, but allow command line argument
    days_back = 21
    if len(sys.argv) > 1:
        try:
            days_back = int(sys.argv[1])
        except ValueError:
            print("Usage: python backfill_historical_data.py [days_back]")
            sys.exit(1)

    backfill_portfolio_data(days_back)