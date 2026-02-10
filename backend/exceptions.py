"""
Custom Exceptions for AlphaVelocity API

Provides structured error handling with detailed error messages,
error codes, and proper HTTP status codes.
"""

from typing import Any, Dict, Optional


class AlphaVelocityException(Exception):
    """
    Base exception for AlphaVelocity.

    All custom exceptions inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# Input Validation Errors (400)
class ValidationError(AlphaVelocityException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class InvalidTickerError(ValidationError):
    """Raised when ticker symbol is invalid."""

    def __init__(self, ticker: str, reason: Optional[str] = None):
        message = f"Invalid ticker symbol: {ticker}"
        if reason:
            message += f" - {reason}"

        super().__init__(
            message=message,
            details={"ticker": ticker, "reason": reason}
        )


class InvalidParameterError(ValidationError):
    """Raised when request parameter is invalid."""

    def __init__(self, parameter: str, value: Any, reason: str):
        super().__init__(
            message=f"Invalid parameter '{parameter}': {reason}",
            details={
                "parameter": parameter,
                "value": str(value),
                "reason": reason
            }
        )


# Authentication & Authorization Errors (401, 403)
class AuthenticationError(AlphaVelocityException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AccountLockedError(AlphaVelocityException):
    """Raised when account is locked due to too many failed login attempts."""

    def __init__(self, retry_after_seconds: int):
        super().__init__(
            message=f"Account is locked due to too many failed login attempts. Try again in {retry_after_seconds} seconds.",
            error_code="ACCOUNT_LOCKED",
            status_code=403,
            details={"retry_after_seconds": retry_after_seconds}
        )
        self.retry_after_seconds = retry_after_seconds


class AuthorizationError(AlphaVelocityException):
    """Raised when user lacks permission."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403
        )


# Resource Not Found Errors (404)
class ResourceNotFoundError(AlphaVelocityException):
    """Raised when requested resource doesn't exist."""

    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        message: Optional[str] = None
    ):
        if not message:
            message = f"{resource_type} not found: {resource_id}"

        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={
                "resource_type": resource_type,
                "resource_id": str(resource_id)
            }
        )


class TickerNotFoundError(ResourceNotFoundError):
    """Raised when ticker data cannot be found."""

    def __init__(self, ticker: str):
        super().__init__(
            resource_type="Ticker",
            resource_id=ticker,
            message=f"No data found for ticker: {ticker}"
        )


class PortfolioNotFoundError(ResourceNotFoundError):
    """Raised when portfolio doesn't exist."""

    def __init__(self, portfolio_id: int):
        super().__init__(
            resource_type="Portfolio",
            resource_id=portfolio_id
        )


# Conflict Errors (409)
class ConflictError(AlphaVelocityException):
    """Raised when request conflicts with existing data."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details
        )


class DuplicateResourceError(ConflictError):
    """Raised when attempting to create duplicate resource."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} already exists: {identifier}",
            details={
                "resource_type": resource_type,
                "identifier": identifier
            }
        )


# Rate Limiting Errors (429)
class RateLimitExceededError(AlphaVelocityException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None
    ):
        if not message:
            message = f"Rate limit exceeded: {limit}"
            if retry_after:
                message += f". Retry after {retry_after} seconds"

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={
                "limit": limit,
                "retry_after": retry_after
            }
        )


# External Service Errors (502, 503)
class ExternalServiceError(AlphaVelocityException):
    """Raised when external service (API, database) fails."""

    def __init__(
        self,
        service: str,
        message: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        if not message:
            message = f"External service error: {service}"

        details = {"service": service}
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details=details
        )


class DatabaseError(ExternalServiceError):
    """Raised when database operation fails."""

    def __init__(
        self,
        operation: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service="PostgreSQL",
            message=f"Database operation failed: {operation}",
            original_error=original_error
        )


class CacheError(ExternalServiceError):
    """Raised when cache operation fails."""

    def __init__(
        self,
        operation: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service="Redis",
            message=f"Cache operation failed: {operation}",
            original_error=original_error
        )


class MarketDataError(ExternalServiceError):
    """Raised when market data provider fails."""

    def __init__(
        self,
        ticker: str,
        provider: str = "yfinance",
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service=provider,
            message=f"Failed to fetch market data for {ticker}",
            original_error=original_error
        )
        self.details["ticker"] = ticker


# Service Unavailable (503)
class ServiceUnavailableError(AlphaVelocityException):
    """Raised when service is temporarily unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None
    ):
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
            details={"retry_after": retry_after}
        )


# Business Logic Errors (422)
class BusinessLogicError(AlphaVelocityException):
    """Raised when business logic validation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            status_code=422,
            details=details
        )


class InsufficientDataError(BusinessLogicError):
    """Raised when insufficient data for calculation."""

    def __init__(self, ticker: str, required_days: int, available_days: int):
        super().__init__(
            message=(
                f"Insufficient data for {ticker}: "
                f"need {required_days} days, have {available_days}"
            ),
            details={
                "ticker": ticker,
                "required_days": required_days,
                "available_days": available_days
            }
        )


class InvalidPortfolioError(BusinessLogicError):
    """Raised when portfolio validation fails."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Invalid portfolio: {reason}",
            details=details
        )


# Error Code Registry
ERROR_CODES = {
    "VALIDATION_ERROR": {
        "description": "Input validation failed",
        "status_code": 400,
        "user_action": "Check request parameters and try again"
    },
    "AUTHENTICATION_ERROR": {
        "description": "Authentication required or failed",
        "status_code": 401,
        "user_action": "Provide valid credentials"
    },
    "ACCOUNT_LOCKED": {
        "description": "Account locked due to too many failed login attempts",
        "status_code": 403,
        "user_action": "Wait for the lockout period to expire and try again"
    },
    "AUTHORIZATION_ERROR": {
        "description": "Insufficient permissions",
        "status_code": 403,
        "user_action": "Contact administrator for access"
    },
    "RESOURCE_NOT_FOUND": {
        "description": "Requested resource not found",
        "status_code": 404,
        "user_action": "Verify resource identifier and try again"
    },
    "CONFLICT": {
        "description": "Request conflicts with existing data",
        "status_code": 409,
        "user_action": "Check for duplicates and try again"
    },
    "BUSINESS_LOGIC_ERROR": {
        "description": "Business logic validation failed",
        "status_code": 422,
        "user_action": "Review business rules and adjust request"
    },
    "RATE_LIMIT_EXCEEDED": {
        "description": "Too many requests",
        "status_code": 429,
        "user_action": "Wait and retry after specified time"
    },
    "INTERNAL_ERROR": {
        "description": "Internal server error",
        "status_code": 500,
        "user_action": "Contact support if error persists"
    },
    "EXTERNAL_SERVICE_ERROR": {
        "description": "External service failed",
        "status_code": 502,
        "user_action": "Retry request or contact support"
    },
    "SERVICE_UNAVAILABLE": {
        "description": "Service temporarily unavailable",
        "status_code": 503,
        "user_action": "Retry after specified time"
    }
}


def get_error_info(error_code: str) -> Dict[str, Any]:
    """
    Get detailed information about an error code.

    Args:
        error_code: Error code to look up

    Returns:
        Dictionary with error information
    """
    return ERROR_CODES.get(error_code, ERROR_CODES["INTERNAL_ERROR"])
