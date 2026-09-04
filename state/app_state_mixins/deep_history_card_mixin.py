"""Executable AppState mixin: Deep Historical Data Settings card.

PATH: state/app_state_mixins/deep_history_card_mixin.py (NEW FILE)

FIX v0.4.45 - card shows "0.003 days" right after startup despite tons of
real data already downloaded, while the "smaller duration" confirm dialog
correctly shows the real large number moments later. Root cause: both
paths read get_deep_history_progress()'s "covered_days" field, which
measures ONLY the newest UNBROKEN chunk of candles (CandleStoreWorker's
"contiguous_days") - a real, honest metric, but the wrong one for "how
much history do I actually have". If there is ever a tiny gap right at
the live edge (very common immediately after a restart, before the
background gap-healer's next pass), that metric collapses toward zero
even though a much larger separate archive sits just behind that one
small gap. The confirm dialog "looked correct" only because a few seconds
had passed and the auto-healer had already closed that edge gap by then -
both were reading the same fragile metric, just at different moments.

Fix: this card now sums ALL physically stored ranges
(candle_store.get_physical_ranges(symbol, tf)) instead of using the
newest-contiguous-chunk-only metric, for both the mini-bar "days in
database" label AND the confirm-dialog's "already has X days" check -
both numbers are now guaranteed to be in sync and reflect the true total
archive size regardless of a small live-edge gap.

NOTE: this assumes CandleStoreWorker exposes get_physical_ranges(symbol,
timeframe) -> list[tuple[int, int]] (confirmed present in an earlier
version of that file). If your current candle_store_worker.py has since
renamed or removed this method, this card will raise an AttributeError -
if that happens, paste that file's real current content and I will adapt
this in one pass.

FIX v0.4.39 (carried forward) - poll_deep_history_cards runs every 10s and
self-stops when leaving the Settings tab.
"""
from __future__ import annotations

import asyncio
from typing import List, TypedDict

import reflex as rx

from state.app_state_mixins.shared import _engine, TRADING_PANEL_TF_OPTIONS

_DURATION_UNIT_TO_DAYS = {"Days": 1, "Months": 30, "Years": 365}
_BUSY_STATES = {"downloading", "queued"}
_POLL_INTERVAL_SECONDS = 10.0
_DAY_MS = 86_400_000


class GapMarker(TypedDict):
    left_pct: float
    width_pct: float


class TfRow(TypedDict):
    tf: str
    state: str
    green_pct: int
    db_label: str
    present_range_label: str
    broker_label: str
    has_gap: bool
    gap_labels: List[str]
    gaps: List[GapMarker]
    is_busy: bool
    eta_label: str
    broker_probed: bool


class CardRow(TypedDict):
    symbol: str
    duration_value: str
    duration_unit: str
    confirm_open: bool
    confirm_message: str
    combined_active: bool
    combined_percent: int
    tfs: List[TfRow]


def _format_eta(seconds) -> str:
    if seconds is None:
        return ""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"~{seconds}s remaining"
    minutes = seconds // 60
    if minutes < 60:
        return f"~{minutes}m remaining"
    hours = minutes // 60
    return f"~{hours}h {minutes % 60}m remaining"


def _total_stored_days(symbol: str, tf: str) -> float:
    """Sums ALL physically stored candle ranges for this symbol/timeframe -
    not just the newest unbroken chunk. This is the single source of truth
    for "how much history do I actually have", used consistently by both
    the mini-bar label and the confirm-dialog check below."""
    ranges = _engine.market_data.candle_store.get_physical_ranges(symbol, tf)
    total_ms = sum(end - start for start, end in ranges)
    return round(total_ms / _DAY_MS, 3)


