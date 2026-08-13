"""Secure_KeyStorage_Worker - wraps `keyring` for OS-native encrypted secret storage.

PATH: engines/workers/security/secure_keystorage_worker.py  (REPLACE ENTIRE FILE)

FIX (the real, recurring cause of the login-screen delay): the earlier warm-up fix only
pre-initialized keyring's backend DETECTION - every actual credential lookup (auth_username,
totp_secret, etc.) still hit the real Windows Credential Manager API fresh, every single
splash->login handoff, with no caching at all. None of these values change moment-to-moment
during a session - they only change when Manage Account Security explicitly writes a new one.
Added an in-memory cache: each key is read from the real keychain AT MOST ONCE per server
process lifetime; every read after that (including every subsequent screen transition) is
served instantly from memory. Writes update the cache immediately, so nothing goes stale.
"""
from __future__ import annotations
import uuid

try:
    import keyring
except ImportError:
    keyring = None

_SERVICE = "QuantumTrade19"


class SecureKeyStorageWorker:
    def __init__(self, force_memory: bool = False) -> None:
        self._force_memory = force_memory
        self._memory_fallback: dict[str, str] = {}
        self._cache: dict[str, str | None] = {}
        self._warm_up_keyring_backend()

    def _warm_up_keyring_backend(self) -> None:
        """Force keyring's lazy backend auto-detection to happen now, at startup."""
        if self._use_keychain():
            try:
                keyring.get_password(_SERVICE, "__warmup__")
            except Exception:
                pass

    def _use_keychain(self) -> bool:
        return keyring is not None and not self._force_memory

    def set_secret(self, key: str, value: str) -> None:
        if self._use_keychain():
            keyring.set_password(_SERVICE, key, value)
        else:
            self._memory_fallback[key] = value
        self._cache[key] = value  # keep the cache authoritative immediately

    def get_secret(self, key: str) -> str | None:
        if key in self._cache:
            return self._cache[key]
        if self._use_keychain():
            value = keyring.get_password(_SERVICE, key)
        else:
            value = self._memory_fallback.get(key)
        self._cache[key] = value
        return value

    def delete_secret(self, key: str) -> None:
        if self._use_keychain():
            try:
                keyring.delete_password(_SERVICE, key)
            except Exception:
                pass
        else:
            self._memory_fallback.pop(key, None)
        self._cache.pop(key, None)

    def get_or_create_salt(self) -> str:
        salt = self.get_secret("auth_salt")
        if salt is None:
            salt = uuid.uuid4().hex
            self.set_secret("auth_salt", salt)
        return salt
