"""
Tests for Authentication Module (backend/auth.py)

Covers secret key management, password hashing/verification,
JWT token creation/decoding, and Pydantic auth models.
"""

import os
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from fastapi import HTTPException
from jose import jwt

from backend.auth import (
    _get_secret_key,
    _DEFAULT_SECRET,
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    TokenData,
    Token,
    TokenPair,
    UserCredentials,
    UserRegistration,
    UserProfile,
)


# ============================================================================
# _get_secret_key() Tests
# ============================================================================


class TestGetSecretKey:
    """Tests for _get_secret_key() function."""

    def test_returns_env_var_when_set(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "my-custom-secret-key-value")
        monkeypatch.setenv("ENVIRONMENT", "development")
        result = _get_secret_key()
        assert result == "my-custom-secret-key-value"

    def test_auto_generates_in_dev_when_missing(self, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")
        result = _get_secret_key()
        assert len(result) > 10  # auto-generated key is long

    def test_auto_generates_in_dev_when_default(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", _DEFAULT_SECRET)
        monkeypatch.setenv("ENVIRONMENT", "development")
        result = _get_secret_key()
        assert result != _DEFAULT_SECRET
        assert len(result) > 10

    def test_raises_in_production_when_missing(self, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
            _get_secret_key()

    def test_raises_in_production_when_default(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", _DEFAULT_SECRET)
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
            _get_secret_key()

    def test_returns_key_in_production_when_valid(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "a-strong-production-key-1234")
        monkeypatch.setenv("ENVIRONMENT", "production")
        result = _get_secret_key()
        assert result == "a-strong-production-key-1234"

    def test_strips_whitespace_from_key(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "  my-key  ")
        monkeypatch.setenv("ENVIRONMENT", "development")
        result = _get_secret_key()
        assert result == "my-key"

    def test_empty_string_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "   ")
        monkeypatch.setenv("ENVIRONMENT", "development")
        result = _get_secret_key()
        # Should auto-generate since stripped key is empty
        assert len(result) > 10


# ============================================================================
# Password Functions Tests
# ============================================================================


class TestPasswordFunctions:
    """Tests for password hashing and verification."""

    def test_get_password_hash_returns_bcrypt_hash(self):
        h = get_password_hash("TestPassword123")
        assert h.startswith("$2")  # bcrypt prefix
        assert len(h) == 60  # bcrypt hash length

    def test_verify_password_correct(self):
        h = get_password_hash("MySecurePass1")
        assert verify_password("MySecurePass1", h) is True

    def test_verify_password_wrong(self):
        h = get_password_hash("MySecurePass1")
        assert verify_password("WrongPassword1", h) is False

    def test_password_truncated_at_72_bytes(self):
        long_pass = "A" * 100
        h = get_password_hash(long_pass)
        # bcrypt truncates at 72 bytes — first 72 chars should still match
        assert verify_password("A" * 72, h) is True

    def test_different_passwords_different_hashes(self):
        h1 = get_password_hash("Password1")
        h2 = get_password_hash("Password2")
        assert h1 != h2


# ============================================================================
# Token Creation/Decoding Tests
# ============================================================================


class TestAccessToken:
    """Tests for access token creation and decoding."""

    def test_create_access_token_returns_string(self):
        token = create_access_token(user_id=1, username="testuser")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_access_token_returns_token_data(self):
        token = create_access_token(user_id=42, username="alice")
        data = decode_access_token(token)
        assert isinstance(data, TokenData)
        assert data.user_id == 42
        assert data.username == "alice"
        assert data.exp is not None

    def test_decode_access_token_rejects_expired(self):
        payload = {
            "user_id": 1,
            "username": "testuser",
            "type": "access",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_decode_access_token_rejects_refresh_type(self):
        token = create_refresh_token(user_id=1, username="testuser")
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401
        assert "expected access token" in exc_info.value.detail

    def test_decode_access_token_rejects_malformed(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_access_token_contains_correct_type(self):
        token = create_access_token(user_id=1, username="testuser")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "access"


class TestRefreshToken:
    """Tests for refresh token creation and decoding."""

    def test_create_refresh_token_returns_string(self):
        token = create_refresh_token(user_id=1, username="testuser")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_refresh_token_returns_token_data(self):
        token = create_refresh_token(user_id=99, username="bob")
        data = decode_refresh_token(token)
        assert isinstance(data, TokenData)
        assert data.user_id == 99
        assert data.username == "bob"

    def test_decode_refresh_token_rejects_access_type(self):
        token = create_access_token(user_id=1, username="testuser")
        with pytest.raises(HTTPException) as exc_info:
            decode_refresh_token(token)
        assert exc_info.value.status_code == 401
        assert "expected refresh token" in exc_info.value.detail

    def test_decode_refresh_token_rejects_expired(self):
        payload = {
            "user_id": 1,
            "username": "testuser",
            "type": "refresh",
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            decode_refresh_token(token)
        assert exc_info.value.status_code == 401

    def test_decode_refresh_token_rejects_malformed(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_refresh_token("garbage-token")
        assert exc_info.value.status_code == 401

    def test_refresh_token_contains_correct_type(self):
        token = create_refresh_token(user_id=1, username="testuser")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "refresh"

    def test_refresh_token_has_longer_expiry_than_access(self):
        access = create_access_token(user_id=1, username="testuser")
        refresh = create_refresh_token(user_id=1, username="testuser")
        access_payload = jwt.decode(access, SECRET_KEY, algorithms=[ALGORITHM])
        refresh_payload = jwt.decode(refresh, SECRET_KEY, algorithms=[ALGORITHM])
        assert refresh_payload["exp"] > access_payload["exp"]


# ============================================================================
# Pydantic Model Tests
# ============================================================================


class TestTokenModels:
    """Tests for Token and TokenPair Pydantic models."""

    def test_token_defaults(self):
        t = Token(access_token="abc123")
        assert t.access_token == "abc123"
        assert t.token_type == "bearer"

    def test_token_pair_defaults(self):
        tp = TokenPair(access_token="access_abc", refresh_token="refresh_xyz")
        assert tp.access_token == "access_abc"
        assert tp.refresh_token == "refresh_xyz"
        assert tp.token_type == "bearer"
        assert tp.expires_in == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_token_data_fields(self):
        td = TokenData(user_id=5, username="charlie")
        assert td.user_id == 5
        assert td.username == "charlie"
        assert td.exp is None


class TestUserCredentials:
    """Tests for UserCredentials Pydantic model."""

    def test_accepts_valid_input(self):
        creds = UserCredentials(username="testuser", password="ValidPass1")
        assert creds.username == "testuser"
        assert creds.password == "ValidPass1"

    def test_rejects_short_username(self):
        with pytest.raises(Exception):  # ValidationError from Pydantic
            UserCredentials(username="ab", password="ValidPass1")

    def test_rejects_short_password(self):
        with pytest.raises(Exception):
            UserCredentials(username="testuser", password="Short1")

    def test_accepts_email_as_username(self):
        creds = UserCredentials(username="user@example.com", password="ValidPass1")
        assert creds.username == "user@example.com"


class TestUserRegistration:
    """Tests for UserRegistration Pydantic model."""

    def test_accepts_valid_input(self):
        reg = UserRegistration(
            username="newuser",
            email="new@example.com",
            password="StrongPass1",
            first_name="John",
            last_name="Doe",
        )
        assert reg.username == "newuser"
        assert reg.email == "new@example.com"

    def test_rejects_weak_password_no_uppercase(self):
        with pytest.raises(Exception):
            UserRegistration(
                username="newuser",
                email="new@example.com",
                password="weakpass1",
            )

    def test_rejects_weak_password_no_lowercase(self):
        with pytest.raises(Exception):
            UserRegistration(
                username="newuser",
                email="new@example.com",
                password="WEAKPASS1",
            )

    def test_rejects_weak_password_no_digit(self):
        with pytest.raises(Exception):
            UserRegistration(
                username="newuser",
                email="new@example.com",
                password="WeakPasswd",
            )

    def test_rejects_invalid_email(self):
        with pytest.raises(Exception):
            UserRegistration(
                username="newuser",
                email="not-an-email",
                password="StrongPass1",
            )

    def test_rejects_username_starting_with_special(self):
        with pytest.raises(Exception):
            UserRegistration(
                username=".dotuser",
                email="dot@example.com",
                password="StrongPass1",
            )

    def test_rejects_username_ending_with_special(self):
        with pytest.raises(Exception):
            UserRegistration(
                username="dotuser.",
                email="dot@example.com",
                password="StrongPass1",
            )

    def test_validates_name_letters_spaces_hyphens(self):
        reg = UserRegistration(
            username="newuser",
            email="new@example.com",
            password="StrongPass1",
            first_name="Mary-Jane",
            last_name="O'Brien",
        )
        assert reg.first_name == "Mary-Jane"
        assert reg.last_name == "O'Brien"

    def test_rejects_name_with_numbers(self):
        with pytest.raises(Exception):
            UserRegistration(
                username="newuser",
                email="new@example.com",
                password="StrongPass1",
                first_name="John123",
            )

    def test_accepts_none_names(self):
        reg = UserRegistration(
            username="newuser",
            email="new@example.com",
            password="StrongPass1",
        )
        assert reg.first_name is None
        assert reg.last_name is None

    def test_email_normalized_to_lowercase(self):
        reg = UserRegistration(
            username="newuser",
            email="User@Example.COM",
            password="StrongPass1",
        )
        assert reg.email == "user@example.com"

    def test_rejects_username_with_invalid_chars(self):
        with pytest.raises(Exception):
            UserRegistration(
                username="user name",  # space not allowed
                email="u@example.com",
                password="StrongPass1",
            )
