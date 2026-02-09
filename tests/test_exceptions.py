"""
Tests for Exception Hierarchy (backend/exceptions.py)

Covers all custom exception classes, their attributes,
inheritance chains, and the error code registry.
"""

import pytest

from backend.exceptions import (
    AlphaVelocityException,
    ValidationError,
    InvalidTickerError,
    InvalidParameterError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    TickerNotFoundError,
    PortfolioNotFoundError,
    ConflictError,
    DuplicateResourceError,
    RateLimitExceededError,
    ExternalServiceError,
    DatabaseError,
    CacheError,
    MarketDataError,
    ServiceUnavailableError,
    BusinessLogicError,
    InsufficientDataError,
    InvalidPortfolioError,
    ERROR_CODES,
    get_error_info,
)


class TestAlphaVelocityException:
    """Tests for the base exception class."""

    def test_base_attributes(self):
        exc = AlphaVelocityException("Something broke", "TEST_ERROR", 500, {"key": "val"})
        assert exc.message == "Something broke"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 500
        assert exc.details == {"key": "val"}

    def test_defaults(self):
        exc = AlphaVelocityException("fail")
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_str_is_message(self):
        exc = AlphaVelocityException("readable message")
        assert str(exc) == "readable message"


class TestValidationError:
    """Tests for ValidationError and subclasses."""

    def test_defaults(self):
        exc = ValidationError()
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.message == "Validation error"

    def test_custom_message(self):
        exc = ValidationError("Bad input", details={"field": "name"})
        assert exc.message == "Bad input"
        assert exc.details["field"] == "name"

    def test_invalid_parameter_error(self):
        exc = InvalidParameterError("limit", -1, "Must be positive")
        assert "limit" in exc.message
        assert "Must be positive" in exc.message
        assert exc.details["parameter"] == "limit"
        assert exc.details["value"] == "-1"
        assert exc.details["reason"] == "Must be positive"
        assert exc.status_code == 400


class TestAuthErrors:
    """Tests for authentication and authorization errors."""

    def test_authentication_error_defaults(self):
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"
        assert exc.message == "Authentication required"

    def test_authentication_error_custom_message(self):
        exc = AuthenticationError("Token expired")
        assert exc.message == "Token expired"

    def test_authorization_error_defaults(self):
        exc = AuthorizationError()
        assert exc.status_code == 403
        assert exc.error_code == "AUTHORIZATION_ERROR"
        assert exc.message == "Insufficient permissions"


class TestResourceNotFoundErrors:
    """Tests for resource not found errors."""

    def test_resource_not_found_auto_message(self):
        exc = ResourceNotFoundError("User", 42)
        assert exc.message == "User not found: 42"
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.details["resource_type"] == "User"
        assert exc.details["resource_id"] == "42"

    def test_resource_not_found_custom_message(self):
        exc = ResourceNotFoundError("Item", "abc", message="Custom not found msg")
        assert exc.message == "Custom not found msg"

    def test_portfolio_not_found(self):
        exc = PortfolioNotFoundError(99)
        assert "Portfolio" in exc.message
        assert "99" in exc.message
        assert exc.status_code == 404
        assert exc.details["resource_type"] == "Portfolio"


class TestConflictErrors:
    """Tests for conflict and duplicate resource errors."""

    def test_conflict_error(self):
        exc = ConflictError("Already exists", details={"id": 1})
        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"
        assert exc.message == "Already exists"
        assert exc.details["id"] == 1

    def test_duplicate_resource_error(self):
        exc = DuplicateResourceError("User", "john")
        assert exc.message == "User already exists: john"
        assert exc.status_code == 409
        assert exc.details["resource_type"] == "User"
        assert exc.details["identifier"] == "john"


class TestRateLimitError:
    """Tests for rate limit exceeded error."""

    def test_with_retry_after(self):
        exc = RateLimitExceededError("100/min", retry_after=30)
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert "100/min" in exc.message
        assert "30 seconds" in exc.message
        assert exc.details["limit"] == "100/min"
        assert exc.details["retry_after"] == 30

    def test_without_retry_after(self):
        exc = RateLimitExceededError("50/hour")
        assert "50/hour" in exc.message
        assert exc.details["retry_after"] is None

    def test_custom_message(self):
        exc = RateLimitExceededError("10/sec", message="Slow down please")
        assert exc.message == "Slow down please"


