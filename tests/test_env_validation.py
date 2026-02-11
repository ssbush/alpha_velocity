"""Tests for startup environment variable validation."""

import os
from unittest.mock import patch

import pytest

from backend.config.env_validation import (
    validate_environment,
    _check_environment_value,
    _check_integer_vars,
    _check_log_level,
    _check_production_secrets,
)


class TestEnvironmentValue:
    """Tests for ENVIRONMENT variable validation."""

    @pytest.mark.parametrize("env", ["development", "staging", "production", "test"])
    def test_valid_values_accepted(self, env):
        warnings = []
        _check_environment_value(env, warnings)
        assert warnings == []

    def test_invalid_value_warns(self):
        warnings = []
        _check_environment_value("bogus", warnings)
        assert len(warnings) == 1
        assert "bogus" in warnings[0]
        assert "not a recognized value" in warnings[0]

    def test_missing_defaults_to_development(self):
        """When ENVIRONMENT is unset, validate_environment uses 'development' — no warning."""
        with patch.dict(os.environ, {}, clear=True):
            warnings = []
            _check_environment_value("development", warnings)
            assert warnings == []


class TestIntegerValidation:
    """Tests for integer environment variable validation."""

    def test_valid_integer_passes(self):
        warnings = []
        with patch.dict(os.environ, {"CORS_MAX_AGE": "600"}, clear=False):
            _check_integer_vars(warnings)
        cors_warnings = [w for w in warnings if "CORS_MAX_AGE" in w]
        assert cors_warnings == []

    def test_non_integer_warns(self):
        warnings = []
        with patch.dict(os.environ, {"CORS_MAX_AGE": "abc"}, clear=False):
            _check_integer_vars(warnings)
        assert any("CORS_MAX_AGE" in w and "not a valid integer" in w for w in warnings)

    def test_negative_for_positive_only_warns(self):
        warnings = []
        with patch.dict(os.environ, {"MAX_FAILED_LOGIN_ATTEMPTS": "-1"}, clear=False):
            _check_integer_vars(warnings)
        assert any("MAX_FAILED_LOGIN_ATTEMPTS" in w and "below minimum" in w for w in warnings)

    def test_port_out_of_range_warns(self):
        warnings = []
        with patch.dict(os.environ, {"DB_PORT": "99999"}, clear=False):
            _check_integer_vars(warnings)
        assert any("DB_PORT" in w and "above maximum" in w for w in warnings)

    def test_unset_vars_skipped(self):
        """Variables that are not set should not produce warnings."""
        warnings = []
        env = {k: v for k, v in os.environ.items()
               if k not in ("CORS_MAX_AGE", "CSRF_TOKEN_EXPIRY_HOURS",
                            "MAX_FAILED_LOGIN_ATTEMPTS", "LOCKOUT_DURATION_MINUTES",
                            "DB_PORT")}
        with patch.dict(os.environ, env, clear=True):
            _check_integer_vars(warnings)
        assert warnings == []


class TestLogLevel:
    """Tests for LOG_LEVEL validation."""

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_valid_levels_pass(self, level):
        warnings = []
        with patch.dict(os.environ, {"LOG_LEVEL": level}, clear=False):
            _check_log_level(warnings)
        assert warnings == []

    def test_invalid_level_warns(self):
        warnings = []
        with patch.dict(os.environ, {"LOG_LEVEL": "VERBOSE"}, clear=False):
            _check_log_level(warnings)
        assert len(warnings) == 1
        assert "VERBOSE" in warnings[0]
        assert "not a valid log level" in warnings[0]

    def test_unset_skipped(self):
        warnings = []
        env = {k: v for k, v in os.environ.items() if k != "LOG_LEVEL"}
        with patch.dict(os.environ, env, clear=True):
            _check_log_level(warnings)
        assert warnings == []


class TestProductionChecks:
    """Tests for production-specific secret validation."""

    def test_default_db_password_in_production_errors(self):
        warnings = []
        errors = []
        with patch.dict(os.environ, {"DB_PASSWORD": "alphavelocity", "DB_HOST": "db.example.com"}):
            _check_production_secrets("production", warnings, errors)
        assert any("DB_PASSWORD" in e and "default value" in e for e in errors)

    def test_custom_db_password_in_production_passes(self):
        warnings = []
        errors = []
        with patch.dict(os.environ, {"DB_PASSWORD": "super-secure-pw-123", "DB_HOST": "db.example.com"}):
            _check_production_secrets("production", warnings, errors)
        assert not any("DB_PASSWORD" in e for e in errors)

    def test_db_host_localhost_in_production_warns(self):
        warnings = []
        errors = []
        with patch.dict(os.environ, {"DB_PASSWORD": "super-secure-pw-123", "DB_HOST": "localhost"}):
            _check_production_secrets("production", warnings, errors)
        assert any("DB_HOST=localhost" in w for w in warnings)

    def test_dev_mode_defaults_no_error(self):
        """Dev mode with default credentials should warn but not error."""
        warnings = []
        errors = []
        with patch.dict(os.environ, {"DB_PASSWORD": "alphavelocity", "DB_HOST": "localhost"}):
            _check_production_secrets("development", warnings, errors)
        assert errors == []
        assert any("DB_PASSWORD" in w for w in warnings)

    def test_no_db_vars_skips_check(self):
        """When no DB env vars are set, skip DB checks entirely."""
        warnings = []
        errors = []
        env = {k: v for k, v in os.environ.items()
               if k not in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")}
        with patch.dict(os.environ, env, clear=True):
            _check_production_secrets("production", warnings, errors)
        assert warnings == []
        assert errors == []


class TestValidateEnvironment:
    """Tests for the top-level validate_environment() function."""

    def test_clean_environment_returns_empty(self):
        """A clean environment with no problematic vars returns no warnings."""
        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("CORS_MAX_AGE", "CSRF_TOKEN_EXPIRY_HOURS",
                                  "MAX_FAILED_LOGIN_ATTEMPTS", "LOCKOUT_DURATION_MINUTES",
                                  "DB_PORT", "LOG_LEVEL", "DB_HOST", "DB_PORT",
                                  "DB_NAME", "DB_USER", "DB_PASSWORD")}
        clean_env["ENVIRONMENT"] = "test"
        with patch.dict(os.environ, clean_env, clear=True):
            result = validate_environment()
        assert result == []

    def test_returns_warnings_for_issues(self):
        env = dict(os.environ)
        env["LOG_LEVEL"] = "BOGUS"
        env["ENVIRONMENT"] = "development"
        with patch.dict(os.environ, env, clear=True):
            result = validate_environment()
        assert any("LOG_LEVEL" in w for w in result)

    def test_production_critical_raises(self):
        """Production with default DB_PASSWORD raises RuntimeError."""
        env = {
            "ENVIRONMENT": "production",
            "DB_PASSWORD": "alphavelocity",
            "DB_HOST": "db.example.com",
            "SECRET_KEY": "not-checked-here",
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="Environment validation failed"):
                validate_environment()

    def test_runs_without_error_in_test_env(self):
        """Full validation runs without error in the test environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}, clear=False):
            result = validate_environment()
        assert isinstance(result, list)
