"""
Error Code Documentation Endpoint (v1)

Exposes the ERROR_CODES registry as a browsable API resource so that
consumers can programmatically discover every error code the API may return.
"""

from fastapi import APIRouter, Request
import logging

from ...exceptions import ERROR_CODES
from ...config.rate_limit_config import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()

# Realistic example responses keyed by error code.
_EXAMPLE_RESPONSES = {
    "VALIDATION_ERROR": {
        "error": "VALIDATION_ERROR",
        "message": "Invalid ticker symbol: INVALID",
        "status_code": 400,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "path": "/api/v1/momentum/INVALID",
        "details": {"ticker": "INVALID", "reason": "Ticker must be 1-5 uppercase letters"},
    },
    "AUTHENTICATION_ERROR": {
        "error": "AUTHENTICATION_ERROR",
        "message": "Authentication required",
        "status_code": 401,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "path": "/api/v1/user/profile",
    },
    "ACCOUNT_LOCKED": {
        "error": "ACCOUNT_LOCKED",
        "message": "Account is locked due to too many failed login attempts. Try again in 300 seconds.",
        "status_code": 403,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "path": "/api/v1/auth/login",
        "details": {"retry_after_seconds": 300},
    },
    "AUTHORIZATION_ERROR": {
        "error": "AUTHORIZATION_ERROR",
        "message": "Insufficient permissions",
        "status_code": 403,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "path": "/api/v1/cache/clear",
    },
    "RESOURCE_NOT_FOUND": {
        "error": "RESOURCE_NOT_FOUND",
        "message": "No data found for ticker: ZZZZZ",
        "status_code": 404,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "path": "/api/v1/momentum/ZZZZZ",
        "details": {"resource_type": "Ticker", "resource_id": "ZZZZZ"},
    },
    "CONFLICT": {
        "error": "CONFLICT",
        "message": "User already exists: alice@example.com",
        "status_code": 409,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "path": "/api/v1/auth/register",
        "details": {"resource_type": "User", "identifier": "alice@example.com"},
    },
    "BUSINESS_LOGIC_ERROR": {
        "error": "BUSINESS_LOGIC_ERROR",
        "message": "Insufficient data for NEWIPO: need 30 days, have 5",
        "status_code": 422,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "path": "/api/v1/momentum/NEWIPO",
        "details": {"ticker": "NEWIPO", "required_days": 30, "available_days": 5},
    },
    "RATE_LIMIT_EXCEEDED": {
        "error": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded: 100 requests per minute",
        "status_code": 429,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "retry_after": 45,
        "limit": "100/minute",
    },
    "INTERNAL_ERROR": {
        "error": "INTERNAL_ERROR",
        "message": "Internal server error",
        "status_code": 500,
        "timestamp": "2026-01-25T12:34:56.789Z",
    },
    "EXTERNAL_SERVICE_ERROR": {
        "error": "EXTERNAL_SERVICE_ERROR",
        "message": "Failed to fetch market data for AAPL",
        "status_code": 502,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "service": "yfinance",
        "details": {"ticker": "AAPL", "original_error": "Connection timeout"},
    },
    "SERVICE_UNAVAILABLE": {
        "error": "SERVICE_UNAVAILABLE",
        "message": "Service temporarily unavailable",
        "status_code": 503,
        "timestamp": "2026-01-25T12:34:56.789Z",
        "details": {"retry_after": 30},
    },
}


def _categorize(status_code: int) -> str:
    if 400 <= status_code < 500:
        return "client_error"
    return "server_error"


@router.get("/codes")
@limiter.limit(RateLimits.PUBLIC_API)
async def get_error_codes(request: Request):
    """
    List all error codes the API may return.

    Returns a complete catalog of machine-readable error codes with
    descriptions, HTTP status codes, suggested user actions, and
    example response bodies.  Useful for building robust API clients.

    **Returns:**
    - error_codes: Full details for every registered error code
    - by_status_code: Codes grouped into 4xx client / 5xx server buckets
    - total_codes: Number of registered error codes

    **Rate Limit:** 100 requests/minute (public)
    """
    error_codes = {}
    client_errors = []
    server_errors = []

    for code, info in ERROR_CODES.items():
        category = _categorize(info["status_code"])
        entry = {
            "code": code,
            "description": info["description"],
            "status_code": info["status_code"],
            "category": category,
            "user_action": info["user_action"],
            "example_response": _EXAMPLE_RESPONSES.get(code, {}),
        }
        error_codes[code] = entry

        if category == "client_error":
            client_errors.append(code)
        else:
            server_errors.append(code)

    return {
        "error_codes": error_codes,
        "by_status_code": {
            "4xx_client_errors": client_errors,
            "5xx_server_errors": server_errors,
        },
        "total_codes": len(error_codes),
    }
