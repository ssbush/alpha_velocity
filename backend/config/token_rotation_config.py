"""
Refresh Token Rotation Configuration

Implements token family tracking for refresh token rotation.
Each login creates a "family" of refresh tokens. On each refresh,
the old token is invalidated and a new one issued. If a revoked
token is replayed (indicating theft), the entire family is revoked.

Uses in-memory tracking (consistent with LoginAttemptTracker pattern).
"""

import os
import logging
import threading
import time
import uuid
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration from environment
TOKEN_ROTATION_ENABLED = os.getenv('TOKEN_ROTATION_ENABLED', 'true').lower() == 'true'

# Refresh token lifetime in seconds (must match auth.py REFRESH_TOKEN_EXPIRE_MINUTES)
_REFRESH_TOKEN_LIFETIME_SECONDS = 60 * 24 * 7 * 60  # 7 days in seconds


class RefreshTokenTracker:
    """
    Tracks refresh token families and enforces single-use rotation.

    Each login/register creates a new family (UUID). Each family tracks
    the latest valid jti. On refresh:
      - If jti matches latest → rotate (issue new jti, invalidate old)
      - If jti doesn't match → revoke entire family (likely token theft)

    Thread-safe via threading.Lock().
    """

    def __init__(self, enabled: Optional[bool] = None):
        self._enabled = enabled if enabled is not None else TOKEN_ROTATION_ENABLED
        # family_id -> {"latest_jti": str, "user_id": int, "created_at": float}
        self._families: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._operation_count = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def register_family(self, family: str, jti: str, user_id: int) -> None:
        """Register a new token family (called on login/register)."""
        with self._lock:
            self._families[family] = {
                "latest_jti": jti,
                "user_id": user_id,
                "created_at": time.time(),
            }
            self._operation_count += 1
            if self._operation_count % 100 == 0:
                self._cleanup_expired()

    def validate_and_rotate(self, family: str, jti: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a refresh token and rotate to a new jti.

        Returns:
            (valid, new_jti):
              - (True, new_jti) if the token is valid and was rotated
              - (False, None) if the token is invalid or the family is revoked
        """
        if not self._enabled:
            # When disabled, always valid — generate a new jti for the new token
            return True, str(uuid.uuid4())

        with self._lock:
            entry = self._families.get(family)
            if entry is None:
                # Unknown family — token not tracked (e.g. issued before rotation was enabled)
                # Allow it but start tracking
                return True, str(uuid.uuid4())

            if entry["latest_jti"] != jti:
                # Replay of a previously used token — possible theft
                # Revoke entire family
                del self._families[family]
                logger.warning(
                    f"Token reuse detected for family {family[:8]}... — "
                    f"revoking entire family (user_id={entry['user_id']})"
                )
                return False, None

            # Valid token — rotate to new jti
            new_jti = str(uuid.uuid4())
            entry["latest_jti"] = new_jti
            return True, new_jti

    def revoke_family(self, family: str) -> bool:
        """Revoke all tokens in a family. Returns True if the family existed."""
        with self._lock:
            return self._families.pop(family, None) is not None

    def revoke_all_for_user(self, user_id: int) -> int:
        """Revoke all token families for a user. Returns count of revoked families."""
        with self._lock:
            to_remove = [
                fam for fam, entry in self._families.items()
                if entry["user_id"] == user_id
            ]
            for fam in to_remove:
                del self._families[fam]
            return len(to_remove)

    def clear(self) -> None:
        """Clear all tracking data."""
        with self._lock:
            self._families.clear()

    def _cleanup_expired(self) -> None:
        """Remove families older than refresh token lifetime (called under lock)."""
        cutoff = time.time() - _REFRESH_TOKEN_LIFETIME_SECONDS
        expired = [
            fam for fam, entry in self._families.items()
            if entry["created_at"] < cutoff
        ]
        for fam in expired:
            del self._families[fam]


# Module-level singleton
refresh_token_tracker = RefreshTokenTracker()


def get_token_rotation_config() -> dict:
    """Get current token rotation configuration."""
    return {
        "enabled": TOKEN_ROTATION_ENABLED,
    }


def log_token_rotation_config() -> None:
    """Log token rotation configuration on startup."""
    config = get_token_rotation_config()

    if config["enabled"]:
        logger.info("Refresh token rotation ENABLED")
    else:
        logger.warning("Refresh token rotation DISABLED — tokens will not be rotated")
