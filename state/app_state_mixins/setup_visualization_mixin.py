"""File 04.1 - Trading Panel Setup Visualization - executable AppState mixin.

TARGET PATH: D:\\QuantumTrade19\\state\\app_state_mixins\\setup_visualization_mixin.py
REPLACE ENTIRE FILE - File 04 Core Correction v1 (revision 2).

Read-only against SetupDetectionMonitor (File 04, LOCKED at v0.4.0-alpha):
only calls _engine.get_confirmed_setups(symbol, tf) / _engine.get_pending_setups(symbol, tf).
Does NOT re-derive 123Bull/123Bear FSM logic, POI logic, or add new Worker logic.

Overlays/dots are built by engines/workers/setup/setup_visualization_helper.py
(pure functions) and then COMBINED with the existing POI overlays/dots via
combined_chart_overlays / combined_chart_dots / combined_chart_overlays_version
- this is what lets ui/components/trading_panel_chart.py feed BOTH POI and
setup markers into kline_chart.py's existing generic renderer with ZERO
changes to kline_chart.py itself.

============================================================================
FILE 04 CORE CORRECTION v1 - REVISION 2 FIX (this file)
============================================================================
BUG FOUND (post-deploy, live report): after wiring
`on_trading_panel_symbol_or_tf_changed()` into trading_panel_mixin.py's
symbol/tf setters, POI lines stopped appearing on the FIRST Trading Panel
page load, only reappearing after navigating away and back. Root cause:
those setters can fire during initial page-load state restoration (not
just a genuine user-initiated switch), and the previous revision of
`on_trading_panel_symbol_or_tf_changed()` refreshed ONLY the setup-
detection overlays. Since the chart actually renders POI + setup markers
together as one COMBINED list/version (`combined_chart_overlays` /
`combined_chart_dots` / `combined_chart_overlays_version`), refreshing
only one half could increment the combined version before POI data had
finished loading, leaving the chart's first paint stale until a full
remount forced everything back in sync.

FIX: `on_trading_panel_symbol_or_tf_changed()` now ALSO calls
`refresh_poi_chart_overlays()` (the existing POI mixin method) in the SAME
call, so POI and setup overlays always refresh together atomically -
never one without the other. Wrapped defensively in case that method name
ever changes, so a POI-side error can never block the setup-side refresh
or vice versa.
============================================================================
"""
from __future__ import annotations

import reflex as rx

from state.app_state_mixins.shared import engine as _engine
from engines.workers.setup.setup_visualization_helper import (
    build_setup_overlays_and_dots,
    build_setup_stats_rows,
)
from engines.workers.setup.candle_reuse_settings import set_strict_candle_reuse_lock_enabled
from engines.workers.setup.setup_callout_helper import build_setup_callouts
from engines.workers.setup.setup_buffer_settings import SetupBufferSettings

_DEFAULT_LOOKBACK_DAYS = "5"
_MIN_LOOKBACK_DAYS = 1
_MAX_LOOKBACK_DAYS = 90
_SETUP_VIZ_POLL_INTERVAL_SECONDS = 3.0


