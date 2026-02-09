"""
Tests for Auth API Endpoints (backend/main.py auth routes)

Covers /auth/register, /auth/login, /auth/refresh, /auth/profile
using mocked UserService to avoid database dependency.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient

from backend.auth import (
    create_access_token,
    create_refresh_token,
    TokenPair,
)
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _mock_user(user_id=1, username="testuser_ep", email="ep@example.com"):
    """Create a mock user object."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = email
    user.first_name = "Test"
    user.last_name = "User"
    user.is_active = True
    user.created_at = datetime(2024, 1, 1, 12, 0, 0)
    return user


# ============================================================================
# POST /auth/register
# ============================================================================


class TestRegisterEndpoint:
    """Tests for POST /auth/register."""

    @patch("backend.main.get_user_service")
    def test_register_valid(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.create_user.return_value = _mock_user()
        mock_get_svc.return_value = mock_svc

        resp = client.post("/auth/register", json={
            "username": "newuser1",
            "email": "new1@example.com",
            "password": "StrongPass1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "User registered successfully"
        assert "token" in data
        assert "access_token" in data["token"]
        assert "refresh_token" in data["token"]

    def test_register_weak_password(self, client):
        """Pydantic validation rejects weak password before hitting service."""
        resp = client.post("/auth/register", json={
            "username": "newuser2",
            "email": "new2@example.com",
            "password": "weakpass",  # no uppercase, no digit
        })
        assert resp.status_code in [400, 422]

    def test_register_invalid_email(self, client):
        resp = client.post("/auth/register", json={
            "username": "newuser3",
            "email": "not-an-email",
            "password": "StrongPass1",
        })
        assert resp.status_code in [400, 422]

    @patch("backend.main.get_user_service")
    def test_register_duplicate_username(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.create_user.side_effect = ValueError("Username already exists")
        mock_get_svc.return_value = mock_svc

        resp = client.post("/auth/register", json={
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "StrongPass1",
        })
        assert resp.status_code == 400
        data = resp.json()
        # Error handler may use structured response or detail
        msg = data.get("detail") or data.get("message", "")
        assert "already exists" in msg.lower() or "Username" in msg

    def test_register_short_username(self, client):
        resp = client.post("/auth/register", json={
            "username": "ab",
            "email": "short@example.com",
            "password": "StrongPass1",
        })
        assert resp.status_code in [400, 422]


# ============================================================================
# POST /auth/login
# ============================================================================


class TestLoginEndpoint:
    """Tests for POST /auth/login."""

    @patch("backend.main.get_user_service")
    def test_login_valid(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = _mock_user()
        mock_get_svc.return_value = mock_svc

        resp = client.post("/auth/login", json={
            "username": "testuser_ep",
            "password": "ValidPass1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Login successful"
        assert "token" in data
        assert "access_token" in data["token"]
        assert "refresh_token" in data["token"]

    @patch("backend.main.get_user_service")
    def test_login_wrong_password(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        resp = client.post("/auth/login", json={
            "username": "testuser_ep",
            "password": "WrongPass1",
        })
        assert resp.status_code == 401
        data = resp.json()
        msg = data.get("detail") or data.get("message", "")
        assert "Invalid" in msg or "invalid" in msg.lower()

    @patch("backend.main.get_user_service")
    def test_login_nonexistent_user(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_svc.authenticate_user.return_value = None
        mock_get_svc.return_value = mock_svc

        resp = client.post("/auth/login", json={
            "username": "nouser",
            "password": "SomePass1",
        })
        assert resp.status_code == 401


# ============================================================================
# POST /auth/refresh
# ============================================================================


class TestRefreshEndpoint:
    """Tests for POST /auth/refresh."""

    def test_refresh_valid(self, client):
        refresh_token = create_refresh_token(user_id=1, username="testuser")
        resp = client.post("/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_access_token_rejected(self, client):
        access_token = create_access_token(user_id=1, username="testuser")
        resp = client.post("/auth/refresh", json={
            "refresh_token": access_token,
        })
        assert resp.status_code == 401

    def test_refresh_invalid_token(self, client):
        resp = client.post("/auth/refresh", json={
            "refresh_token": "not-a-valid-token",
        })
        assert resp.status_code == 401


# ============================================================================
# GET /auth/profile
# ============================================================================


class TestProfileEndpoint:
    """Tests for GET /auth/profile."""

    @patch("backend.main.get_user_service")
    def test_profile_with_valid_token(self, mock_get_svc, client):
        mock_svc = MagicMock()
        mock_user = _mock_user()
        from backend.auth import UserProfile
        mock_svc.get_user_profile.return_value = UserProfile(
            id=mock_user.id,
            username=mock_user.username,
            email=mock_user.email,
            first_name=mock_user.first_name,
            last_name=mock_user.last_name,
            is_active=mock_user.is_active,
            created_at=mock_user.created_at,
        )
        mock_get_svc.return_value = mock_svc

        token = create_access_token(user_id=1, username="testuser_ep")
        resp = client.get("/auth/profile", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser_ep"
        assert data["email"] == "ep@example.com"

    def test_profile_without_token(self, client):
        resp = client.get("/auth/profile")
        assert resp.status_code == 403  # HTTPBearer returns 403

    def test_profile_with_invalid_token(self, client):
        resp = client.get("/auth/profile", headers={
            "Authorization": "Bearer invalid-token",
        })
        assert resp.status_code == 401

    def test_token_pair_response_structure(self, client):
        """Verify TokenPair model includes both tokens."""
        tp = TokenPair(access_token="a", refresh_token="r")
        d = tp.model_dump()
        assert "access_token" in d
        assert "refresh_token" in d
        assert "token_type" in d
        assert "expires_in" in d
