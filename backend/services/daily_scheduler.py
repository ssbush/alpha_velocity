"""
Daily Scheduler for AlphaVelocity
Handles scheduled daily cache updates after market close.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import List
import pytz

logger = logging.getLogger(__name__)

from .daily_cache_service import DailyCacheService


class DailyScheduler:
    """Scheduler for daily cache updates"""

    def __init__(self, momentum_engine, portfolio_tickers: List[str], price_service=None, db_config=None):
        self.momentum_engine = momentum_engine
        self.portfolio_tickers = portfolio_tickers
        self.cache_service = DailyCacheService(price_service=price_service)
        self.db_config = db_config
        self.is_running = False
        self.scheduler_thread = None

        # Trading timezone
        self.trading_tz = pytz.timezone('US/Eastern')

        # Schedule daily updates
        self.setup_schedule()

    def setup_schedule(self):
        """Setup the daily update schedule"""
        logger.info("Daily cache scheduler initialized — will check for updates every hour during trading days")

    def run_daily_update(self):
        """Run the daily cache update"""
        try:
            logger.info("Starting daily cache update at %s", datetime.now())

            # Update cache with latest data
            success = self.cache_service.update_daily_cache(
                tickers=self.portfolio_tickers,
                momentum_engine=self.momentum_engine
            )

            if success:
                logger.info("Daily cache update completed successfully")
            else:
                logger.error("Daily cache update failed")

        except Exception as e:
            logger.error("Error during daily cache update: %s", e)

    def run_manual_update(self, force: bool = False):
        """Manually trigger cache update"""
        logger.info("Running manual cache update")

        return self.cache_service.update_daily_cache(
            tickers=self.portfolio_tickers,
            momentum_engine=self.momentum_engine,
            force_update=force
        )

    def start_scheduler(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True

        def run_schedule():
            logger.info("Daily scheduler started")
            while self.is_running:
                # Check if we should update cache
                if MarketHoursHelper.should_update_cache() and not self.cache_service.is_cache_current():
                    logger.info("Market closed — running daily cache update")
                    self.run_daily_update()

                time.sleep(3600)  # Check every hour

        self.scheduler_thread = Thread(target=run_schedule, daemon=True)
        self.scheduler_thread.start()

        logger.info("Daily scheduler is now running in background")

    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        logger.info("Daily scheduler stopped")

    def get_next_update_time(self):
        """Get the next scheduled update time"""
        if not self.is_running:
            return "Scheduler not running"

        # Next check will be within the next hour
        now = datetime.now(self.trading_tz)
        next_check = now + timedelta(hours=1)
        return next_check.strftime("%Y-%m-%d %H:%M:%S")

    def is_cache_current(self):
        """Check if cache is current"""
        return self.cache_service.is_cache_current()

    def get_scheduler_status(self):
        """Get scheduler status information"""
        cache_stats = self.cache_service.get_cache_stats()

        return {
            'is_running': self.is_running,
            'next_update': self.get_next_update_time(),
            'cache_current': self.is_cache_current(),
            'cache_stats': cache_stats,
            'total_tickers': len(self.portfolio_tickers)
        }


class MarketHoursHelper:
    """Helper for market hours and trading day logic"""

    @staticmethod
    def is_market_open():
        """Check if market is currently open"""
        now = datetime.now(pytz.timezone('US/Eastern'))

        # Check if it's a weekday
        if now.weekday() > 4:  # Saturday = 5, Sunday = 6
            return False

        # Check if it's within market hours (9:30 AM - 4:00 PM ET)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now <= market_close

    @staticmethod
    def is_trading_day():
        """Check if today is a trading day"""
        now = datetime.now(pytz.timezone('US/Eastern'))
        return now.weekday() < 5  # Monday = 0, Friday = 4

    @staticmethod
    def get_next_trading_day():
        """Get the next trading day"""
        now = datetime.now(pytz.timezone('US/Eastern'))
        next_day = now + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() > 4:
            next_day += timedelta(days=1)

        return next_day.strftime('%Y-%m-%d')

    @staticmethod
    def should_update_cache():
        """Determine if cache should be updated based on market hours"""
        now = datetime.now(pytz.timezone('US/Eastern'))

        # Update if it's after 4:00 PM ET on a trading day
        if MarketHoursHelper.is_trading_day():
            market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            return now >= market_close

        return False


# Global scheduler instance (will be initialized in main.py)
daily_scheduler: DailyScheduler = None


def initialize_scheduler(momentum_engine, portfolio_tickers: List[str], price_service=None, db_config=None):
    """Initialize the global scheduler"""
    global daily_scheduler
    daily_scheduler = DailyScheduler(momentum_engine, portfolio_tickers, price_service=price_service, db_config=db_config)
    return daily_scheduler


def get_scheduler() -> DailyScheduler:
    """Get the global scheduler instance"""
    global daily_scheduler
    if daily_scheduler is None:
        raise RuntimeError("Daily scheduler not initialized. Call initialize_scheduler() first.")
    return daily_scheduler