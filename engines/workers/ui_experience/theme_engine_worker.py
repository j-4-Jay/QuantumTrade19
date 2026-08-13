from __future__ import annotations
from config.settings import THEMES, DEFAULT_THEME_KEY, THEME_ORDER
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker

class ThemeEngineWorker:
    def __init__(self, persistence: SettingsPersistenceWorker):
        self._persistence = persistence
    def get_active_key(self):
        key = self._persistence.load().get("theme_key", DEFAULT_THEME_KEY)
        return key if key in THEMES else DEFAULT_THEME_KEY
    def get_active_theme(self):
        return THEMES[self.get_active_key()]
    def set_active_key(self, key):
        if key not in THEMES: return False
        self._persistence.save({"theme_key": key}); return True
    def cycle(self):
        cur = self.get_active_key()
        nxt = THEME_ORDER[(THEME_ORDER.index(cur) + 1) % len(THEME_ORDER)]
        self.set_active_key(nxt); return nxt
