"""File 04 Core Correction v1 - "Strict Candle Reuse Lock" live setting holder.

PATH: engines/workers/setup/candle_reuse_settings.py (NEW FILE)

Setting name:    Strict Candle Reuse Lock
Setting default: OFF

| State | Behavior |
|---|---|
| ON  | Current locked behavior: once a candle is part of a CONFIRMED setup, it
       can never be used as Candle1/2/3 in any other setup on that
       (symbol, timeframe), ever again. |
| OFF | (default) Every candle that interacts with a POI runs the full
       Candle1/2/3 detection test, regardless of whether it or its
       neighbors already belong to a previously confirmed setup. |

WHY THIS TINY STANDALONE MODULE EXISTS: `_fsm_base.py` is a pure
engine-layer file with zero dependency on reflex/AppState, and it must
read this value LIVE on every `_step_waiting_c3()` call (not just once at
worker construction) so that flipping the toggle takes effect immediately
without an app restart. This module is the single shared point both sides
read/write:
    - `state/app_state_mixins/setup_visualization_mixin.py` calls
      `set_strict_candle_reuse_lock_enabled(...)` whenever the user flips
      the Settings toggle, and also on app/page load to restore the
      persisted value (same persisted-Settings pattern already used for
      poi_display_enabled / poi_strategy_enabled).
    - `_fsm_base.py` calls `is_strict_candle_reuse_lock_enabled()` fresh
      every time it needs to decide whether to enforce the no-reuse check.
"""
from __future__ import annotations

_strict_candle_reuse_lock_enabled: bool = False


def is_strict_candle_reuse_lock_enabled() -> bool:
    """Read the CURRENT live value. Never cache this result across calls."""
    return _strict_candle_reuse_lock_enabled


def set_strict_candle_reuse_lock_enabled(value: bool) -> None:
    """Update the live value. Call this from the Settings toggle handler
    and once on app/page load to restore the persisted value."""
    global _strict_candle_reuse_lock_enabled
    _strict_candle_reuse_lock_enabled = bool(value)
