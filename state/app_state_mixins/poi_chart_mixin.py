"""Executable AppState mixin: POI line/zone overlays for the Trading Panel chart.

TARGET PATH: D:\\QuantumTrade19\\state\\app_state_mixins\\poi_chart_mixin.py
REPLACE THE ENTIRE FILE (v10 - dedup vlines, fix High/Low label bug, named/AM-PM custom lines).

FIX v0.5.0-r11:
  1. "Start label shows twice / 4H End missing" - REAL root cause: vline
     candidates were generated ONCE PER POI OBJECT, and PDH+PDL (or
     4H_HIGH+4H_LOW) are TWO separate POI objects that share the exact
     same source_tf and exact same previous-period start/end timestamps.
     That produced 2 duplicate "Start" entries and 2 duplicate "End"
     entries per TF, all at identical timestamps - the lane-stagger logic
     then pushed some of those duplicates into overlapping/hidden lanes,
     which is why "4H End" appeared to vanish (fighting for the same lane
     as its own duplicate) while "Day Start" appeared twice (visibly
     spread across 2 lanes instead of colliding). Fixed by keying vline
     generation by (tf, edge) instead of by POI, so each timeframe now
     produces exactly ONE Start and ONE End marker, no matter how many
     POI objects (High + Low) share that timeframe.
  2. "POI line labels not fixed" - REAL root cause: _is_high_type() (and
     the vline label logic before it) called `str(poi.poi_type)` again -
     the exact same str-mixed-Enum mistake fixed elsewhere in this file
     already (str() on a POIType returns "POIType.PDH", not "PDH", so the
     High/Low check always failed and silently defaulted to "Low"). Fixed
     by comparing poi_type directly (no str() wrapper) - .endswith() and
     == already work correctly on the raw enum member since it IS a str
     subclass by construction.
  3. Custom recurring lines now support an optional display Name (shown
     on the chart instead of the raw time), and store hour/minute in
     12-hour form + a separate AM/PM field (see poi_settings_mixin.py).
"""
from __future__ import annotations

import asyncio
import datetime

import reflex as rx

from state.app_state_mixins.shared import _engine, TRADING_PANEL_CHART_ID

try:
    from zoneinfo import ZoneInfo
    _NY_TZ = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    _NY_TZ = None

_POI_POLL_INTERVAL_SECONDS = 3.0

_ZONE_COLOR = {
    "RESISTANCE_FLIP": "rgba(234,57,67,0.28)",
    "SUPPORT_FLIP": "rgba(22,199,132,0.28)",
    "FVG": "rgba(30,143,255,0.24)",
    "INVERSE_FVG": "rgba(168,85,247,0.24)",
    "ORDER_BLOCK": "rgba(234,179,8,0.24)",
}
_ZONE_BORDER_DASHED = {"INVERSE_FVG"}

_DEFAULT_TF_COLOR = {
    "1m": "#38BDF8", "5m": "#38BDF8", "15m": "#38BDF8",
    "1H": "#32CD32", "4H": "#FFFFFF",
    "1D": "#FFA500", "1W": "#FFFF00", "1M": "#DC143C",
}

_TF_PERIOD_WORD = {
    "1m": "1m", "5m": "5m", "15m": "15m", "1H": "1H", "4H": "4H",
    "1D": "Day", "1W": "Week", "1M": "Month",
}

_TF_DURATION_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000,
    "1H": 3_600_000, "4H": 14_400_000,
    "1D": 86_400_000, "1W": 604_800_000, "1M": 2_592_000_000,
}

_MAX_LABEL_LANES = 3


def _normalize_ts_ms(value) -> int:
    numeric = int(value or 0)
    if 0 < numeric < 10_000_000_000:
        return numeric * 1000
    return numeric


def _is_high_type(poi_type) -> bool:
    # IMPORTANT: never wrap poi_type in str(...) here - see module
    # docstring. .endswith()/== already work directly on the raw enum
    # member because POIType is a str subclass.
    return poi_type.endswith("_HIGH") or poi_type == "PDH"


def _pretty_line_label(poi_type, source_tf: str, price: float) -> str:
    period = _TF_PERIOD_WORD.get(source_tf, str(source_tf))
    hl = "High" if _is_high_type(poi_type) else "Low"
    return f"Prv. {period} {hl} ({price:,.2f})"


def _assign_label_lanes(entries: list[dict], threshold_ms: float) -> None:
    lane_last_ts: list[float | None] = [None] * _MAX_LABEL_LANES
    for entry in sorted(entries, key=lambda e: e["timestamp"]):
        placed = False
        for lane in range(_MAX_LABEL_LANES):
            if lane_last_ts[lane] is None or entry["timestamp"] - lane_last_ts[lane] >= threshold_ms:
                entry["lane"] = lane
                lane_last_ts[lane] = entry["timestamp"]
                placed = True
                break
        if not placed:
            entry["lane"] = _MAX_LABEL_LANES - 1


def _hour12_to_24(hour12: int, minute: int, meridiem: str) -> tuple[int, int]:
    hour12 = max(1, min(12, hour12))
    minute = max(0, min(59, minute))
    if meridiem == "PM":
        hour24 = hour12 if hour12 == 12 else hour12 + 12
    else:
        hour24 = 0 if hour12 == 12 else hour12
    return hour24, minute


