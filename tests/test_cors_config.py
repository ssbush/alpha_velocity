"""
Tests for CORS Configuration (backend/config/cors_config.py)

Covers get_cors_origins(), get_cors_settings(), and setup_cors().
"""

import pytest
from unittest.mock import MagicMock

from backend.config.cors_config import (
    get_cors_origins,
    get_cors_settings,
    validate_origin,
    get_cors_config_info,
)


class TestGetCorsOrigins:
    """Tests for get_cors_origins()."""

    def test_returns_defaults_when_no_env(self, monkeypatch):
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        origins = get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0
        # Should contain localhost
        assert any("localhost" in o for o in origins)

    def test_parses_env_var(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com,https://www.example.com")
        origins = get_cors_origins()
        assert "https://app.example.com" in origins
        assert "https://www.example.com" in origins

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", " https://a.com , https://b.com ")
        origins = get_cors_origins()
        assert "https://a.com" in origins
        assert "https://b.com" in origins


class TestGetCorsSettings:
    """Tests for get_cors_settings()."""

    def test_returns_dict(self, monkeypatch):
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        settings = get_cors_settings()
        assert "allow_origins" in settings
        assert "allow_credentials" in settings
        assert "allow_methods" in settings
        assert "allow_headers" in settings
        assert "max_age" in settings

    def test_credentials_default_true(self, monkeypatch):
        monkeypatch.delenv("CORS_ALLOW_CREDENTIALS", raising=False)
        settings = get_cors_settings()
        assert settings["allow_credentials"] is True

    def test_max_age_default(self, monkeypatch):
        monkeypatch.delenv("CORS_MAX_AGE", raising=False)
        settings = get_cors_settings()
        assert isinstance(settings["max_age"], int)


class TestValidateOrigin:
    """Tests for validate_origin()."""

    def test_valid_origin_in_list(self, monkeypatch):
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        origins = get_cors_origins()
        if origins:
            assert validate_origin(origins[0]) is True

    def test_invalid_origin(self):
        assert validate_origin("https://evil.example.com") is False


class TestGetCorsConfigInfo:
    """Tests for get_cors_config_info()."""

    def test_returns_dict(self):
        info = get_cors_config_info()
        assert isinstance(info, dict)
        assert "origins" in info or "allow_origins" in info or len(info) > 0
