from engines.workers.security.secure_keystorage_worker import SecureKeyStorageWorker
from engines.workers.security.totp_2fa_worker import Totp2FAWorker

def test_secret_persisted():
    k = SecureKeyStorageWorker(force_memory=True); w = Totp2FAWorker(k)
    assert w.get_or_create_secret() == w.get_or_create_secret()
