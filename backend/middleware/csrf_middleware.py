"""
CSRF Middleware (Double-Submit Cookie Pattern)

Sets a signed CSRF cookie on every response and validates that state-changing
requests (POST/PUT/DELETE/PATCH) include a matching X-CSRF-Token header.

See backend/config/csrf_config.py for configuration and token signing.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config.csrf_config import (
    CSRF_ENABLED,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CSRF_EXEMPT_PATHS,
    generate_csrf_token,
    validate_csrf_token,
)
from ..config.cors_config import is_production

logger = logging.getLogger(__name__)

STATE_CHANGING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces double-submit cookie CSRF protection."""

    def __init__(self, app, enabled: bool | None = None):
        super().__init__(app)
        self._enabled = enabled if enabled is not None else CSRF_ENABLED

    async def dispatch(self, request: Request, call_next):
        # Validate CSRF for state-changing methods (before processing)
        if self._enabled and request.method in STATE_CHANGING_METHODS:
            path = request.url.path.rstrip("/")
            if path not in CSRF_EXEMPT_PATHS and path != "":
                error = self._validate_csrf(request)
                if error:
                    logger.warning(
                        "CSRF validation failed: %s (path=%s, method=%s)",
                        error, request.url.path, request.method,
                    )
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "CSRF_VALIDATION_FAILED",
                            "message": error,
                        },
                    )

        response: Response = await call_next(request)

        # Set CSRF cookie if not already present or invalid
        existing_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        if not existing_cookie or not validate_csrf_token(existing_cookie):
            token = generate_csrf_token()
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token,
                httponly=False,  # JS must be able to read this cookie
                samesite="lax",
                secure=is_production(),
                path="/",
            )

        return response

    @staticmethod
    def _validate_csrf(request: Request) -> str | None:
        """
        Validate CSRF token from header against cookie.

        Returns an error message string on failure, or None on success.
        """
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        if not cookie_token:
            return "Missing CSRF cookie"

        header_token = request.headers.get(CSRF_HEADER_NAME)
        if not header_token:
            return "Missing CSRF header"

        if cookie_token != header_token:
            return "CSRF token mismatch"

        if not validate_csrf_token(header_token):
            return "Invalid or expired CSRF token"

        return None
