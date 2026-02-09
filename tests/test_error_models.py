"""
Tests for Error Response Models (backend/models/error_models.py)

Covers ErrorDetail, ErrorResponse, ValidationErrorResponse,
RateLimitErrorResponse, ServiceErrorResponse, and ErrorResponseBuilder.
"""

import pytest
from datetime import datetime

from backend.models.error_models import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorResponse,
    RateLimitErrorResponse,
    ServiceErrorResponse,
    ErrorResponseBuilder,
)


class TestErrorDetail:
    """Tests for ErrorDetail model."""

    def test_creation_with_all_fields(self):
        detail = ErrorDetail(field="email", message="Invalid format", type="value_error")
        assert detail.field == "email"
        assert detail.message == "Invalid format"
        assert detail.type == "value_error"

    def test_optional_fields_default_none(self):
        detail = ErrorDetail(message="Required field")
        assert detail.field is None
        assert detail.type is None

    def test_serialization(self):
        detail = ErrorDetail(field="name", message="Too short", type="min_length")
        d = detail.model_dump()
        assert d["field"] == "name"
        assert d["message"] == "Too short"
        assert d["type"] == "min_length"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_creation(self):
        resp = ErrorResponse(
            error="VALIDATION_ERROR",
            message="Bad input",
            status_code=400,
            path="/api/v1/test",
            request_id="req_123",
            details={"field": "name"},
        )
        assert resp.error == "VALIDATION_ERROR"
        assert resp.message == "Bad input"
        assert resp.status_code == 400
        assert resp.path == "/api/v1/test"
        assert resp.request_id == "req_123"
        assert resp.details["field"] == "name"

    def test_timestamp_auto_generated(self):
        resp = ErrorResponse(error="TEST", message="msg", status_code=500)
        assert resp.timestamp is not None
        assert "T" in resp.timestamp  # ISO format

    def test_optional_fields_default_none(self):
        resp = ErrorResponse(error="TEST", message="msg", status_code=500)
        assert resp.path is None
        assert resp.request_id is None
        assert resp.details is None

    def test_model_dump_structure(self):
        resp = ErrorResponse(
            error="TEST_ERROR",
            message="Test message",
            status_code=400,
        )
        d = resp.model_dump()
        assert "error" in d
        assert "message" in d
        assert "status_code" in d
        assert "timestamp" in d
        assert d["error"] == "TEST_ERROR"


class TestValidationErrorResponse:
    """Tests for ValidationErrorResponse model."""

    def test_includes_validation_errors(self):
        errors = [
            ErrorDetail(field="email", message="Invalid", type="value_error"),
            ErrorDetail(field="name", message="Required", type="missing"),
        ]
        resp = ValidationErrorResponse(
            message="Validation failed",
            status_code=400,
            validation_errors=errors,
        )
        assert resp.error == "VALIDATION_ERROR"
        assert len(resp.validation_errors) == 2
        assert resp.validation_errors[0].field == "email"
        assert resp.validation_errors[1].field == "name"

    def test_default_empty_validation_errors(self):
        resp = ValidationErrorResponse(message="fail", status_code=400)
        assert resp.validation_errors == []

    def test_inherits_error_response(self):
        resp = ValidationErrorResponse(message="fail", status_code=400)
        assert isinstance(resp, ErrorResponse)


class TestRateLimitErrorResponse:
    """Tests for RateLimitErrorResponse model."""

    def test_includes_retry_after_and_limit(self):
        resp = RateLimitErrorResponse(
            message="Too many requests",
            status_code=429,
            retry_after=30,
            limit="100/minute",
        )
        assert resp.error == "RATE_LIMIT_EXCEEDED"
        assert resp.retry_after == 30
        assert resp.limit == "100/minute"

    def test_optional_fields(self):
        resp = RateLimitErrorResponse(message="Rate limited", status_code=429)
        assert resp.retry_after is None
        assert resp.limit is None

    def test_inherits_error_response(self):
        resp = RateLimitErrorResponse(message="msg", status_code=429)
        assert isinstance(resp, ErrorResponse)


class TestServiceErrorResponse:
    """Tests for ServiceErrorResponse model."""

    def test_includes_service_field(self):
        resp = ServiceErrorResponse(
            message="Database down",
            status_code=502,
            service="PostgreSQL",
            retry_after=60,
        )
        assert resp.error == "EXTERNAL_SERVICE_ERROR"
        assert resp.service == "PostgreSQL"
        assert resp.retry_after == 60

    def test_optional_fields(self):
        resp = ServiceErrorResponse(message="Error", status_code=503)
        assert resp.service is None
        assert resp.retry_after is None

    def test_inherits_error_response(self):
        resp = ServiceErrorResponse(message="msg", status_code=502)
        assert isinstance(resp, ErrorResponse)


class TestErrorResponseBuilder:
    """Tests for ErrorResponseBuilder factory methods."""

    def test_build(self):
        resp = ErrorResponseBuilder.build(
            error_code="TEST_ERROR",
            message="Something went wrong",
            status_code=500,
            path="/api/test",
            request_id="req_abc",
            details={"key": "value"},
        )
        assert isinstance(resp, ErrorResponse)
        assert resp.error == "TEST_ERROR"
        assert resp.message == "Something went wrong"
        assert resp.status_code == 500
        assert resp.path == "/api/test"

    def test_build_validation_error(self):
        errors = [ErrorDetail(field="ticker", message="Required", type="missing")]
        resp = ErrorResponseBuilder.build_validation_error(
            message="Validation failed",
            validation_errors=errors,
            path="/api/v1/momentum",
            request_id="req_xyz",
        )
        assert isinstance(resp, ValidationErrorResponse)
        assert resp.status_code == 400
        assert len(resp.validation_errors) == 1

    def test_build_rate_limit_error_with_retry(self):
        resp = ErrorResponseBuilder.build_rate_limit_error(
            limit="100/minute",
            retry_after=45,
            path="/api/v1/momentum/AAPL",
        )
        assert isinstance(resp, RateLimitErrorResponse)
        assert resp.status_code == 429
        assert resp.retry_after == 45
        assert resp.limit == "100/minute"
        assert "45 seconds" in resp.message

    def test_build_rate_limit_error_without_retry(self):
        resp = ErrorResponseBuilder.build_rate_limit_error(limit="50/hour")
        assert isinstance(resp, RateLimitErrorResponse)
        assert resp.retry_after is None
        assert "50/hour" in resp.message

    def test_build_service_error(self):
        resp = ErrorResponseBuilder.build_service_error(
            service="yfinance",
            message="Connection timeout",
            status_code=502,
            retry_after=10,
            path="/api/v1/momentum/AAPL",
            details={"ticker": "AAPL"},
        )
        assert isinstance(resp, ServiceErrorResponse)
        assert resp.service == "yfinance"
        assert resp.status_code == 502
        assert resp.retry_after == 10
        assert resp.details["ticker"] == "AAPL"

    def test_build_service_error_503(self):
        resp = ErrorResponseBuilder.build_service_error(
            service="database",
            message="DB unavailable",
            status_code=503,
        )
        assert resp.status_code == 503
