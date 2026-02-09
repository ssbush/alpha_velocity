"""
Tests for Error Handlers (backend/error_handlers.py)

Covers exception handlers invoked via the FastAPI test client.
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.error_handlers import get_request_id


client = TestClient(app)


class TestGetRequestId:
    """Tests for get_request_id() helper."""

    def test_returns_custom_header(self):
        request = MagicMock()
        request.headers = {"X-Request-ID": "custom-123"}
        assert get_request_id(request) == "custom-123"

    def test_generates_fallback_id(self):
        request = MagicMock()
        request.headers = {}
        rid = get_request_id(request)
        assert rid.startswith("req_")


class TestHTTPExceptionHandler:
    """Tests for http_exception_handler via real requests."""

    def test_400_mapped_to_bad_request(self):
        # Trigger a 400 via invalid ticker
        resp = client.get("/api/v1/momentum/TOOLONG12345")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] in ("VALIDATION_ERROR", "BAD_REQUEST")

    def test_404_response(self):
        resp = client.get("/api/v1/nonexistent/endpoint")
        assert resp.status_code == 404

    def test_401_mapped_to_auth_error(self):
        resp = client.get("/auth/profile", headers={"Authorization": "Bearer bad-token"})
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"] == "AUTHENTICATION_ERROR"


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler via real requests."""

    def test_pydantic_validation_error(self):
        # POST /auth/register with missing required fields
        resp = client.post("/auth/register", json={})
        assert resp.status_code in (400, 422)
        data = resp.json()
        assert "error" in data
        assert "message" in data

    def test_batch_validation_error(self):
        resp = client.post("/api/v1/momentum/batch", json={"tickers": []})
        assert resp.status_code in (400, 422)
        data = resp.json()
        assert "error" in data


class TestErrorResponseFormat:
    """Tests for consistent error response format."""

    def test_error_response_has_required_fields(self):
        resp = client.get("/api/v1/momentum/TOOLONG12345")
        data = resp.json()
        assert "error" in data
        assert "message" in data
        assert "status_code" in data
        assert "timestamp" in data
        assert "path" in data

    def test_request_id_in_response(self):
        resp = client.get(
            "/api/v1/momentum/TOOLONG12345",
            headers={"X-Request-ID": "test-id-abc"}
        )
        data = resp.json()
        assert "request_id" in data
