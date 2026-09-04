"""Executable AppState mixin: Trading Panel chart state and methods (react-klinecharts).

TARGET PATH: D:\QuantumTrade19\state\app_state_mixins\trading_panel_mixin.py
REPLACE THE ENTIRE FILE.

FIX v0.4.62 - every poll tick now calls window.QT19_ensureLiveCallback
(installed by kline_chart.py) BEFORE attempting to use the live push
callback - self-heals the registration if React StrictMode's remount
cycle ever leaves it empty (confirmed via console: the final mounted
chart instance's own cleanup fired with no later re-subscribe,
permanently emptying the registry). See kline_chart.py's v0.4.62
docstring for the full explanation.

FIX v0.4.60 (carried forward) - throttled success/failure console logging
on the push side (first 5 calls only).

FIX v0.4.59 (carried forward) - trading_panel_data_version, incremented
only inside refresh_trading_panel_chart() (a genuine full reload), never
inside build_live_ohlc_update() (the 0.5s poll).

FIX v0.4.54 (carried forward) - klinecharts v10.0.2 removed updateData()/
applyNewData(); live ticks go through the callback stored in
window.QT19_LIVE_CALLBACKS via subscribeBar().
"""
from __future__ import annotations

import asyncio
import datetime
import json
import time

import reflex as rx

from state.app_state_mixins.shared import (
    engine,
    TRADING_PANEL_CHART_ID,
    TRADING_PANEL_PERIOD_MAP,
    TRADING_PANEL_TF_OPTIONS,
    TRADING_PANEL_DAY_PRESETS,
)

_TF_DURATION_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000}


def _today_str() -> str:
    return datetime.date.today().isoformat()


def _normalize_timestamp_ms(value) -> int:
    numeric = int(value)
    if numeric < 10_000_000_000:
        return numeric * 1000
    return numeric


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


