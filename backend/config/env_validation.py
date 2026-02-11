"""
Startup Environment Variable Validation

Centralized validation of critical environment variables, called early
in application startup. In production, fails fast on critical
misconfigurations. In development, warns but continues.

Does NOT re-validate things already enforced elsewhere:
- SECRET_KEY: enforced in auth.py (crashes in production if missing)
- CORS_ORIGINS: enforced in cors_config.py (blocks wildcard in production)
"""

import os
import logging

logger = logging.getLogger(__name__)

VALID_ENVIRONMENTS = {"development", "staging", "production", "test"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
DEFAULT_DB_PASSWORDS = {"alphavelocity", "alphavelocity_secure_password", "password", ""}


def validate_environment() -> list[str]:
    """
    Validate critical environment variables at startup.

    Returns list of warning messages (empty = all good).
    Raises RuntimeError in production for critical issues.
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    is_production = env == "production"

    warnings: list[str] = []
    errors: list[str] = []

    _check_environment_value(env, warnings)
    _check_integer_vars(warnings)
    _check_log_level(warnings)
    _check_production_secrets(env, warnings, errors)

    for w in warnings:
        logger.warning(w)

    if errors and is_production:
        for e in errors:
            logger.error(e)
        raise RuntimeError(
            "Environment validation failed in production:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    if warnings or errors:
        logger.info(
            "Environment validation complete: %d warning(s)", len(warnings) + len(errors)
        )
    else:
        logger.info("Environment validation passed")

    return warnings + errors


def _check_environment_value(env: str, warnings: list[str]) -> None:
    """Validate ENVIRONMENT is a known value."""
    if env not in VALID_ENVIRONMENTS:
        warnings.append(
            f"ENVIRONMENT={env!r} is not a recognized value. "
            f"Expected one of: {', '.join(sorted(VALID_ENVIRONMENTS))}"
        )


def _check_integer_vars(warnings: list[str]) -> None:
    """Validate integer environment variables parse correctly and are in valid ranges."""
    int_vars = {
        "CORS_MAX_AGE": {"min": 0},
        "CSRF_TOKEN_EXPIRY_HOURS": {"min": 1},
        "MAX_FAILED_LOGIN_ATTEMPTS": {"min": 1},
        "LOCKOUT_DURATION_MINUTES": {"min": 0},
        "DB_PORT": {"min": 1, "max": 65535},
    }

    for var_name, constraints in int_vars.items():
        raw = os.getenv(var_name)
        if raw is None:
            continue

        try:
            value = int(raw)
        except ValueError:
            warnings.append(f"{var_name}={raw!r} is not a valid integer")
            continue

        min_val = constraints.get("min")
        max_val = constraints.get("max")

        if min_val is not None and value < min_val:
            warnings.append(
                f"{var_name}={value} is below minimum ({min_val})"
            )
        if max_val is not None and value > max_val:
            warnings.append(
                f"{var_name}={value} is above maximum ({max_val})"
            )


def _check_log_level(warnings: list[str]) -> None:
    """Validate LOG_LEVEL is a valid Python log level."""
    raw = os.getenv("LOG_LEVEL")
    if raw is None:
        return

    if raw.upper() not in VALID_LOG_LEVELS:
        warnings.append(
            f"LOG_LEVEL={raw!r} is not a valid log level. "
            f"Expected one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
        )


def _check_production_secrets(
    env: str, warnings: list[str], errors: list[str]
) -> None:
    """Check database credentials in production."""
    is_production = env == "production"

    # Only check DB vars if any DB env var is set (app can run without database)
    db_vars_set = any(
        os.getenv(v) is not None
        for v in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    )
    if not db_vars_set:
        return

    db_password = os.getenv("DB_PASSWORD", "")

    if is_production and db_password in DEFAULT_DB_PASSWORDS:
        errors.append(
            "DB_PASSWORD is set to a default value — "
            "this is a security risk in production"
        )
    elif not is_production and db_password in DEFAULT_DB_PASSWORDS:
        warnings.append("DB_PASSWORD is using a default value")

    db_host = os.getenv("DB_HOST", "localhost")
    if is_production and db_host == "localhost":
        warnings.append(
            "DB_HOST=localhost in production — "
            "this is likely incorrect for a deployed environment"
        )
