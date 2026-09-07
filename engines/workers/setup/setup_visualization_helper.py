"""File 04.1 - Trading Panel Setup Visualization - pure helper functions.

PATH: engines/workers/setup/setup_visualization_helper.py (NEW FILE)

Read-only formatting/aggregation ONLY. Every input is consumed exactly as
returned by SetupDetectionMonitor.get_confirmed_setups(symbol, tf) /
get_pending_setups(symbol, tf) - this file does not re-derive, re-score, or
alter any 123Bull/123Bear FSM logic, POI logic, or confidence logic.

Produces dicts in the EXACT shape already consumed by
ui/components/kline_chart.py's generic overlay renderer (kind="zone") and
its poi_dots renderer - no new chart-side code required.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Tuple

try:
    from zoneinfo import ZoneInfo
    _NY_TZ = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover
    _NY_TZ = None

_BULL_COLOR = "#16C784"
_BEAR_COLOR = "#EA3943"
_PENDING_COLOR = "#F5A623"
_CONFIRMED_ZONE_OPACITY = 0.16
_PENDING_ZONE_OPACITY = 0.08


def _ms(candle_ts: float) -> int:
    """Normalizes a candle's own timestamp field to epoch ms, tolerating
    either seconds or already-ms values (mirrors poi_chart_mixin.py's
    _normalize_ts_ms convention)."""
    value = float(candle_ts or 0)
    return int(value if value > 10_000_000_000 else value * 1000)


def _candle_open_ms(candle) -> int:
    return _ms(getattr(candle, "open_time", 0))


def _candle_close_ms(candle, tf_duration_ms: int) -> int:
    close_time = getattr(candle, "close_time", None)
    if close_time:
        return _ms(close_time)
    return _candle_open_ms(candle) + max(tf_duration_ms - 1, 0)


_TF_DURATION_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000}


def build_setup_overlays_and_dots(
    confirmed_setups: List[Any],
    pending_setups: List[Any],
    timeframe: str,
) -> Tuple[List[Dict], List[Dict]]:
    """Read-only: confirmed_setups / pending_setups must come straight from
    SetupDetectionMonitor.get_confirmed_setups()/get_pending_setups().

    Returns (overlays, dots) - both already shaped for kline_chart.py:
      overlay kind="zone": id, kind, price_high, price_low, start_time,
        end_time, color(rgba string), dashed, label, opacity
      dot: id, timestamp, price, color
    """
    duration_ms = _TF_DURATION_MS.get(timeframe, 60_000)
    overlays: List[Dict] = []
    dots: List[Dict] = []

    for setup in confirmed_setups:
        direction = str(getattr(setup, "direction", ""))
        is_bull = direction.endswith("Bull")
        color = _BULL_COLOR if is_bull else _BEAR_COLOR
        c1, c2, c3 = setup.c1, setup.c2, setup.c3
        price_high = max(c1.high, c2.high, c3.high)
        price_low = min(c1.low, c2.low, c3.low)
        start_ms = _candle_open_ms(c1)
        end_ms = _candle_close_ms(c3, duration_ms)

        r, g, b = _hex_to_rgb(color)
        overlays.append({
            "id": f"setup_confirmed:{setup.event_id}",
            "kind": "zone",
            "price_high": float(price_high),
            "price_low": float(price_low),
            "start_time": start_ms,
            "end_time": end_ms,
            "color": f"rgba({r},{g},{b},{_CONFIRMED_ZONE_OPACITY})",
            "dashed": False,
            "label": f"{direction} \u2713",
            "opacity": _CONFIRMED_ZONE_OPACITY,
        })
        dots.append({
            "id": f"setup_confirmed_dot:{setup.event_id}",
            "timestamp": _candle_open_ms(c3),
            "price": float(c3.close),
            "color": color,
        })

    for pending in pending_setups:
        anchor_candle = pending.c2 if getattr(pending, "c2", None) is not None else pending.c1
        if anchor_candle is None:
            continue
        direction = str(getattr(pending, "direction", ""))
        r, g, b = _hex_to_rgb(_PENDING_COLOR)
        dots.append({
            "id": f"setup_pending_dot:{pending.pending_id}",
            "timestamp": _candle_open_ms(anchor_candle),
            "price": float(anchor_candle.close),
            "color": _PENDING_COLOR,
        })
        if pending.c1 is not None and pending.c2 is not None:
            price_high = max(pending.c1.high, pending.c2.high)
            price_low = min(pending.c1.low, pending.c2.low)
            overlays.append({
                "id": f"setup_pending:{pending.pending_id}",
                "kind": "zone",
                "price_high": float(price_high),
                "price_low": float(price_low),
                "start_time": _candle_open_ms(pending.c1),
                "end_time": _candle_close_ms(pending.c2, duration_ms),
                "color": f"rgba({r},{g},{b},{_PENDING_ZONE_OPACITY})",
                "dashed": True,
                "label": f"{direction} \u2026",
                "opacity": _PENDING_ZONE_OPACITY,
            })

    return overlays, dots


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    color = hex_color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def build_setup_stats_rows(confirmed_setups: List[Any]) -> List[Dict]:
    """Date-wise (America/New_York) count of confirmed Bull / confirmed Bear,
    sourced ONLY from SetupDetectionMonitor.get_confirmed_setups(). Aggregation
    only - no scoring, no re-derivation.

    NOTE: SetupDetectionMonitor currently exposes confirmed + pending setups
    only - it does not persist a record of failed/aborted FSM attempts (those
    are ephemeral internal FSM state, never emitted anywhere). Per the File
    04.1 instruction not to add new Worker logic, failed_aborted is reported
    as 0 here until File 04 itself is extended to emit that event - the
    column is already wired end-to-end and will populate automatically the
    moment that data exists.
    """
    by_date: Dict[Tuple[int, int, int], Dict[str, int]] = {}
    for setup in confirmed_setups:
        unix_seconds = getattr(setup, "confirmed_at", 0)
        if _NY_TZ is None:
            dt = datetime.datetime.utcfromtimestamp(unix_seconds)
        else:
            dt = datetime.datetime.fromtimestamp(unix_seconds, tz=_NY_TZ)
        sort_key = (dt.year, dt.month, dt.day)
        row = by_date.setdefault(
            sort_key,
            {"date": dt.strftime("%d-%m-%Y"), "confirmed_bull": 0, "confirmed_bear": 0, "failed_aborted": 0},
        )
        direction = str(getattr(setup, "direction", ""))
        if direction.endswith("Bull"):
            row["confirmed_bull"] += 1
        elif direction.endswith("Bear"):
            row["confirmed_bear"] += 1

    rows = [row for _, row in sorted(by_date.items(), key=lambda kv: kv[0], reverse=True)]
    return rows
