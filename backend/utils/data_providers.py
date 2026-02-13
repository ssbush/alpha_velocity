import logging

import yfinance as yf
import pandas as pd
from typing import Tuple, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseDataProvider(ABC):
    """Abstract base class for data providers"""

    @abstractmethod
    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[dict]]:
        """Fetch stock data and info"""
        pass

class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance data provider (for development/testing)"""

    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[dict]]:
        """Fetch stock data from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            info = stock.info
            return hist, info
        except Exception as e:
            logger.error("Error fetching data for %s: %s", ticker, e)
            return None, None

class AlphaVantageProvider(BaseDataProvider):
    """Alpha Vantage data provider (for production)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # TODO: Implement Alpha Vantage API calls

    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[dict]]:
        """Fetch stock data from Alpha Vantage"""
        # TODO: Implement Alpha Vantage API calls
        # For now, fallback to Yahoo Finance
        fallback_provider = YahooFinanceProvider()
        return fallback_provider.get_stock_data(ticker, period)

# Default data provider factory
class DataProvider:
    """Data provider factory and wrapper"""

    def __init__(self, provider_type: str = 'yahoo', api_key: str = None):
        if provider_type == 'yahoo':
            self.provider = YahooFinanceProvider()
        elif provider_type == 'alphavantage':
            if not api_key:
                raise ValueError("Alpha Vantage requires an API key")
            self.provider = AlphaVantageProvider(api_key)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[dict]]:
        """Fetch stock data via configured provider"""
        return self.provider.get_stock_data(ticker, period)