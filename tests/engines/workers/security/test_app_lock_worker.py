import time
from engines.workers.security.app_lock_worker import AppLockWorker

def test_lock_unlock():
    w = AppLockWorker(auto_lock_seconds=999)
    assert w.is_locked() is False
    w.lock(); assert w.is_locked() is True
    w.unlock(); assert w.is_locked() is False
