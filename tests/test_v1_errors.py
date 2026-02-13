"""
Tests for Error Code Documentation Endpoint (v1).

Covers GET /api/v1/errors/codes and verifies that OpenAPI schema
includes error responses on v1 endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.exceptions import ERROR_CODES


@pytest.fixture
def client():
    return TestClient(app)


class TestErrorCodesEndpoint:
    """Tests for GET /api/v1/errors/codes."""

    def test_returns_200(self, client):
        resp = client.get("/api/v1/errors/codes")
        assert resp.status_code == 200

    def test_top_level_keys(self, client):
        data = client.get("/api/v1/errors/codes").json()
        assert "error_codes" in data
        assert "by_status_code" in data
        assert "total_codes" in data

    def test_all_error_codes_present(self, client):
        data = client.get("/api/v1/errors/codes").json()
        for code in ERROR_CODES:
            assert code in data["error_codes"], f"Missing error code: {code}"

    def test_total_codes_matches(self, client):
        data = client.get("/api/v1/errors/codes").json()
        assert data["total_codes"] == len(ERROR_CODES)

    def test_entry_has_required_fields(self, client):
        data = client.get("/api/v1/errors/codes").json()
        required = {"code", "description", "status_code", "category", "user_action", "example_response"}
        for code, entry in data["error_codes"].items():
            missing = required - set(entry.keys())
            assert not missing, f"{code} missing fields: {missing}"

    def test_4xx_5xx_grouping(self, client):
        data = client.get("/api/v1/errors/codes").json()
        by_status = data["by_status_code"]
        assert "4xx_client_errors" in by_status
        assert "5xx_server_errors" in by_status

        for code in by_status["4xx_client_errors"]:
            assert 400 <= data["error_codes"][code]["status_code"] < 500

        for code in by_status["5xx_server_errors"]:
            assert 500 <= data["error_codes"][code]["status_code"] < 600

    def test_example_responses_have_error_fields(self, client):
        data = client.get("/api/v1/errors/codes").json()
        for code, entry in data["error_codes"].items():
            example = entry["example_response"]
            assert "error" in example, f"{code} example missing 'error'"
            assert "message" in example, f"{code} example missing 'message'"
            assert "status_code" in example, f"{code} example missing 'status_code'"

    def test_status_codes_match_registry(self, client):
        data = client.get("/api/v1/errors/codes").json()
        for code, entry in data["error_codes"].items():
            assert entry["status_code"] == ERROR_CODES[code]["status_code"], (
                f"{code}: endpoint says {entry['status_code']} but registry says {ERROR_CODES[code]['status_code']}"
            )


class TestOpenAPISchema:
    """Verify error responses appear in the OpenAPI schema."""

    def test_errors_codes_in_openapi(self, client):
        schema = client.get("/openapi.json").json()
        paths = schema["paths"]
        assert "/api/v1/errors/codes" in paths

    def test_momentum_ticker_has_error_responses(self, client):
        schema = client.get("/openapi.json").json()
        path = schema["paths"].get("/api/v1/momentum/{ticker}", {})
        get_responses = path.get("get", {}).get("responses", {})
        for status in ["400", "429", "500", "502"]:
            assert status in get_responses, (
                f"GET /api/v1/momentum/{{ticker}} missing {status} response in OpenAPI"
            )
