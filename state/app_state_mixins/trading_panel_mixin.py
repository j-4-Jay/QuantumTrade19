"""Executable AppState mixin: Trading Panel chart state and methods (react-klinecharts).

PATH: state/app_state_mixins/trading_panel_mixin.py

CHANGE (v0.3.6 - real chart control + no-jump + editable Display Days):

1. refresh_trading_panel_chart() (full reload) now also records the newest
   candle's timestamp into _trading_panel_last_candle_ts, used to detect a
   genuine candle close for Follow Live.

2. refresh_trading_panel_ohlc_only() still only updates displayed O/H/L/C and
   never touches trading_panel_candles - this is what keeps the chart's
   scroll position fixed while the user reviews history.

3. poll_trading_panel_chart() now also checks, on every 3s tick, whether the
   current live candle's timestamp has changed (i.e. the previous candle on
   this timeframe actually closed). If so, AND Follow Live is ON, it yields
   an rx.call_script that tells the real klinecharts Chart instance (via
   window.QT19_CHARTS, populated by ui/components/kline_chart.py) to
   scrollToRealTime(). If Follow Live is OFF, nothing is scrolled - the
   user's scroll/pan position is left exactly where it was.

4. New: toggle_trading_panel_grid, reset_trading_panel_view,
   go_live_trading_panel - Grid is now a real reactive style (via
   trading_panel_styles computed var); Reset View and Go Live use direct
   Chart-instance method calls through the registry, not DOM guessing.

5. New: trading_panel_display_days_draft + set_trading_panel_display_days_draft
   + commit_trading_panel_display_days - fixes the input box that was stuck
   on "5". The input is now bound to the draft var (updates on every
   keystroke) and only commits (persists + triggers a full reload) on
   blur/Apply, never silently overwritten mid-typing.
"""
from __future__ import annotations

import asyncio
import reflex as rx

from state.app_state_mixins.shared import (
    _engine,
    TRADING_PANEL_CHART_ID,
    TRADING_PANEL_PERIOD_MAP,
    TRADING_PANEL_TF_OPTIONS,
    TRADING_PANEL_DAY_PRESETS,
)


