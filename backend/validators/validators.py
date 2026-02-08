"""
Input Validators and Sanitizers

Provides validation and sanitization functions for user inputs
to prevent injection attacks and ensure data integrity.
"""

import re
import logging
from typing import Optional, Any
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pydantic import validator

from ..exceptions import InvalidTickerError, ValidationError, InvalidParameterError

logger = logging.getLogger(__name__)


# ============================================================================
# TICKER VALIDATION
# ============================================================================

def validate_ticker(ticker: str, allow_empty: bool = False) -> str:
    """
    Validate stock ticker symbol

    Args:
        ticker: Ticker symbol to validate
        allow_empty: Whether to allow empty strings

    Returns:
        Validated and normalized ticker (uppercase, stripped)

    Raises:
        InvalidTickerError: If ticker is invalid

    Security:
        - Prevents SQL injection
        - Prevents command injection
        - Prevents directory traversal

    Valid formats:
        - 1-10 uppercase letters/numbers
        - May contain dots (.) or hyphens (-)
        - Examples: AAPL, BRK.A, BRK-B, GOOGL
    """
    if not ticker and allow_empty:
        return ""

    if not ticker or not isinstance(ticker, str):
        raise InvalidTickerError(
            ticker=str(ticker) if ticker else "empty",
            reason="Ticker symbol is required and must be a string"
        )

    # Strip whitespace and convert to uppercase
    ticker = ticker.strip().upper()

    # Check length
    if len(ticker) < 1 or len(ticker) > 10:
        raise InvalidTickerError(
            ticker=ticker,
            reason="Ticker symbol must be 1-10 characters"
        )

    # Validate format: letters, numbers, dots, hyphens only
    if not re.match(r'^[A-Z0-9.-]+$', ticker):
        raise InvalidTickerError(
            ticker=ticker,
            reason="Ticker symbol can only contain letters, numbers, dots, and hyphens"
        )

    # Prevent directory traversal attempts
    if '..' in ticker or '/' in ticker or '\\' in ticker:
        raise InvalidTickerError(
            ticker=ticker,
            reason="Invalid ticker symbol format"
        )

    # Blacklist dangerous patterns
    dangerous_patterns = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', '--', ';']
    ticker_upper = ticker.upper()
    for pattern in dangerous_patterns:
        if pattern in ticker_upper and len(ticker) > len(pattern):
            logger.warning(
                f"Suspicious ticker symbol rejected: {ticker}",
                extra={'ticker': ticker, 'pattern': pattern}
            )
            raise InvalidTickerError(
                ticker=ticker,
                reason="Invalid ticker symbol"
            )

    return ticker


# ============================================================================
# DATE VALIDATION
# ============================================================================

