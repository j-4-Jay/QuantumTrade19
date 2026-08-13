from __future__ import annotations
import hashlib, hmac
from engines.workers.security.secure_keystorage_worker import SecureKeyStorageWorker
from config.settings import MIN_PASSWORD_LENGTH

class AuthLoginWorker:
    def __init__(self, keystore: SecureKeyStorageWorker):
        self._keystore = keystore
    def _hash(self, password, salt):
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    def is_valid_credentials(self, username, password):
        return len(username.strip()) >= 1 and len(password) >= MIN_PASSWORD_LENGTH
    def set_credentials(self, username, password):
        if not self.is_valid_credentials(username, password): return False
        salt = self._keystore.get_or_create_salt()
        self._keystore.set_secret("auth_username", username.strip())
        self._keystore.set_secret("auth_password_hash", self._hash(password, salt))
        return True
    def verify(self, username, password):
        if not self.is_valid_credentials(username, password): return False
        su, sh = self._keystore.get_secret("auth_username"), self._keystore.get_secret("auth_password_hash")
        salt = self._keystore.get_or_create_salt()
        if su is None or sh is None: return False
        return hmac.compare_digest(su, username.strip()) and hmac.compare_digest(sh, self._hash(password, salt))
