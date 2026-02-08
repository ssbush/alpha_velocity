"""
Pytest-based Validation Tests

Tests input validation and sanitization functions.
"""

import pytest
from decimal import Decimal

pytestmark = pytest.mark.unit


class TestTickerValidation:
    """Test ticker symbol validation"""

    def test_valid_tickers(self, valid_tickers):
        """Test that valid ticker symbols are accepted"""
        from backend.validators.validators import validate_ticker

        for ticker in valid_tickers:
            result = validate_ticker(ticker)
            assert result == ticker.upper()

    def test_invalid_tickers(self, invalid_tickers):
        """Test that invalid ticker symbols are rejected"""
        from backend.validators.validators import validate_ticker
        from backend.exceptions import InvalidTickerError

        for ticker, reason in invalid_tickers:
            with pytest.raises((ValueError, InvalidTickerError)):
                validate_ticker(ticker)


class TestEmailValidation:
    """Test email validation"""

    def test_valid_emails(self, valid_emails):
        """Test that valid emails are accepted"""
        from backend.validators.validators import validate_email

        for email in valid_emails:
            result = validate_email(email)
            assert result == email.lower()

    def test_invalid_emails(self, invalid_emails):
        """Test that invalid emails are rejected"""
        from backend.validators.validators import validate_email

        for email, reason in invalid_emails:
            with pytest.raises(ValueError):
                validate_email(email)


class TestFinancialValidation:
    """Test financial data validation"""

    def test_validate_shares(self):
        """Test shares validation"""
        from backend.validators.validators import validate_shares

        # Valid shares
        assert validate_shares(10) == Decimal('10')
        assert validate_shares(10.5) == Decimal('10.5')

        # Invalid shares
        with pytest.raises(ValueError):
            validate_shares(0)

        with pytest.raises(ValueError):
            validate_shares(-10)

    def test_validate_price(self):
        """Test price validation"""
        from backend.validators.validators import validate_price

        # Valid prices
        assert validate_price(100.50) == Decimal('100.50')
        assert validate_price(0) == Decimal('0')

        # Invalid prices
        with pytest.raises(ValueError):
            validate_price(-10)

    def test_validate_percentage(self):
        """Test percentage validation"""
        from backend.validators.validators import validate_percentage

        # Valid percentages
        assert validate_percentage(50) == 50
        assert validate_percentage(0) == 0
        assert validate_percentage(100) == 100

        # Invalid percentages
        with pytest.raises(ValueError):
            validate_percentage(150)

        with pytest.raises(ValueError):
            validate_percentage(-10)
