"""
Security Headers Configuration for AlphaVelocity

Adds standard security response headers to harden the frontend against
clickjacking, XSS, MIME-sniffing, and protocol downgrade attacks.

Configuration is environment-based, following the same pattern as cors_config.py.
"""

import os
import logging
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .cors_config import is_production

logger = logging.getLogger(__name__)

# Default CSP policy — allows inline scripts/styles for the SPA frontend
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "img-src 'self' data:; "
    "font-src 'self' https://fonts.gstatic.com; "
    "connect-src 'self'"
)


def get_security_headers_settings() -> dict:
    """
    Read security header settings from environment variables with sensible defaults.

    Returns:
        Dictionary of header name -> value pairs.
        HSTS is only included when max_age > 0.
    """
    prod = is_production()

    # HSTS — disabled in dev (HTTP), auto-enabled in production
    default_max_age = "31536000" if prod else "0"
    try:
        hsts_max_age = int(os.getenv("SECURITY_HSTS_MAX_AGE", default_max_age))
    except ValueError:
        hsts_max_age = int(default_max_age)
        logger.warning("Invalid SECURITY_HSTS_MAX_AGE value, using default: %s", default_max_age)

    default_include_sub = "true" if prod else "false"
    hsts_include_subdomains = os.getenv(
        "SECURITY_HSTS_INCLUDE_SUBDOMAINS", default_include_sub
    ).lower() == "true"
    hsts_preload = os.getenv("SECURITY_HSTS_PRELOAD", "false").lower() == "true"

    # Build header map
    headers: dict[str, str] = {}

    # HSTS (only when max_age > 0)
    if hsts_max_age > 0:
        hsts_value = f"max-age={hsts_max_age}"
        if hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if hsts_preload:
            hsts_value += "; preload"
        headers["Strict-Transport-Security"] = hsts_value

    # X-Content-Type-Options — always nosniff, no env override needed
    headers["X-Content-Type-Options"] = "nosniff"

    # X-Frame-Options
    x_frame = os.getenv("SECURITY_X_FRAME_OPTIONS", "DENY")
    if x_frame:
        headers["X-Frame-Options"] = x_frame

    # Referrer-Policy
    referrer = os.getenv("SECURITY_REFERRER_POLICY", "strict-origin-when-cross-origin")
    if referrer:
        headers["Referrer-Policy"] = referrer

    # Content-Security-Policy
    csp = os.getenv("SECURITY_CSP", DEFAULT_CSP)
    if csp:
        headers["Content-Security-Policy"] = csp

    # Permissions-Policy
    permissions = os.getenv(
        "SECURITY_PERMISSIONS_POLICY", "camera=(), microphone=(), geolocation=()"
    )
    if permissions:
        headers["Permissions-Policy"] = permissions

    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to every response."""

    def __init__(self, app, headers: dict[str, str] | None = None):
        super().__init__(app)
        self.headers = headers or get_security_headers_settings()

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for name, value in self.headers.items():
            # Skip headers that already exist (allows per-route overrides)
            if name.lower() not in {k.lower() for k in response.headers.keys()}:
                response.headers[name] = value
        return response


def setup_security_headers(app: FastAPI) -> None:
    """
    Configure and add the security headers middleware to the app.

    Args:
        app: FastAPI application instance
    """
    headers = get_security_headers_settings()

    logger.info(
        "Security headers configured: %s",
        ", ".join(headers.keys()),
    )

    app.add_middleware(SecurityHeadersMiddleware, headers=headers)
    logger.info("Security headers middleware added successfully")
