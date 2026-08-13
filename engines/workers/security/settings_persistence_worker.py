"""Settings_Persistence_Worker - reads/writes non-secret runtime settings to data/settings.json.

PATH: engines/workers/security/settings_persistence_worker.py  (REPLACE ENTIRE FILE)

FIX: same principle as secure_keystorage_worker.py - `load()` used to re-read and re-parse
data/settings.json from disk on every single call (including on every splash->login handoff,
via is_totp_enabled()). Added an in-memory cache: the file is read from disk once, then served
from memory; `save()` updates both the in-memory cache and the on-disk file together, so
nothing ever goes stale, but repeated reads within a session cost nothing.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

_SETTINGS_PATH = Path("data") / "settings.json"
_DEFAULTS: dict[str, Any] = {
    "theme_key": "blue-night",
    "sound_master_on": True,
    "dnd_on": False,
    "paper_mode": True,
    "run_on_startup": False,
    "totp_enabled": False,
    "telegram_notify_enabled": False,
    "discord_notify_enabled": False,
    "transition_effects_enabled": ["dissolve", "zoom-in", "slide-up", "flip-x", "blur-in"],
    "transition_mode": "shuffle",
}


class SettingsPersistenceWorker:
    def __init__(self, path: Path = _SETTINGS_PATH) -> None:
        self._path = path
        self._cache: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        if self._cache is not None:
            return dict(self._cache)
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(_DEFAULTS, indent=2))
            self._cache = dict(_DEFAULTS)
            return dict(self._cache)
        try:
            on_disk = json.loads(self._path.read_text())
        except json.JSONDecodeError:
            on_disk = {}
        merged = dict(_DEFAULTS)
        merged.update(on_disk)
        self._cache = merged
        return dict(merged)

    def save(self, settings: dict[str, Any]) -> None:
        current = self.load()
        current.update(settings)
        self._cache = current
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(current, indent=2))