class TradingPanelMixin(rx.State, mixin=True):

    def _symbol_display_days_key(self, symbol: str) -> str:
        return f"chart_display_days_{symbol}"

    def _coverage_cache_key(self, symbol: str, tf: str) -> str:
        return f"chart_coverage_cache_{symbol}_{tf}"

    def load_trading_panel_display_days(self) -> None:
        saved = engine.security.persistence.load().get(self._symbol_display_days_key(self.trading_panel_symbol))
        value = str(saved) if saved else "5"
        self.trading_panel_display_days_input = value
        self.trading_panel_display_days_draft = value

    def _update_tf_progress(self, symbol: str, tf: str) -> dict:
        progress = engine.market_data.get_deep_history_progress(symbol, tf)
        entry = {
            "percent": int(progress.get("percent", 0)),
            "state": progress.get("state", "idle"),
            "eta_seconds": progress.get("eta_seconds"),
            "present_candles": int(progress.get("present_candles", 0)),
            "required_candles": int(progress.get("required_candles", 0)),
            "missing_candles": int(progress.get("missing_candles", 0)),
            "broker_ceiling_reached": bool(progress.get("broker_ceiling_reached", False)),
            "error": progress.get("error"),
        }
        current = dict(self.trading_panel_tf_progress)
        current[tf] = entry
        self.trading_panel_tf_progress = current
        return progress

    def get_coverage(self, symbol: str, tf: str, force: bool = False) -> tuple[int, str]:
        progress = self._update_tf_progress(symbol, tf)

        settings = engine.security.persistence.load()
        cache_key = self._coverage_cache_key(symbol, tf)
        cached = settings.get(cache_key)
        if not force and cached and cached.get("date") == _today_str():
            return int(cached.get("local_days", 0)), str(cached.get("broker_days", "Not checked yet"))

        local_days = int(progress.get("covered_days", 0))
        ceiling = engine.market_data.get_ceiling_days(symbol, tf)
        broker_label = f"{ceiling} days" if ceiling is not None else "Not checked yet"
        engine.security.persistence.save(
            {cache_key: {"date": _today_str(), "local_days": local_days, "broker_days": broker_label}}
        )
        return local_days, broker_label

    def _set_coverage_pending(self, symbol: str, tf: str, pending: bool) -> None:
        engine.security.persistence.save({f"chart_coverage_pending_{symbol}_{tf}": pending})

    def _is_coverage_pending(self, symbol: str, tf: str) -> bool:
        return bool(engine.security.persistence.load().get(f"chart_coverage_pending_{symbol}_{tf}", False))

    def set_trading_panel_symbol(self, value: str) -> None:
        self.trading_panel_symbol = value
        engine.security.persistence.save({"trading_panel_symbol": value})
        self.load_trading_panel_display_days()
        self.refresh_trading_panel_chart()

    def set_trading_panel_chart_tf(self, value: str) -> None:
        self.trading_panel_chart_tf = value
        engine.security.persistence.save({"trading_panel_chart_tf": value})
        self.refresh_trading_panel_chart()

    def set_trading_panel_display_days_draft(self, value: str) -> None:
        self.trading_panel_display_days_draft = value

    def handle_display_days_keydown(self, key: str) -> None:
        if key == "Enter":
            self.commit_trading_panel_display_days()

    def commit_trading_panel_display_days(self) -> None:
        self.set_trading_panel_display_days(self.trading_panel_display_days_draft)

    def set_trading_panel_display_days(self, value: str) -> None:
        self.trading_panel_display_days_input = value
        self.trading_panel_display_days_draft = value
        try:
            requested_days = int(value)
            if requested_days <= 0:
                self.trading_panel_notice = "Enter a positive whole number of days."
                return
        except ValueError:
            self.trading_panel_notice = "Enter a positive whole number of days."
            return

        symbol = self.trading_panel_symbol
        engine.security.persistence.save({self._symbol_display_days_key(symbol): requested_days})

        for tf in TRADING_PANEL_TF_OPTIONS:
            local_days, _ = self.get_coverage(symbol, tf, force=True)
            if local_days < requested_days:
                engine.market_data.start_deep_history(symbol, tf, requested_days)
                self._set_coverage_pending(symbol, tf, True)
            else:
                self._set_coverage_pending(symbol, tf, False)

        self.refresh_trading_panel_chart()

    def set_trading_panel_chart_theme(self, value: str) -> None:
        self.trading_panel_chart_theme = value
        engine.security.persistence.save({"trading_panel_chart_theme": value})

    def toggle_trading_panel_grid(self) -> None:
        self.trading_panel_grid_enabled = not self.trading_panel_grid_enabled
        engine.security.persistence.save({"trading_panel_grid_enabled": self.trading_panel_grid_enabled})

    def toggle_trading_panel_follow_live(self) -> None:
        self.trading_panel_follow_live = not self.trading_panel_follow_live
        engine.security.persistence.save({"trading_panel_follow_live": self.trading_panel_follow_live})

    def reset_trading_panel_view(self):
        return rx.call_script(
            f"""(function() {{
                var chart = window.QT19_CHARTS && window.QT19_CHARTS['{TRADING_PANEL_CHART_ID}'];
                if (chart && typeof chart.setBarSpace === 'function') chart.setBarSpace(6);
            }})()"""
        )

    def go_live_trading_panel(self):
        return rx.call_script(
            f"""(function() {{
                var chart = window.QT19_CHARTS && window.QT19_CHARTS['{TRADING_PANEL_CHART_ID}'];
                if (chart && typeof chart.scrollToRealTime === 'function') chart.scrollToRealTime();
            }})()"""
        )

    def open_trading_panel_menu(self, x: int, y: int) -> None:
        self.trading_panel_menu_x = int(x)
        self.trading_panel_menu_y = int(y)
        self.trading_panel_menu_open = True

    def close_trading_panel_menu(self) -> None:
        self.trading_panel_menu_open = False

    def refresh_trading_panel_chart(self) -> None:
        symbol = self.trading_panel_symbol
        tf = self.trading_panel_chart_tf
        try:
            requested_days = int(self.trading_panel_display_days_input)
        except ValueError:
            requested_days = 5

        force = self._is_coverage_pending(symbol, tf)
        local_days, broker_label = self.get_coverage(symbol, tf, force=force)
        self.trading_panel_local_days = str(local_days)
        self.trading_panel_broker_days = broker_label

        if local_days >= requested_days and force:
            self._set_coverage_pending(symbol, tf, False)

        effective_days = min(requested_days, local_days) if local_days else requested_days
        if local_days and requested_days > local_days:
            self.trading_panel_notice = (
                f"{requested_days} days requested \u2014 {local_days} days available locally \u2014 downloading the rest\u2026"
            )
        elif not local_days:
            self.trading_panel_notice = "No local historical coverage yet for this symbol/timeframe \u2014 downloading\u2026"
        else:
            self.trading_panel_notice = ""

        candles = engine.market_data.get_chart_candles(symbol, tf, effective_days)
        rows = [
            {
                "timestamp": _normalize_timestamp_ms(c.open_time),
                "open": float(c.open), "high": float(c.high),
                "low": float(c.low), "close": float(c.close),
                "volume": float(c.volume),
            }
            for c in candles
        ]
        self.trading_panel_candles = rows
        self.trading_panel_data_version += 1

        current = candles[-1] if candles else None
        if current:
            self.trading_panel_current_open = f"{current.open:.2f}"
            self.trading_panel_current_high = f"{current.high:.2f}"
            self.trading_panel_current_low = f"{current.low:.2f}"
            self.trading_panel_current_close = f"{current.close:.2f}"
            self.trading_panel_last_candle_ts = float(_normalize_timestamp_ms(current.open_time))
        else:
            self.trading_panel_current_open = "--"
            self.trading_panel_current_high = "--"
            self.trading_panel_current_low = "--"
            self.trading_panel_current_close = "--"
            self.trading_panel_last_candle_ts = 0.0

    def build_live_ohlc_update(self):
        symbol = self.trading_panel_symbol
        tf = self.trading_panel_chart_tf

        if self._is_coverage_pending(symbol, tf):
            try:
                requested_days = int(self.trading_panel_display_days_input)
            except ValueError:
                requested_days = 5
            local_days, broker_label = self.get_coverage(symbol, tf, force=True)
            self.trading_panel_local_days = str(local_days)
            self.trading_panel_broker_days = broker_label
            if local_days >= requested_days:
                self._set_coverage_pending(symbol, tf, False)
                self.trading_panel_notice = ""
                self.refresh_trading_panel_chart()
        else:
            self._update_tf_progress(symbol, tf)

        live = engine.market_data.get_live_candle(symbol, tf)
        if not live:
            return None, False

        self.trading_panel_current_open = f"{live.open:.2f}"
        self.trading_panel_current_high = f"{live.high:.2f}"
        self.trading_panel_current_low = f"{live.low:.2f}"
        self.trading_panel_current_close = f"{live.close:.2f}"

        live_ts = _normalize_timestamp_ms(live.open_time)
        live_row = {
            "timestamp": live_ts, "open": float(live.open), "high": float(live.high),
            "low": float(live.low), "close": float(live.close),
            "volume": float(getattr(live, "volume", 0.0) or 0.0),
        }
        candle_closed = (
            self.trading_panel_last_candle_ts != 0.0
            and float(live_ts) != self.trading_panel_last_candle_ts
        )
        self.trading_panel_last_candle_ts = float(live_ts)
        return live_row, candle_closed

    @rx.event(background=True)
    async def poll_trading_panel_chart(self):
        async with self:
            if self.trading_panel_poll_running:
                return
            self.trading_panel_poll_running = True
        try:
            while True:
                live_row = None
                should_snap = False
                async with self:
                    live_row, candle_closed = self.build_live_ohlc_update()
                    if candle_closed and self.trading_panel_follow_live:
                        should_snap = True

                if live_row is not None:
                    bar_json = json.dumps(live_row)
                    snap_call = (
                        f"if (chart.scrollToRealTime) chart.scrollToRealTime();"
                        if should_snap else ""
                    )
                    # v0.4.62: self-heal FIRST, every tick, before attempting
                    # to use the live callback - defends against StrictMode
                    # (or any future remount) leaving the registry empty
                    # with no later re-subscribe.
                    yield rx.call_script(
                        f"""(function() {{
                            var chart = window.QT19_CHARTS && window.QT19_CHARTS['{TRADING_PANEL_CHART_ID}'];
                            if (window.QT19_ensureLiveCallback && window.QT19_ensureLiveCallback['{TRADING_PANEL_CHART_ID}']) {{
                                window.QT19_ensureLiveCallback['{TRADING_PANEL_CHART_ID}']();
                            }}
                            var pushLive = window.QT19_LIVE_CALLBACKS && window.QT19_LIVE_CALLBACKS['{TRADING_PANEL_CHART_ID}'];
                            window.QT19_PUSH_COUNT = (window.QT19_PUSH_COUNT || 0) + 1;
                            if (pushLive) {{
                                pushLive({bar_json});
                                if (window.QT19_PUSH_COUNT <= 5) {{
                                    console.log('QT19: pushLive() SUCCEEDED, call #' + window.QT19_PUSH_COUNT + ', bar:', {bar_json});
                                }}
                            }} else {{
                                if (window.QT19_PUSH_COUNT <= 5) {{
                                    console.warn('QT19: no live callback registered for {TRADING_PANEL_CHART_ID} on call #' + window.QT19_PUSH_COUNT + '. Bar that could not be pushed:', {bar_json});
                                }}
                            }}
                            if (chart) {{
                                {snap_call}
                            }}
                        }})()"""
                    )
                await asyncio.sleep(0.5)
        finally:
            async with self:
                self.trading_panel_poll_running = False

    @rx.var
    def trading_panel_backfill_active(self) -> bool:
        return self._is_coverage_pending(self.trading_panel_symbol, self.trading_panel_chart_tf)

    @rx.var
    def trading_panel_backfill_percent(self) -> int:
        entry = self.trading_panel_tf_progress.get(self.trading_panel_chart_tf)
        if not entry:
            return 0
        return max(0, min(100, int(entry.get("percent", 0))))

    @rx.var
    def trading_panel_eta_text(self) -> str:
        entry = self.trading_panel_tf_progress.get(self.trading_panel_chart_tf)
        if not entry:
            return ""
        if entry.get("error"):
            return f"Error: {entry['error']}"
        if entry.get("broker_ceiling_reached"):
            return "Broker has no more history for this range (real exchange data limit)."
        if entry.get("state") == "complete":
            return "Complete"
        eta_text = _format_eta(entry.get("eta_seconds"))
        if eta_text:
            return eta_text
        if entry.get("state") in ("downloading", "queued"):
            return "Estimating\u2026"
        return ""

    @rx.var
    def trading_panel_combined_percent(self) -> int:
        values = [
            int(self.trading_panel_tf_progress.get(tf, {}).get("percent", 0))
            for tf in TRADING_PANEL_TF_OPTIONS
        ]
        if not values:
            return 0
        return int(round(sum(values) / len(values)))

    @rx.var
    def trading_panel_combined_active(self) -> bool:
        return any(
            self.trading_panel_tf_progress.get(tf, {}).get("state") in ("downloading", "queued")
            for tf in TRADING_PANEL_TF_OPTIONS
        )

    @rx.var
    def trading_panel_countdown_text(self) -> str:
        duration_ms = _TF_DURATION_MS.get(self.trading_panel_chart_tf, 60_000)
        if self.trading_panel_last_candle_ts <= 0:
            return "--:--"
        close_at_ms = self.trading_panel_last_candle_ts + duration_ms
        now_ms = time.time() * 1000
        remaining_s = max(0, int((close_at_ms - now_ms) / 1000))
        minutes, seconds = divmod(remaining_s, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @rx.var
    def trading_panel_symbol_options(self) -> list[str]:
        return engine.market_data.symbol_registry.get_symbols_sorted(active_only=True)

    @rx.var
    def trading_panel_symbol_info(self) -> dict:
        registry = engine.market_data.symbol_registry
        info = registry.get_symbol_info(self.trading_panel_symbol)
        if info is None or not info.tick_size:
            return {"ticker": self.trading_panel_symbol, "precision": 2}
        tick = info.tick_size
        precision = 0
        while round(tick, precision) != tick and precision < 8:
            precision += 1
        return {"ticker": self.trading_panel_symbol, "precision": precision}

    @rx.var
    def trading_panel_period(self) -> dict:
        return TRADING_PANEL_PERIOD_MAP.get(self.trading_panel_chart_tf, TRADING_PANEL_PERIOD_MAP["5m"])

    @rx.var
    def trading_panel_styles(self) -> dict:
        day = self.trading_panel_chart_theme == "day"
        grid_show = self.trading_panel_grid_enabled
        foreground = "#152238" if day else "#dce8f7"
        grid_color = "rgba(56,78,108,.14)" if day else "rgba(151,176,207,.15)"
        return {
            "grid": {
                "show": grid_show,
                "horizontal": {"show": grid_show, "color": grid_color},
                "vertical": {"show": grid_show, "color": grid_color},
            },
            "candle": {"bar": {"upColor": "#16c784", "downColor": "#ea3943", "noChangeColor": "#8b98aa"}},
            "xAxis": {"axisLine": {"color": grid_color}, "tickLine": {"color": grid_color}, "tickText": {"color": foreground}},
            "yAxis": {"axisLine": {"color": grid_color}, "tickLine": {"color": grid_color}, "tickText": {"color": foreground}},
        }

    @rx.var
    def trading_panel_menu_style(self) -> dict:
        day = self.trading_panel_chart_theme == "day"
        background = "#f4f7fb" if day else "#141d29"
        border_color = "rgba(20,30,50,0.18)" if day else "rgba(147,173,205,0.28)"
        text_color = "#152238" if day else "#dce8f7"
        return {
            "background": background,
            "border": f"1px solid {border_color}",
            "borderRadius": "0.9rem",
            "boxShadow": "0 10px 30px rgba(0,0,0,0.28)",
            "color": text_color,
            "left": f"{self.trading_panel_menu_x}px",
            "top": f"{self.trading_panel_menu_y}px",
        }