def validate_date_string(date_str: str, format: str = '%Y-%m-%d') -> str:
    """
    Validate date string format

    Args:
        date_str: Date string to validate
        format: Expected date format (default: YYYY-MM-DD)

    Returns:
        Validated date string

    Raises:
        ValueError: If date format is invalid
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date string is required")

    try:
        # Parse date to validate format
        parsed_date = datetime.strptime(date_str, format)

        # Check if date is reasonable (not too far in past or future)
        min_date = datetime(1900, 1, 1)
        max_date = datetime.now().replace(year=datetime.now().year + 10)

        if parsed_date < min_date or parsed_date > max_date:
            raise ValueError(
                f"Date must be between {min_date.year} and {max_date.year}"
            )

        return date_str

    except ValueError as e:
        raise ValueError(f"Invalid date format. Expected {format}: {str(e)}")


def validate_date_range(
    start_date: str,
    end_date: str,
    max_range_days: Optional[int] = None
) -> tuple[str, str]:
    """
    Validate date range

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        max_range_days: Maximum allowed range in days

    Returns:
        Tuple of (validated_start, validated_end)

    Raises:
        ValueError: If date range is invalid
    """
    start = validate_date_string(start_date)
    end = validate_date_string(end_date)

    start_dt = datetime.strptime(start, '%Y-%m-%d')
    end_dt = datetime.strptime(end, '%Y-%m-%d')

    if start_dt > end_dt:
        raise ValueError("Start date must be before or equal to end date")

    if max_range_days:
        range_days = (end_dt - start_dt).days
        if range_days > max_range_days:
            raise ValueError(
                f"Date range cannot exceed {max_range_days} days "
                f"(requested: {range_days} days)"
            )

    return start, end


# ============================================================================
# STRING VALIDATION & SANITIZATION
# ============================================================================

def sanitize_string(
    value: str,
    max_length: int = 255,
    allow_newlines: bool = False,
    strip_html: bool = True
) -> str:
    """
    Sanitize string input

    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        allow_newlines: Whether to allow newline characters
        strip_html: Whether to strip HTML tags

    Returns:
        Sanitized string

    Raises:
        ValueError: If string is invalid
    """
    if not isinstance(value, str):
        raise ValueError("Value must be a string")

    # Strip leading/trailing whitespace
    value = value.strip()

    # Check length
    if len(value) > max_length:
        raise ValueError(f"String cannot exceed {max_length} characters")

    # Remove newlines if not allowed
    if not allow_newlines:
        value = value.replace('\n', ' ').replace('\r', ' ')

    # Strip HTML tags if requested
    if strip_html:
        value = re.sub(r'<[^>]+>', '', value)

    # Remove null bytes (security risk)
    value = value.replace('\x00', '')

    # Prevent SQL injection patterns
    dangerous_patterns = [
        r'--',  # SQL comment
        r'/\*',  # SQL comment start
        r'\*/',  # SQL comment end
        r';.*?DROP',
        r';.*?DELETE',
        r';.*?INSERT',
        r';.*?UPDATE',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(
                f"Suspicious input pattern detected: {pattern}",
                extra={'value_preview': value[:50]}
            )
            # Don't reject, but log for monitoring
            # SQLAlchemy parameterization will handle it safely

    return value


def validate_portfolio_name(name: str) -> str:
    """
    Validate portfolio name

    Args:
        name: Portfolio name to validate

    Returns:
        Validated portfolio name

    Raises:
        ValueError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError("Portfolio name is required")

    # Sanitize and check length
    name = sanitize_string(name, max_length=100, allow_newlines=False)

    # Must have at least some content
    if len(name) < 1:
        raise ValueError("Portfolio name cannot be empty")

    # Validate characters (letters, numbers, spaces, basic punctuation)
    if not re.match(r'^[a-zA-Z0-9\s\-_.,()]+$', name):
        raise ValueError(
            "Portfolio name can only contain letters, numbers, spaces, "
            "and basic punctuation (- _ . , ( ))"
        )

    return name


def validate_description(description: str, max_length: int = 500) -> str:
    """
    Validate description field

    Args:
        description: Description to validate
        max_length: Maximum length

    Returns:
        Validated description

    Raises:
        ValueError: If description is invalid
    """
    if not description:
        return ""

    return sanitize_string(
        description,
        max_length=max_length,
        allow_newlines=True,
        strip_html=True
    )


# ============================================================================
# EMAIL VALIDATION
# ============================================================================

def validate_email(email: str) -> str:
    """
    Validate email address

    Args:
        email: Email address to validate

    Returns:
        Validated email (lowercase)

    Raises:
        ValueError: If email is invalid

    Note:
        Uses RFC 5322 simplified pattern
    """
    if not email or not isinstance(email, str):
        raise ValueError("Email is required")

    # Convert to lowercase
    email = email.strip().lower()

    # Check length
    if len(email) > 255:
        raise ValueError("Email address is too long")

    # Validate format using simplified RFC 5322 pattern
    email_pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'

    if not re.match(email_pattern, email):
        raise ValueError("Invalid email address format")

    # Additional checks
    if '..' in email or email.startswith('.') or email.endswith('.'):
        raise ValueError("Invalid email address format")

    # Check for common typos
    if '@.' in email or '.@' in email:
        raise ValueError("Invalid email address format")

    return email


# ============================================================================
# FINANCIAL DATA VALIDATION
# ============================================================================

def validate_shares(shares: float, allow_fractional: bool = True) -> Decimal:
    """
    Validate number of shares

    Args:
        shares: Number of shares
        allow_fractional: Whether to allow fractional shares

    Returns:
        Validated shares as Decimal

    Raises:
        ValueError: If shares value is invalid
    """
    try:
        shares_decimal = Decimal(str(shares))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Shares must be a valid number")

    # Must be positive
    if shares_decimal <= 0:
        raise ValueError("Shares must be greater than zero")

    # Check for fractional shares if not allowed
    if not allow_fractional and shares_decimal % 1 != 0:
        raise ValueError("Fractional shares are not allowed")

    # Reasonable upper limit (prevent overflow/errors)
    if shares_decimal > Decimal('1000000000'):  # 1 billion shares
        raise ValueError("Shares value is too large")

    # Check precision (max 6 decimal places)
    if abs(shares_decimal.as_tuple().exponent) > 6:
        raise ValueError("Shares cannot have more than 6 decimal places")

    return shares_decimal


