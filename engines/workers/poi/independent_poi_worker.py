"""Independent POI lines (stage FT-C, task FT-C.2).

PATH: engines/workers/poi/independent_poi_worker.py (NEW FILE)
SPEC: docs/specs/File_04.1b_CustomPOI_Spec_v2.md

What it does: keeps the Independent POI lines of each symbol (cap 10, lowest
free number, unique id, price snapped to the tick size) and turns them into
ordinary POI objects. A callback hands the POI list to the POI monitor, so the
lines run through the same state tracker and setup detection as real POIs.

What it does NOT do (later tasks): saving to disk (FT-C.5, FT-C.7), drawing
on the chart (FT-C.3, FT-C.4), the paper-only badge (FT-C.5).

Moving a line creates a NEW poi_id (the revision number rises) and a new
creation time, so old touch history is dropped and detection restarts from
the live candle. The line id (uid) and the number stay the same.
"""
from __future__ import annotations

import math
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from engines.workers.poi.poi_types import POI

IND_POI_TYPE = "IND_POI"
MAX_LINES_PER_SYMBOL = 10


def snap_to_tick(price: float, tick_size: float) -> float:
    """Round a price to the nearest multiple of the tick size."""
    if not tick_size or tick_size <= 0:
        return float(price)
    steps = round(float(price) / float(tick_size))
    return round(steps * float(tick_size), 12)


@dataclass
class IndependentLine:
    uid: str
    number: int
    symbol: str
    price: float
    created_ts: float
    rev: int = 1
    allow_live: bool = False
    style: Dict[str, object] = field(default_factory=dict)
    updated_ts: float = 0.0

    @property
    def poi_id(self) -> str:
        return f"{self.symbol}:IND:{self.uid}:{self.rev}"

    @property
    def label(self) -> str:
        return f"Ind. POI {self.number}"


