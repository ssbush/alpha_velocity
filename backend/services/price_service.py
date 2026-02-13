"""
Price Service for AlphaVelocity
Centralizes all price fetching logic through a single service layer.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import yfinance as yf

from ..utils.data_providers import DataProvider

logger = logging.getLogger(__name__)


class PriceService:
    """Centralized service for all stock price and data fetching."""

    def __init__(self, data_provider: Optional[DataProvider] = None) -> None:
        self.data_provider: DataProvider = data_provider or DataProvider()

    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """Fetch stock data (history + info) via DataProvider."""
        return self.data_provider.get_stock_data(ticker, period)

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get the current (last close) price for a single ticker."""
        try:
            hist, _ = self.data_provider.get_stock_data(ticker, '1d')
            if hist is not None and not hist.empty:
                return float(hist['Close'].iloc[-1])
            return None
        except Exception as e:
            logger.error("Error fetching current price for %s: %s", ticker, e)
            return None

    def get_current_prices(self, tickers: List[str]) -> Dict[str, Optional[float]]:
        """Get current prices for multiple tickers."""
        prices: Dict[str, Optional[float]] = {}
        for ticker in tickers:
            prices[ticker] = self.get_current_price(ticker)
        return prices

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
