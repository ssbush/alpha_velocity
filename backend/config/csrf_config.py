"""
CSRF Protection Configuration (Double-Submit Cookie Pattern)

The server sets a signed CSRF token as a cookie on every response.
The frontend reads this cookie and sends its value as an X-CSRF-Token
header on state-changing requests (POST/PUT/DELETE/PATCH). The middleware
validates that header and cookie match and that the token signature is valid.

Uses HMAC-SHA256 signing with the application SECRET_KEY.
"""

import os
import hmac
import hashlib
import logging
import secrets
import time

logger = logging.getLogger(__name__)

# Configuration from environment
CSRF_ENABLED = os.getenv('CSRF_ENABLED', 'true').lower() == 'true'
CSRF_COOKIE_NAME = os.getenv('CSRF_COOKIE_NAME', '_csrf_token')
CSRF_HEADER_NAME = os.getenv('CSRF_HEADER_NAME', 'X-CSRF-Token')

try:
    CSRF_TOKEN_EXPIRY_HOURS = int(os.getenv('CSRF_TOKEN_EXPIRY_HOURS', '24'))
except ValueError:
    CSRF_TOKEN_EXPIRY_HOURS = 24
    logger.warning("Invalid CSRF_TOKEN_EXPIRY_HOURS value, using default: 24")

# Paths exempt from CSRF validation (auth uses credentials/tokens, not sessions)
CSRF_EXEMPT_PATHS = {
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/",
}


def _get_secret_key() -> str:
    """Get the signing key — imported lazily to avoid circular imports."""
    from ..auth import SECRET_KEY
    return SECRET_KEY


def generate_csrf_token() -> str:
    """
    Generate a signed CSRF token.

    Format: {random_hex}.{timestamp}.{signature}
    The signature is HMAC-SHA256(secret, random_hex + "." + timestamp).
    """
    random_part = secrets.token_hex(32)
    timestamp = str(int(time.time()))
    payload = f"{random_part}.{timestamp}"
    signature = hmac.new(
        _get_secret_key().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{signature}"


def validate_csrf_token(token: str) -> bool:
    """
    Validate a CSRF token's signature and expiry.

    Returns True if the token is well-formed, correctly signed, and not expired.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return False

    random_part, timestamp_str, provided_sig = parts

    # Verify signature
    payload = f"{random_part}.{timestamp_str}"
    expected_sig = hmac.new(
        _get_secret_key().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        return False

    # Verify expiry
    try:
        token_time = int(timestamp_str)
    except ValueError:
        return False

    expiry_seconds = CSRF_TOKEN_EXPIRY_HOURS * 3600
    if time.time() - token_time > expiry_seconds:
        return False

    return True


def get_csrf_config() -> dict:
    """Get current CSRF configuration."""
    return {
        "enabled": CSRF_ENABLED,
        "cookie_name": CSRF_COOKIE_NAME,
        "header_name": CSRF_HEADER_NAME,
        "token_expiry_hours": CSRF_TOKEN_EXPIRY_HOURS,
        "exempt_paths": sorted(CSRF_EXEMPT_PATHS),
    }


def log_csrf_config() -> None:
    """Log CSRF configuration on startup."""
    config = get_csrf_config()

    if config["enabled"]:
        logger.info(
            "CSRF protection ENABLED — cookie=%s, header=%s, expiry=%dh",
            config["cookie_name"],
            config["header_name"],
            config["token_expiry_hours"],
        )
    else:
        logger.warning("CSRF protection DISABLED")
