"""
Reusable OpenAPI Error Response Definitions (v1)

Pre-composed response dicts for use in FastAPI endpoint decorators.
Import the set that matches your endpoint's error profile and pass it
as ``responses=`` to ``@router.get()`` / ``@router.post()`` etc.
"""

from ...models.error_models import (
    ErrorResponse,
    ValidationErrorResponse,
    RateLimitErrorResponse,
    ServiceErrorResponse,
)

# --- Individual response definitions ----------------------------------------

VALIDATION_ERROR_RESPONSE = {
    400: {"model": ValidationErrorResponse, "description": "Validation error"},
}

NOT_FOUND_RESPONSE = {
    404: {"model": ErrorResponse, "description": "Resource not found"},
}

RATE_LIMIT_RESPONSE = {
    429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
}

INTERNAL_ERROR_RESPONSE = {
    500: {"model": ErrorResponse, "description": "Internal server error"},
}

EXTERNAL_SERVICE_RESPONSE = {
    502: {"model": ServiceErrorResponse, "description": "External service error"},
}

# --- Composed sets for common endpoint patterns -----------------------------

STANDARD_ERRORS = {**RATE_LIMIT_RESPONSE, **INTERNAL_ERROR_RESPONSE}

VALIDATION_ERRORS = {**VALIDATION_ERROR_RESPONSE, **STANDARD_ERRORS}

RESOURCE_ERRORS = {**NOT_FOUND_RESPONSE, **STANDARD_ERRORS}

MOMENTUM_ERRORS = {
    **VALIDATION_ERROR_RESPONSE,
    **RATE_LIMIT_RESPONSE,
    **INTERNAL_ERROR_RESPONSE,
    **EXTERNAL_SERVICE_RESPONSE,
}