class DeepHistoryCardMixin(rx.State, mixin=True):
    def set_card_duration_value(self, symbol: str, value: str) -> None:
        current = dict(self._card_duration_value)
        current[symbol] = value
        self._card_duration_value = current

    def set_card_duration_unit(self, symbol: str, value: str) -> None:
        current = dict(self._card_duration_unit)
        current[symbol] = value
        self._card_duration_unit = current

    def _requested_days_for(self, symbol: str) -> int:
        raw = self._card_duration_value.get(symbol, "5")
        unit = self._card_duration_unit.get(symbol, "Days")
        try:
            amount = max(1, int(raw))
        except ValueError:
            amount = 5
        return amount * _DURATION_UNIT_TO_DAYS.get(unit, 1)

    def _start_symbol_download(self, symbol: str, requested_days: int) -> None:
        for tf in TRADING_PANEL_TF_OPTIONS:
            _engine.market_data.start_deep_history(symbol, tf, requested_days)
        _engine.market_data.start_ceiling_probe(symbol, TRADING_PANEL_TF_OPTIONS[0])

    def handle_duration_keydown(self, symbol: str, key: str) -> None:
        """Pressing Enter inside a card's duration input starts the download
        directly - no separate Download button. If the requested duration is
        SMALLER than what is already stored locally for at least one of this
        symbol's timeframes, opens a confirmation dialog instead (nothing is
        ever deleted or reduced by proceeding - it simply won't try to
        backfill further back than the number just entered). Uses
        _total_stored_days() (sum of ALL ranges) - same metric the mini-bar
        label uses, so this check and what the card displays never
        disagree."""
        if key != "Enter":
            return
        requested_days = self._requested_days_for(symbol)
        max_local_days = 0.0
        for tf in TRADING_PANEL_TF_OPTIONS:
            max_local_days = max(max_local_days, _total_stored_days(symbol, tf))

        if max_local_days > requested_days:
            confirm_open = dict(self._card_confirm_open)
            confirm_message = dict(self._card_confirm_message)
            pending = dict(self._card_pending_requested_days)
            confirm_open[symbol] = True
            confirm_message[symbol] = (
                f"{symbol} already has {max_local_days:g} days stored locally for at "
                f"least one timeframe - more than the {requested_days} days you just "
                f"entered.\n\nProceeding is safe: nothing is ever deleted or reduced. "
                f"It simply won't download further back than what you typed. Cancel "
                f"instead if you meant to enter a larger number."
            )
            pending[symbol] = requested_days
            self._card_confirm_open = confirm_open
            self._card_confirm_message = confirm_message
            self._card_pending_requested_days = pending
            return

        self._start_symbol_download(symbol, requested_days)

    def cancel_download_confirm(self, symbol: str) -> None:
        confirm_open = dict(self._card_confirm_open)
        confirm_open[symbol] = False
        self._card_confirm_open = confirm_open

    def confirm_download_proceed(self, symbol: str) -> None:
        confirm_open = dict(self._card_confirm_open)
        confirm_open[symbol] = False
        self._card_confirm_open = confirm_open
        requested_days = self._card_pending_requested_days.get(symbol, 5)
        self._start_symbol_download(symbol, requested_days)

    def cancel_symbol_downloads(self, symbol: str) -> None:
        for tf in TRADING_PANEL_TF_OPTIONS:
            _engine.market_data.cancel_deep_history(symbol, tf)

    def delete_symbol_history(self, symbol: str) -> None:
        for tf in TRADING_PANEL_TF_OPTIONS:
            _engine.market_data.delete_deep_history(symbol, tf)

    @rx.event(background=True)
    async def poll_deep_history_cards(self):
        """Started from core_shell_mixin.py's on_load() and again every
        time the Settings tab is opened. Self-stops once the user leaves
        the Settings tab (checked every tick)."""
        async with self:
            if self._deep_history_cards_poll_running:
                return
            self._deep_history_cards_poll_running = True
        try:
            while True:
                async with self:
                    if self.active_tab != "Settings":
                        break
                    self._deep_history_cards_poll_tick += 1
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        finally:
            async with self:
                self._deep_history_cards_poll_running = False

    @rx.var
    def deep_history_symbol_cards(self) -> List[CardRow]:
        """Builds one card per active symbol from live MasterAppEngine
        interfaces only. "days in database" now uses _total_stored_days()
        (sum of every physically stored range) instead of the fragile
        newest-contiguous-chunk-only metric - see module docstring."""
        _ = self._deep_history_cards_poll_tick

        cards: List[CardRow] = []
        symbols = _engine.market_data.symbol_registry.get_symbols_sorted(active_only=True)

        for symbol in symbols:
            tf_rows: List[TfRow] = []
            combined_present = 0
            combined_required = 0
            any_busy = False

            for tf in TRADING_PANEL_TF_OPTIONS:
                progress = _engine.market_data.get_deep_history_progress(symbol, tf)
                present = int(progress.get("present_candles", 0))
                required = int(progress.get("required_candles", 0))
                total_days = _total_stored_days(symbol, tf)
                state = str(progress.get("state", "idle"))
                is_busy = state in _BUSY_STATES
                broker_ceiling_reached = bool(progress.get("broker_ceiling_reached", False))
                error = progress.get("error")

                ceiling = _engine.market_data.get_ceiling_days(symbol, tf)
                broker_probed = ceiling is not None
                broker_label = f"{ceiling} days" if ceiling is not None else "Not checked yet"

                if is_busy:
                    green_pct = int(progress.get("percent", 0))
                elif ceiling and ceiling > 0:
                    green_pct = int(round(min(100.0, (total_days / ceiling) * 100)))
                else:
                    green_pct = 100 if total_days > 0 else 0
                green_pct = max(0, min(100, green_pct))

                if error:
                    eta_label = f"Error: {error}"
                elif broker_ceiling_reached:
                    eta_label = "Broker has no more history for this range (real exchange data limit)."
                elif state == "complete":
                    eta_label = "Complete"
                else:
                    eta_label = _format_eta(progress.get("eta_seconds")) or ("Estimating..." if is_busy else "")

                tf_rows.append({
                    "tf": tf,
                    "state": state,
                    "green_pct": green_pct,
                    "db_label": f"{total_days:g} days in QT19 database",
                    "present_range_label": f"{present:,} candles present",
                    "broker_label": broker_label,
                    "has_gap": False,
                    "gap_labels": [],
                    "gaps": [],
                    "is_busy": is_busy,
                    "eta_label": eta_label,
                    "broker_probed": broker_probed,
                })

                combined_present += present
                combined_required += required
                if is_busy:
                    any_busy = True

            combined_percent = int(round((combined_present / combined_required) * 100)) if combined_required else 0

            cards.append({
                "symbol": symbol,
                "duration_value": self._card_duration_value.get(symbol, "5"),
                "duration_unit": self._card_duration_unit.get(symbol, "Days"),
                "confirm_open": self._card_confirm_open.get(symbol, False),
                "confirm_message": self._card_confirm_message.get(symbol, ""),
                "combined_active": any_busy,
                "combined_percent": max(0, min(100, combined_percent)),
                "tfs": tf_rows,
            })

        return cards
