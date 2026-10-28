"""PATH: engines/workers/setup/setup_buffer_settings.py  (NEW FILE)

FT-H.3 - SL buffer setting per symbol. Spec: docs/specs/File_04.1c_Callouts_Spec_v1.md, section 8.

The SL buffer is a number of ticks that is added below (Bull) or above (Bear) the setup extreme
to get the SL. Default 7 ticks, adjustable per symbol by Jay. The value feeds the buffer_ticks
argument of SetupOutcomeWorker.track().

Saved with the existing SettingsPersistenceWorker (data/settings.json, non-secret):
- the default under the key "setup_sl_buffer_default_ticks"
- a per-symbol override under per_symbol_settings[symbol]["sl_buffer_ticks"]
Other keys of per_symbol_settings are never touched. A symbol without an override gets the default.
Not wired into the app or the Settings screen yet (that is the next step).
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Union

from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker

DEFAULT_BUFFER_TICKS = 7
MAX_BUFFER_TICKS = 1000
DEFAULT_KEY = "setup_sl_buffer_default_ticks"
SYMBOL_KEY = "sl_buffer_ticks"
PER_SYMBOL_KEY = "per_symbol_settings"

Number = Union[int, float]


def clean_buffer_ticks(value: Any) -> Number:
    """Returns a valid buffer (0 to 1000 ticks) or raises ValueError."""
    if isinstance(value, bool) or value is None:
        raise ValueError("buffer ticks must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("buffer ticks must be a number") from None
    if not math.isfinite(number):
        raise ValueError("buffer ticks must be a finite number")
    if number < 0 or number > MAX_BUFFER_TICKS:
        raise ValueError(f"buffer ticks must be between 0 and {MAX_BUFFER_TICKS}")
    return int(number) if number == int(number) else round(number, 4)


class SetupBufferSettings:
    """Adapter on SettingsPersistenceWorker for the SL buffer (default and per symbol)."""

    def __init__(self, persistence: Optional[SettingsPersistenceWorker] = None) -> None:
        self._persistence = persistence or SettingsPersistenceWorker()

    def get_default_ticks(self) -> Number:
        raw = self._persistence.load().get(DEFAULT_KEY)
        try:
            return clean_buffer_ticks(raw)
        except ValueError:
            return DEFAULT_BUFFER_TICKS

    def set_default_ticks(self, value: Any) -> Number:
        number = clean_buffer_ticks(value)
        self._persistence.save({DEFAULT_KEY: number})
        return number

    def get_buffer_ticks(self, symbol: str) -> Number:
        raw = self._persistence.get_per_symbol_setting(symbol, SYMBOL_KEY, None)
        if raw is None:
            return self.get_default_ticks()
        try:
            return clean_buffer_ticks(raw)
        except ValueError:
            return self.get_default_ticks()

    def has_override(self, symbol: str) -> bool:
        return self._persistence.get_per_symbol_setting(symbol, SYMBOL_KEY, None) is not None

    def set_buffer_ticks(self, symbol: str, value: Any) -> Number:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("symbol must be a non-empty text")
        number = clean_buffer_ticks(value)
        self._persistence.set_per_symbol_setting(symbol, SYMBOL_KEY, number)
        return number

    def reset_symbol(self, symbol: str) -> bool:
        """Removes the override of one symbol (it then uses the default). Returns True if one existed."""
        per_symbol = dict(self._persistence.load().get(PER_SYMBOL_KEY, {}))
        bucket = dict(per_symbol.get(symbol, {}))
        if SYMBOL_KEY not in bucket:
            return False
        del bucket[SYMBOL_KEY]
        if bucket:
            per_symbol[symbol] = bucket
        else:
            per_symbol.pop(symbol, None)
        self._persistence.save({PER_SYMBOL_KEY: per_symbol})
        return True

    def overrides(self) -> Dict[str, Number]:
        result: Dict[str, Number] = {}
        for symbol, bucket in self._persistence.load().get(PER_SYMBOL_KEY, {}).items():
            if isinstance(bucket, dict) and SYMBOL_KEY in bucket:
                try:
                    result[symbol] = clean_buffer_ticks(bucket[SYMBOL_KEY])
                except ValueError:
                    continue
        return result