class PoiChartMixin(rx.State, mixin=True):
    def _next_custom_line_ms(self, hour12: int, minute: int, meridiem: str) -> int | None:
        """Computes the next occurrence (today or tomorrow) of the given
        12-hour wall-clock time in America/New_York. Recomputed fresh
        every call - inherently recurring, nothing stored absolute."""
        if _NY_TZ is None:
            return None
        try:
            hour24, minute = _hour12_to_24(int(hour12), int(minute), meridiem)
        except Exception:
            return None
        now_ny = datetime.datetime.now(_NY_TZ)
        candidate = now_ny.replace(hour=hour24, minute=minute, second=0, microsecond=0)
        if candidate <= now_ny:
            candidate += datetime.timedelta(days=1)
        return int(candidate.timestamp() * 1000)

    def _build_poi_overlays(self, symbol: str) -> list[dict]:
        try:
            pois = list(_engine.get_active_pois(symbol) or [])
        except Exception:
            pois = []

        overlays: list[dict] = []
        # Keyed by (tf, "start"|"end") so PDH+PDL (same tf="1D") or
        # 4H_HIGH+4H_LOW (same tf="4H") never produce duplicate markers.
        vline_by_key: dict[tuple[str, str], dict] = {}

        for poi in pois:
            poi_type = poi.poi_type
            tf = poi.source_tf

            if poi.is_range():
                if not self.poi_display_enabled.get(poi_type, False):
                    continue
                label_bits = [poi.chart_label]
                if self.poi_show_source_tf_badge and tf:
                    label_bits.append(f"[{tf}]")
                label = " ".join(label_bits)
                if self.poi_show_logical_id:
                    label += f"  ({poi.poi_id})"
                overlays.append({
                    "id": poi.poi_id,
                    "kind": "zone",
                    "price_high": float(poi.price_high),
                    "price_low": float(poi.price_low),
                    "start_time": _normalize_ts_ms(poi.formed_at_ts),
                    "end_time": None,
                    "color": _ZONE_COLOR.get(poi_type, "rgba(150,150,150,0.22)"),
                    "dashed": poi_type in _ZONE_BORDER_DASHED,
                    "label": label if self.poi_show_labels else "",
                    "opacity": self.poi_zone_opacity / 100.0,
                })
                continue

            if poi.price is None:
                continue
            if not self.poi_tf_display_enabled.get(tf, False):
                continue

            color = self.poi_tf_color.get(tf, _DEFAULT_TF_COLOR.get(tf, "#38BDF8"))
            label = _pretty_line_label(poi_type, tf, poi.price) if self.poi_show_labels else ""
            if self.poi_show_logical_id:
                label += f" ({poi.poi_id})"

            overlays.append({
                "id": poi.poi_id,
                "kind": "line",
                "price": float(poi.price),
                "color": color,
                "width": 1,
                "label": label,
                "opacity": self.poi_line_transparency / 100.0,
            })

            if self.poi_tf_vertical_enabled.get(tf, False):
                duration_ms = _TF_DURATION_MS.get(tf)
                if duration_ms:
                    start_ms = _normalize_ts_ms(poi.formed_at_ts)
                    end_ms = start_ms + duration_ms
                    period = _TF_PERIOD_WORD.get(tf, tf)
                    start_key = (tf, "start")
                    end_key = (tf, "end")
                    if start_key not in vline_by_key:
                        vline_by_key[start_key] = {
                            "id": f"vline:{tf}:start",
                            "timestamp": start_ms,
                            "color": color,
                            "text": f"Prv. {period} Start" if self.poi_show_labels else "",
                        }
                    if end_key not in vline_by_key:
                        vline_by_key[end_key] = {
                            "id": f"vline:{tf}:end",
                            "timestamp": end_ms,
                            "color": color,
                            "text": f"Prv. {period} End" if self.poi_show_labels else "",
                        }

        vline_candidates = list(vline_by_key.values())

        for index, custom in enumerate(self.poi_custom_lines):
            if not custom.get("enabled"):
                continue
            ts = self._next_custom_line_ms(
                custom.get("hour12", 8), custom.get("minute", 30), custom.get("meridiem", "AM")
            )
            if ts is None:
                continue
            name = custom.get("name", "").strip()
            display_text = name if name else f"{custom.get('hour12', 8)}:{custom.get('minute', 30):02d} {custom.get('meridiem', 'AM')}"
            vline_candidates.append({
                "id": f"custom_line_{index}",
                "timestamp": ts,
                "color": custom.get("color", "#38BDF8"),
                "text": display_text if self.poi_show_labels else "",
            })

        try:
            requested_days = int(self.trading_panel_display_days_input)
        except ValueError:
            requested_days = 5
        threshold_ms = max(1, requested_days) * 86_400_000 * 0.02
        _assign_label_lanes(vline_candidates, threshold_ms)

        for entry in vline_candidates:
            overlays.append({
                "id": entry["id"],
                "kind": "vline",
                "timestamp": entry["timestamp"],
                "color": entry["color"],
                "dashed": self.poi_vertical_line_style != "solid",
                "opacity": self.poi_vertical_line_opacity / 100.0,
                "label": entry["text"],
                "lane": entry.get("lane", 0),
            })

        return overlays

    def refresh_poi_chart_overlays(self) -> None:
        self.poi_chart_overlays = self._build_poi_overlays(self.trading_panel_symbol)
        self.poi_chart_overlays_version += 1

    @rx.event(background=True)
    async def poll_poi_chart_overlays(self):
        async with self:
            if self._poi_chart_poll_running:
                return
            self._poi_chart_poll_running = True
        try:
            while True:
                async with self:
                    if self.active_tab != "Trading Panel":
                        break
                    self.refresh_poi_chart_overlays()
                await asyncio.sleep(_POI_POLL_INTERVAL_SECONDS)
        finally:
            async with self:
                self._poi_chart_poll_running = False
