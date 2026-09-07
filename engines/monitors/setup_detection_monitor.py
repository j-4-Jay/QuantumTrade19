"""File 04 - Setup Detection Monitor - Tier 2 Assembly.
PATH: engines/monitors/setup_detection_monitor.py (REPLACE ENTIRE FILE)

Wires the 7 Tier 1 Workers behind the exact interface locked in
04_SetupDetectionMonitor_Prompt.md Section 3:

    get_pending_setups(symbol, tf)
    get_confirmed_setups(symbol, tf)

Every CONFIRMED setup is pushed onto the shared internal event bus exactly
once, carrying a unique event_id (supports the locked idempotency rule) - for
Confidence Monitor (File 05) and, later, Execution Monitor's Opposite-Setup
Exit Guard (File 11) to consume.

Does NOT re-derive or alter File 03 POI/FVG/Order Block logic (consumed
read-only via POIMonitor) or the locked 123Bull/123Bear rules (consumed via
Bull123FSMWorker / Bear123FSMWorker, unmodified).

(No wiring changes in this revision - only the internal FSM engine in
_fsm_base.py changed. Replace this file only to keep the whole File 04
module on one consistent revision.)
"""
from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from engines.workers.setup.setup_types import ConfirmedSetup, PendingSetup, SetupDirection
from engines.workers.setup.candle_lock_registry import CandleLockRegistry
from engines.workers.setup.poi_interaction_detector_worker import POIInteractionDetectorWorker
from engines.workers.setup.engulfing_detector_worker import EngulfingDetectorWorker
from engines.workers.setup.fvg_confirmation_detector_worker import FVGConfirmationDetectorWorker
from engines.workers.setup.bull123_fsm_worker import Bull123FSMWorker
from engines.workers.setup.bear123_fsm_worker import Bear123FSMWorker
from engines.workers.setup.mtf_cascade_worker import MTFCascadeWorker

TRADING_TFS = ("1m", "5m", "15m")


class SetupDetectionMonitor:
    """Tier-2 orchestration layer; workers own calculations, monitor owns wiring.

    poi_monitor must expose: get_active_pois(symbol), get_poi_state(symbol, poi_id)
    (File 03, locked, read-only).
    symbol_registry must expose: get_active_symbols(), get_tick_size(symbol)
    (File 02, locked, read-only)."""

    def __init__(self, poi_monitor, symbol_registry) -> None:
        self.poi_monitor = poi_monitor
        self.symbol_registry = symbol_registry

        self._interaction = POIInteractionDetectorWorker()
        self._engulfing = EngulfingDetectorWorker()
        self._fvg_confirm = FVGConfirmationDetectorWorker()

        self._lock_registry: Dict[Tuple[str, str], CandleLockRegistry] = {}
        self._bull_fsm: Dict[Tuple[str, str], Bull123FSMWorker] = {}
        self._bear_fsm: Dict[Tuple[str, str], Bear123FSMWorker] = {}
        self._cascade: Dict[str, MTFCascadeWorker] = {}

        self._confirmed_setups: Dict[Tuple[str, str], List[ConfirmedSetup]] = {}
        self._seen_event_ids: set = set()
        self._subscribers: List[Callable[[ConfirmedSetup], None]] = []

        for symbol in self.symbol_registry.get_active_symbols():
            self._wire_symbol(symbol)

    def _wire_symbol(self, symbol: str) -> None:
        for tf in TRADING_TFS:
            key = (symbol, tf)
            self._lock_registry[key] = CandleLockRegistry()
            self._bull_fsm[key] = Bull123FSMWorker(self._lock_registry[key])
            self._bear_fsm[key] = Bear123FSMWorker(self._lock_registry[key])
            self._confirmed_setups[key] = []
        self._cascade[symbol] = MTFCascadeWorker(
            bull_1m_fsm=self._bull_fsm[(symbol, "1m")],
            bear_1m_fsm=self._bear_fsm[(symbol, "1m")],
        )

    def get_pending_setups(self, symbol: str, tf: str) -> List[PendingSetup]:
        key = (symbol, tf)
        pending: List[PendingSetup] = []
        if key in self._bull_fsm:
            pending.extend(self._bull_fsm[key].get_pending(symbol, tf))
        if key in self._bear_fsm:
            pending.extend(self._bear_fsm[key].get_pending(symbol, tf))
        return pending

    def get_confirmed_setups(self, symbol: str, tf: str) -> List[ConfirmedSetup]:
        return list(self._confirmed_setups.get((symbol, tf), []))

    def subscribe(self, callback: Callable[[ConfirmedSetup], None]) -> None:
        self._subscribers.append(callback)

    def on_candle_closed(self, candle) -> List[ConfirmedSetup]:
        symbol, tf = candle.symbol, candle.timeframe
        if tf not in TRADING_TFS:
            return []
        key = (symbol, tf)
        if key not in self._bull_fsm:
            self._wire_symbol(symbol)

        pois = self.poi_monitor.get_active_pois(symbol)
        states = {poi.poi_id: self.poi_monitor.get_poi_state(symbol, poi.poi_id) for poi in pois}
        interactions = self._interaction.detect(candle, pois, states)

        bull_interactions = {i.poi_id: i for i in interactions if i.search_direction == SetupDirection.BULL}
        bear_interactions = {i.poi_id: i for i in interactions if i.search_direction == SetupDirection.BEAR}

        newly_confirmed: List[ConfirmedSetup] = []
        newly_confirmed.extend(self._bull_fsm[key].on_candle_closed(candle, bull_interactions))
        newly_confirmed.extend(self._bear_fsm[key].on_candle_closed(candle, bear_interactions))

        for confirmed in newly_confirmed:
            self._enrich(confirmed)
            self._emit(confirmed)

        if tf == "1m":
            cascade_hits = self._cascade[symbol].on_1m_candle_closed(candle, bull_interactions, bear_interactions)
            for confirmed in cascade_hits:
                self._enrich(confirmed, already_scored=True)
                self._emit(confirmed)

        for confirmed in newly_confirmed:
            if tf in ("5m", "15m"):
                tick_size = self.symbol_registry.get_tick_size(symbol)
                self._cascade[symbol].start_watch(confirmed, tick_size)

        return newly_confirmed

    def _enrich(self, confirmed: ConfirmedSetup, already_scored: bool = False) -> None:
        if already_scored:
            return
        confirmed.engulfing = self._engulfing.candle2_engulfs_candle1(confirmed.c1, confirmed.c2)
        confirmed.fvg_confirmation, confirmed.fvg_range = self._fvg_confirm.check(
            confirmed.c1, confirmed.c3, confirmed.direction
        )
        confirmed.sl_price = (
            min(confirmed.c1.low, confirmed.c2.low, confirmed.c3.low)
            if confirmed.direction == SetupDirection.BULL
            else max(confirmed.c1.high, confirmed.c2.high, confirmed.c3.high)
        )

    def _emit(self, confirmed: ConfirmedSetup) -> None:
        if confirmed.event_id in self._seen_event_ids:
            return
        self._seen_event_ids.add(confirmed.event_id)
        key = (confirmed.symbol, confirmed.timeframe)
        self._confirmed_setups.setdefault(key, []).append(confirmed)
        for callback in self._subscribers:
            callback(confirmed)

    def get_health(self, symbol: str) -> str:
        for tf in TRADING_TFS:
            if (symbol, tf) not in self._bull_fsm:
                return "DOWN"
        return "OK"
