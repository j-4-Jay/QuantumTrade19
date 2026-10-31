"""PATH: engines/workers/setup/setup_callout_helper.py  (NEW FILE)

FT-H.4 Step 1 - builds the callout data for every confirmed 123Bull / 123Bear setup.
Pure function: no screen, no engine, no saving. It only reads the setups it is given.
Spec: docs/specs/File_04.1c_Callouts_Spec_v1.md (sections 2, 3, 5).
Rows 3 to 5 show a dash until FT-H.7 and FT-H.8; row 6 is the Confidence placeholder.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

BULL_BORDER = "#0E9464"
BEAR_BORDER = "#990000"
FILL_PROFIT = "#9FE2BF"
FILL_SL_HIT = "#FF6200"
FILL_RUNNING = "#4188FF"
GLOW_BULL = "#1FE0A0"
GLOW_BEAR = "#FF3B3B"
TEXT_LIGHT = "#FFFFFF"
INK_DARK = "#06231A"
TAIL_GAP_TICKS = 3
DASH = "\u2014"


def _direction_is_bull(direction: Any) -> bool:
    return "BULL" in str(direction or "").upper()


def _ms(value: Any) -> int:
    number = float(value or 0)
    return int(number if number > 10_000_000_000 else number * 1000)


def _decimals(tick_size: float) -> int:
    text = f"{float(tick_size):.10f}".rstrip("0")
    return len(text.split(".")[1]) if "." in text else 0


def _prices(candle: Any) -> List[float]:
    values = [getattr(candle, name, None) for name in ("open", "high", "low", "close")]
    return [float(v) for v in values if v is not None]


_ZONE_SHORT = {
    "RESISTANCE_FLIP": "R-Flip",
    "SUPPORT_FLIP": "S-Flip",
    "FVG": "FVG",
    "INVERSE_FVG": "iFVG",
    "ORDER_BLOCK": "OB",
}
_TF_PREFIX = {"1M": "1Mo"}


def poi_short_names(pois: Optional[List[Any]]) -> Dict[str, str]:
    """Short POI name for each poi_id, as shown on a callout.
    Lines use the chart label already in the software (PDH, P4H H ...).
    Zones carry the source timeframe in front (4H FVG, 1Mo OB; month is 1Mo, minute is 1m)."""
    names: Dict[str, str] = {}
    for poi in pois or []:
        poi_id = str(getattr(poi, "poi_id", "") or "")
        if not poi_id:
            continue
        raw = getattr(poi, "poi_type", "")
        kind = str(getattr(raw, "value", raw) or "")
        if kind in _ZONE_SHORT:
            tf = str(getattr(poi, "source_tf", "") or "")
            tf = _TF_PREFIX.get(tf, tf)
            names[poi_id] = (tf + " " if tf else "") + _ZONE_SHORT[kind]
        elif kind.upper().startswith(("IND", "CUSTOM")):
            names[poi_id] = "IND"
        else:
            names[poi_id] = str(getattr(poi, "chart_label", "") or kind)
    return names


def build_setup_callouts(confirmed_setups: List[Any], tick_size: float, buffer_ticks: int, poi_names: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    tick = float(tick_size or 0)
    if tick <= 0:
        return []
    places = _decimals(tick)
    buffer_ticks = int(buffer_ticks)
    callouts: List[Dict[str, Any]] = []
    for setup in confirmed_setups or []:
        candles = [getattr(setup, "c1", None), getattr(setup, "c2", None), getattr(setup, "c3", None)]
        if any(c is None for c in candles):
            continue
        is_bull = _direction_is_bull(getattr(setup, "direction", ""))
        c3 = candles[2]
        every_price = [p for c in candles for p in _prices(c)]
        entry = float(c3.close)
        if is_bull:
            stop = min(every_price) - buffer_ticks * tick
            anchor = float(c3.low) - TAIL_GAP_TICKS * tick
        else:
            stop = max(every_price) + buffer_ticks * tick
            anchor = float(c3.high) + TAIL_GAP_TICKS * tick
        risk_ticks = int(round(abs(entry - stop) / tick))
        name = "123Bull" if is_bull else "123Bear"
        timeframe = str(getattr(setup, "timeframe", "") or "")
        callouts.append({
            "id": f"setup_callout:{setup.event_id}",
            "uid": str(setup.event_id),
            "name": name,
            "is_bull": is_bull,
            "timeframe": timeframe,
            "timestamp": _ms(getattr(c3, "open_time", 0)),
            "anchor_price": round(anchor, places),
            "entry": round(entry, places),
            "sl": round(stop, places),
            "risk_ticks": risk_ticks,
            "border_color": BULL_BORDER if is_bull else BEAR_BORDER,
            "glow_color": GLOW_BULL if is_bull else GLOW_BEAR,
            "fill_from": FILL_RUNNING,
            "fill_win": FILL_PROFIT,
            "fill_to": FILL_SL_HIT,
            "fade": 0.0,
            "state": "running",
            "poi_short": (poi_names or {}).get(str(getattr(setup, "poi_id", "") or ""), ""),
            "text_color": TEXT_LIGHT,
            "entry_text": f"{entry:.{places}f}",
            "sl_text": f"{stop:.{places}f}",
            "ticks_text": str(risk_ticks),
            "qty_text": DASH,
            "risk_text": DASH,
            "profit_text": DASH,
            "live_text": DASH,
            "peak_text": DASH,
            "confidence_text": "Confidence: File 05 pending",
        })
    return callouts
