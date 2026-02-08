#!/usr/bin/env python3
"""
Input Validation Test Script

Tests all validation functions to ensure they properly
validate and reject invalid inputs.

Usage:
    python test_validators.py
"""

import sys
from decimal import Decimal

# Import validators
from backend.validators.validators import (
    validate_ticker,
    validate_date_string,
    validate_date_range,
    sanitize_string,
    validate_portfolio_name,
    validate_email,
    validate_shares,
    validate_price,
    validate_percentage,
    validate_positive_int,
    validate_limit,
)


def test_ticker_validation():
    """Test ticker symbol validation"""
    print("\n" + "="*60)
    print("Testing Ticker Validation")
    print("="*60)

    # Valid tickers
    valid_tickers = ['AAPL', 'NVDA', 'BRK.A', 'BRK-B', 'GOOGL', 'TSM']
    for ticker in valid_tickers:
        result = validate_ticker(ticker)
        assert result == ticker.upper(), f"Failed: {ticker}"
        print(f"✓ Valid ticker: {ticker} -> {result}")

    # Invalid tickers
    invalid_tickers = [
        ('', 'empty'),
        ('A' * 11, 'too long'),
        ('ABC;DROP', 'SQL injection'),
        ('../etc', 'directory traversal'),
        ('ABC DEF', 'contains space'),
        ('ABC@DEF', 'invalid character'),
    ]

    for ticker, reason in invalid_tickers:
        try:
            validate_ticker(ticker)
            print(f"✗ FAILED: Should reject {reason}: {ticker}")
            return False
        except ValueError:
            print(f"✓ Correctly rejected {reason}: {ticker}")

    return True


def test_date_validation():
    """Test date validation"""
    print("\n" + "="*60)
    print("Testing Date Validation")
    print("="*60)

    # Valid dates
    valid_dates = [
        '2024-01-15',
        '2023-12-31',
        '2025-06-01',
    ]

    for date_str in valid_dates:
        result = validate_date_string(date_str)
        assert result == date_str
        print(f"✓ Valid date: {date_str}")

    # Invalid dates
    invalid_dates = [
        ('2024-13-01', 'invalid month'),
        ('2024-01-32', 'invalid day'),
        ('1899-01-01', 'too old'),
        ('2099-01-01', 'too far future'),
        ('not-a-date', 'invalid format'),
    ]

    for date_str, reason in invalid_dates:
        try:
            validate_date_string(date_str)
            print(f"✗ FAILED: Should reject {reason}: {date_str}")
            return False
        except ValueError:
            print(f"✓ Correctly rejected {reason}: {date_str}")

    # Test date range
    start, end = validate_date_range('2024-01-01', '2024-01-31')
    print(f"✓ Valid date range: {start} to {end}")

    # Test invalid range (start > end)
    try:
        validate_date_range('2024-12-31', '2024-01-01')
        print("✗ FAILED: Should reject end before start")
        return False
    except ValueError:
        print("✓ Correctly rejected end before start")

    return True


def test_string_sanitization():
    """Test string sanitization"""
    print("\n" + "="*60)
    print("Testing String Sanitization")
    print("="*60)

    # Test basic sanitization
    test_cases = [
        ('  Hello World  ', 'Hello World', 'trim whitespace'),
        ('Line1\nLine2', 'Line1 Line2', 'remove newlines'),
        ('<script>alert()</script>', 'alert()', 'strip HTML'),
        ('Test\x00Null', 'TestNull', 'remove null bytes'),
    ]

    for input_str, expected, description in test_cases:
        result = sanitize_string(input_str)
        assert result == expected, f"Failed: {description}"
        print(f"✓ {description}: '{input_str}' -> '{result}'")

    # Test length limit
    try:
        sanitize_string('A' * 1000, max_length=100)
        print("✗ FAILED: Should reject too long string")
        return False
    except ValueError:
        print("✓ Correctly rejected too long string")

    return True


def test_portfolio_name_validation():
    """Test portfolio name validation"""
    print("\n" + "="*60)
    print("Testing Portfolio Name Validation")
    print("="*60)

    # Valid names
    valid_names = [
        'My Portfolio',
        'Tech Stocks 2024',
        'Growth-Portfolio_1',
        'Conservative (Safe)',
    ]

    for name in valid_names:
        result = validate_portfolio_name(name)
        print(f"✓ Valid name: {name}")

    # Invalid names (after sanitization)
    invalid_names = [
        ('', 'empty'),
        ('Name; DROP TABLE', 'SQL injection attempt'),
        ('../../etc/passwd', 'path traversal'),
        ('Name@#$%^&*', 'invalid characters'),
    ]

    # Note: HTML tags and null bytes are stripped by sanitization before validation.
    # For example: '<script>alert()</script>' becomes 'alert()' which is valid.
    # This is intentional - we sanitize first, then validate the clean result.

    for name, reason in invalid_names:
        try:
            validate_portfolio_name(name)
            print(f"✗ FAILED: Should reject {reason}: {name}")
            return False
        except ValueError:
            print(f"✓ Correctly rejected {reason}")

    return True