class IndependentPOIStore:
    def __init__(
        self,
        on_change: Optional[Callable[[str, List[POI]], None]] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._on_change = on_change
        self._clock = clock
        self._lines: Dict[str, Dict[str, IndependentLine]] = {}

    def lines(self, symbol: str) -> List[IndependentLine]:
        return sorted(self._lines.get(symbol, {}).values(), key=lambda line: line.number)

    def pois(self, symbol: str) -> List[POI]:
        return [self._to_poi(line) for line in self.lines(symbol)]

    def add(self, symbol: str, price: float, tick_size: float) -> Optional[IndependentLine]:
        if not self._valid_price(price):
            return None
        number = self._free_number(symbol)
        if number is None:
            return None
        line = IndependentLine(
            uid=uuid.uuid4().hex[:12], number=number, symbol=symbol,
            price=snap_to_tick(price, tick_size), created_ts=float(self._clock()),
            updated_ts=float(self._clock()),
        )
        self._lines.setdefault(symbol, {})[line.uid] = line
        self._notify(symbol)
        return line

    def move(self, symbol: str, uid: str, price: float, tick_size: float) -> Optional[IndependentLine]:
        line = self._lines.get(symbol, {}).get(uid)
        if line is None or not self._valid_price(price):
            return None
        line.price = snap_to_tick(price, tick_size)
        line.rev += 1
        line.created_ts = float(self._clock())
        line.updated_ts = line.created_ts
        self._notify(symbol)
        return line

    def delete(self, symbol: str, uid: str) -> bool:
        if uid not in self._lines.get(symbol, {}):
            return False
        del self._lines[symbol][uid]
        self._notify(symbol)
        return True

    def set_style(self, symbol: str, uid: str, **changes) -> Optional[IndependentLine]:
        """Change colour, width, opacity or line_style of one line. Bad values are ignored."""
        line = self._lines.get(symbol, {}).get(uid)
        if line is None:
            return None
        clean = _clean_style(changes)
        if clean:
            line.style = {**line.style, **clean}
            line.updated_ts = float(self._clock())
            self._notify(symbol)
        return line

    @staticmethod
    def _valid_price(price: float) -> bool:
        try:
            return math.isfinite(float(price)) and float(price) > 0
        except (TypeError, ValueError):
            return False

    def _free_number(self, symbol: str) -> Optional[int]:
        used = {line.number for line in self._lines.get(symbol, {}).values()}
        for number in range(1, MAX_LINES_PER_SYMBOL + 1):
            if number not in used:
                return number
        return None

    def _to_poi(self, line: IndependentLine) -> POI:
        return POI(
            poi_id=line.poi_id, symbol=line.symbol, poi_type=IND_POI_TYPE,
            role="independent", source_tf="independent", price=line.price,
            formed_at_index=-1, formed_at_ts=line.created_ts, active=True,
            display_enabled=True, strategy_enabled=True,
            metadata={
                "independent": True, "uid": line.uid, "number": line.number,
                "rev": line.rev, "allow_live": line.allow_live, "source_tf": "independent",
            },
        )

    def symbols(self) -> List[str]:
        return sorted(symbol for symbol, lines in self._lines.items() if lines)

    def all_lines(self) -> Dict[str, List[IndependentLine]]:
        return {symbol: self.lines(symbol) for symbol in self.symbols()}

    def restore(self, lines: List[IndependentLine]) -> int:
        """Load saved lines without notifying anyone. Keeps the cap and unique numbers.
        The live switch is always OFF after loading."""
        count = 0
        for line in lines:
            bucket = self._lines.setdefault(line.symbol, {})
            if line.uid in bucket or len(bucket) >= MAX_LINES_PER_SYMBOL:
                continue
            if any(other.number == line.number for other in bucket.values()):
                continue
            line.allow_live = False
            bucket[line.uid] = line
            count += 1
        return count

    def set_allow_live(self, symbol: str, uid: str, value: bool) -> Optional[IndependentLine]:
        line = self._lines.get(symbol, {}).get(uid)
        if line is None:
            return None
        line.allow_live = bool(value)
        self._notify(symbol)
        return line

    def _notify(self, symbol: str) -> None:
        if self._on_change is not None:
            self._on_change(symbol, self.pois(symbol))


LINE_STYLES = ("solid", "dashed", "dotted")
DEFAULT_LINE_STYLE = {"color": "#F59E0B", "width": 2, "line_style": "dashed", "opacity": 100}
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def hex_to_rgba(color: str, opacity_pct: int) -> str:
    """'#F59E0B' and 50 -> 'rgba(245,158,11,0.5)'."""
    red, green, blue = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    alpha = max(0, min(100, int(opacity_pct))) / 100.0
    return f"rgba({red},{green},{blue},{alpha:g})"


def _clean_style(changes: Dict[str, object]) -> Dict[str, object]:
    """Keep only valid style values: color #RRGGBB, width 1-5, opacity 0-100, line_style."""
    clean: Dict[str, object] = {}
    color = changes.get("color")
    if isinstance(color, str) and _HEX_RE.match(color):
        clean["color"] = color.upper()
    for key, low, high in (("width", 1, 5), ("opacity", 0, 100)):
        try:
            number = int(float(changes.get(key)))
        except (TypeError, ValueError):
            continue
        if low <= number <= high:
            clean[key] = number
    if changes.get("line_style") in LINE_STYLES:
        clean["line_style"] = changes["line_style"]
    return clean


def build_chart_items(lines: List[IndependentLine]) -> List[Dict[str, object]]:
    """Turn lines into the plain dicts the chart draws (kind "ind_line")."""
    items: List[Dict[str, object]] = []
    for line in lines:
        style = {**DEFAULT_LINE_STYLE, **line.style}
        items.append({
            "id": f"ind:{line.uid}", "kind": "ind_line", "uid": line.uid,
            "number": line.number, "price": line.price, "label": line.label,
            "color": style["color"], "line_color": hex_to_rgba(style["color"], style["opacity"]),
            "width": style["width"], "line_style": style["line_style"],
            "dashed": style["line_style"] != "solid", "opacity": style["opacity"],
            "allow_live": line.allow_live,
            "chart_label": f"{line.label}  |  {'LIVE' if line.allow_live else 'PAPER'}",
        })
    return items