class SetupVisualizationMixin(rx.State, mixin=True):
    # --- "Detect setups from last N days" - persisted per symbol+timeframe,
    # same pattern as trading_panel_display_days_input/draft (03.1) ---
    setup_detect_lookback_days_map: dict[str, str] = {}
    setup_detect_lookback_days_draft: str = _DEFAULT_LOOKBACK_DAYS

    # --- Setup chart markers (confirmed candle-highlight + Candle3 icon,
    # pending subtle marker) ---
    setup_chart_overlays: list[dict] = []
    setup_chart_overlays_version: int = 0
    setup_dots: list[dict] = []
    setup_dots_version: int = 0

    # --- FT-H.4: callout data for each confirmed setup (drawn by kline_chart.py in a later step) ---
    setup_callouts: list[dict] = []
    setup_callouts_version: int = 0

    # --- Compact setup-stats panel: date-wise confirmed Bull/Bear/failed ---
    setup_stats_rows: list[dict] = []

    # --- New Settings toggle (File 04 Core Correction v1), default OFF ---
    strict_candle_reuse_lock_enabled: bool = False

    _setup_viz_poll_running: bool = False

    def _setup_viz_key(self) -> str:
        return f"{self.trading_panel_symbol}|{self.trading_panel_chart_tf}"

    def load_setup_detect_lookback(self) -> None:
        """Call this alongside load_poi_settings()/on_load() whenever the
        Trading Panel symbol or chart timeframe changes, so the saved N
        for THIS symbol+timeframe is restored (mirrors 03.1's Display Last
        X Days restore in core_shell_mixin.py's on_load()).

        Also restores the persisted Strict Candle Reuse Lock setting and
        mirrors it live into candle_reuse_settings, and performs an
        IMMEDIATE setup-visualization refresh (see
        on_trading_panel_symbol_or_tf_changed() below)."""
        settings = _engine.security.persistence.load()
        stored_map = settings.get("setup_detect_lookback_days_map", {})
        self.setup_detect_lookback_days_map = stored_map
        key = self._setup_viz_key()
        self.setup_detect_lookback_days_draft = stored_map.get(key, _DEFAULT_LOOKBACK_DAYS)

        stored_strict_lock = bool(settings.get("strict_candle_reuse_lock_enabled", False))
        self.strict_candle_reuse_lock_enabled = stored_strict_lock
        set_strict_candle_reuse_lock_enabled(stored_strict_lock)

        self.refresh_setup_visualization()

    def on_trading_panel_symbol_or_tf_changed(self) -> None:
        """Wired into trading_panel_mixin.py's set_trading_panel_symbol /
        set_trading_panel_chart_tf (spec Section 5). FIXED (revision 2):
        this now refreshes POI overlays AND setup overlays together in the
        SAME call, since the chart renders them as one combined list/
        version - refreshing only one half risked a stale first paint
        whenever this fires during initial page-load state restoration,
        not just a genuine user-initiated switch. Each half is wrapped
        independently so one failing can never block the other."""
        try:
            self.load_setup_detect_lookback()
        except Exception:
            pass
        try:
            self.refresh_poi_chart_overlays()
        except Exception:
            pass

    def set_setup_detect_lookback_draft(self, value: str) -> None:
        self.setup_detect_lookback_days_draft = value

    def commit_setup_detect_lookback_days(self) -> None:
        try:
            parsed = int(self.setup_detect_lookback_days_draft)
        except ValueError:
            parsed = int(_DEFAULT_LOOKBACK_DAYS)
        parsed = max(_MIN_LOOKBACK_DAYS, min(_MAX_LOOKBACK_DAYS, parsed))
        self.setup_detect_lookback_days_draft = str(parsed)
        key = self._setup_viz_key()
        self.setup_detect_lookback_days_map = {**self.setup_detect_lookback_days_map, key: str(parsed)}
        _engine.security.persistence.save({
            "setup_detect_lookback_days_map": dict(self.setup_detect_lookback_days_map)
        })
        self.refresh_setup_visualization()

    def handle_setup_lookback_keydown(self, key: str) -> None:
        if key == "Enter":
            self.commit_setup_detect_lookback_days()

    def toggle_strict_candle_reuse_lock(self, checked: bool) -> None:
        """New Settings toggle (File 04 Core Correction v1), default OFF.
        Read LIVE by _fsm_base.py's _step_waiting_c3() on every check - not
        baked in at construction. Persisted via the same generic
        _engine.security.persistence pattern already used elsewhere
        (poi_display_enabled / poi_strategy_enabled)."""
        self.strict_candle_reuse_lock_enabled = checked
        set_strict_candle_reuse_lock_enabled(checked)
        _engine.security.persistence.save({"strict_candle_reuse_lock_enabled": checked})

    def _current_lookback_days(self) -> int:
        try:
            return max(_MIN_LOOKBACK_DAYS, min(_MAX_LOOKBACK_DAYS, int(self.setup_detect_lookback_days_draft)))
        except ValueError:
            return int(_DEFAULT_LOOKBACK_DAYS)

    def refresh_setup_visualization(self) -> None:
        """Read-only against SetupDetectionMonitor. Filters to the last
        `_current_lookback_days()` days by confirmed_at / pending
        updated_at, purely for what gets drawn/counted - never touches
        FSM state itself.

        File 04 Core Correction v1 (spec Section 5): also force-filters
        to the EXACT currently selected (symbol, timeframe) pair as a
        defensive check on top of the already symbol/tf-scoped engine
        query, so a stale/wrong-timeframe setup marker can never render
        even for one frame."""
        symbol = self.trading_panel_symbol
        tf = self.trading_panel_chart_tf
        try:
            confirmed = list(_engine.get_confirmed_setups(symbol, tf) or [])
        except Exception:
            confirmed = []
        try:
            pending = list(_engine.get_pending_setups(symbol, tf) or [])
        except Exception:
            pending = []

        # Defensive exact-match filter (belt-and-braces cross-timeframe
        # overlay leakage fix) - never trust upstream scoping alone.
        confirmed = [
            c for c in confirmed
            if getattr(c, "symbol", symbol) == symbol and getattr(c, "timeframe", tf) == tf
        ]
        pending = [
            p for p in pending
            if getattr(p, "symbol", symbol) == symbol and getattr(p, "timeframe", tf) == tf
        ]

        cutoff_ts = __import__("time").time() - self._current_lookback_days() * 86400
        confirmed = [c for c in confirmed if getattr(c, "confirmed_at", 0) >= cutoff_ts]
        pending = [p for p in pending if getattr(p, "updated_at", 0) >= cutoff_ts]

        overlays, dots = build_setup_overlays_and_dots(confirmed, pending, tf)
        self.setup_chart_overlays = overlays
        self.setup_chart_overlays_version += 1
        self.setup_dots = dots
        self.setup_dots_version += 1
        try:
            tick = float(_engine.market_data.symbol_registry.get_tick_size(symbol))
            buffer_ticks = SetupBufferSettings(_engine.security.persistence).get_buffer_ticks(symbol)
            new_callouts = build_setup_callouts(confirmed, tick, buffer_ticks)
        except Exception:
            new_callouts = []
        if new_callouts != self.setup_callouts:
            self.setup_callouts = new_callouts
            self.setup_callouts_version += 1
        self.setup_stats_rows = build_setup_stats_rows(confirmed)

    @rx.var
    def combined_chart_overlays(self) -> list[dict]:
        return list(self.poi_chart_overlays) + list(self.setup_chart_overlays)

    @rx.var
    def combined_chart_overlays_version(self) -> int:
        return self.poi_chart_overlays_version + self.setup_chart_overlays_version

    @rx.var
    def combined_chart_dots(self) -> list[dict]:
        return list(self.poi_dots) + list(self.setup_dots)

    @rx.var
    def combined_chart_dots_version(self) -> int:
        return self.poi_dots_version + self.setup_dots_version

    @rx.var
    def setup_stats_totals(self) -> dict:
        bull = sum(row.get("confirmed_bull", 0) for row in self.setup_stats_rows)
        bear = sum(row.get("confirmed_bear", 0) for row in self.setup_stats_rows)
        failed = sum(row.get("failed_aborted", 0) for row in self.setup_stats_rows)
        return {"confirmed_bull": bull, "confirmed_bear": bear, "failed_aborted": failed}

    @rx.event(background=True)
    async def poll_setup_visualization(self):
        async with self:
            if self._setup_viz_poll_running:
                return
            self._setup_viz_poll_running = True
        try:
            while True:
                async with self:
                    if self.active_tab != "Trading Panel":
                        self._setup_viz_poll_running = False
                        return
                    self.refresh_setup_visualization()
                await __import__("asyncio").sleep(_SETUP_VIZ_POLL_INTERVAL_SECONDS)
        finally:
            async with self:
                self._setup_viz_poll_running = False
