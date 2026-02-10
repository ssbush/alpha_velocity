"""
Tests for Security Headers Middleware (backend/config/security_headers_config.py)

Covers get_security_headers_settings(), SecurityHeadersMiddleware, and integration
via TestClient.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.config.security_headers_config import (
    get_security_headers_settings,
    SecurityHeadersMiddleware,
    setup_security_headers,
    DEFAULT_CSP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(headers=None):
    """Create a minimal FastAPI app with security headers middleware."""
    app = FastAPI()
    if headers is not None:
        app.add_middleware(SecurityHeadersMiddleware, headers=headers)
    else:
        setup_security_headers(app)

    @app.get("/test")
    def _test_endpoint():
        return {"ok": True}

    return app


def _make_app_with_override():
    """App where an endpoint sets its own X-Frame-Options."""
    app = FastAPI()
    setup_security_headers(app)

    from fastapi import Response as FastAPIResponse

    @app.get("/custom")
    def _custom(response: FastAPIResponse):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# Config function tests
# ---------------------------------------------------------------------------

class TestGetSecurityHeadersSettings:
    """Tests for get_security_headers_settings()."""

    def test_returns_dict(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        headers = get_security_headers_settings()
        assert isinstance(headers, dict)

    def test_dev_defaults_include_expected_headers(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("SECURITY_HSTS_MAX_AGE", raising=False)
        monkeypatch.delenv("SECURITY_X_FRAME_OPTIONS", raising=False)
        monkeypatch.delenv("SECURITY_REFERRER_POLICY", raising=False)
        monkeypatch.delenv("SECURITY_CSP", raising=False)
        monkeypatch.delenv("SECURITY_PERMISSIONS_POLICY", raising=False)
        headers = get_security_headers_settings()
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in headers
        assert "Permissions-Policy" in headers

    def test_hsts_disabled_in_dev_by_default(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("SECURITY_HSTS_MAX_AGE", raising=False)
        headers = get_security_headers_settings()
        assert "Strict-Transport-Security" not in headers

    def test_hsts_enabled_in_production_by_default(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("SECURITY_HSTS_MAX_AGE", raising=False)
        headers = get_security_headers_settings()
        assert "Strict-Transport-Security" in headers
        assert "max-age=31536000" in headers["Strict-Transport-Security"]
        assert "includeSubDomains" in headers["Strict-Transport-Security"]

    def test_hsts_enabled_via_env_var(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_HSTS_MAX_AGE", "3600")
        headers = get_security_headers_settings()
        assert "Strict-Transport-Security" in headers
        assert "max-age=3600" in headers["Strict-Transport-Security"]

    def test_hsts_preload(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_HSTS_MAX_AGE", "3600")
        monkeypatch.setenv("SECURITY_HSTS_PRELOAD", "true")
        headers = get_security_headers_settings()
        assert "preload" in headers["Strict-Transport-Security"]

    def test_custom_x_frame_options(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_X_FRAME_OPTIONS", "SAMEORIGIN")
        headers = get_security_headers_settings()
        assert headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_custom_referrer_policy(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_REFERRER_POLICY", "no-referrer")
        headers = get_security_headers_settings()
        assert headers["Referrer-Policy"] == "no-referrer"

    def test_custom_csp(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_CSP", "default-src 'none'")
        headers = get_security_headers_settings()
        assert headers["Content-Security-Policy"] == "default-src 'none'"

    def test_empty_csp_disables_header(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_CSP", "")
        headers = get_security_headers_settings()
        assert "Content-Security-Policy" not in headers

    def test_custom_permissions_policy(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_PERMISSIONS_POLICY", "camera=(self)")
        headers = get_security_headers_settings()
        assert headers["Permissions-Policy"] == "camera=(self)"

    def test_invalid_hsts_max_age_uses_default(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_HSTS_MAX_AGE", "not_a_number")
        headers = get_security_headers_settings()
        # Dev default is 0, so HSTS should be absent
        assert "Strict-Transport-Security" not in headers

    def test_default_csp_constant(self):
        assert "default-src 'self'" in DEFAULT_CSP
        assert "script-src" in DEFAULT_CSP


# ---------------------------------------------------------------------------
# Middleware integration tests (via TestClient)
# ---------------------------------------------------------------------------

class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware via TestClient."""

    def test_nosniff_present(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_present(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["X-Frame-Options"] == "DENY"

    def test_referrer_policy_present(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_present(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert "Permissions-Policy" in resp.headers

    def test_csp_present(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert "Content-Security-Policy" in resp.headers

    def test_hsts_absent_in_dev(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("SECURITY_HSTS_MAX_AGE", raising=False)
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert "Strict-Transport-Security" not in resp.headers

    def test_hsts_present_when_configured(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SECURITY_HSTS_MAX_AGE", "600")
        client = TestClient(_make_app())
        resp = client.get("/test")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=600" in resp.headers["Strict-Transport-Security"]

    def test_per_route_override_respected(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        client = TestClient(_make_app_with_override())
        resp = client.get("/custom")
        assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_custom_headers_dict(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        custom = {"X-Custom": "test-value"}
        client = TestClient(_make_app(headers=custom))
        resp = client.get("/test")
        assert resp.headers["X-Custom"] == "test-value"


# ---------------------------------------------------------------------------
# setup_security_headers() tests
# ---------------------------------------------------------------------------

class TestSetupSecurityHeaders:
    """Tests for setup_security_headers()."""

    def test_adds_middleware(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        app = FastAPI()

        @app.get("/ping")
        def _ping():
            return {"pong": True}

        setup_security_headers(app)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
