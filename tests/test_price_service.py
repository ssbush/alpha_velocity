"""Tests for PriceService — centralized price fetching."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from backend.services.price_service import PriceService, get_price_service, set_price_service


@pytest.fixture
def price_service():
    return PriceService()


@pytest.fixture
def sample_hist_df():
    """Create a sample historical DataFrame."""
    return pd.DataFrame(
        {'Close': [100.0, 101.5, 102.0], 'Volume': [1000, 1100, 1200]},
        index=pd.date_range('2026-01-10', periods=3, freq='D')
    )


@pytest.fixture
def sample_info():
    return {'sector': 'Technology', 'forwardPE': 25.0, 'shortName': 'Test Corp'}


class TestGetStockData:
    """Tests for get_stock_data (delegates to DataProvider)."""

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_delegates_to_data_provider(self, mock_yf, price_service, sample_hist_df, sample_info):
        mock_yf.return_value = (sample_hist_df, sample_info)
        hist, info = price_service.get_stock_data('NVDA', '1y')
        assert hist is not None
        assert len(hist) == 3
        assert info['sector'] == 'Technology'
        mock_yf.assert_called_once_with('NVDA', '1y')

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_returns_none_on_provider_error(self, mock_yf, price_service):
        mock_yf.return_value = (None, None)
        hist, info = price_service.get_stock_data('INVALID')
        assert hist is None
        assert info is None


class TestGetCurrentPrice:
    """Tests for get_current_price."""

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_returns_float(self, mock_yf, price_service, sample_hist_df):
        mock_yf.return_value = (sample_hist_df, {})
        price = price_service.get_current_price('NVDA')
        assert price == 102.0
        assert isinstance(price, float)

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_returns_none_on_empty_df(self, mock_yf, price_service):
        mock_yf.return_value = (pd.DataFrame(), {})
        price = price_service.get_current_price('NVDA')
        assert price is None

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_returns_none_on_error(self, mock_yf, price_service):
        mock_yf.side_effect = Exception("Network error")
        price = price_service.get_current_price('NVDA')
        assert price is None


class TestGetCurrentPrices:
    """Tests for get_current_prices (batch)."""

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_batch_prices(self, mock_yf, price_service, sample_hist_df):
        mock_yf.return_value = (sample_hist_df, {})
        prices = price_service.get_current_prices(['NVDA', 'AAPL'])
        assert prices['NVDA'] == 102.0
        assert prices['AAPL'] == 102.0
        assert mock_yf.call_count == 2


class TestGetHistoryByDateRange:
    """Tests for get_history_by_date_range."""

    @patch('backend.services.price_service.yf')
    def test_returns_dataframe(self, mock_yf, price_service, sample_hist_df):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = sample_hist_df
        mock_yf.Ticker.return_value = mock_ticker

        result = price_service.get_history_by_date_range('NVDA', '2026-01-10', '2026-01-13')
        assert result is not None
        assert len(result) == 3
        mock_yf.Ticker.assert_called_once_with('NVDA')

    @patch('backend.services.price_service.yf')
    def test_returns_none_on_empty(self, mock_yf, price_service):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        result = price_service.get_history_by_date_range('NVDA', '2026-01-10', '2026-01-13')
        assert result is None

    @patch('backend.services.price_service.yf')
    def test_returns_none_on_error(self, mock_yf, price_service):
        mock_yf.Ticker.side_effect = Exception("API error")

        result = price_service.get_history_by_date_range('NVDA', '2026-01-10', '2026-01-13')
        assert result is None


class TestGetStockInfo:
    """Tests for get_stock_info."""

    @patch('backend.services.price_service.yf')
    def test_returns_info_dict(self, mock_yf, price_service, sample_info):
        mock_ticker = MagicMock()
        mock_ticker.info = sample_info
        mock_yf.Ticker.return_value = mock_ticker

        result = price_service.get_stock_info('NVDA')
        assert result == sample_info
        assert result['sector'] == 'Technology'

    @patch('backend.services.price_service.yf')
    def test_returns_none_on_error(self, mock_yf, price_service):
        mock_yf.Ticker.side_effect = Exception("API error")

        result = price_service.get_stock_info('NVDA')
        assert result is None


class TestDownloadDailyPrices:
    """Tests for download_daily_prices."""

    @patch('backend.services.price_service.yf')
    def test_returns_dataframe(self, mock_yf, price_service, sample_hist_df):
        mock_yf.download.return_value = sample_hist_df

        result = price_service.download_daily_prices('NVDA', '2026-01-10', '2026-01-13')
        assert result is not None
        assert len(result) == 3
        mock_yf.download.assert_called_once_with(
            'NVDA', start='2026-01-10', end='2026-01-13',
            interval='1d', auto_adjust=True, progress=False
        )

    @patch('backend.services.price_service.yf')
    def test_returns_none_on_empty(self, mock_yf, price_service):
        mock_yf.download.return_value = pd.DataFrame()

        result = price_service.download_daily_prices('NVDA', '2026-01-10', '2026-01-13')
        assert result is None

    @patch('backend.services.price_service.yf')
    def test_returns_none_on_error(self, mock_yf, price_service):
        mock_yf.download.side_effect = Exception("Download error")

        result = price_service.download_daily_prices('NVDA', '2026-01-10', '2026-01-13')
        assert result is None


class TestSingleton:
    """Tests for get_price_service / set_price_service."""

    def test_set_and_get(self):
        original = get_price_service()
        try:
            custom = PriceService()
            set_price_service(custom)
            assert get_price_service() is custom
        finally:
            # Restore original to avoid polluting other tests
            set_price_service(original)

    def test_get_creates_default_if_none(self):
        import backend.services.price_service as mod
        old = mod._price_service
        try:
            mod._price_service = None
            result = get_price_service()
            assert result is not None
            assert isinstance(result, PriceService)
        finally:
            mod._price_service = old
