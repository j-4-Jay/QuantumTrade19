"""Executable AppState mixin: POI line/zone overlays for the Trading Panel chart.

TARGET PATH: D:\\QuantumTrade19\\state\\app_state_mixins\\poi_chart_mixin.py
REPLACE THE ENTIRE FILE (v16b - restores the has_dot extra clearance on
top of the new TF-rank vertical stacking).
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

_DEFAULT_TF_COLOR = {
    "1m": "#38BDF8", "5m": "#38BDF8", "15m": "#38BDF8",
    "1H": "#32CD32", "4H": "#FFFFFF",
    "1D": "#FFA500", "1W": "#FFFF00", "1M": "#DC143C",
}

_DEFAULT_ZONE_COLOR = {
    "RESISTANCE_FLIP": "#EF4444",
    "SUPPORT_FLIP": "#22C55E",
    "FVG": "#3B82F6",
    "INVERSE_FVG": "#A855F7",
    "ORDER_BLOCK": "#F59E0B",
}

_ZONE_BORDER_DASHED = {"INVERSE_FVG"}
_MITIGATED_STATES = {"Hit", "Crossed", "Retesting"}

_TF_PERIOD_WORD = {
    "1m": "1m", "5m": "5m", "15m": "15m", "1H": "1H", "4H": "4H",
    "1D": "Day", "1W": "Week", "1M": "Month",
}

_TF_DURATION_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000,
    "1H": 3_600_000, "4H": 14_400_000,
    "1D": 86_400_000, "1W": 604_800_000, "1M": 2_592_000_000,
}

_TF_RANK = {"1m": 0, "5m": 1, "15m": 2, "1H": 3, "4H": 4, "1D": 5, "1W": 6, "1M": 7}

_MAX_LABEL_LANES = 3
_PRICE_CLUSTER_THRESHOLD_PCT = 0.0035
_LABEL_STACK_GAP_PX = 16
_HAS_DOT_EXTRA_CLEARANCE_PX = 20


def _hex_to_rgba(hex_color: str, opacity_pct: int) -> str:
    color = (hex_color or "").strip()
    if not color.startswith("#") or len(color) not in (4, 7):
        return color
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    try:
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    except ValueError:
        return hex_color
    alpha = max(0.0, min(1.0, opacity_pct / 100.0))
    return f"rgba({r},{g},{b},{alpha})"


def _normalize_ts_ms(value) -> int:
    numeric = int(value or 0)
    if 0 < numeric < 10_000_000_000:
        return numeric * 1000
    return numeric


def _is_high_type(poi_type) -> bool:
    return poi_type.endswith("_HIGH") or poi_type == "PDH"


def _pretty_line_label(poi_type, source_tf: str, price: float) -> str:
    period = _TF_PERIOD_WORD.get(source_tf, str(source_tf))
    hl = "High" if _is_high_type(poi_type) else "Low"
    return f"Prv. {period} {hl} ({price:,.2f})"


def _assign_line_stack_offsets(entries: list[dict]) -> None:
    """Clusters entries by price proximity; within each cluster (2+
    items only), sorts higher-TF-first and assigns an increasing
    vertical pixel offset so labels stack top-to-bottom without
    overlapping. Clusters of size 1 get offset 0 - untouched, at their
    own natural line position. A separate has_dot clearance is added on
    top afterward, regardless of cluster size."""
    if not entries:
        return
    max_price = max(e["price"] for e in entries) or 1.0
    threshold = max(max_price * _PRICE_CLUSTER_THRESHOLD_PCT, 0.01)

    ordered = sorted(entries, key=lambda e: e["price"])
    clusters: list[list[dict]] = []
    current: list[dict] = []
    for entry in ordered:
        if current and abs(entry["price"] - current[-1]["price"]) > threshold:
            clusters.append(current)
            current = []
        current.append(entry)
    if current:
        clusters.append(current)

    for cluster in clusters:
        if len(cluster) < 2:
            cluster[0]["stack_offset"] = 0
            continue
        cluster.sort(key=lambda e: _TF_RANK.get(e["tf"], 0), reverse=True)
        for position, entry in enumerate(cluster):
            entry["stack_offset"] = position * _LABEL_STACK_GAP_PX


def _assign_lanes_generic(entries: list[dict], key: str, threshold: float) -> None:
    lane_last_value: list[float | None] = [None] * _MAX_LABEL_LANES
    for entry in sorted(entries, key=lambda e: e[key]):
        placed = False
        for lane in range(_MAX_LABEL_LANES):
            if lane_last_value[lane] is None or abs(entry[key] - lane_last_value[lane]) >= threshold:
                entry["lane"] = lane
                lane_last_value[lane] = entry[key]
                placed = True
                break
        if not placed:
            entry["lane"] = _MAX_LABEL_LANES - 1


class PoiChartMixin(rx.State, mixin=True):
    def _next_custom_line_ms(self, hour12: int, minute: int, meridiem: str) -> int | None:
        if _NY_TZ is None:
            return None
        try:
            hour12 = max(1, min(12, int(hour12)))
            minute = max(0, min(59, int(minute)))
        except Exception:
            return None
        hour24 = (hour12 if hour12 != 12 else 0) + (12 if meridiem == "PM" and hour12 != 12 else 0)
        now_ny = datetime.datetime.now(_NY_TZ)
        candidate = now_ny.replace(hour=hour24, minute=minute, second=0, microsecond=0)
        if candidate <= now_ny:
            candidate += datetime.timedelta(days=1)
        return int(candidate.timestamp() * 1000)

    def _precise_dot_point(self, poi_type: str, source_tf: str, formed_at_ms: int, price: float) -> tuple[int, float]:
        duration_ms = _TF_DURATION_MS.get(source_tf, 0)
        window_end = formed_at_ms + duration_ms if duration_ms else formed_at_ms + 1
        is_high = _is_high_type(poi_type)
        best_ts = None
        best_val = None
        for candle in self.trading_panel_candles:
            ts = candle.get("timestamp", 0)
            if ts < formed_at_ms or ts >= window_end:
                continue
            val = candle.get("high") if is_high else candle.get("low")
            if best_val is None or (is_high and val > best_val) or (not is_high and val < best_val):
                best_ts, best_val = ts, val
        if best_ts is not None:
            return best_ts, best_val
        return formed_at_ms, price

    def _build_poi_overlays(self, symbol: str) -> tuple[list[dict], list[dict]]:
        try:
            pois = list(_engine.get_active_pois(symbol) or [])
        except Exception:
            pois = []

        overlays: list[dict] = []
        dots: list[dict] = []
        vline_by_key: dict[tuple[str, str], dict] = {}
        line_candidates: list[dict] = []
        zone_by_type: dict[str, list[dict]] = {}

        for poi in pois:
            poi_type = poi.poi_type
            tf = poi.source_tf

            if poi.is_range():
                if not self.poi_display_enabled.get(poi_type, False):
                    continue

                state_obj = None
                try:
                    state_obj = _engine.get_poi_state(symbol, poi.poi_id)
                except Exception:
                    state_obj = None
                state_label = getattr(state_obj, "state", None) if state_obj else None
                if state_label in _MITIGATED_STATES:
                    continue

                color = self.poi_zone_color.get(poi_type, _DEFAULT_ZONE_COLOR.get(poi_type, "#3B82F6"))
                opacity = self.poi_zone_type_opacity.get(poi_type, 30) / 100.0
                label_bits = [poi.chart_label]
                if self.poi_show_source_tf_badge and tf:
                    label_bits.append(f"[{tf}]")
                label = " ".join(label_bits)
                if self.poi_show_logical_id:
                    label += f"  ({poi.poi_id})"

                zone_by_type.setdefault(poi_type, []).append({
                    "id": poi.poi_id,
                    "kind": "zone",
                    "price_high": float(poi.price_high),
                    "price_low": float(poi.price_low),
                    "start_time": _normalize_ts_ms(poi.formed_at_ts),
                    "end_time": None,
                    "color": _hex_to_rgba(color, int(opacity * 100)),
                    "dashed": poi_type in _ZONE_BORDER_DASHED,
                    "label": label if self.poi_show_labels else "",
                    "opacity": opacity,
                    "_formed_at_ts": poi.formed_at_ts,
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

            is_high = _is_high_type(poi_type)
            width = self.poi_high_line_thickness if is_high else self.poi_low_line_thickness
            line_dashed = (self.poi_high_line_style if is_high else self.poi_low_line_style) != "solid"
            has_dot = self.poi_tf_droplet_enabled.get(tf, False)

            line_candidates.append({
                "id": poi.poi_id,
                "kind": "line",
                "price": float(poi.price),
                "tf": tf,
                "color": color,
                "width": width,
                "dashed": line_dashed,
                "label": label,
                "opacity": self.poi_line_transparency / 100.0,
                "has_dot": has_dot,
            })

            formed_at_ms = _normalize_ts_ms(poi.formed_at_ts)

            if has_dot:
                dot_ts, dot_price = self._precise_dot_point(poi_type, tf, formed_at_ms, poi.price)
                dots.append({
                    "id": f"{poi.poi_id}:dot",
                    "timestamp": dot_ts,
                    "price": dot_price,
                    "color": color,
                })

            if self.poi_tf_vertical_enabled.get(tf, False):
                duration_ms = _TF_DURATION_MS.get(tf)
                if duration_ms:
                    start_ms = formed_at_ms
                    end_ms = start_ms + duration_ms
                    period = _TF_PERIOD_WORD.get(tf, tf)
                    v_dashed = self.poi_tf_vertical_style.get(tf, "solid") != "solid"
                    v_opacity_color = _hex_to_rgba(color, self.poi_tf_vertical_opacity.get(tf, 50))
                    start_key = (tf, "start")
                    end_key = (tf, "end")
                    if start_key not in vline_by_key:
                        vline_by_key[start_key] = {
                            "id": f"vline:{tf}:start",
                            "timestamp": start_ms,
                            "color": v_opacity_color,
                            "dashed": v_dashed,
                            "text": f"Prv. {period} Start" if self.poi_show_labels else "",
                        }
                    if end_key not in vline_by_key:
                        vline_by_key[end_key] = {
                            "id": f"vline:{tf}:end",
                            "timestamp": end_ms,
                            "color": v_opacity_color,
                            "dashed": v_dashed,
                            "text": f"Prv. {period} End" if self.poi_show_labels else "",
                        }

        for zone_type, zones in zone_by_type.items():
            max_count = self.poi_zone_max_count.get(zone_type, 5)
            zones.sort(key=lambda z: z["_formed_at_ts"], reverse=True)
            for z in zones[:max_count]:
                z.pop("_formed_at_ts", None)
                overlays.append(z)

        _assign_line_stack_offsets(line_candidates)
        for entry in line_candidates:
            base_offset = entry.get("stack_offset", 0)
            if entry.get("has_dot"):
                base_offset += _HAS_DOT_EXTRA_CLEARANCE_PX
            entry["stack_offset"] = base_offset
            overlays.append(entry)

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
                "dashed": False,
                "text": display_text if self.poi_show_labels else "",
            })

        try:
            requested_days = int(self.trading_panel_display_days_input)
        except ValueError:
            requested_days = 5
        time_threshold_ms = max(1, requested_days) * 86_400_000 * 0.02
        _assign_lanes_generic(vline_candidates, "timestamp", time_threshold_ms)

        for entry in vline_candidates:
            overlays.append({
                "id": entry["id"],
                "kind": "vline",
                "timestamp": entry["timestamp"],
                "color": entry["color"],
                "dashed": entry.get("dashed", True),
                "label": entry["text"],
                "lane": entry.get("lane", 0),
            })

        return overlays, dots

    def refresh_poi_chart_overlays(self) -> None:
        overlays, dots = self._build_poi_overlays(self.trading_panel_symbol)
        self.poi_chart_overlays = overlays
        self.poi_chart_overlays_version += 1
        self.poi_dots = dots
        self.poi_dots_version += 1

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
