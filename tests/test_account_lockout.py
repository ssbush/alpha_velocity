"""
Tests for Account Lockout Feature

Covers:
- LoginAttemptTracker unit tests
- Lockout config helpers
- Login endpoint integration with lockout
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

from backend.config.account_lockout_config import (
    LoginAttemptTracker,
    get_lockout_config,
    log_lockout_config,
)
from backend.exceptions import AccountLockedError
from backend.main import app


# ============================================================================
# LoginAttemptTracker Unit Tests
# ============================================================================


class TestLoginAttemptTracker:
    """Unit tests for LoginAttemptTracker."""

    def test_unknown_user_not_locked(self):
        tracker = LoginAttemptTracker()
        locked, remaining = tracker.is_locked("newuser")
        assert locked is False
        assert remaining is None

    def test_single_failure_does_not_lock(self):
        tracker = LoginAttemptTracker(max_attempts=5)
        locked, _ = tracker.record_failed_attempt("user1")
        assert locked is False

    def test_below_threshold_does_not_lock(self):
        tracker = LoginAttemptTracker(max_attempts=5)
        for _ in range(4):
            locked, _ = tracker.record_failed_attempt("user1")
        assert locked is False

    def test_exact_threshold_locks(self):
        tracker = LoginAttemptTracker(max_attempts=3)
        for _ in range(2):
            tracker.record_failed_attempt("user1")
        locked, seconds = tracker.record_failed_attempt("user1")
        assert locked is True
        assert seconds is not None
        assert seconds > 0

    def test_locked_user_returns_seconds_remaining(self):
        tracker = LoginAttemptTracker(max_attempts=2, lockout_duration_minutes=10)
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user1")
        locked, seconds = tracker.is_locked("user1")
        assert locked is True
        assert seconds is not None
        assert 0 < seconds <= 600

    def test_successful_login_resets_counter(self):
        tracker = LoginAttemptTracker(max_attempts=3)
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user1")
        tracker.record_successful_login("user1")
        # After reset, should be able to fail again without locking
        locked, _ = tracker.record_failed_attempt("user1")
        assert locked is False

    def test_case_insensitive_usernames(self):
        tracker = LoginAttemptTracker(max_attempts=3)
        tracker.record_failed_attempt("User1")
        tracker.record_failed_attempt("USER1")
        locked, _ = tracker.record_failed_attempt("user1")
        assert locked is True

    def test_clear_specific_user(self):
        tracker = LoginAttemptTracker(max_attempts=2)
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user1")
        assert tracker.is_locked("user1")[0] is True
        tracker.clear("user1")
        assert tracker.is_locked("user1")[0] is False

    def test_clear_all(self):
        tracker = LoginAttemptTracker(max_attempts=2)
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user2")
        tracker.record_failed_attempt("user2")
        tracker.clear()
        assert tracker.is_locked("user1")[0] is False
        assert tracker.is_locked("user2")[0] is False

    def test_disabled_tracker_never_locks(self):
        tracker = LoginAttemptTracker(max_attempts=1, enabled=False)
        locked, _ = tracker.record_failed_attempt("user1")
        assert locked is False
        locked, _ = tracker.is_locked("user1")
        assert locked is False

    def test_custom_max_attempts(self):
        tracker = LoginAttemptTracker(max_attempts=2)
        tracker.record_failed_attempt("user1")
        locked, _ = tracker.record_failed_attempt("user1")
        assert locked is True

    def test_custom_lockout_duration(self):
        tracker = LoginAttemptTracker(max_attempts=1, lockout_duration_minutes=30)
        tracker.record_failed_attempt("user1")
        _, seconds = tracker.is_locked("user1")
        assert seconds is not None
        assert seconds <= 1800

    def test_get_status_no_attempts(self):
        tracker = LoginAttemptTracker()
        status = tracker.get_status("unknown")
        assert status['failed_attempts'] == 0
        assert status['locked'] is False

    def test_get_status_with_attempts(self):
        tracker = LoginAttemptTracker(max_attempts=5)
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user1")
        status = tracker.get_status("user1")
        assert status['failed_attempts'] == 2
        assert status['locked'] is False

    def test_get_status_locked(self):
        tracker = LoginAttemptTracker(max_attempts=2)
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user1")
        status = tracker.get_status("user1")
        assert status['locked'] is True
        assert status['seconds_remaining'] is not None

    def test_record_failed_on_already_locked_returns_locked(self):
        tracker = LoginAttemptTracker(max_attempts=2)
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user1")
        # Additional failure on locked account
        locked, seconds = tracker.record_failed_attempt("user1")
        assert locked is True
        assert seconds is not None

    def test_disabled_tracker_successful_login_noop(self):
        tracker = LoginAttemptTracker(enabled=False)
        # Should not raise
        tracker.record_successful_login("user1")

    def test_cleanup_expired_entries(self):
        tracker = LoginAttemptTracker(max_attempts=1, lockout_duration_minutes=0)
        # lockout_duration_minutes=0 means lockout_duration=0 seconds
        # Record a failure - it will lock with 0-second duration
        tracker.record_failed_attempt("user1")
        # Wait a tiny bit for the lock to expire
        time.sleep(0.01)
        # Force cleanup by calling is_locked enough times
        # (cleanup triggers every 100 checks)
        for i in range(101):
            tracker.is_locked(f"dummy{i}")
        # Entry should be cleaned up
        status = tracker.get_status("user1")
        assert status['failed_attempts'] == 0


# ============================================================================
# Lockout Config Tests
# ============================================================================


class TestLockoutConfig:
    """Tests for config helper functions."""

    def test_default_config_values(self):
        config = get_lockout_config()
        assert 'enabled' in config
        assert 'max_failed_attempts' in config
        assert 'lockout_duration_minutes' in config

    def test_env_var_overrides(self, monkeypatch):
        monkeypatch.setenv('ACCOUNT_LOCKOUT_ENABLED', 'false')
        monkeypatch.setenv('MAX_FAILED_LOGIN_ATTEMPTS', '10')
        monkeypatch.setenv('LOCKOUT_DURATION_MINUTES', '30')

        # Re-import to pick up new env vars
        import importlib
        import backend.config.account_lockout_config as mod
        importlib.reload(mod)

        config = mod.get_lockout_config()
        assert config['enabled'] is False
        assert config['max_failed_attempts'] == 10
        assert config['lockout_duration_minutes'] == 30

        # Restore defaults
        monkeypatch.delenv('ACCOUNT_LOCKOUT_ENABLED')
        monkeypatch.delenv('MAX_FAILED_LOGIN_ATTEMPTS')
        monkeypatch.delenv('LOCKOUT_DURATION_MINUTES')
        importlib.reload(mod)

    def test_log_lockout_config_runs(self):
        """log_lockout_config should not raise."""
        log_lockout_config()


# ============================================================================
# AccountLockedError Exception Tests
# ============================================================================


class TestAccountLockedError:
    """Tests for AccountLockedError exception."""

    def test_error_attributes(self):
        err = AccountLockedError(retry_after_seconds=120)
        assert err.status_code == 403
        assert err.error_code == "ACCOUNT_LOCKED"
        assert err.retry_after_seconds == 120
        assert "120" in err.message

    def test_error_details(self):
        err = AccountLockedError(retry_after_seconds=60)
        assert err.details['retry_after_seconds'] == 60


# ============================================================================
# Login Endpoint Lockout Integration Tests
# ============================================================================


def _mock_user(user_id=1, username="lockout_user"):
    """Create a mock user object for login tests."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = "lockout@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, 12, 0, 0)
    return user


