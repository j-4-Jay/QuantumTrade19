"""Auth_Login_Worker - verifies username/password against a securely hashed local credential.

PATH: engines/workers/security/auth_login_worker.py  (REPLACE ENTIRE FILE)

CHANGE: password hashing upgraded from raw SHA-256 to argon2id (via argon2-cffi).
argon2's PasswordHasher embeds its own random salt + algorithm parameters directly inside
the returned hash string ("$argon2id$v=19$m=65536,t=3,p=4$...") — the old manual
get_or_create_salt() + SHA-256 concatenation is no longer used for password hashing.
BREAKING: any account registered under the old SHA-256 hash format will fail verify() after
this lands — verify() catches InvalidHashError for those old-format strings and returns False
rather than crashing. Existing test accounts must re-register (set_credentials again) once
this is deployed. No dual-format fallback was requested, so none was added.
"""
from __future__ import annotations
import hmac
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from engines.workers.security.secure_keystorage_worker import SecureKeyStorageWorker
from config.settings import MIN_PASSWORD_LENGTH


_ph = PasswordHasher()


class AuthLoginWorker:
    def __init__(self, keystore: SecureKeyStorageWorker):
        self._keystore = keystore

    def is_valid_credentials(self, username, password):
        return len(username.strip()) >= 1 and len(password) >= MIN_PASSWORD_LENGTH

    def set_credentials(self, username, password):
        if not self.is_valid_credentials(username, password):
            return False
        self._keystore.set_secret("auth_username", username.strip())
        self._keystore.set_secret("auth_password_hash", _ph.hash(password))
        return True

    def verify(self, username, password):
        if not self.is_valid_credentials(username, password):
            return False
        su = self._keystore.get_secret("auth_username")
        sh = self._keystore.get_secret("auth_password_hash")
        if su is None or sh is None:
            return False
        if not hmac.compare_digest(su, username.strip()):
            return False
        try:
            _ph.verify(sh, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        if _ph.check_needs_rehash(sh):
            self._keystore.set_secret("auth_password_hash", _ph.hash(password))
        return True