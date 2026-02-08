"""
Rate Limiting Configuration

Provides rate limiting for FastAPI endpoints to prevent:
- Brute force attacks on authentication
- API abuse and excessive usage
- DDoS attempts
- Resource exhaustion

Uses slowapi (FastAPI-compatible rate limiting library)
based on Flask-Limiter with Redis or in-memory storage.
"""

import os
import logging
from typing import Optional, Callable
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# Rate limit configuration from environment
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
RATE_LIMIT_STORAGE_URL = os.getenv('RATE_LIMIT_STORAGE_URL', 'memory://')  # or redis://localhost:6379
RATE_LIMIT_STRATEGY = os.getenv('RATE_LIMIT_STRATEGY', 'fixed-window')  # fixed-window or moving-window

# Default rate limits (can be overridden per endpoint)
DEFAULT_RATE_LIMIT = os.getenv('DEFAULT_RATE_LIMIT', '100/minute')
AUTH_RATE_LIMIT = os.getenv('AUTH_RATE_LIMIT', '5/minute')  # Stricter for auth
EXPENSIVE_RATE_LIMIT = os.getenv('EXPENSIVE_RATE_LIMIT', '10/minute')  # For heavy operations
AUTHENTICATED_RATE_LIMIT = os.getenv('AUTHENTICATED_RATE_LIMIT', '200/minute')  # Higher for authenticated users


def get_identifier(request: Request) -> str:
    """
    Get rate limit identifier for the request.

    Priority:
    1. User ID from JWT token (if authenticated)
    2. API key (if provided)
    3. IP address (fallback)

    This allows different limits for authenticated vs anonymous users.
    """
    # Try to get user from JWT token
    try:
        # Check if authorization header exists
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            # Extract user info from token (simplified - in production, decode JWT)
            # For now, we'll use a marker that this is an authenticated request
            # The actual user ID would come from token validation
            if hasattr(request.state, 'user_id'):
                return f"user:{request.state.user_id}"
    except Exception as e:
        logger.debug(f"Failed to extract user from token: {e}")

    # Try to get API key
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return f"apikey:{api_key[:16]}"  # Use first 16 chars

    # Fallback to IP address
    return get_remote_address(request)


def get_rate_limit_key(request: Request) -> str:
    """
    Generate a unique key for rate limiting based on:
    - User identifier (user ID, API key, or IP)
    - Endpoint path

    This allows different rate limits per endpoint per user.
    """
    identifier = get_identifier(request)
    path = request.url.path
    return f"{identifier}:{path}"


