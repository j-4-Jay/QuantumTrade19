"""Settings_Persistence_Worker - reads/writes non-secret runtime settings to data/settings.json.

PATH: engines/workers/security/settings_persistence_worker.py  (REPLACE ENTIRE FILE)

FIX (ISSUE-010): added an optional `force_memory` flag, mirroring the exact
same pattern SecureKeyStorageWorker already uses. When True, this worker
never touches the real data/settings.json file at all - it only ever
operates on an in-memory copy of the defaults. Default is False, so every
existing call site (which never passes this argument) behaves EXACTLY as
before - this is a pure, backward-compatible addition, not a change to any
existing behavior.

Root cause this fixes: SecurityMonitor.__init__ already passes
force_memory=force_memory to SecureKeyStorageWorker, but was never able to
pass it here because this class had no such parameter - meaning every
test using SecurityMonitor(force_memory=True) was still silently reading
and writing the one real settings file on disk, letting state leak between
test runs (e.g. a TOTP-enabled flag set by one test bleeding into another
test that expected a clean slate).

CHANGE (unchanged from before): added tab_transition_effects_enabled / tab_transition_mode
defaults - the tab-switch animation (Dashboard <-> Trading Panel <-> Journal & Reports <->
Alerts <-> Settings) is independently configurable from Settings, separate from the
screen-entrance transition pool.
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
    "tab_transition_effects_enabled": ["slide-left"],
    "tab_transition_mode": "single",
    "per_symbol_settings": {},
}


class SettingsPersistenceWorker:
    def __init__(self, path: Path = _SETTINGS_PATH, force_memory: bool = False) -> None:
        self._path = path
        self._force_memory = force_memory
        self._cache: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        if self._cache is not None:
            return dict(self._cache)
        if self._force_memory:
            self._cache = dict(_DEFAULTS)
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
        if self._force_memory:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(current, indent=2))

    def get_per_symbol_setting(self, symbol: str, key: str, default=None):
        per_symbol = self.load().get("per_symbol_settings", {})
        return per_symbol.get(symbol, {}).get(key, default)

    def set_per_symbol_setting(self, symbol: str, key: str, value) -> None:
        current = self.load()
        per_symbol = dict(current.get("per_symbol_settings", {}))
        symbol_bucket = dict(per_symbol.get(symbol, {}))
        symbol_bucket[key] = value
        per_symbol[symbol] = symbol_bucket
        self.save({"per_symbol_settings": per_symbol})
