"""
Tests for CSRF Protection (Double-Submit Cookie Pattern)

Covers:
- Token generation and validation (csrf_config.py)
- CSRF middleware behavior (csrf_middleware.py)
- Full flow integration tests
"""

import time
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.config.csrf_config import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    generate_csrf_token,
    validate_csrf_token,
    get_csrf_config,
    log_csrf_config,
)
from backend.middleware.csrf_middleware import CSRFMiddleware


# ============================================================================
# Helper: Minimal FastAPI app with CSRF middleware for isolated testing
# ============================================================================


def _create_test_app(csrf_enabled=True):
    """Create a minimal FastAPI app with CSRF middleware for testing."""
    test_app = FastAPI()

    test_app.add_middleware(CSRFMiddleware, enabled=csrf_enabled)

    @test_app.get("/")
    async def health():
        return {"status": "ok"}

    @test_app.get("/page")
    async def page():
        return {"page": "data"}

    @test_app.post("/data")
    async def create_data():
        return {"created": True}

    @test_app.put("/data/1")
    async def update_data():
        return {"updated": True}

    @test_app.delete("/data/1")
    async def delete_data():
        return {"deleted": True}

    @test_app.patch("/data/1")
    async def patch_data():
        return {"patched": True}

    @test_app.post("/auth/login")
    async def login():
        return {"token": "abc"}

    @test_app.post("/auth/register")
    async def register():
        return {"token": "def"}

    @test_app.post("/auth/refresh")
    async def refresh():
        return {"token": "ghi"}

    return test_app


# ============================================================================
# Token Generation & Validation Unit Tests
# ============================================================================


class TestCSRFTokenGeneration:
    """Unit tests for CSRF token generation and validation."""

    def test_generate_produces_nonempty_string(self):
        token = generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_produces_three_part_token(self):
        token = generate_csrf_token()
        parts = token.split(".")
        assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}: {token}"

    def test_valid_token_passes_validation(self):
        token = generate_csrf_token()
        assert validate_csrf_token(token) is True

    def test_tampered_token_fails_validation(self):
        token = generate_csrf_token()
        parts = token.split(".")
        # Tamper with the random part
        tampered = "a" * len(parts[0]) + "." + parts[1] + "." + parts[2]
        assert validate_csrf_token(tampered) is False

    def test_tampered_signature_fails_validation(self):
        token = generate_csrf_token()
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "." + "x" * 64
        assert validate_csrf_token(tampered) is False

    def test_expired_token_fails_validation(self):
        token = generate_csrf_token()
        parts = token.split(".")
        # Set timestamp to 48 hours ago (default expiry is 24h)
        old_ts = str(int(time.time()) - 48 * 3600)
        old_payload = f"{parts[0]}.{old_ts}"
        # Re-sign with correct key
        import hmac
        import hashlib
        from backend.auth import SECRET_KEY
        sig = hmac.new(
            SECRET_KEY.encode(), old_payload.encode(), hashlib.sha256
        ).hexdigest()
        expired_token = f"{old_payload}.{sig}"
        assert validate_csrf_token(expired_token) is False

    def test_different_calls_produce_different_tokens(self):
        t1 = generate_csrf_token()
        t2 = generate_csrf_token()
        assert t1 != t2

    def test_malformed_token_fails(self):
        assert validate_csrf_token("not-a-valid-token") is False
        assert validate_csrf_token("") is False
        assert validate_csrf_token("a.b") is False
        assert validate_csrf_token("a.b.c.d") is False

    def test_non_numeric_timestamp_fails(self):
        assert validate_csrf_token("abc.notanumber.def") is False


# ============================================================================
# CSRF Config Tests
# ============================================================================


class TestCSRFConfig:
    """Tests for CSRF config helper functions."""

    def test_get_config_returns_expected_keys(self):
        config = get_csrf_config()
        assert "enabled" in config
        assert "cookie_name" in config
        assert "header_name" in config
        assert "token_expiry_hours" in config
        assert "exempt_paths" in config

    def test_log_csrf_config_runs(self):
        """log_csrf_config should not raise."""
        log_csrf_config()

    def test_exempt_paths_include_auth_routes(self):
        config = get_csrf_config()
        assert "/auth/login" in config["exempt_paths"]
        assert "/auth/register" in config["exempt_paths"]
        assert "/auth/refresh" in config["exempt_paths"]


# ============================================================================
# CSRF Middleware Tests (using isolated test app)
# ============================================================================


