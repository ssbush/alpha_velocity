"""
CORS Configuration for AlphaVelocity

Provides secure, environment-based CORS configuration for the API.
Prevents security vulnerabilities while allowing legitimate cross-origin requests.
"""

import os
import logging
from typing import List, Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def get_cors_origins() -> List[str]:
    """
    Get allowed CORS origins from environment variable

    Returns:
        List of allowed origin URLs

    Environment:
        CORS_ORIGINS: Comma-separated list of allowed origins
                     Example: "http://localhost:3000,https://app.example.com"

        If not set, defaults to localhost for development
    """
    # Get origins from environment
    origins_str = os.getenv('CORS_ORIGINS', '')

    if origins_str:
        # Parse comma-separated origins and strip whitespace
        origins = [origin.strip() for origin in origins_str.split(',') if origin.strip()]
        logger.info(f"CORS origins configured: {len(origins)} origins")
        logger.debug(f"CORS origins: {origins}")
        return origins

    # Default to localhost development origins if not configured
    default_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    ]

    logger.warning(
        "CORS_ORIGINS not configured - using default localhost origins. "
        "Set CORS_ORIGINS environment variable for production!"
    )

    return default_origins


def get_cors_settings() -> dict:
    """
    Get CORS middleware settings

    Returns:
        Dictionary of CORS configuration settings

    Environment Variables:
        CORS_ORIGINS: Allowed origins (comma-separated)
        CORS_ALLOW_CREDENTIALS: Allow credentials (default: true)
        CORS_ALLOW_METHODS: Allowed HTTP methods (default: *)
        CORS_ALLOW_HEADERS: Allowed headers (default: *)
        CORS_MAX_AGE: Preflight cache duration in seconds (default: 600)
    """
    # Get environment or use sensible defaults
    allow_credentials = os.getenv('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'

    # Get allowed methods
    methods_str = os.getenv('CORS_ALLOW_METHODS', '*')
    if methods_str == '*':
        allow_methods = ['*']
    else:
        allow_methods = [method.strip() for method in methods_str.split(',')]

    # Get allowed headers
    headers_str = os.getenv('CORS_ALLOW_HEADERS', '*')
    if headers_str == '*':
        allow_headers = ['*']
    else:
        allow_headers = [header.strip() for header in headers_str.split(',')]

    # Get max age for preflight cache
    try:
        max_age = int(os.getenv('CORS_MAX_AGE', '600'))
    except ValueError:
        max_age = 600
        logger.warning("Invalid CORS_MAX_AGE value, using default: 600")

    settings = {
        'allow_origins': get_cors_origins(),
        'allow_credentials': allow_credentials,
        'allow_methods': allow_methods,
        'allow_headers': allow_headers,
        'max_age': max_age,
    }

    # Log configuration (security-safe)
    logger.info(
        f"CORS configured - Origins: {len(settings['allow_origins'])}, "
        f"Credentials: {allow_credentials}, Methods: {methods_str}, "
        f"Headers: {headers_str}"
    )

    return settings


def is_production() -> bool:
    """
    Check if running in production environment

    Returns:
        True if production, False otherwise

    Environment:
        ENVIRONMENT: Set to 'production' for production mode
    """
    env = os.getenv('ENVIRONMENT', 'development').lower()
    return env in ('production', 'prod')


def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware for the FastAPI application

    Args:
        app: FastAPI application instance

    Security Notes:
        - In production, CORS_ORIGINS MUST be set to specific domains
        - Wildcard (*) origins are blocked in production
        - Credentials are enabled by default for authentication
        - Preflight requests are cached for 10 minutes by default

    Raises:
        ValueError: If running in production without proper CORS configuration
    """
    cors_settings = get_cors_settings()

    # Security check: Block wildcard origins in production
    if is_production():
        origins = cors_settings['allow_origins']

        # Check for wildcard
        if '*' in origins or not origins:
            error_msg = (
                "SECURITY ERROR: Wildcard CORS origins not allowed in production! "
                "Set CORS_ORIGINS environment variable to specific domains."
            )
            logger.critical(error_msg)
            raise ValueError(error_msg)

        # Validate origins format
        for origin in origins:
            if not origin.startswith(('http://', 'https://')):
                logger.error(f"Invalid CORS origin format: {origin}")
                raise ValueError(f"Invalid origin format: {origin}. Must start with http:// or https://")

        logger.info(f"Production CORS configured with {len(origins)} allowed origins")
    else:
        logger.info("Development CORS configured - using permissive settings")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_settings['allow_origins'],
        allow_credentials=cors_settings['allow_credentials'],
        allow_methods=cors_settings['allow_methods'],
        allow_headers=cors_settings['allow_headers'],
        max_age=cors_settings['max_age'],
    )

    logger.info("CORS middleware configured successfully")


def validate_origin(origin: str) -> bool:
    """
    Validate if an origin is allowed

    Args:
        origin: Origin URL to validate

    Returns:
        True if origin is allowed, False otherwise

    Usage:
        This can be used for additional origin validation in custom middleware
    """
    allowed_origins = get_cors_origins()

    # Check if origin is in allowed list
    if origin in allowed_origins:
        return True

    # Check for wildcard (only in development)
    if '*' in allowed_origins and not is_production():
        return True

    return False


# Export configuration for testing
def get_cors_config_info() -> dict:
    """
    Get CORS configuration information for debugging/testing

    Returns:
        Dictionary with CORS configuration details
    """
    return {
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'is_production': is_production(),
        'origins_count': len(get_cors_origins()),
        'origins': get_cors_origins() if not is_production() else ['<hidden in production>'],
        'allow_credentials': os.getenv('CORS_ALLOW_CREDENTIALS', 'true'),
        'allow_methods': os.getenv('CORS_ALLOW_METHODS', '*'),
        'allow_headers': os.getenv('CORS_ALLOW_HEADERS', '*'),
        'max_age': os.getenv('CORS_MAX_AGE', '600'),
    }
