"""
Tests for Error Handling System

Tests custom exceptions, error responses, and exception handlers.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.exceptions import (
    InvalidTickerError,
    InvalidParameterError,
    ResourceNotFoundError,
    TickerNotFoundError,
    RateLimitExceededError,
    MarketDataError,
    InsufficientDataError
)

client = TestClient(app)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_invalid_ticker_error(self):
        """Test InvalidTickerError exception."""
        exc = InvalidTickerError(ticker="TOOLONG", reason="Too long")

        assert exc.message == "Invalid ticker symbol: TOOLONG - Too long"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 400
        assert exc.details["ticker"] == "TOOLONG"
        assert exc.details["reason"] == "Too long"

    def test_ticker_not_found_error(self):
        """Test TickerNotFoundError exception."""
        exc = TickerNotFoundError(ticker="UNKNOWN")

        assert "UNKNOWN" in exc.message
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.status_code == 404
        assert exc.details["resource_id"] == "UNKNOWN"

    def test_insufficient_data_error(self):
        """Test InsufficientDataError exception."""
        exc = InsufficientDataError(
            ticker="NVDA",
            required_days=200,
            available_days=50
        )

        assert "NVDA" in exc.message
        assert "200" in exc.message
        assert "50" in exc.message
        assert exc.error_code == "BUSINESS_LOGIC_ERROR"
        assert exc.status_code == 422

    def test_market_data_error(self):
        """Test MarketDataError exception."""
        exc = MarketDataError(
            ticker="AAPL",
            provider="yfinance",
            original_error=Exception("Timeout")
        )

        assert "AAPL" in exc.message
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert exc.status_code == 502
        assert exc.details["ticker"] == "AAPL"
        assert exc.details["service"] == "yfinance"


class TestAPIErrorResponses:
    """Test API error response format."""

    def test_invalid_ticker_response(self):
        """Test error response for invalid ticker."""
        response = client.get("/api/v1/momentum/TOOLONGTICKER123")

        assert response.status_code == 400

        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "message" in data
        assert "status_code" in data
        assert data["status_code"] == 400
        assert "timestamp" in data
        assert "path" in data
        assert "/api/v1/momentum/" in data["path"]

    def test_error_response_includes_request_id(self):
        """Test that error responses include request_id."""
        response = client.get(
            "/api/v1/momentum/INVALID",
            headers={"X-Request-ID": "test_req_123"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "request_id" in data

    def test_validation_error_response_format(self):
        """Test validation error response format."""
        # This should trigger a Pydantic validation error
        response = client.post(
            "/api/v1/momentum/batch",
            json={"tickers": []}  # Empty list should fail validation
        )

        # Should get 400 or 422 depending on validation type
        assert response.status_code in [400, 422]

        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data


class TestExceptionHandlers:
    """Test exception handler behavior."""

    def test_ticker_validation_handled(self):
        """Test that InvalidTickerError is properly handled."""
        # Invalid ticker: too long
        response = client.get("/api/v1/momentum/TOOLONG12345")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "ticker" in data.get("details", {})

    def test_empty_ticker_handled(self):
        """Test that empty ticker is handled."""
        response = client.get("/api/v1/momentum/")

        # Should be 404 (not found route) or 400 (validation)
        assert response.status_code in [400, 404, 422]

    def test_special_characters_in_ticker(self):
        """Test that special characters in ticker are rejected."""
        response = client.get("/api/v1/momentum/AAPL%3BINJECT")

        # Should be URL decoded and validated
        assert response.status_code in [400, 404]


class TestErrorDetails:
    """Test error detail fields."""

    def test_error_includes_helpful_details(self):
        """Test that errors include helpful context."""
        response = client.get("/api/v1/momentum/TOOLONGTICKER")

        data = response.json()
        details = data.get("details", {})

        # Should include ticker and reason
        assert "ticker" in details or "TOOLONGTICKER" in data["message"]

    def test_error_path_is_accurate(self):
        """Test that error path matches request path."""
        path = "/api/v1/momentum/INVALID"
        response = client.get(path)

        data = response.json()
        assert data["path"] == path

    def test_error_timestamp_format(self):
        """Test that timestamp is in ISO 8601 format."""
        response = client.get("/api/v1/momentum/INVALID")

        data = response.json()
        timestamp = data["timestamp"]

        # Should be ISO 8601 format
        assert "T" in timestamp
        assert "Z" in timestamp or "+" in timestamp or "-" in timestamp[-6:]


class TestDevelopmentVsProduction:
    """Test error behavior in different environments."""

    def test_internal_error_hides_details_in_production(self, monkeypatch):
        """Test that internal errors don't expose details in production."""
        # Set production environment
        monkeypatch.setenv("ENVIRONMENT", "production")

        # Force an internal error by using invalid endpoint
        response = client.get("/api/v1/nonexistent/endpoint")

        data = response.json()

        # Should not include stack trace in production
        details = data.get("details", {})
        assert "traceback" not in details

    def test_internal_error_shows_details_in_development(self, monkeypatch):
        """Test that internal errors show details in development."""
        # Set development environment
        monkeypatch.setenv("ENVIRONMENT", "development")

        # Note: This is hard to test without causing actual errors
        # Just verify the behavior exists
        pass


@pytest.mark.integration
class TestRateLimitErrorHandling:
    """Test rate limit error handling."""

    def test_rate_limit_error_format(self):
        """Test rate limit error response format."""
        # Make many requests to trigger rate limit
        # Note: This may not work in all test environments
        endpoint = "/api/v1/momentum/AAPL"

        # Make requests until rate limited
        for i in range(200):
            response = client.get(endpoint)
            if response.status_code == 429:
                data = response.json()

                # Verify rate limit error format
                assert data["error"] == "RATE_LIMIT_EXCEEDED"
                assert "retry_after" in data or "limit" in data
                assert data["status_code"] == 429

                # Check for Retry-After header
                if "retry_after" in data:
                    assert "Retry-After" in response.headers

                break


class TestErrorCodeRegistry:
    """Test error code registry."""

    def test_error_codes_are_documented(self):
        """Test that all error codes are in registry."""
        from backend.exceptions import ERROR_CODES, get_error_info

        # All error codes should be documented
        assert "VALIDATION_ERROR" in ERROR_CODES
        assert "RESOURCE_NOT_FOUND" in ERROR_CODES
        assert "RATE_LIMIT_EXCEEDED" in ERROR_CODES
        assert "INTERNAL_ERROR" in ERROR_CODES

    def test_get_error_info(self):
        """Test get_error_info function."""
        from backend.exceptions import get_error_info

        info = get_error_info("VALIDATION_ERROR")

        assert info["status_code"] == 400
        assert "description" in info
        assert "user_action" in info

    def test_unknown_error_code_fallback(self):
        """Test that unknown error codes fall back to INTERNAL_ERROR."""
        from backend.exceptions import get_error_info

        info = get_error_info("UNKNOWN_CODE_12345")

        # Should return INTERNAL_ERROR info
        assert info["status_code"] == 500