# Create limiter instance
limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=RATE_LIMIT_STORAGE_URL,
    strategy=RATE_LIMIT_STRATEGY,
    enabled=RATE_LIMIT_ENABLED,
    headers_enabled=True,  # Add X-RateLimit-* headers to responses
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a 429 Too Many Requests response with:
    - Clear error message
    - Retry-After header
    - Rate limit information
    """
    # Log rate limit violation
    identifier = get_identifier(request)
    path = request.url.path
    logger.warning(
        f"Rate limit exceeded for {identifier} on {path}",
        extra={
            'identifier': identifier,
            'path': path,
            'limit': exc.detail,
        }
    )

    # Create response
    response = JSONResponse(
        status_code=429,
        content={
            'error': 'rate_limit_exceeded',
            'message': 'Too many requests. Please slow down and try again later.',
            'detail': exc.detail,
            'retry_after_seconds': getattr(exc, 'retry_after', 60),
        }
    )

    # Add Retry-After header
    if hasattr(exc, 'retry_after'):
        response.headers['Retry-After'] = str(exc.retry_after)

    return response


def get_rate_limit_for_user(request: Request) -> str:
    """
    Determine the appropriate rate limit based on user authentication status.

    Authenticated users get higher limits than anonymous users.
    """
    # Check if user is authenticated
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') or request.headers.get('X-API-Key'):
        return AUTHENTICATED_RATE_LIMIT

    return DEFAULT_RATE_LIMIT


class RateLimitInfo:
    """
    Helper class to add rate limit information to responses.
    """

    @staticmethod
    def add_headers(response: Response, limit: str, remaining: int, reset: int) -> None:
        """
        Add rate limit headers to response.

        Headers added:
        - X-RateLimit-Limit: Maximum requests allowed
        - X-RateLimit-Remaining: Requests remaining in current window
        - X-RateLimit-Reset: Unix timestamp when the limit resets
        """
        response.headers['X-RateLimit-Limit'] = limit.split('/')[0]
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        response.headers['X-RateLimit-Reset'] = str(reset)


def create_rate_limit_exemption(exempt_ips: Optional[list] = None) -> Callable:
    """
    Create a function to check if a request should be exempt from rate limiting.

    Useful for:
    - Internal services
    - Health check endpoints
    - Admin IPs
    """
    exempt_ips = exempt_ips or []
    exempt_ips.extend(os.getenv('RATE_LIMIT_EXEMPT_IPS', '').split(','))
    exempt_ips = [ip.strip() for ip in exempt_ips if ip.strip()]

    def is_exempt(request: Request) -> bool:
        """Check if request should be exempt from rate limiting"""
        client_ip = get_remote_address(request)

        # Check if IP is in exempt list
        if client_ip in exempt_ips:
            logger.debug(f"Rate limit exemption for IP: {client_ip}")
            return True

        # Exempt health check endpoints
        if request.url.path in ['/', '/health', '/ping']:
            return True

        return False

    return is_exempt


# Rate limit presets for common use cases
class RateLimits:
    """
    Predefined rate limits for different endpoint types.

    Usage:
        @app.post("/login")
        @limiter.limit(RateLimits.AUTHENTICATION)
        async def login():
            ...
    """

    # Authentication endpoints (strict)
    AUTHENTICATION = AUTH_RATE_LIMIT  # 5/minute - prevent brute force

    # Public API endpoints (moderate)
    PUBLIC_API = DEFAULT_RATE_LIMIT  # 100/minute

    # Authenticated API endpoints (generous)
    AUTHENTICATED_API = AUTHENTICATED_RATE_LIMIT  # 200/minute

    # Expensive operations (strict)
    EXPENSIVE = EXPENSIVE_RATE_LIMIT  # 10/minute - resource intensive

    # Read operations (generous)
    READ_ONLY = '500/minute'  # High limit for GET requests

    # Write operations (moderate)
    WRITE = '50/minute'  # Lower limit for POST/PUT/DELETE

    # Search/query endpoints (moderate)
    SEARCH = '30/minute'  # Can be expensive

    # File upload (strict)
    UPLOAD = '10/minute'  # Bandwidth intensive

    # Bulk operations (very strict)
    BULK = '5/minute'  # Very resource intensive

    # Admin operations (strict)
    ADMIN = '10/minute'  # Administrative endpoints


def get_rate_limit_config() -> dict:
    """
    Get current rate limit configuration.

    Useful for debugging and monitoring.
    """
    return {
        'enabled': RATE_LIMIT_ENABLED,
        'storage_url': RATE_LIMIT_STORAGE_URL,
        'strategy': RATE_LIMIT_STRATEGY,
        'limits': {
            'default': DEFAULT_RATE_LIMIT,
            'authentication': AUTH_RATE_LIMIT,
            'expensive': EXPENSIVE_RATE_LIMIT,
            'authenticated': AUTHENTICATED_RATE_LIMIT,
        },
        'exemptions': {
            'paths': ['/', '/health', '/ping'],
            'ips': os.getenv('RATE_LIMIT_EXEMPT_IPS', '').split(','),
        }
    }


def log_rate_limit_config() -> None:
    """Log rate limit configuration on startup"""
    config = get_rate_limit_config()

    if config['enabled']:
        logger.info("Rate limiting ENABLED")
        logger.info(f"  Storage: {config['storage_url']}")
        logger.info(f"  Strategy: {config['strategy']}")
        logger.info(f"  Default limit: {config['limits']['default']}")
        logger.info(f"  Auth limit: {config['limits']['authentication']}")
        logger.info(f"  Authenticated limit: {config['limits']['authenticated']}")
        logger.info(f"  Expensive limit: {config['limits']['expensive']}")
    else:
        logger.warning("Rate limiting DISABLED - not recommended for production")
