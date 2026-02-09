"""
Tests for Validators (backend/validators/validators.py)

Extends coverage for date validation, string sanitization,
portfolio name validation, and numeric validators not covered
by test_validators_pytest.py.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from backend.validators.validators import (
    validate_date_string,
    validate_date_range,
    sanitize_string,
    validate_portfolio_name,
    validate_description,
    validate_email,
    validate_score,
    validate_positive_int,
    validate_limit,
    validate_shares,
    validate_price,
    validate_percentage,
)


# ============================================================================
# Date Validation
# ============================================================================


class TestValidateDateString:
    """Tests for validate_date_string()."""

    def test_accepts_valid_date(self):
        result = validate_date_string("2024-06-15")
        assert result == "2024-06-15"

    def test_rejects_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_string("15-06-2024")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Date string is required"):
            validate_date_string("")

    def test_rejects_none(self):
        with pytest.raises(ValueError, match="Date string is required"):
            validate_date_string(None)

    def test_rejects_date_too_far_in_past(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_string("1899-01-01")

    def test_accepts_boundary_year_1900(self):
        result = validate_date_string("1900-01-01")
        assert result == "1900-01-01"

    def test_rejects_nonsense_string(self):
        with pytest.raises(ValueError):
            validate_date_string("not-a-date")


class TestValidateDateRange:
    """Tests for validate_date_range()."""

    def test_accepts_valid_range(self):
        start, end = validate_date_range("2024-01-01", "2024-06-30")
        assert start == "2024-01-01"
        assert end == "2024-06-30"

    def test_rejects_start_after_end(self):
        with pytest.raises(ValueError, match="Start date must be before"):
            validate_date_range("2024-06-30", "2024-01-01")

    def test_rejects_range_exceeding_max(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            validate_date_range("2024-01-01", "2024-12-31", max_range_days=30)

    def test_accepts_same_start_end(self):
        start, end = validate_date_range("2024-06-15", "2024-06-15")
        assert start == end

    def test_accepts_range_within_max(self):
        start, end = validate_date_range("2024-01-01", "2024-01-15", max_range_days=30)
        assert start == "2024-01-01"
        assert end == "2024-01-15"


# ============================================================================
# String Sanitization
# ============================================================================


class TestSanitizeString:
    """Tests for sanitize_string()."""

    def test_strips_whitespace(self):
        result = sanitize_string("  hello  ")
        assert result == "hello"

    def test_enforces_max_length(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            sanitize_string("a" * 300, max_length=255)

    def test_removes_newlines_when_not_allowed(self):
        result = sanitize_string("line1\nline2\rline3", allow_newlines=False)
        assert "\n" not in result
        assert "\r" not in result
        assert "line1" in result

    def test_allows_newlines_when_permitted(self):
        result = sanitize_string("line1\nline2", allow_newlines=True)
        assert "\n" in result

    def test_strips_html_tags(self):
        result = sanitize_string("<b>bold</b> text", strip_html=True)
        assert "<b>" not in result
        assert "bold" in result

    def test_removes_null_bytes(self):
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
        assert "helloworld" in result

    def test_rejects_non_string_input(self):
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_string(123)

    def test_preserves_html_when_disabled(self):
        result = sanitize_string("<b>text</b>", strip_html=False)
        assert "<b>" in result

    def test_custom_max_length(self):
        with pytest.raises(ValueError, match="cannot exceed 10"):
            sanitize_string("a" * 20, max_length=10)


# ============================================================================
# Portfolio Name / Description
# ============================================================================


class TestValidatePortfolioName:
    """Tests for validate_portfolio_name()."""

    def test_accepts_valid_names(self):
        assert validate_portfolio_name("My Portfolio") == "My Portfolio"
        assert validate_portfolio_name("Growth-2024") == "Growth-2024"
        assert validate_portfolio_name("Tech_Stocks (Q1)") == "Tech_Stocks (Q1)"

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError):
            validate_portfolio_name("")

    def test_rejects_none(self):
        with pytest.raises(ValueError):
            validate_portfolio_name(None)

    def test_rejects_invalid_characters(self):
        with pytest.raises(ValueError, match="can only contain"):
            validate_portfolio_name("Portfolio @#$%")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError):
            validate_portfolio_name("A" * 200)


class TestValidateDescription:
    """Tests for validate_description()."""

    def test_returns_empty_for_none(self):
        assert validate_description(None) == ""

    def test_returns_empty_for_empty(self):
        assert validate_description("") == ""

    def test_enforces_max_length(self):
        with pytest.raises(ValueError):
            validate_description("x" * 600, max_length=500)

    def test_accepts_valid_description(self):
        result = validate_description("A good portfolio for growth stocks")
        assert result == "A good portfolio for growth stocks"

    def test_allows_newlines(self):
        result = validate_description("Line 1\nLine 2")
        assert "\n" in result


# ============================================================================
# Score / Numeric Validators
# ============================================================================


class TestValidateScore:
    """Tests for validate_score()."""

    def test_accepts_valid_scores(self):
        assert validate_score(0) == 0.0
        assert validate_score(50) == 50.0
        assert validate_score(100) == 100.0

    def test_rejects_below_min(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_score(-1)

    def test_rejects_above_max(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_score(101)

    def test_custom_range(self):
        assert validate_score(5, min_score=1, max_score=10) == 5.0
        with pytest.raises(ValueError):
            validate_score(0, min_score=1, max_score=10)

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError):
            validate_score("abc")


class TestValidatePositiveInt:
    """Tests for validate_positive_int()."""

    def test_accepts_positive_integers(self):
        assert validate_positive_int(1) == 1
        assert validate_positive_int(100) == 100

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_int(0)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive_int(-5)

    def test_rejects_too_large(self):
        with pytest.raises(ValueError, match="too large"):
            validate_positive_int(2147483648)

    def test_custom_field_name_in_error(self):
        with pytest.raises(ValueError, match="user_id must be positive"):
            validate_positive_int(0, field_name="user_id")

    def test_rejects_non_integer(self):
        with pytest.raises(ValueError):
            validate_positive_int("abc")


class TestValidateLimit:
    """Tests for validate_limit()."""

    def test_accepts_valid_limits(self):
        assert validate_limit(1) == 1
        assert validate_limit(500) == 500
        assert validate_limit(1000) == 1000

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="at least 1"):
            validate_limit(0)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="at least 1"):
            validate_limit(-1)

    def test_rejects_exceeding_max(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            validate_limit(1001, max_limit=1000)

    def test_custom_max_limit(self):
        assert validate_limit(50, max_limit=50) == 50
        with pytest.raises(ValueError):
            validate_limit(51, max_limit=50)


# ============================================================================
# Email Validation
# ============================================================================


class TestValidateEmail:
    """Tests for validate_email()."""

    def test_accepts_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_normalizes_to_lowercase(self):
        assert validate_email("User@Example.COM") == "user@example.com"

    def test_rejects_missing_at(self):
        with pytest.raises(ValueError):
            validate_email("userexample.com")

    def test_rejects_double_dots(self):
        with pytest.raises(ValueError):
            validate_email("user@example..com")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validate_email("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            validate_email("a" * 250 + "@example.com")


# ============================================================================
# Financial Validators
# ============================================================================


class TestValidateShares:
    """Tests for validate_shares()."""

    def test_accepts_valid_shares(self):
        assert validate_shares(10) == Decimal("10")

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="greater than zero"):
            validate_shares(0)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="greater than zero"):
            validate_shares(-5)

    def test_rejects_too_large(self):
        with pytest.raises(ValueError, match="too large"):
            validate_shares(2000000000)

    def test_fractional_allowed(self):
        result = validate_shares(0.5, allow_fractional=True)
        assert result == Decimal("0.5")

    def test_fractional_disallowed(self):
        with pytest.raises(ValueError, match="Fractional"):
            validate_shares(0.5, allow_fractional=False)


class TestValidatePrice:
    """Tests for validate_price()."""

    def test_accepts_valid_price(self):
        assert validate_price(100.50) == Decimal("100.50")

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            validate_price(-10)

    def test_accepts_zero(self):
        assert validate_price(0) == Decimal("0")


class TestValidatePercentage:
    """Tests for validate_percentage()."""

    def test_accepts_valid_percentage(self):
        assert validate_percentage(50) == 50.0

    def test_rejects_below_min(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_percentage(-1)

    def test_rejects_above_max(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_percentage(101)
