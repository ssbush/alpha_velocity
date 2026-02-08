"""
Exception Handlers for FastAPI

Converts exceptions to standardized error responses.
"""

import logging
import traceback
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from slowapi.errors import RateLimitExceeded

from .exceptions import AlphaVelocityException
from .models.error_models import (
    ErrorResponse,
    ErrorDetail,
    ValidationErrorResponse,
    RateLimitErrorResponse,
    ErrorResponseBuilder
)

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    """Extract or generate request ID."""
    return request.headers.get("X-Request-ID", f"req_{id(request)}")


async def alphavelocity_exception_handler(
    request: Request,
    exc: AlphaVelocityException
) -> JSONResponse:
    """
    Handle custom AlphaVelocity exceptions.

    Args:
        request: FastAPI request
        exc: AlphaVelocityException instance

    Returns:
        JSONResponse with standardized error
    """
    request_id = get_request_id(request)

    logger.warning(
        f"AlphaVelocity exception: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )

    error_response = ErrorResponseBuilder.build(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=str(request.url.path),
        request_id=request_id,
        details=exc.details
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts Pydantic validation errors to standardized format.

    Args:
        request: FastAPI request
        exc: Validation error

    Returns:
        JSONResponse with validation errors
    """
    request_id = get_request_id(request)

    # Convert Pydantic errors to ErrorDetail format
    validation_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        validation_errors.append(
            ErrorDetail(
                field=field,
                message=error["msg"],
                type=error["type"]
            )
        )

    logger.warning(
        f"Validation error: {len(validation_errors)} errors",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "errors": [e.model_dump() for e in validation_errors]
        }
    )

    error_response = ErrorResponseBuilder.build_validation_error(
        message="Request validation failed",
        validation_errors=validation_errors,
        path=str(request.url.path),
        request_id=request_id
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump()
    )


async def rate_limit_exception_handler(
    request: Request,
    exc: RateLimitExceeded
) -> JSONResponse:
    """
    Handle rate limit exceeded errors.

    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse with rate limit error
    """
    request_id = get_request_id(request)

    # Extract retry_after from exception if available
    retry_after = None
    if hasattr(exc, 'retry_after'):
        retry_after = int(exc.retry_after)

    # Extract limit from exception detail
    limit = "Rate limit exceeded"
    if hasattr(exc, 'detail'):
        limit = exc.detail

    logger.warning(
        f"Rate limit exceeded: {limit}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "limit": limit,
            "retry_after": retry_after
        }
    )

    error_response = ErrorResponseBuilder.build_rate_limit_error(
        limit=limit,
        retry_after=retry_after,
        path=str(request.url.path),
        request_id=request_id
    )

    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_response.model_dump()
    )

    # Add Retry-After header
    if retry_after:
        response.headers["Retry-After"] = str(retry_after)

    return response


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Catches all unhandled exceptions and returns 500 error.

    Args:
        request: FastAPI request
        exc: Any exception

    Returns:
        JSONResponse with internal server error
    """
    request_id = get_request_id(request)

    # Log full traceback for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "exception_type": type(exc).__name__
        }
    )

    # Don't expose internal errors to users in production
    message = "An internal server error occurred"
    details = {"error_type": type(exc).__name__}

    # In development, include more details
    import os
    if os.getenv("ENVIRONMENT", "production") == "development":
        message = f"Internal error: {str(exc)}"
        details["traceback"] = traceback.format_exc()

    error_response = ErrorResponseBuilder.build(
        error_code="INTERNAL_ERROR",
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        path=str(request.url.path),
        request_id=request_id,
        details=details
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


async def http_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle FastAPI HTTPException.

    Args:
        request: FastAPI request
        exc: HTTPException

    Returns:
        JSONResponse with standardized error
    """
    request_id = get_request_id(request)

    # Extract status code and detail from HTTPException
    status_code = getattr(exc, 'status_code', 500)
    detail = getattr(exc, 'detail', 'HTTP exception occurred')

    # Map status code to error code
    error_code_map = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_ERROR",
        403: "AUTHORIZATION_ERROR",
        404: "RESOURCE_NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        502: "EXTERNAL_SERVICE_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }

    error_code = error_code_map.get(status_code, "INTERNAL_ERROR")

    logger.warning(
        f"HTTP exception: {status_code} - {detail}",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "status_code": status_code,
            "error_code": error_code
        }
    )

    error_response = ErrorResponseBuilder.build(
        error_code=error_code,
        message=detail,
        status_code=status_code,
        path=str(request.url.path),
        request_id=request_id
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    from fastapi.exceptions import HTTPException

    # Custom exceptions
    app.add_exception_handler(
        AlphaVelocityException,
        alphavelocity_exception_handler
    )

    # Validation errors
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler
    )

    app.add_exception_handler(
        PydanticValidationError,
        validation_exception_handler
    )

    # Rate limiting
    app.add_exception_handler(
        RateLimitExceeded,
        rate_limit_exception_handler
    )

    # HTTP exceptions
    app.add_exception_handler(
        HTTPException,
        http_exception_handler
    )

    # Catch-all for unexpected errors
    app.add_exception_handler(
        Exception,
        generic_exception_handler
    )

    logger.info("Exception handlers registered successfully")