class TestCSRFMiddleware:
    """Tests for CSRF middleware behavior."""

    @pytest.fixture
    def app_client(self):
        """Client with CSRF enabled."""
        app = _create_test_app(csrf_enabled=True)
        return TestClient(app)

    @pytest.fixture
    def disabled_client(self):
        """Client with CSRF disabled."""
        app = _create_test_app(csrf_enabled=False)
        return TestClient(app)

    def test_get_request_passes_without_csrf(self, app_client):
        resp = app_client.get("/page")
        assert resp.status_code == 200

    def test_get_response_sets_csrf_cookie(self, app_client):
        resp = app_client.get("/page")
        assert CSRF_COOKIE_NAME in resp.cookies

    def test_post_without_csrf_header_returns_403(self, app_client):
        resp = app_client.post("/data")
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"] == "CSRF_VALIDATION_FAILED"

    def test_post_with_valid_csrf_succeeds(self, app_client):
        # First GET to obtain cookie
        get_resp = app_client.get("/page")
        csrf_token = get_resp.cookies[CSRF_COOKIE_NAME]

        # POST with matching header
        resp = app_client.post(
            "/data",
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        assert resp.status_code == 200
        assert resp.json()["created"] is True

    def test_post_with_mismatched_header_returns_403(self, app_client):
        # GET to obtain cookie
        app_client.get("/page")

        # POST with wrong header value
        resp = app_client.post(
            "/data",
            headers={CSRF_HEADER_NAME: "wrong-token-value"},
        )
        assert resp.status_code == 403

    def test_post_to_exempt_login_passes(self, app_client):
        resp = app_client.post("/auth/login")
        assert resp.status_code == 200

    def test_post_to_exempt_register_passes(self, app_client):
        resp = app_client.post("/auth/register")
        assert resp.status_code == 200

    def test_post_to_exempt_refresh_passes(self, app_client):
        resp = app_client.post("/auth/refresh")
        assert resp.status_code == 200

    def test_put_requires_csrf(self, app_client):
        resp = app_client.put("/data/1")
        assert resp.status_code == 403

    def test_put_with_valid_csrf_succeeds(self, app_client):
        get_resp = app_client.get("/page")
        csrf_token = get_resp.cookies[CSRF_COOKIE_NAME]

        resp = app_client.put(
            "/data/1",
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        assert resp.status_code == 200

    def test_delete_requires_csrf(self, app_client):
        resp = app_client.delete("/data/1")
        assert resp.status_code == 403

    def test_delete_with_valid_csrf_succeeds(self, app_client):
        get_resp = app_client.get("/page")
        csrf_token = get_resp.cookies[CSRF_COOKIE_NAME]

        resp = app_client.delete(
            "/data/1",
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        assert resp.status_code == 200

    def test_patch_requires_csrf(self, app_client):
        resp = app_client.patch("/data/1")
        assert resp.status_code == 403

    def test_patch_with_valid_csrf_succeeds(self, app_client):
        get_resp = app_client.get("/page")
        csrf_token = get_resp.cookies[CSRF_COOKIE_NAME]

        resp = app_client.patch(
            "/data/1",
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        assert resp.status_code == 200

    def test_csrf_disabled_allows_all_requests(self, disabled_client):
        resp = disabled_client.post("/data")
        assert resp.status_code == 200

    def test_csrf_disabled_allows_put(self, disabled_client):
        resp = disabled_client.put("/data/1")
        assert resp.status_code == 200

    def test_csrf_disabled_allows_delete(self, disabled_client):
        resp = disabled_client.delete("/data/1")
        assert resp.status_code == 200


# ============================================================================
# Integration Tests (full flow)
# ============================================================================


class TestCSRFIntegration:
    """Integration tests for full CSRF flow."""

    @pytest.fixture
    def app_client(self):
        app = _create_test_app(csrf_enabled=True)
        return TestClient(app)

    def test_full_flow_get_then_post(self, app_client):
        """GET to obtain cookie, then POST with cookie+header succeeds."""
        get_resp = app_client.get("/")
        assert get_resp.status_code == 200
        csrf_token = get_resp.cookies[CSRF_COOKIE_NAME]

        post_resp = app_client.post(
            "/data",
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        assert post_resp.status_code == 200

    def test_tampered_header_rejected(self, app_client):
        """POST with a tampered header value is rejected."""
        get_resp = app_client.get("/")
        csrf_token = get_resp.cookies[CSRF_COOKIE_NAME]

        # Tamper with the token
        tampered = csrf_token[:-4] + "XXXX"

        post_resp = app_client.post(
            "/data",
            headers={CSRF_HEADER_NAME: tampered},
        )
        assert post_resp.status_code == 403

    def test_cookie_persists_across_requests(self, app_client):
        """Cookie set on first GET persists for subsequent requests."""
        resp1 = app_client.get("/page")
        token1 = resp1.cookies[CSRF_COOKIE_NAME]

        # Second GET should still have the same cookie (client jar persists)
        resp2 = app_client.get("/page")
        # The cookie from the client's jar should still be valid
        assert validate_csrf_token(token1) is True

    def test_multiple_posts_with_same_token(self, app_client):
        """Same CSRF token can be used for multiple requests within expiry."""
        get_resp = app_client.get("/")
        csrf_token = get_resp.cookies[CSRF_COOKIE_NAME]

        for _ in range(3):
            resp = app_client.post(
                "/data",
                headers={CSRF_HEADER_NAME: csrf_token},
            )
            assert resp.status_code == 200

    def test_exempt_paths_work_without_cookie(self):
        """Auth endpoints work even on a fresh client with no prior GET."""
        app = _create_test_app(csrf_enabled=True)
        client = TestClient(app, cookies={})

        resp = client.post("/auth/login")
        assert resp.status_code == 200

    def test_error_response_format(self, app_client):
        """403 response has structured error body."""
        resp = app_client.post("/data")
        assert resp.status_code == 403
        data = resp.json()
        assert "error" in data
        assert "message" in data
        assert data["error"] == "CSRF_VALIDATION_FAILED"


# ============================================================================
# Main app integration (CSRF disabled by default in test env)
# ============================================================================


class TestCSRFMainAppDisabled:
    """Verify CSRF is disabled in test env so existing tests are unaffected."""

    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    def test_post_to_cache_clear_works_without_csrf(self, client):
        """When CSRF_ENABLED=false (test env), POST works without CSRF token."""
        resp = client.post("/cache/clear")
        # Should not be 403 — CSRF is disabled
        assert resp.status_code != 403