class TestLoginEndpointLockout:
    """Integration tests for account lockout in the login endpoint."""

    @pytest.fixture(autouse=True)
    def _fresh_tracker(self):
        """Replace the global tracker with a fresh instance for each test."""
        fresh = LoginAttemptTracker(max_attempts=3, lockout_duration_minutes=15)
        with patch("backend.main.login_attempt_tracker", new=fresh):
            self.tracker = fresh
            yield

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("backend.main.get_user_service")
    def test_login_success_unaffected(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = _mock_user()
        mock_get_svc.return_value = mock_svc

        resp = client.post("/auth/login", json={
            "username": "lockout_user",
            "password": "ValidPass1",
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "Login successful"

    @patch("backend.main.get_user_service")
    def test_failed_login_returns_401(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        resp = client.post("/auth/login", json={
            "username": "lockout_user",
            "password": "WrongPass1",
        })
        assert resp.status_code == 401

    @patch("backend.main.get_user_service")
    def test_account_locks_after_max_failures(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        # Fail 3 times (max_attempts=3)
        for _ in range(2):
            resp = client.post("/auth/login", json={
                "username": "lockout_user",
                "password": "WrongPass1",
            })
            assert resp.status_code == 401

        # Third failure should lock
        resp = client.post("/auth/login", json={
            "username": "lockout_user",
            "password": "WrongPass1",
        })
        assert resp.status_code == 403

    @patch("backend.main.get_user_service")
    def test_locked_response_contains_retry_after(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        for _ in range(3):
            client.post("/auth/login", json={
                "username": "lockout_user",
                "password": "WrongPass1",
            })

        # Subsequent attempt on locked account
        resp = client.post("/auth/login", json={
            "username": "lockout_user",
            "password": "WrongPass1",
        })
        assert resp.status_code == 403
        data = resp.json()
        assert data.get("error") == "ACCOUNT_LOCKED"
        assert "retry_after_seconds" in data
        assert data["retry_after_seconds"] > 0

    @patch("backend.main.get_user_service")
    def test_locked_account_does_not_hit_db(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        # Lock the account
        for _ in range(3):
            client.post("/auth/login", json={
                "username": "lockout_user",
                "password": "WrongPass1",
            })

        # Reset call count
        mock_svc.authenticate_user.reset_mock()

        # Attempt login on locked account
        resp = client.post("/auth/login", json={
            "username": "lockout_user",
            "password": "WrongPass1",
        })
        assert resp.status_code == 403
        # authenticate_user should NOT have been called
        mock_svc.authenticate_user.assert_not_called()

    @patch("backend.main.get_user_service")
    def test_successful_login_resets_counter(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_get_svc.return_value = mock_svc

        # Fail twice (below threshold of 3)
        mock_svc.authenticate_user.return_value = None
        for _ in range(2):
            client.post("/auth/login", json={
                "username": "lockout_user",
                "password": "WrongPass1",
            })

        # Succeed
        mock_svc.authenticate_user.return_value = _mock_user()
        resp = client.post("/auth/login", json={
            "username": "lockout_user",
            "password": "ValidPass1",
        })
        assert resp.status_code == 200

        # Fail again - counter should be reset, so 2 more failures won't lock
        mock_svc.authenticate_user.return_value = None
        for _ in range(2):
            resp = client.post("/auth/login", json={
                "username": "lockout_user",
                "password": "WrongPass1",
            })
            assert resp.status_code == 401

    @patch("backend.main.get_user_service")
    def test_different_usernames_tracked_independently(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        # Lock user1
        for _ in range(3):
            client.post("/auth/login", json={
                "username": "user_one",
                "password": "WrongPass1",
            })

        # user2 should still be able to fail without 403
        resp = client.post("/auth/login", json={
            "username": "user_two",
            "password": "WrongPass1",
        })
        assert resp.status_code == 401

    @patch("backend.main.get_user_service")
    def test_lockout_disabled_never_403(self, mock_get_svc, client):
        """When lockout is disabled, no 403 even after many failures."""
        disabled_tracker = LoginAttemptTracker(max_attempts=1, enabled=False)
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        with patch("backend.main.login_attempt_tracker", new=disabled_tracker):
            for _ in range(5):
                resp = client.post("/auth/login", json={
                    "username": "lockout_user",
                    "password": "WrongPass1",
                })
                assert resp.status_code == 401
