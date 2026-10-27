"""PATH: engines/workers/setup/setup_outcome_worker.py  (NEW FILE)

FT-H.2 - Setup outcome tracker (read-only). Spec: docs/specs/File_04.1c_Callouts_Spec_v1.md, section 7.

Pure logic: no screen, no database, no network, no orders. It is NOT wired into the app yet.
It takes a ConfirmedSetup (from SetupDetectionMonitor) and then reads the closed candles of the
SAME symbol and timeframe that come after Candle 3.

Rules (Jay):
- Entry = Candle 3 close.
- SL = lowest (Bull) or highest (Bear) OHLC value of Candle 1 to 3, minus (Bull) or plus (Bear)
  buffer_ticks * tick_size (default 7 ticks). It is worked out here; ConfirmedSetup.sl_price is not used.
- Risk = distance entry to SL (also stored in ticks).
- SL Hit = a wick touch (low <= SL for Bull, high >= SL for Bear) before 1.5R is reached.
- If one candle touches both the SL and the 1.5R price, the SL counts first (Jay, 27-10-2026).
- 1.5R reached = a win. The trade closes when a LATER candle trades back to the 1.5R price.
  The candle that first reaches 1.5R never closes the trade. After 1.5R the SL no longer matters.
- On the closing candle the peak is not raised by that candle (cautious reading, same idea as SL first).
- Peak RRR = the best favourable distance (in R) seen up to the close (or so far, while open).
- Not hit and not closed = OPEN (a trade that reached 1.5R but has not come back is still OPEN, win_reached True).
- Stores the first touch time (candle open_time) of each 0.5R level, the SL time (open_time of the
  candle) and the deepest adverse dip (in R) seen before the trade resolved.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engines.workers.setup.setup_types import SetupDirection

WIN_R = 1.5
STEP_R = 0.5
DEFAULT_BUFFER_TICKS = 7
_EPS = 1e-9

STATUS_OPEN = "OPEN"
STATUS_SL_HIT = "SL_HIT"
STATUS_WIN = "WIN"


@dataclass
class SetupOutcome:
    event_id: str
    symbol: str
    timeframe: str
    direction: str
    is_bull: bool
    entry: float
    sl: float
    risk: float
    risk_ticks: float
    tick_size: float
    buffer_ticks: float
    win_price: float
    status: str = STATUS_OPEN
    win_reached: bool = False
    win_time: Optional[int] = None
    close_time: Optional[int] = None
    sl_time: Optional[int] = None
    peak_rrr: float = 0.0
    max_adverse_r: float = 0.0
    level_times: Dict[float, int] = field(default_factory=dict)
    last_close_time: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": str(getattr(self.direction, "value", self.direction)),
            "entry": self.entry,
            "sl": self.sl,
            "risk": self.risk,
            "risk_ticks": self.risk_ticks,
            "tick_size": self.tick_size,
            "buffer_ticks": self.buffer_ticks,
            "win_price": self.win_price,
            "status": self.status,
            "win_reached": self.win_reached,
            "win_time": self.win_time,
            "close_time": self.close_time,
            "sl_time": self.sl_time,
            "peak_rrr": self.peak_rrr,
            "max_adverse_r": self.max_adverse_r,
            "level_times": {str(k): v for k, v in self.level_times.items()},
        }


class SetupOutcomeWorker:
    """Tracks the outcome of confirmed setups, one SetupOutcome per setup event_id."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._all: Dict[str, SetupOutcome] = {}
        self._active: Dict[str, SetupOutcome] = {}

    def track(self, confirmed: Any, tick_size: float, buffer_ticks: float = DEFAULT_BUFFER_TICKS) -> Optional[SetupOutcome]:
        """Starts tracking a confirmed setup. Returns the outcome, the existing one for a repeated
        event_id, or None when the setup cannot be tracked (unknown direction, bad tick, zero risk)."""
        with self._lock:
            existing = self._all.get(confirmed.event_id)
            if existing is not None:
                return existing
            tick = float(tick_size)
            if tick <= 0:
                return None
            if confirmed.direction == SetupDirection.BULL:
                is_bull = True
            elif confirmed.direction == SetupDirection.BEAR:
                is_bull = False
            else:
                return None
            candles = (confirmed.c1, confirmed.c2, confirmed.c3)
            values = [float(getattr(c, f)) for c in candles for f in ("open", "high", "low", "close")]
            entry = float(confirmed.c3.close)
            buffer_price = tick * float(buffer_ticks)
            sl = (min(values) - buffer_price) if is_bull else (max(values) + buffer_price)
            risk = (entry - sl) if is_bull else (sl - entry)
            if risk <= 0:
                return None
            win_price = entry + WIN_R * risk if is_bull else entry - WIN_R * risk
            outcome = SetupOutcome(
                event_id=confirmed.event_id,
                symbol=confirmed.symbol,
                timeframe=confirmed.timeframe,
                direction=confirmed.direction,
                is_bull=is_bull,
                entry=entry,
                sl=sl,
                risk=risk,
                risk_ticks=round(risk / tick, 6),
                tick_size=tick,
                buffer_ticks=float(buffer_ticks),
                win_price=win_price,
                last_close_time=int(confirmed.c3.close_time),
            )
            self._all[outcome.event_id] = outcome
            self._active[outcome.event_id] = outcome
            return outcome

    def on_candle_closed(self, candle: Any) -> List[SetupOutcome]:
        """Feeds one closed candle. Returns the outcomes that changed because of it."""
        changed: List[SetupOutcome] = []
        with self._lock:
            for outcome in list(self._active.values()):
                if outcome.symbol != candle.symbol or outcome.timeframe != candle.timeframe:
                    continue
                close_time = int(candle.close_time)
                if close_time <= outcome.last_close_time:
                    continue
                outcome.last_close_time = close_time
                if self._apply(outcome, candle):
                    changed.append(outcome)
                if outcome.status != STATUS_OPEN:
                    self._active.pop(outcome.event_id, None)
        return changed

    def get(self, event_id: str) -> Optional[SetupOutcome]:
        with self._lock:
            return self._all.get(event_id)

    def all_outcomes(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> List[SetupOutcome]:
        with self._lock:
            return [
                o for o in self._all.values()
                if (symbol is None or o.symbol == symbol) and (timeframe is None or o.timeframe == timeframe)
            ]

    def open_count(self) -> int:
        with self._lock:
            return len(self._active)

    @staticmethod
    def _apply(o: SetupOutcome, candle: Any) -> bool:
        high = float(candle.high)
        low = float(candle.low)
        t = int(candle.open_time)
        best = high if o.is_bull else low
        worst = low if o.is_bull else high
        fav_r = ((best - o.entry) if o.is_bull else (o.entry - best)) / o.risk
        adv_r = ((o.entry - worst) if o.is_bull else (worst - o.entry)) / o.risk
        sl_touched = (worst <= o.sl) if o.is_bull else (worst >= o.sl)
        back_at_win = (worst <= o.win_price) if o.is_bull else (worst >= o.win_price)

        if not o.win_reached:
            if sl_touched:
                o.status = STATUS_SL_HIT
                o.sl_time = t
                o.close_time = int(candle.close_time)
                o.max_adverse_r = max(o.max_adverse_r, adv_r)
                return True
            changed = False
            if adv_r > o.max_adverse_r:
                o.max_adverse_r = adv_r
                changed = True
            if SetupOutcomeWorker._record_progress(o, fav_r, t):
                changed = True
            if fav_r >= WIN_R - _EPS:
                o.win_reached = True
                o.win_time = t
                changed = True
            return changed

        if back_at_win:
            o.status = STATUS_WIN
            o.close_time = int(candle.close_time)
            return True
        return SetupOutcomeWorker._record_progress(o, fav_r, t)

    @staticmethod
    def _record_progress(o: SetupOutcome, fav_r: float, t: int) -> bool:
        changed = False
        if fav_r > o.peak_rrr:
            o.peak_rrr = fav_r
            changed = True
        steps = int(math.floor(fav_r / STEP_R + _EPS))
        for k in range(1, steps + 1):
            level = round(k * STEP_R, 2)
            if level not in o.level_times:
                o.level_times[level] = t
                changed = True
        return changed
