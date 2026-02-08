"""
Error Response Models

Standardized error response models for consistent API error handling.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    type: Optional[str] = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """
    Standardized error response model.

    Used for all API errors to provide consistent error format.
    """

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp (ISO 8601)"
    )
    path: Optional[str] = Field(None, description="Request path that caused error")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Invalid ticker symbol: INVALID",
                "status_code": 400,
                "timestamp": "2024-01-25T12:34:56.789Z",
                "path": "/api/v1/momentum/INVALID",
                "request_id": "req_abc123",
                "details": {
                    "ticker": "INVALID",
                    "reason": "Ticker must be 1-5 uppercase letters"
                }
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """
    Validation error response with field-level errors.

    Used for input validation failures (400).
    """

    error: str = Field(default="VALIDATION_ERROR")
    validation_errors: List[ErrorDetail] = Field(
        default_factory=list,
        description="List of validation errors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "status_code": 400,
                "timestamp": "2024-01-25T12:34:56.789Z",
                "path": "/api/v1/portfolio/analyze",
                "validation_errors": [
                    {
                        "field": "tickers",
                        "message": "Field required",
                        "type": "missing"
                    },
                    {
                        "field": "shares",
                        "message": "Input should be greater than 0",
                        "type": "greater_than"
                    }
                ]
            }
        }


class RateLimitErrorResponse(ErrorResponse):
    """
    Rate limit error response.

    Used when rate limit is exceeded (429).
    """

    error: str = Field(default="RATE_LIMIT_EXCEEDED")
    retry_after: Optional[int] = Field(
        None,
        description="Seconds to wait before retrying"
    )
    limit: Optional[str] = Field(None, description="Rate limit that was exceeded")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded: 100 requests per minute",
                "status_code": 429,
                "timestamp": "2024-01-25T12:34:56.789Z",
                "retry_after": 45,
                "limit": "100/minute"
            }
        }


class ServiceErrorResponse(ErrorResponse):
    """
    External service error response.

    Used when external service fails (502, 503).
    """

    error: str = Field(default="EXTERNAL_SERVICE_ERROR")
    service: Optional[str] = Field(None, description="Service that failed")
    retry_after: Optional[int] = Field(
        None,
        description="Seconds to wait before retrying"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "EXTERNAL_SERVICE_ERROR",
                "message": "Failed to fetch market data for AAPL",
                "status_code": 502,
                "timestamp": "2024-01-25T12:34:56.789Z",
                "service": "yfinance",
                "details": {
                    "ticker": "AAPL",
                    "original_error": "Connection timeout"
                }
            }
        }


class ErrorResponseBuilder:
    """
    Builder for creating standardized error responses.

    Simplifies error response creation across the application.
    """

    @staticmethod
    def build(
        error_code: str,
        message: str,
        status_code: int,
        path: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse:
        """
        Build standard error response.

        Args:
            error_code: Error code (e.g., "VALIDATION_ERROR")
            message: Human-readable error message
            status_code: HTTP status code
            path: Request path
            request_id: Request identifier
            details: Additional error details

        Returns:
            ErrorResponse instance
        """
        return ErrorResponse(
            error=error_code,
            message=message,
            status_code=status_code,
            path=path,
            request_id=request_id,
            details=details
        )

    @staticmethod
    def build_validation_error(
        message: str,
        validation_errors: List[ErrorDetail],
        path: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> ValidationErrorResponse:
        """
        Build validation error response.

        Args:
            message: Error message
            validation_errors: List of field-level errors
            path: Request path
            request_id: Request identifier

        Returns:
            ValidationErrorResponse instance
        """
        return ValidationErrorResponse(
            message=message,
            status_code=400,
            path=path,
            request_id=request_id,
            validation_errors=validation_errors
        )

    @staticmethod
    def build_rate_limit_error(
        limit: str,
        retry_after: Optional[int] = None,
        path: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> RateLimitErrorResponse:
        """
        Build rate limit error response.

        Args:
            limit: Rate limit description
            retry_after: Seconds until retry
            path: Request path
            request_id: Request identifier

        Returns:
            RateLimitErrorResponse instance
        """
        message = f"Rate limit exceeded: {limit}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"

        return RateLimitErrorResponse(
            message=message,
            status_code=429,
            path=path,
            request_id=request_id,
            retry_after=retry_after,
            limit=limit
        )

    @staticmethod
    def build_service_error(
        service: str,
        message: str,
        status_code: int = 502,
        retry_after: Optional[int] = None,
        path: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ServiceErrorResponse:
        """
        Build service error response.

        Args:
            service: Service name
            message: Error message
            status_code: HTTP status code (502 or 503)
            retry_after: Seconds until retry
            path: Request path
            request_id: Request identifier
            details: Additional details

        Returns:
            ServiceErrorResponse instance
        """
        return ServiceErrorResponse(
            message=message,
            status_code=status_code,
            path=path,
            request_id=request_id,
            service=service,
            retry_after=retry_after,
            details=details
        )
