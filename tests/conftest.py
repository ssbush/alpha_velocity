"""
Pytest Configuration and Fixtures

Provides shared fixtures for testing AlphaVelocity components.
"""

import pytest
import os
import sys
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['LOG_LEVEL'] = 'ERROR'  # Reduce log noise in tests
os.environ['RATE_LIMIT_ENABLED'] = 'false'  # Disable rate limiting for tests
os.environ['CSRF_ENABLED'] = 'false'  # Disable CSRF for non-CSRF tests


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def sample_portfolio() -> Dict[str, int]:
    """Sample portfolio holdings for testing"""
    return {
        'NVDA': 10,
        'AAPL': 20,
        'MSFT': 15,
        'GOOGL': 12,
        'TSLA': 8,
    }


@pytest.fixture
def sample_ticker() -> str:
    """Sample ticker symbol for testing"""
    return 'AAPL'


@pytest.fixture
def sample_momentum_score() -> Dict[str, Any]:
    """Sample momentum score data"""
    return {
        'ticker': 'AAPL',
        'current_price': 175.50,
        'price_momentum_score': 8.5,
        'technical_momentum_score': 7.2,
        'fundamental_momentum_score': 6.8,
        'relative_momentum_score': 7.5,
        'overall_momentum_score': 7.5,
        'rating': 'Strong Buy',
        'components': {
            'sma_20': 170.25,
            'sma_50': 165.80,
            'rsi': 65.5,
            'volume_ratio': 1.2,
        }
    }


@pytest.fixture
def sample_stock_data():
    """Sample stock price data (yfinance format)"""
    import pandas as pd
    from datetime import datetime, timedelta

    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    data = {
        'Open': [100 + i * 0.5 for i in range(100)],
        'High': [102 + i * 0.5 for i in range(100)],
        'Low': [98 + i * 0.5 for i in range(100)],
        'Close': [100 + i * 0.5 for i in range(100)],
        'Volume': [1000000 + i * 10000 for i in range(100)],
    }

    df = pd.DataFrame(data, index=dates)
    return df


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for authentication tests"""
    return {
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'TestPassword123',
        'first_name': 'Test',
        'last_name': 'User',
    }


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def mock_momentum_engine():
    """Mock MomentumEngine for testing"""
    from backend.services.momentum_engine import MomentumEngine

    engine = Mock(spec=MomentumEngine)

    # Mock calculate_momentum_score method
    engine.calculate_momentum_score.return_value = {
        'ticker': 'AAPL',
        'current_price': 175.50,
        'price_momentum_score': 8.5,
        'technical_momentum_score': 7.2,
        'fundamental_momentum_score': 6.8,
        'relative_momentum_score': 7.5,
        'overall_momentum_score': 7.5,
        'rating': 'Strong Buy',
    }

    # Mock get_cached_price method
    engine.get_cached_price.return_value = 175.50

    return engine


@pytest.fixture
def mock_portfolio_service():
    """Mock PortfolioService for testing"""
    from backend.services.portfolio_service import PortfolioService

    service = Mock(spec=PortfolioService)

    # Mock analyze_portfolio method
    import pandas as pd
    df = pd.DataFrame({
        'Ticker': ['AAPL', 'NVDA'],
        'Shares': [10, 5],
        'Price': [175.50, 450.25],
        'Market_Value': [1755.00, 2251.25],
        'Portfolio_%': [43.75, 56.25],
        'Momentum_Score': [7.5, 8.2],
        'Rating': ['Strong Buy', 'Strong Buy'],
        'Price_Momentum': [8.5, 9.0],
        'Technical_Momentum': [7.2, 8.0],
    })

    service.analyze_portfolio.return_value = (df, 4006.25, 7.85)

    return service


# ============================================================================
# API Fixtures
# ============================================================================

@pytest.fixture
def test_client():
    """FastAPI test client"""
    from fastapi.testclient import TestClient
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def authenticated_client(test_client, sample_user_data):
    """FastAPI test client with authentication"""
    # Register user
    response = test_client.post('/auth/register', json=sample_user_data)

    if response.status_code == 200:
        token = response.json()['token']['access_token']
        test_client.headers = {
            'Authorization': f'Bearer {token}'
        }

    return test_client


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None

    return session


# ============================================================================
# yfinance Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_yfinance(sample_stock_data):
    """Mock yfinance Ticker class"""
    with patch('yfinance.Ticker') as mock_ticker:
        # Create mock ticker instance
        ticker_instance = Mock()

        # Mock history method
        ticker_instance.history.return_value = sample_stock_data

        # Mock info property
        ticker_instance.info = {
            'currentPrice': 175.50,
            'fiftyDayAverage': 170.25,
            'twoHundredDayAverage': 165.80,
            'trailingPE': 28.5,
            'forwardPE': 25.2,
            'priceToBook': 12.5,
            'recommendationKey': 'buy',
            'targetMeanPrice': 185.00,
        }

        # Return ticker instance when Ticker is called
        mock_ticker.return_value = ticker_instance

        yield mock_ticker


# ============================================================================
# Validation Fixtures
# ============================================================================

@pytest.fixture
def valid_tickers():
    """List of valid ticker symbols for testing"""
    return ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'TSLA', 'BRK.A', 'BRK-B']


@pytest.fixture
def invalid_tickers():
    """List of invalid ticker symbols for testing"""
    return [
        ('', 'empty'),
        ('A' * 11, 'too long'),
        ('ABC;DROP', 'SQL injection'),
        ('../etc', 'directory traversal'),
        ('ABC DEF', 'contains space'),
        ('ABC@DEF', 'invalid character'),
    ]


@pytest.fixture
def valid_emails():
    """List of valid email addresses for testing"""
    return [
        'user@example.com',
        'test.user@company.co.uk',
        'user+tag@example.com',
        'user_name@example.com',
    ]


@pytest.fixture
def invalid_emails():
    """List of invalid email addresses for testing"""
    return [
        ('', 'empty'),
        ('not-an-email', 'missing @'),
        ('@example.com', 'missing local'),
        ('user@', 'missing domain'),
        ('user@.com', 'invalid domain'),
    ]


# ============================================================================
# Utility Functions
# ============================================================================

@pytest.fixture
def assert_decimal():
    """Helper function to assert Decimal values"""
    def _assert_decimal(value, expected, places=2):
        """Assert decimal value with precision"""
        assert isinstance(value, Decimal), f"Expected Decimal, got {type(value)}"
        assert abs(value - Decimal(str(expected))) < Decimal(10) ** -places
    return _assert_decimal


@pytest.fixture
def assert_momentum_score():
    """Helper function to assert momentum score structure"""
    def _assert_momentum_score(score):
        """Assert momentum score has required fields"""
        required_fields = [
            'ticker',
            'current_price',
            'price_momentum_score',
            'technical_momentum_score',
            'overall_momentum_score',
            'rating',
        ]

        for field in required_fields:
            assert field in score, f"Missing required field: {field}"

        # Assert score ranges
        assert 0 <= score['overall_momentum_score'] <= 10, "Score should be 0-10"
        assert score['rating'] in ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell'], \
            f"Invalid rating: {score['rating']}"

    return _assert_momentum_score


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment after each test"""
    yield
    # Cleanup code here if needed
    pass


@pytest.fixture(scope='session')
def test_data_dir(tmp_path_factory):
    """Temporary directory for test data files"""
    return tmp_path_factory.mktemp('test_data')
