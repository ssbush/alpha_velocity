"""
Tests for User Service (backend/services/user_service.py)

Uses mocked database session to test user CRUD operations.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from backend.services.user_service import UserService
from backend.auth import UserRegistration, get_password_hash


def _make_mock_user(**kwargs):
    """Create a mock user DB object."""
    user = MagicMock()
    user.id = kwargs.get("id", 1)
    user.username = kwargs.get("username", "testuser")
    user.email = kwargs.get("email", "test@example.com")
    user.password_hash = kwargs.get("password_hash", get_password_hash("TestPass1"))
    user.first_name = kwargs.get("first_name", "Test")
    user.last_name = kwargs.get("last_name", "User")
    user.is_active = kwargs.get("is_active", True)
    user.created_at = kwargs.get("created_at", datetime(2024, 1, 1))
    user.updated_at = kwargs.get("updated_at", datetime(2024, 1, 1))
    return user


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


@pytest.fixture
def service(mock_db):
    return UserService(mock_db)


class TestCreateUser:
    """Tests for UserService.create_user()."""

    def test_create_user_success(self, service, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        reg = UserRegistration(
            username="newuser",
            email="new@example.com",
            password="StrongPass1",
        )

        # Mock the add and commit to capture the user
        def fake_add(user_obj):
            user_obj.id = 42
            user_obj.created_at = datetime(2024, 1, 1)

        mock_db.add.side_effect = fake_add
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        user = service.create_user(reg)
        assert mock_db.add.call_count >= 1  # user + default portfolio
        mock_db.commit.assert_called()

    def test_create_user_duplicate_username(self, service, mock_db):
        existing = _make_mock_user(username="existing")
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        reg = UserRegistration(
            username="existing",
            email="new@example.com",
            password="StrongPass1",
        )

        with pytest.raises(ValueError, match="[Uu]sername"):
            service.create_user(reg)


class TestAuthenticateUser:
    """Tests for UserService.authenticate_user()."""

    def test_authenticate_success(self, service, mock_db):
        pw_hash = get_password_hash("ValidPass1")
        mock_user = _make_mock_user(password_hash=pw_hash)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = service.authenticate_user("testuser", "ValidPass1")
        assert result is not None
        assert result.username == "testuser"

    def test_authenticate_wrong_password(self, service, mock_db):
        pw_hash = get_password_hash("ValidPass1")
        mock_user = _make_mock_user(password_hash=pw_hash)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = service.authenticate_user("testuser", "WrongPass1")
        assert result is None

    def test_authenticate_user_not_found(self, service, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.authenticate_user("nouser", "SomePass1")
        assert result is None

    def test_authenticate_inactive_user(self, service, mock_db):
        pw_hash = get_password_hash("ValidPass1")
        mock_user = _make_mock_user(password_hash=pw_hash, is_active=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = service.authenticate_user("testuser", "ValidPass1")
        assert result is None


class TestGetUserProfile:
    """Tests for UserService.get_user_profile()."""

    def test_get_profile_found(self, service, mock_db):
        mock_user = _make_mock_user()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        profile = service.get_user_profile(1)
        assert profile is not None

    def test_get_profile_not_found(self, service, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        profile = service.get_user_profile(999)
        assert profile is None


class TestGetUserById:
    """Tests for UserService.get_user_by_id()."""

    def test_returns_user(self, service, mock_db):
        mock_user = _make_mock_user()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = service.get_user_by_id(1)
        assert result.username == "testuser"

    def test_returns_none_when_missing(self, service, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.get_user_by_id(999)
        assert result is None
