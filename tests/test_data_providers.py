"""
Tests for Data Providers (backend/utils/data_providers.py)

Covers DataProvider factory, YahooFinanceProvider, AlphaVantageProvider.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.utils.data_providers import (
    DataProvider,
    YahooFinanceProvider,
    AlphaVantageProvider,
)


class TestDataProviderFactory:
    """Tests for DataProvider factory class."""

    def test_creates_yahoo_provider(self):
        dp = DataProvider(provider_type="yahoo")
        assert isinstance(dp.provider, YahooFinanceProvider)

    def test_creates_alphavantage_provider(self):
        dp = DataProvider(provider_type="alphavantage", api_key="test-key")
        assert isinstance(dp.provider, AlphaVantageProvider)

    def test_alphavantage_requires_key(self):
        with pytest.raises(ValueError, match="API key"):
            DataProvider(provider_type="alphavantage")

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            DataProvider(provider_type="bloomberg")


class TestAlphaVantageProvider:
    """Tests for AlphaVantageProvider."""

    def test_init_stores_key(self):
        provider = AlphaVantageProvider(api_key="my-key")
        assert provider.api_key == "my-key"


class TestYahooFinanceProvider:
    """Tests for YahooFinanceProvider."""

    def test_handles_error(self):
        provider = YahooFinanceProvider()
        with patch("backend.utils.data_providers.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")
            hist, info = provider.get_stock_data("AAPL")
            assert hist is None
            assert info is None