def test_email_validation():
    """Test email validation"""
    print("\n" + "="*60)
    print("Testing Email Validation")
    print("="*60)

    # Valid emails
    valid_emails = [
        'user@example.com',
        'test.user@company.co.uk',
        'user+tag@example.com',
        'user_name@example.com',
    ]

    for email in valid_emails:
        result = validate_email(email)
        print(f"✓ Valid email: {email} -> {result}")

    # Invalid emails
    invalid_emails = [
        ('', 'empty'),
        ('not-an-email', 'missing @'),
        ('@example.com', 'missing local part'),
        ('user@', 'missing domain'),
        ('user@.com', 'invalid domain'),
        ('user..name@example.com', 'double dot'),
        ('.user@example.com', 'starts with dot'),
    ]

    for email, reason in invalid_emails:
        try:
            validate_email(email)
            print(f"✗ FAILED: Should reject {reason}: {email}")
            return False
        except ValueError:
            print(f"✓ Correctly rejected {reason}")

    return True


def test_financial_validation():
    """Test financial data validation"""
    print("\n" + "="*60)
    print("Testing Financial Data Validation")
    print("="*60)

    # Test shares validation
    valid_shares = [1, 10.5, 100, 0.1, 1000.123456]
    for shares in valid_shares:
        result = validate_shares(shares)
        assert isinstance(result, Decimal)
        print(f"✓ Valid shares: {shares} -> {result}")

    # Invalid shares
    invalid_shares = [
        (0, 'zero'),
        (-10, 'negative'),
        (1e10, 'too large'),
        (1.1234567, 'too many decimals'),
    ]

    for shares, reason in invalid_shares:
        try:
            validate_shares(shares)
            print(f"✗ FAILED: Should reject {reason}: {shares}")
            return False
        except ValueError:
            print(f"✓ Correctly rejected {reason}: {shares}")

    # Test price validation
    valid_prices = [0, 10.50, 100.25, 1000.1234]
    for price in valid_prices:
        result = validate_price(price)
        assert isinstance(result, Decimal)
        print(f"✓ Valid price: ${price}")

    # Invalid prices
    try:
        validate_price(-10)
        print("✗ FAILED: Should reject negative price")
        return False
    except ValueError:
        print("✓ Correctly rejected negative price")

    # Test percentage validation
    valid_percentages = [0, 50, 100, 25.5]
    for pct in valid_percentages:
        result = validate_percentage(pct)
        assert result == pct
        print(f"✓ Valid percentage: {pct}%")

    # Invalid percentages
    try:
        validate_percentage(150)
        print("✗ FAILED: Should reject > 100%")
        return False
    except ValueError:
        print("✓ Correctly rejected > 100%")

    return True


def test_integer_validation():
    """Test integer validation"""
    print("\n" + "="*60)
    print("Testing Integer Validation")
    print("="*60)

    # Valid integers
    valid_ints = [1, 10, 100, 1000]
    for val in valid_ints:
        result = validate_positive_int(val)
        assert result == val
        print(f"✓ Valid integer: {val}")

    # Invalid integers
    invalid_ints = [
        (0, 'zero'),
        (-5, 'negative'),
        (2**32, 'too large'),
    ]

    for val, reason in invalid_ints:
        try:
            validate_positive_int(val)
            print(f"✗ FAILED: Should reject {reason}: {val}")
            return False
        except ValueError:
            print(f"✓ Correctly rejected {reason}: {val}")

    # Test limit validation
    valid_limits = [1, 10, 50, 100]
    for limit in valid_limits:
        result = validate_limit(limit, max_limit=100)
        assert result == limit
        print(f"✓ Valid limit: {limit}")

    # Invalid limits
    try:
        validate_limit(1001, max_limit=1000)
        print("✗ FAILED: Should reject limit > max")
        return False
    except ValueError:
        print("✓ Correctly rejected limit > max")

    return True


def main():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("Input Validation Test Suite")
    print("="*60)

    tests = [
        ("Ticker Validation", test_ticker_validation),
        ("Date Validation", test_date_validation),
        ("String Sanitization", test_string_sanitization),
        ("Portfolio Name Validation", test_portfolio_name_validation),
        ("Email Validation", test_email_validation),
        ("Financial Data Validation", test_financial_validation),
        ("Integer Validation", test_integer_validation),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result is None or result is True:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print("Test Results")
    print("="*60)
    print(f"✓ Passed: {passed}/{len(tests)}")
    print(f"✗ Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 All validation tests passed!")
        print("\n✅ Input validation is working correctly:")
        print("  - Ticker symbols validated")
        print("  - Dates validated and sanitized")
        print("  - Strings sanitized (XSS/SQL injection protected)")
        print("  - Emails validated")
        print("  - Financial data validated")
        print("  - Integer limits enforced")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