def validate_price(price: float) -> Decimal:
    """
    Validate price value

    Args:
        price: Price to validate

    Returns:
        Validated price as Decimal

    Raises:
        ValueError: If price is invalid
    """
    try:
        price_decimal = Decimal(str(price))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Price must be a valid number")

    # Must be non-negative
    if price_decimal < 0:
        raise ValueError("Price cannot be negative")

    # Reasonable upper limit
    if price_decimal > Decimal('1000000'):  # $1M per share max
        raise ValueError("Price value is too large")

    # Check precision (max 4 decimal places for prices)
    if abs(price_decimal.as_tuple().exponent) > 4:
        raise ValueError("Price cannot have more than 4 decimal places")

    return price_decimal


def validate_percentage(percentage: float, min_val: float = 0, max_val: float = 100) -> float:
    """
    Validate percentage value

    Args:
        percentage: Percentage to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Validated percentage

    Raises:
        ValueError: If percentage is invalid
    """
    try:
        pct = float(percentage)
    except (ValueError, TypeError):
        raise ValueError("Percentage must be a valid number")

    if pct < min_val or pct > max_val:
        raise ValueError(f"Percentage must be between {min_val} and {max_val}")

    return pct


def validate_score(score: float, min_score: float = 0, max_score: float = 100) -> float:
    """
    Validate momentum/rating score

    Args:
        score: Score to validate
        min_score: Minimum valid score
        max_score: Maximum valid score

    Returns:
        Validated score

    Raises:
        ValueError: If score is out of range
    """
    try:
        score_val = float(score)
    except (ValueError, TypeError):
        raise ValueError("Score must be a valid number")

    if score_val < min_score or score_val > max_score:
        raise ValueError(f"Score must be between {min_score} and {max_score}")

    return score_val


# ============================================================================
# PYDANTIC VALIDATORS (for use in models)
# ============================================================================

class TickerValidator:
    """Pydantic validator for ticker symbols"""

    @classmethod
    def validate_ticker_field(cls, v: str) -> str:
        """Validate ticker field in Pydantic model"""
        return validate_ticker(v)


class DateValidator:
    """Pydantic validator for dates"""

    @classmethod
    def validate_date_field(cls, v: str) -> str:
        """Validate date field in Pydantic model"""
        return validate_date_string(v)


class FinancialValidator:
    """Pydantic validator for financial data"""

    @classmethod
    def validate_shares_field(cls, v: float) -> Decimal:
        """Validate shares field in Pydantic model"""
        return validate_shares(v)

    @classmethod
    def validate_price_field(cls, v: float) -> Decimal:
        """Validate price field in Pydantic model"""
        return validate_price(v)

    @classmethod
    def validate_percentage_field(cls, v: float) -> float:
        """Validate percentage field in Pydantic model"""
        return validate_percentage(v)


# ============================================================================
# INTEGER/ID VALIDATION
# ============================================================================

def validate_positive_int(value: int, field_name: str = "value") -> int:
    """
    Validate positive integer

    Args:
        value: Integer to validate
        field_name: Name of field (for error messages)

    Returns:
        Validated integer

    Raises:
        ValueError: If value is invalid
    """
    try:
        int_val = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be an integer")

    if int_val < 1:
        raise ValueError(f"{field_name} must be positive")

    if int_val > 2147483647:  # Max 32-bit integer
        raise ValueError(f"{field_name} is too large")

    return int_val


def validate_limit(limit: int, max_limit: int = 1000) -> int:
    """
    Validate pagination/query limit

    Args:
        limit: Limit value to validate
        max_limit: Maximum allowed limit

    Returns:
        Validated limit

    Raises:
        ValueError: If limit is invalid
    """
    try:
        limit_val = int(limit)
    except (ValueError, TypeError):
        raise ValueError("Limit must be an integer")

    if limit_val < 1:
        raise ValueError("Limit must be at least 1")

    if limit_val > max_limit:
        raise ValueError(f"Limit cannot exceed {max_limit}")

    return limit_val
