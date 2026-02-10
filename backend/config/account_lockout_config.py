"""
Account Lockout Configuration

Provides per-username lockout after repeated failed login attempts.
This is a second layer of defense beyond IP-based rate limiting,
protecting against distributed brute-force attacks.

Uses in-memory tracking (consistent with rate limiter pattern).
Can be upgraded to Redis-backed storage later.
"""

import os
import logging
import threading
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration from environment
ACCOUNT_LOCKOUT_ENABLED = os.getenv('ACCOUNT_LOCKOUT_ENABLED', 'true').lower() == 'true'
MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv('MAX_FAILED_LOGIN_ATTEMPTS', '5'))
LOCKOUT_DURATION_MINUTES = int(os.getenv('LOCKOUT_DURATION_MINUTES', '15'))


class LoginAttemptTracker:
    """
    Tracks failed login attempts per username and enforces account lockout.

    Thread-safe via threading.Lock(). Usernames are lowercased to prevent
    case-based bypass.
    """

    def __init__(
        self,
        max_attempts: Optional[int] = None,
        lockout_duration_minutes: Optional[int] = None,
        enabled: Optional[bool] = None
    ):
        self._max_attempts = max_attempts if max_attempts is not None else MAX_FAILED_LOGIN_ATTEMPTS
        self._lockout_duration = (lockout_duration_minutes if lockout_duration_minutes is not None
                                  else LOCKOUT_DURATION_MINUTES) * 60  # convert to seconds
        self._enabled = enabled if enabled is not None else ACCOUNT_LOCKOUT_ENABLED
        self._attempts: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._check_count = 0

    def is_locked(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a username is currently locked out.

        Returns:
            (is_locked, seconds_remaining) — seconds_remaining is None if not locked.
        """
        if not self._enabled:
            return False, None

        key = username.lower()

        with self._lock:
            self._check_count += 1
            if self._check_count % 100 == 0:
                self._cleanup_expired()

            entry = self._attempts.get(key)
            if not entry or not entry.get('locked_until'):
                return False, None

            remaining = entry['locked_until'] - time.time()
            if remaining <= 0:
                # Lockout expired — clear entry
                del self._attempts[key]
                return False, None

            return True, int(remaining)

    def record_failed_attempt(self, username: str) -> Tuple[bool, Optional[int]]:
        """
        Record a failed login attempt.

        Returns:
            (is_now_locked, seconds_remaining) — if the account just became locked.
        """
        if not self._enabled:
            return False, None

        key = username.lower()

        with self._lock:
            entry = self._attempts.get(key)

            if entry and entry.get('locked_until'):
                remaining = entry['locked_until'] - time.time()
                if remaining > 0:
                    return True, int(remaining)
                # Expired lock — reset
                entry = None

            if not entry:
                entry = {'count': 0, 'locked_until': None}
                self._attempts[key] = entry

            entry['count'] += 1

            if entry['count'] >= self._max_attempts:
                entry['locked_until'] = time.time() + self._lockout_duration
                seconds_remaining = int(self._lockout_duration)
                logger.warning(
                    f"Account locked: {key} after {entry['count']} failed attempts "
                    f"(lockout: {seconds_remaining}s)"
                )
                return True, seconds_remaining

            return False, None

    def record_successful_login(self, username: str) -> None:
        """Clear failed attempt counter on successful login."""
        if not self._enabled:
            return

        key = username.lower()
        with self._lock:
            self._attempts.pop(key, None)

    def get_status(self, username: str) -> dict:
        """Get debug info for a username."""
        key = username.lower()
        with self._lock:
            entry = self._attempts.get(key)
            if not entry:
                return {'username': key, 'failed_attempts': 0, 'locked': False}

            locked = False
            seconds_remaining = None
            if entry.get('locked_until'):
                remaining = entry['locked_until'] - time.time()
                if remaining > 0:
                    locked = True
                    seconds_remaining = int(remaining)

            return {
                'username': key,
                'failed_attempts': entry['count'],
                'locked': locked,
                'seconds_remaining': seconds_remaining,
            }

    def clear(self, username: Optional[str] = None) -> None:
        """Clear tracking data. If username provided, clear only that user."""
        with self._lock:
            if username:
                self._attempts.pop(username.lower(), None)
            else:
                self._attempts.clear()

    def _cleanup_expired(self) -> None:
        """Remove expired lockout entries (called under lock)."""
        now = time.time()
        expired = [
            key for key, entry in self._attempts.items()
            if entry.get('locked_until') and entry['locked_until'] <= now
        ]
        for key in expired:
            del self._attempts[key]


# Module-level singleton
login_attempt_tracker = LoginAttemptTracker()


def get_lockout_config() -> dict:
    """Get current lockout configuration."""
    return {
        'enabled': ACCOUNT_LOCKOUT_ENABLED,
        'max_failed_attempts': MAX_FAILED_LOGIN_ATTEMPTS,
        'lockout_duration_minutes': LOCKOUT_DURATION_MINUTES,
    }


def log_lockout_config() -> None:
    """Log lockout configuration on startup."""
    config = get_lockout_config()

    if config['enabled']:
        logger.info("Account lockout ENABLED")
        logger.info(f"  Max failed attempts: {config['max_failed_attempts']}")
        logger.info(f"  Lockout duration: {config['lockout_duration_minutes']} minutes")
    else:
        logger.warning("Account lockout DISABLED - not recommended for production")
