from __future__ import annotations
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker

class SoundEngineWorker:
    def __init__(self, persistence: SettingsPersistenceWorker):
        self._persistence = persistence
    def is_master_on(self):
        return bool(self._persistence.load().get("sound_master_on", True))
    def set_master(self, on):
        self._persistence.save({"sound_master_on": on})
    def toggle_master(self):
        new = not self.is_master_on(); self.set_master(new); return new
