"""
Tests for Rate Limit Configuration (backend/config/rate_limit_config.py)

Covers get_identifier(), get_rate_limit_key(), rate_limit_exceeded_handler(),
RateLimits, get_rate_limit_config(), and helper functions.
"""

import pytest
from unittest.mock import MagicMock

from backend.config.rate_limit_config import (
    get_identifier,
    get_rate_limit_key,
    get_rate_limit_for_user,
    RateLimitInfo,
    create_rate_limit_exemption,
    RateLimits,
    get_rate_limit_config,
    log_rate_limit_config,
    DEFAULT_RATE_LIMIT,
    AUTHENTICATED_RATE_LIMIT,
)


def _make_request(headers=None, path="/api/test", client_ip="127.0.0.1"):
    """Create a mock FastAPI request."""
    req = MagicMock()
    req.headers = headers or {}
    req.url.path = path
    req.client.host = client_ip
    req.scope = {"type": "http"}
    return req


class TestGetIdentifier:
    """Tests for get_identifier()."""

    def test_fallback_to_ip(self):
        req = _make_request()
        result = get_identifier(req)
        # Should return something (IP-based)
        assert result is not None
        assert isinstance(result, str)

    def test_api_key_used(self):
        req = _make_request(headers={"X-API-Key": "mykey1234567890abcdef"})
        result = get_identifier(req)
        assert result.startswith("apikey:")

    def test_bearer_with_state_user_id(self):
        req = _make_request(headers={"Authorization": "Bearer sometoken"})
        req.state.user_id = 42
        result = get_identifier(req)
        assert result == "user:42"


class TestGetRateLimitKey:
    """Tests for get_rate_limit_key()."""

    def test_combines_identifier_and_path(self):
        req = _make_request(path="/api/v1/momentum/AAPL")
        key = get_rate_limit_key(req)
        assert "/api/v1/momentum/AAPL" in key
        assert ":" in key


class TestGetRateLimitForUser:
    """Tests for get_rate_limit_for_user()."""

    def test_anonymous_gets_default(self):
        req = _make_request()
        limit = get_rate_limit_for_user(req)
        assert limit == DEFAULT_RATE_LIMIT

    def test_bearer_gets_authenticated(self):
        req = _make_request(headers={"Authorization": "Bearer token"})
        limit = get_rate_limit_for_user(req)
        assert limit == AUTHENTICATED_RATE_LIMIT

    def test_api_key_gets_authenticated(self):
        req = _make_request(headers={"X-API-Key": "somekey"})
        limit = get_rate_limit_for_user(req)
        assert limit == AUTHENTICATED_RATE_LIMIT


class TestRateLimitInfo:
    """Tests for RateLimitInfo.add_headers()."""

    def test_adds_headers(self):
        response = MagicMock()
        response.headers = {}
        RateLimitInfo.add_headers(response, "100/minute", 95, 1700000000)
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "95"
        assert response.headers["X-RateLimit-Reset"] == "1700000000"


class TestCreateRateLimitExemption:
    """Tests for create_rate_limit_exemption()."""

    def test_health_endpoints_exempt(self):
        is_exempt = create_rate_limit_exemption()
        req = _make_request(path="/")
        assert is_exempt(req) is True

    def test_health_path_exempt(self):
        is_exempt = create_rate_limit_exemption()
        req = _make_request(path="/health")
        assert is_exempt(req) is True

    def test_api_path_not_exempt(self):
        is_exempt = create_rate_limit_exemption()
        req = _make_request(path="/api/v1/momentum/AAPL")
        assert is_exempt(req) is False


class TestRateLimitsPresets:
    """Tests for RateLimits class presets."""

    def test_authentication_is_strict(self):
        assert "5" in RateLimits.AUTHENTICATION

    def test_public_api(self):
        assert RateLimits.PUBLIC_API is not None

    def test_admin_exists(self):
        assert RateLimits.ADMIN is not None

    def test_all_presets_are_strings(self):
        for name in ["AUTHENTICATION", "PUBLIC_API", "AUTHENTICATED_API",
                      "EXPENSIVE", "READ_ONLY", "WRITE", "SEARCH", "UPLOAD",
                      "BULK", "ADMIN"]:
            val = getattr(RateLimits, name)
            assert isinstance(val, str), f"RateLimits.{name} is not a string"


class TestGetRateLimitConfig:
    """Tests for get_rate_limit_config()."""

    def test_returns_dict(self):
        config = get_rate_limit_config()
        assert isinstance(config, dict)
        assert "enabled" in config
        assert "limits" in config
        assert "strategy" in config

    def test_limits_have_expected_keys(self):
        config = get_rate_limit_config()
        limits = config["limits"]
        assert "default" in limits
        assert "authentication" in limits
        assert "expensive" in limits
        assert "authenticated" in limits


class TestLogRateLimitConfig:
    """Tests for log_rate_limit_config()."""

    def test_does_not_raise(self):
        # Should run without error
        log_rate_limit_config()
