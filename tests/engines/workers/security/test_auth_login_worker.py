from engines.workers.security.secure_keystorage_worker import SecureKeyStorageWorker
from engines.workers.security.auth_login_worker import AuthLoginWorker

def test_roundtrip():
    k = SecureKeyStorageWorker(force_memory=True); w = AuthLoginWorker(k)
    assert w.set_credentials("trader1", "S3cret!") is True
    assert w.verify("trader1", "S3cret!") is True

def test_rejects_wrong_password():
    k = SecureKeyStorageWorker(force_memory=True); w = AuthLoginWorker(k)
    w.set_credentials("trader1", "S3cret!")
    assert w.verify("trader1", "wrong") is False

def test_rejects_blank_username():
    k = SecureKeyStorageWorker(force_memory=True); w = AuthLoginWorker(k)
    assert w.set_credentials("   ", "S3cret!") is False