class TestExternalServiceErrors:
    """Tests for external service errors."""

    def test_external_service_error_defaults(self):
        exc = ExternalServiceError("Redis")
        assert exc.message == "External service error: Redis"
        assert exc.status_code == 502
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert exc.details["service"] == "Redis"

    def test_external_service_error_with_original(self):
        orig = ConnectionError("Connection refused")
        exc = ExternalServiceError("Redis", original_error=orig)
        assert exc.details["original_error"] == "Connection refused"

    def test_database_error(self):
        orig = Exception("table not found")
        exc = DatabaseError("SELECT query", original_error=orig)
        assert "SELECT query" in exc.message
        assert exc.details["service"] == "PostgreSQL"
        assert exc.details["original_error"] == "table not found"

    def test_cache_error(self):
        exc = CacheError("GET key")
        assert "GET key" in exc.message
        assert exc.details["service"] == "Redis"


class TestServiceUnavailableError:
    """Tests for service unavailable error."""

    def test_defaults(self):
        exc = ServiceUnavailableError()
        assert exc.status_code == 503
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert exc.message == "Service temporarily unavailable"

    def test_with_retry_after(self):
        exc = ServiceUnavailableError(retry_after=60)
        assert exc.details["retry_after"] == 60


class TestBusinessLogicErrors:
    """Tests for business logic errors."""

    def test_business_logic_error(self):
        exc = BusinessLogicError("Portfolio too large", details={"max": 100})
        assert exc.status_code == 422
        assert exc.error_code == "BUSINESS_LOGIC_ERROR"
        assert exc.message == "Portfolio too large"
        assert exc.details["max"] == 100

    def test_invalid_portfolio_error(self):
        exc = InvalidPortfolioError("too many tickers", details={"count": 200})
        assert exc.message == "Invalid portfolio: too many tickers"
        assert exc.status_code == 422
        assert exc.details["count"] == 200


class TestExceptionInheritance:
    """Tests for exception inheritance chain."""

    def test_all_inherit_from_base(self):
        exceptions = [
            ValidationError(),
            AuthenticationError(),
            AuthorizationError(),
            ResourceNotFoundError("X", 1),
            ConflictError("msg"),
            RateLimitExceededError("1/s"),
            ExternalServiceError("svc"),
            ServiceUnavailableError(),
            BusinessLogicError("msg"),
        ]
        for exc in exceptions:
            assert isinstance(exc, AlphaVelocityException)
            assert isinstance(exc, Exception)

    def test_subclass_chains(self):
        assert isinstance(InvalidTickerError("X"), ValidationError)
        assert isinstance(InvalidParameterError("p", 1, "r"), ValidationError)
        assert isinstance(TickerNotFoundError("X"), ResourceNotFoundError)
        assert isinstance(PortfolioNotFoundError(1), ResourceNotFoundError)
        assert isinstance(DuplicateResourceError("T", "id"), ConflictError)
        assert isinstance(DatabaseError("op"), ExternalServiceError)
        assert isinstance(CacheError("op"), ExternalServiceError)
        assert isinstance(MarketDataError("X"), ExternalServiceError)
        assert isinstance(InsufficientDataError("X", 10, 5), BusinessLogicError)
        assert isinstance(InvalidPortfolioError("r"), BusinessLogicError)


class TestErrorCodeRegistry:
    """Tests for ERROR_CODES dict and get_error_info()."""

    def test_all_expected_codes_present(self):
        expected = [
            "VALIDATION_ERROR",
            "AUTHENTICATION_ERROR",
            "AUTHORIZATION_ERROR",
            "RESOURCE_NOT_FOUND",
            "CONFLICT",
            "BUSINESS_LOGIC_ERROR",
            "RATE_LIMIT_EXCEEDED",
            "INTERNAL_ERROR",
            "EXTERNAL_SERVICE_ERROR",
            "SERVICE_UNAVAILABLE",
        ]
        for code in expected:
            assert code in ERROR_CODES

    def test_each_code_has_required_fields(self):
        for code, info in ERROR_CODES.items():
            assert "description" in info, f"{code} missing description"
            assert "status_code" in info, f"{code} missing status_code"
            assert "user_action" in info, f"{code} missing user_action"

    def test_get_error_info_known_code(self):
        info = get_error_info("VALIDATION_ERROR")
        assert info["status_code"] == 400

    def test_get_error_info_unknown_code(self):
        info = get_error_info("DOES_NOT_EXIST")
        assert info["status_code"] == 500  # falls back to INTERNAL_ERROR
