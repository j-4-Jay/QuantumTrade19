"""Executable AppState mixin: SL buffer settings (File 04.1c, FT-H.3 Step B).

PATH: state/app_state_mixins/setup_buffer_mixin.py  (NEW FILE)

Shows and saves the SL buffer (ticks) for the Settings > Trading Defaults card.
It uses the app's own settings object (_engine.security.persistence) through
engines/workers/setup/setup_buffer_settings.py, so no other saved setting is overwritten.
A bad entry is not saved; the card shows a short message instead.
"""
from __future__ import annotations

import reflex as rx

from engines.workers.setup.setup_buffer_settings import SetupBufferSettings
from engines.workers.setup.setup_buffer_view import buffer_rows
from state.app_state_mixins.shared import _engine


def _buffer_settings() -> SetupBufferSettings:
    return SetupBufferSettings(_engine.security.persistence)


def _active_symbols() -> list:
    try:
        return list(_engine.market_data.symbol_registry.get_active_symbols())
    except Exception:
        return []


def _fill(state, message: str = "") -> None:
    settings = _buffer_settings()
    state.sl_buffer_default_text = str(settings.get_default_ticks())
    state.sl_buffer_nonce = int(state.sl_buffer_nonce) + 1
    nonce = state.sl_buffer_nonce
    state.sl_buffer_default_key = f"{nonce}-{state.sl_buffer_default_text}"
    rows = buffer_rows(settings, _active_symbols())
    state.sl_buffer_rows = [dict(row, key=f"{nonce}-{row['symbol']}-{row['ticks']}") for row in rows]
    state.sl_buffer_message = message


class SetupBufferMixin(rx.State, mixin=True):
    sl_buffer_default_text: str = "7"
    sl_buffer_rows: list[dict[str, str]] = []
    sl_buffer_message: str = ""
    sl_buffer_nonce: int = 0
    sl_buffer_default_key: str = "0-7"

    def load_sl_buffer_settings(self) -> None:
        _fill(self)

    def set_sl_buffer_default(self, value: str) -> None:
        try:
            number = _buffer_settings().set_default_ticks(value)
        except ValueError as error:
            _fill(self, f"Not saved: {error}")
            return
        _fill(self, f"Default saved: {number} ticks")

    def set_sl_buffer_symbol(self, symbol: str, value: str) -> None:
        settings = _buffer_settings()
        if str(value).strip() == "":
            settings.reset_symbol(symbol)
            _fill(self, f"{symbol}: back to the default")
            return
        try:
            number = settings.set_buffer_ticks(symbol, value)
        except ValueError as error:
            _fill(self, f"Not saved: {error}")
            return
        _fill(self, f"{symbol}: {number} ticks saved")

    def reset_sl_buffer_symbol(self, symbol: str) -> None:
        _buffer_settings().reset_symbol(symbol)
        _fill(self, f"{symbol}: back to the default")
