from __future__ import annotations
import time

class AppLockWorker:
    def __init__(self, auto_lock_seconds=900):
        self._auto = auto_lock_seconds; self._last = time.time(); self._locked = False
    def touch(self): self._last = time.time()
    def lock(self): self._locked = True
    def unlock(self): self._locked = False; self.touch()
    def is_locked(self):
        if not self._locked and (time.time() - self._last) > self._auto: self._locked = True
        return self._locked