class TradingPanelMixin(rx.State, mixin=True):
    def _chart_workspace_key(self, symbol: str, tf: str) -> str:
        return f"chart_display_days::{symbol}::{tf}"

    def _load_trading_panel_display_days(self) -> None:
        saved = _engine.security.persistence.load().get(
            self._chart_workspace_key(self.trading_panel_symbol, self.trading_panel_chart_tf)
        )
        value = str(saved) if saved else "5"
        self.trading_panel_display_days_input = value
        self.trading_panel_display_days_draft = value

    def set_trading_panel_symbol(self, value: str) -> None:
        self.trading_panel_symbol = value
        self._load_trading_panel_display_days()
        self.refresh_trading_panel_chart()

    def set_trading_panel_chart_tf(self, value: str) -> None:
        self.trading_panel_chart_tf = value
        self._load_trading_panel_display_days()
        self.refresh_trading_panel_chart()

    def set_trading_panel_display_days_draft(self, value: str) -> None:
        """Updates on every keystroke. Never persisted, never reloads the
        chart - purely lets the user type freely without the server
        overwriting what they're typing."""
        self.trading_panel_display_days_draft = value

    def commit_trading_panel_display_days(self) -> None:
        """Call this on blur or when the user clicks Apply. Validates,
        persists, and triggers the actual full candle reload."""
        self.set_trading_panel_display_days(self.trading_panel_display_days_draft)

    def set_trading_panel_display_days(self, value: str) -> None:
        """Never silently calls the broker - only changes how many *locally
        available* days are rendered. If X > A, refresh_trading_panel_chart()
        surfaces a notice instead of fetching anything."""
        self.trading_panel_display_days_input = value
        self.trading_panel_display_days_draft = value
        try:
            days = int(value)
            if days <= 0:
                self.trading_panel_notice = "Enter a positive whole number of days."
                return
        except ValueError:
            self.trading_panel_notice = "Enter a positive whole number of days."
            return
        _engine.security.persistence.save({
            self._chart_workspace_key(self.trading_panel_symbol, self.trading_panel_chart_tf): days
        })
        self.refresh_trading_panel_chart()

    def set_trading_panel_chart_theme(self, value: str) -> None:
        """Chart-local only - never touches the app-wide theme_key.
        Now wired for real: trading_panel_styles (a computed var) reads
        this value and produces real klinecharts Styles."""
        self.trading_panel_chart_theme = value
        _engine.security.persistence.save({"trading_panel_chart_theme": value})

    def toggle_trading_panel_grid(self) -> None:
        """Grid default is OFF (best for viewing POI lines/zones cleanly).
        This is a real reactive style change via trading_panel_styles -
        no JS call needed."""
        self.trading_panel_grid_enabled = not self.trading_panel_grid_enabled
        _engine.security.persistence.save({"trading_panel_grid_enabled": self.trading_panel_grid_enabled})

    def toggle_trading_panel_follow_live(self) -> None:
        self.trading_panel_follow_live = not self.trading_panel_follow_live
        _engine.security.persistence.save({"trading_panel_follow_live": self.trading_panel_follow_live})

    def reset_trading_panel_view(self):
        """Resets only zoom/bar-spacing (X-axis scale). klinecharts
        auto-scales the Y axis to the visible data already, so this alone
        gives a clean 'reset zoom' without moving the chart to the live
        candle."""
        return rx.call_script(
            f"""
            (function() {{
                var chart = window.QT19_CHARTS && window.QT19_CHARTS["{TRADING_PANEL_CHART_ID}"];
                if (chart && typeof chart.setBarSpace === "function") {{
                    chart.setBarSpace(6);
                }}
            }})();
            """
        )

    def go_live_trading_panel(self):
        """Immediate jump to the newest candle - the ONLY control that
        deliberately moves the viewport on demand."""
        return rx.call_script(
            f"""
            (function() {{
                var chart = window.QT19_CHARTS && window.QT19_CHARTS["{TRADING_PANEL_CHART_ID}"];
                if (chart && typeof chart.scrollToRealTime === "function") {{
                    chart.scrollToRealTime();
                }}
            }})();
            """
        )

    def refresh_trading_panel_chart(self) -> None:
        """Full reload: rebuilds the entire candle array. Call this ONLY on
        Trading Panel open, symbol change, timeframe change, or Display Last
        X Days change. Never call this from the 3-second polling loop."""
        try:
            requested_days = int(self.trading_panel_display_days_input)
        except ValueError:
            requested_days = 5

        progress = _engine.market_data.get_deep_history_progress(
            self.trading_panel_symbol, self.trading_panel_chart_tf
        )
        local_days = progress["covered_days"]
        self.trading_panel_local_days = str(local_days)

        ceiling = _engine.market_data.get_ceiling_days(self.trading_panel_symbol, self.trading_panel_chart_tf)
        self.trading_panel_broker_days = f"{ceiling} days" if ceiling is not None else "Not checked yet"

        effective_days = min(requested_days, local_days) if local_days else requested_days
        if local_days and requested_days > local_days:
            self.trading_panel_notice = f"{requested_days} days requested \u2022 {local_days} days available locally"
        elif not local_days:
            self.trading_panel_notice = "No local historical coverage yet for this symbol/timeframe."
        else:
            self.trading_panel_notice = ""

        candles = _engine.market_data.get_chart_candles(
            self.trading_panel_symbol,
            self.trading_panel_chart_tf,
            effective_days,
        )

        # ASSUMPTION FLAGGED: Candle fields assumed to be open/high/low/close/open_time.
        # Confirm against candle_builder_worker.py's real Candle dataclass before running.
        # Volume is NOT confirmed available on Candle - defaulted to 0.0 here.
        # Row keys match react-klinecharts' KLineData shape directly (timestamp/open/high/low/close/volume).
        rows = [
            {
                "timestamp": c.open_time,
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume),
            }
            for c in candles
        ]

        self.trading_panel_candles = rows

        current = candles[-1] if candles else None
        if current:
            self.trading_panel_current_open = f"{current.open:,.2f}"
            self.trading_panel_current_high = f"{current.high:,.2f}"
            self.trading_panel_current_low = f"{current.low:,.2f}"
            self.trading_panel_current_close = f"{current.close:,.2f}"
            self._trading_panel_last_candle_ts = float(current.open_time)
        else:
            self.trading_panel_current_open = self.trading_panel_current_high = \
                self.trading_panel_current_low = self.trading_panel_current_close = "--"
            self._trading_panel_last_candle_ts = 0.0

    def refresh_trading_panel_ohlc_only(self) -> bool:
        """OHLC-only refresh: updates ONLY the displayed Open/High/Low/Close
        text values from the current live candle. NEVER rebuilds or replaces
        trading_panel_candles - this is what keeps the chart's scroll/
        viewport position stable while the user studies historical price
        action.

        Returns True if the current candle's timestamp changed since the
        last check (i.e. the previous candle just closed and a new one
        started), so the caller can decide whether to snap to live under
        Follow Live."""
        live = _engine.market_data.get_live_candle(
            self.trading_panel_symbol, self.trading_panel_chart_tf
        )
        if not live:
            return False

        self.trading_panel_current_open = f"{live.open:,.2f}"
        self.trading_panel_current_high = f"{live.high:,.2f}"
        self.trading_panel_current_low = f"{live.low:,.2f}"
        self.trading_panel_current_close = f"{live.close:,.2f}"

        candle_closed = (
            self._trading_panel_last_candle_ts != 0.0
            and float(live.open_time) != self._trading_panel_last_candle_ts
        )
        self._trading_panel_last_candle_ts = float(live.open_time)
        return candle_closed

    @rx.event(background=True)
    async def poll_trading_panel_chart(self):
        """Same guarded-loop pattern as poll_ws_status/poll_pinned_prices.
        CHANGE (v0.3.6): calls refresh_trading_panel_ohlc_only() - updates
        OHLC display values only, never replaces the full candle array. If
        Follow Live is ON and a candle just closed, yields a script that
        snaps the real chart to the live candle. If Follow Live is OFF, the
        viewport is never touched, no matter how many candles close.
        KNOWN SIMPLIFICATION: does not stop when the user leaves the Trading
        Panel tab - deliberately deferred, not an oversight."""
        async with self:
            if self._trading_panel_poll_running:
                return
            self._trading_panel_poll_running = True
        try:
            while True:
                should_snap = False
                async with self:
                    candle_closed = self.refresh_trading_panel_ohlc_only()
                    if candle_closed and self.trading_panel_follow_live:
                        should_snap = True
                if should_snap:
                    yield rx.call_script(
                        f"""
                        (function() {{
                            var chart = window.QT19_CHARTS && window.QT19_CHARTS["{TRADING_PANEL_CHART_ID}"];
                            if (chart && typeof chart.scrollToRealTime === "function") {{
                                chart.scrollToRealTime();
                            }}
                        }})();
                        """
                    )
                await asyncio.sleep(3)
        finally:
            async with self:
                self._trading_panel_poll_running = False

    @rx.var
    def trading_panel_symbol_options(self) -> list[str]:
        return _engine.market_data.symbol_registry.get_symbols_sorted(active_only=True)

    @rx.var
    def trading_panel_symbol_info(self) -> dict:
        """Shape expected by <KLineChart symbol={...}>: {ticker, precision}.
        precision (decimal places) is derived from the real tick_size on
        SymbolRegistryWorker - falls back to 2 if the symbol isn't found."""
        registry = _engine.market_data.symbol_registry
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
        """Real klinecharts Styles object. Grid on/off and Day/Night are
        both driven declaratively from here - toggling either AppState
        field re-renders the chart with the correct styles automatically,
        with no JS-side DOM manipulation required."""
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
            "candle": {
                "bar": {
                    "upColor": "#16c784",
                    "downColor": "#ea3943",
                    "noChangeColor": "#8b98aa",
                },
            },
            "xAxis": {
                "axisLine": {"color": grid_color},
                "tickLine": {"color": grid_color},
                "tickText": {"color": foreground},
            },
            "yAxis": {
                "axisLine": {"color": grid_color},
                "tickLine": {"color": grid_color},
                "tickText": {"color": foreground},
            },
        }
