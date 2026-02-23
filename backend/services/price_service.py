"""
Price Service for AlphaVelocity
Centralizes all price fetching logic through a single service layer.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import yfinance as yf
from sqlalchemy import func

from ..utils.data_providers import DataProvider

logger = logging.getLogger(__name__)


class PriceService:
    """Centralized service for all stock price and data fetching.

    When db_config is set, price lookups check the price_history DB table
    first (most recent closing price) and only fall back to yfinance for
    tickers not yet in the database.
    """

    def __init__(self, data_provider: Optional[DataProvider] = None,
                 db_config=None) -> None:
        self.data_provider: DataProvider = data_provider or DataProvider()
        self.db_config = db_config

    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """Fetch stock data (history + info) via DataProvider."""
        return self.data_provider.get_stock_data(ticker, period)

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get the most recent closing price for a single ticker.

        Checks DB first (if available), falls back to yfinance.
        """
        if self.db_config is not None:
            db_prices = self._query_db_prices([ticker])
            if ticker in db_prices:
                return db_prices[ticker]

        try:
            hist, _ = self.data_provider.get_stock_data(ticker, '1d')
            if hist is not None and not hist.empty:
                return float(hist['Close'].iloc[-1])
            return None
        except Exception as e:
            logger.error("Error fetching current price for %s: %s", ticker, e)
            return None

    def get_current_prices(self, tickers: List[str]) -> Dict[str, Optional[float]]:
        """Get most recent closing prices for multiple tickers.

        Batch-queries DB first, then fetches remaining from yfinance.
        """
        prices: Dict[str, Optional[float]] = {}

        # Batch DB lookup
        db_prices = self._query_db_prices(tickers)
        remaining = []
        for ticker in tickers:
            if ticker in db_prices:
                prices[ticker] = db_prices[ticker]
            else:
                remaining.append(ticker)

        # yfinance fallback for missing tickers
        for ticker in remaining:
            try:
                hist, _ = self.data_provider.get_stock_data(ticker, '1d')
                if hist is not None and not hist.empty:
                    prices[ticker] = float(hist['Close'].iloc[-1])
                else:
                    prices[ticker] = None
            except Exception as e:
                logger.error("Error fetching current price for %s: %s", ticker, e)
                prices[ticker] = None

        return prices

    def _query_db_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Batch-fetch latest close prices from price_history DB table.

        Returns dict of ticker -> price for tickers found in DB.
        Tickers not in DB are simply omitted from the result.
        """
        if not tickers or self.db_config is None:
            return {}

        from ..models.database import PriceHistory, SecurityMaster

        try:
            with self.db_config.get_session_context() as session:
                subq = (
                    session.query(
                        PriceHistory.security_id,
                        func.max(PriceHistory.price_date).label("max_date"),
                    )
                    .join(SecurityMaster, PriceHistory.security_id == SecurityMaster.id)
                    .filter(SecurityMaster.ticker.in_(tickers))
                    .group_by(PriceHistory.security_id)
                    .subquery()
                )

                rows = (
                    session.query(SecurityMaster.ticker, PriceHistory.close_price)
                    .join(PriceHistory, PriceHistory.security_id == SecurityMaster.id)
                    .join(
                        subq,
                        (PriceHistory.security_id == subq.c.security_id)
                        & (PriceHistory.price_date == subq.c.max_date),
                    )
                    .all()
                )

                return {ticker: float(price) for ticker, price in rows}
        except Exception:
            logger.warning("Failed to batch-query DB prices", exc_info=True)
            return {}

    def get_history_by_date_range(self, ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """Fetch historical data for a date range.

        Args:
            ticker: Stock ticker symbol.
            start: Start date string (YYYY-MM-DD).
            end: End date string (YYYY-MM-DD).

        Returns:
            DataFrame of historical data, or None on error/empty.
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start, end=end)
            if hist.empty:
                return None
            return hist
        except Exception as e:
            logger.error("Error fetching history for %s (%s to %s): %s", ticker, start, end, e)
            return None

    def get_stock_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch stock fundamentals/info."""
        try:
            stock = yf.Ticker(ticker)
            return stock.info
        except Exception as e:
            logger.error("Error fetching info for %s: %s", ticker, e)
            return None

    def get_split_history(self, ticker: str) -> Optional[pd.DataFrame]:
        """Get stock split history for a ticker.

        Returns:
            DataFrame with DatetimeIndex and split ratios, or None on error/empty.
        """
        try:
            stock = yf.Ticker(ticker)
            splits = stock.splits
            if splits is None or splits.empty:
                return None
            return splits
        except Exception as e:
            logger.error("Error fetching split history for %s: %s", ticker, e)
            return None

    def download_daily_prices(self, ticker: str, start: str, end: str,
                              interval: str = '1d', auto_adjust: bool = True) -> Optional[pd.DataFrame]:
        """Download price data via yf.download().

        Args:
            ticker: Stock ticker symbol.
            start: Start date string (YYYY-MM-DD).
            end: End date string (YYYY-MM-DD).
            interval: Data interval (default '1d').
            auto_adjust: Whether to auto-adjust prices (default True).

        Returns:
            DataFrame of downloaded data, or None on error/empty.
        """
        try:
            data = yf.download(
                ticker,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=auto_adjust,
                progress=False
            )
            if data.empty:
                return None
            return data
        except Exception as e:
            logger.error("Error downloading prices for %s: %s", ticker, e)
            return None


# Module-level singleton
_price_service: Optional[PriceService] = None


def get_price_service() -> PriceService:
    """Get the global PriceService singleton (creates one if not set)."""
    global _price_service
    if _price_service is None:
        _price_service = PriceService()
    return _price_service


def set_price_service(instance: PriceService) -> None:
    """Set the global PriceService singleton (called at startup)."""
    global _price_service
    _price_service = instance
