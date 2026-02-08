"""
Authentication and Authorization Module
Handles user authentication, JWT tokens, and password hashing
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator, Field
import os
import logging
import secrets

from .validators.validators import validate_email, sanitize_string

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "your-secret-key-change-in-production"


def _get_secret_key() -> str:
    """Get JWT secret key with environment-appropriate behavior."""
    key = os.getenv("SECRET_KEY", "").strip()
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        if not key or key == _DEFAULT_SECRET:
            raise RuntimeError(
                "SECRET_KEY must be set to a secure random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return key

    # Development / staging: auto-generate if missing
    if not key or key == _DEFAULT_SECRET:
        key = secrets.token_urlsafe(32)
        logger.warning(
            "SECRET_KEY not set — using auto-generated key. "
            "Sessions will not survive restarts. "
            "Set SECRET_KEY in your environment for persistent sessions."
        )
    return key


# Security configuration
SECRET_KEY = _get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data"""
    user_id: int
    username: str
    exp: Optional[datetime] = None


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    """JWT token pair response with access and refresh tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds


class UserCredentials(BaseModel):
    """User login credentials"""
    username: str = Field(..., min_length=3, max_length=50, description="Username or email")
    password: str = Field(..., min_length=8, max_length=72, description="Password")

    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not v or not isinstance(v, str):
            raise ValueError("Username is required")

        # Sanitize input
        v = sanitize_string(v, max_length=50, allow_newlines=False)

        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")

        return v.strip()

    @validator('password')
    def validate_password(cls, v):
        """Validate password"""
        if not v or not isinstance(v, str):
            raise ValueError("Password is required")

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(v) > 72:
            raise ValueError("Password cannot exceed 72 characters (bcrypt limit)")

        return v


class UserRegistration(BaseModel):
    """User registration data"""
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=72, description="Password (8-72 characters)")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")

    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if not v or not isinstance(v, str):
            raise ValueError("Username is required")

        # Sanitize input
        v = sanitize_string(v, max_length=50, allow_newlines=False)

        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")

        # Username can only contain alphanumeric, underscore, hyphen, dot
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError(
                "Username can only contain letters, numbers, dots, underscores, and hyphens"
            )

        # Can't start or end with special characters
        if v[0] in '._-' or v[-1] in '._-':
            raise ValueError("Username cannot start or end with special characters")

        return v.strip()

    @validator('email')
    def validate_email_field(cls, v):
        """Validate email address"""
        if not v:
            raise ValueError("Email is required")

        return validate_email(v)

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if not v or not isinstance(v, str):
            raise ValueError("Password is required")

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(v) > 72:
            raise ValueError("Password cannot exceed 72 characters (bcrypt limit)")

        # Check password strength
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )

        return v

    @validator('first_name', 'last_name')
    def validate_name(cls, v):
        """Validate name fields"""
        if not v:
            return v

        # Sanitize input
        v = sanitize_string(v, max_length=100, allow_newlines=False)

        # Names should only contain letters, spaces, hyphens, apostrophes
        import re
        if not re.match(r"^[a-zA-Z\s'-]+$", v):
            raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")

        return v.strip()


class UserProfile(BaseModel):
    """User profile response"""
    id: int
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    created_at: datetime


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    # Ensure password is properly encoded and within bcrypt's 72 byte limit
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')[:72].decode('utf-8')
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    # Ensure password is properly encoded and within bcrypt's 72 byte limit
    if isinstance(password, str):
        password = password.encode('utf-8')[:72].decode('utf-8')
    return pwd_context.hash(password)


def create_access_token(user_id: int, username: str) -> str:
    """Create a JWT access token"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "user_id": user_id,
        "username": username,
        "type": "access",
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, username: str) -> str:
    """Create a JWT refresh token"""
    expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "user_id": user_id,
        "username": username,
        "type": "refresh",
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """Decode and verify a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        token_type: str = payload.get("type", "access")  # default for old tokens
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))

        if user_id is None or username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected access token"
            )

        return TokenData(user_id=user_id, username=username, exp=exp)

    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token"
        )


def decode_refresh_token(token: str) -> TokenData:
    """Decode and verify a JWT refresh token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        token_type: str = payload.get("type")
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))

        if user_id is None or username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token"
            )

        return TokenData(user_id=user_id, username=username, exp=exp)

    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Dependency to get the current authenticated user from the JWT token
    Usage: user = Depends(get_current_user)
    """
    token = credentials.credentials
    return decode_access_token(token)


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Dependency to get just the current user ID
    Usage: user_id = Depends(get_current_user_id)
    """
    token = credentials.credentials
    token_data = decode_access_token(token)
    return token_data.user_id
