"""
engines/monitors/poi_monitor.py

Tier 2 — POI_Monitor assembly for File 03.

Wires the 5 Tier-1 Workers behind one clean interface, per the Engine
Hierarchy rule: Monitors have zero business logic of their own. Everything
here is orchestration + the shared per-symbol POI/state registries that the
Workers publish into and the interface reads from.

Interface (per 03_POIMonitor_Prompt.md):
    get_active_pois(symbol)
    get_poi_state(symbol, poi_id)
    set_poi_type_enabled(type, bool)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from engines.workers.poi.htf_availability import MarketDataMonitorLike
from engines.workers.poi.poi_types import POI, POIStateRecord, POIType, DEFAULT_ENABLED
from engines.workers.poi.poi_level_calculator_worker import POILevelCalculatorWorker
from engines.workers.poi.fvg_detector_worker import FVGDetectorWorker
from engines.workers.poi.orderblock_detector_worker import OrderBlockDetectorWorker
from engines.workers.poi.inverse_fvg_detector_worker import InverseFVGDetectorWorker
from engines.workers.poi.poi_state_tracker_worker import POIStateTrackerWorker

logger = logging.getLogger("poi_monitor")


class POIMonitor:
    def __init__(self, market_data_monitor: MarketDataMonitorLike, symbol_registry) -> None:
        """symbol_registry must expose get_active_symbols() -> list[str] and
        get_tick_size(symbol) -> float, mirroring Symbol_Registry_Worker from
        File 02 — POI Monitor never hardcodes symbols or tick sizes either."""
        self.mdm = market_data_monitor
        self.symbol_registry = symbol_registry

        # Registries: symbol -> {poi_id: POI} / {poi_id: POIStateRecord}
        self._level_pois: Dict[str, Dict[str, POI]] = {}
        self._fvg_pois: Dict[str, Dict[str, POI]] = {}
        self._ob_pois: Dict[str, Dict[str, POI]] = {}
        self._inv_fvg_pois: Dict[str, Dict[str, POI]] = {}
        self._states: Dict[str, Dict[str, POIStateRecord]] = {}

        # One shared enabled-types dict per symbol so toggles apply live and
        # every Worker for that symbol reads the same source of truth.
        self._enabled_types: Dict[str, Dict[str, bool]] = {}

        self._level_workers: Dict[str, POILevelCalculatorWorker] = {}
        self._fvg_workers: Dict[str, FVGDetectorWorker] = {}
        self._ob_workers: Dict[str, OrderBlockDetectorWorker] = {}
        self._inv_workers: Dict[str, InverseFVGDetectorWorker] = {}
        self._state_workers: Dict[str, POIStateTrackerWorker] = {}

        self._tasks: List[asyncio.Task] = []

        for symbol in self.symbol_registry.get_active_symbols():
            self._wire_symbol(symbol)

    # ------------------------------------------------------------------ wiring
    def _wire_symbol(self, symbol: str) -> None:
        enabled = dict(DEFAULT_ENABLED)
        self._enabled_types[symbol] = enabled
        self._level_pois[symbol] = {}
        self._fvg_pois[symbol] = {}
        self._ob_pois[symbol] = {}
        self._inv_fvg_pois[symbol] = {}
        self._states[symbol] = {}

        def _on_level_update(sym: str, pois: List[POI]) -> None:
            self._level_pois[sym] = {p.poi_id: p for p in pois}

        def _on_fvg_update(sym: str, pois: List[POI]) -> None:
            self._fvg_pois[sym] = {p.poi_id: p for p in pois}

        def _on_ob_update(sym: str, pois: List[POI]) -> None:
            self._ob_pois[sym] = {p.poi_id: p for p in pois}

        def _on_inv_update(sym: str, pois: List[POI]) -> None:
            self._inv_fvg_pois[sym] = {p.poi_id: p for p in pois}

        def _on_state_update(sym: str, states: Dict[str, POIStateRecord]) -> None:
            self._states[sym] = states

        self._level_workers[symbol] = POILevelCalculatorWorker(
            self.mdm, symbol, enabled, _on_level_update)
        self._fvg_workers[symbol] = FVGDetectorWorker(
            self.mdm, symbol, enabled, _on_fvg_update)
        self._ob_workers[symbol] = OrderBlockDetectorWorker(
            self.mdm, symbol, enabled, _on_ob_update)
        self._inv_workers[symbol] = InverseFVGDetectorWorker(
            self.mdm, symbol, enabled,
            get_fvg_pois=lambda sym=symbol: list(self._fvg_pois[sym].values()),
            on_poi_update=_on_inv_update)
        self._state_workers[symbol] = POIStateTrackerWorker(
            self.mdm, symbol, self.symbol_registry.get_tick_size(symbol),
            get_active_pois=lambda sym=symbol: self._collect_all_pois(sym),
            on_state_update=_on_state_update)

        # First synchronous pass so get_active_pois() has data even before
        # the async loops have ticked once (important for tests + fast UI).
        self._level_workers[symbol].recompute()
        self._fvg_workers[symbol].recompute()
        self._ob_workers[symbol].recompute()
        self._inv_workers[symbol].recompute()
        self._state_workers[symbol].recompute()

    def _collect_all_pois(self, symbol: str) -> List[POI]:
        merged: Dict[str, POI] = {}
        for reg in (self._level_pois, self._fvg_pois, self._ob_pois, self._inv_fvg_pois):
            merged.update(reg.get(symbol, {}))
        return [p for p in merged.values() if p.active]

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        for symbol in self.symbol_registry.get_active_symbols():
            self._tasks.append(asyncio.create_task(self._level_workers[symbol].run_forever()))
            self._tasks.append(asyncio.create_task(self._fvg_workers[symbol].run_forever()))
            self._tasks.append(asyncio.create_task(self._ob_workers[symbol].run_forever()))
            self._tasks.append(asyncio.create_task(self._inv_workers[symbol].run_forever()))
            self._tasks.append(asyncio.create_task(self._state_workers[symbol].run_forever()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    # ------------------------------------------------------------------ public interface
    def get_active_pois(self, symbol: str) -> List[POI]:
        return self._collect_all_pois(symbol)

    def get_poi_state(self, symbol: str, poi_id: str) -> Optional[POIStateRecord]:
        return self._states.get(symbol, {}).get(poi_id)

    def set_poi_type_enabled(self, poi_type: str, enabled: bool) -> None:
        """Settings toggle entrypoint. Fans out to every symbol currently
        wired so the change takes effect live across the whole app, not just
        the symbol currently open on the Dashboard."""
        for symbol in self.symbol_registry.get_active_symbols():
            self._enabled_types[symbol][poi_type] = enabled
            if poi_type == POIType.FVG:
                self._fvg_workers[symbol].set_enabled(enabled)
            elif poi_type == POIType.ORDER_BLOCK:
                self._ob_workers[symbol].set_enabled(enabled)
            elif poi_type == POIType.INVERSE_FVG:
                self._inv_workers[symbol].set_enabled(enabled)
            else:
                self._level_workers[symbol].set_type_enabled(poi_type, enabled)
            # State tracker re-derives its POI set on the next recompute via
            # get_active_pois(); no direct call needed, keeping it decoupled.
            self._state_workers[symbol].recompute()

    def get_health(self, symbol: str) -> str:
        """OK if every Worker for the symbol has data; DEGRADED if any HTF
        source used by an enabled type is still unpopulated."""
        worker = self._level_workers.get(symbol)
        if worker is None:
            return "DOWN"
        for poi_type, on in self._enabled_types[symbol].items():
            if not on:
                continue
            if not worker.is_type_ready(poi_type) and poi_type in worker.enabled_types:
                if worker.availability.candle_counts:
                    return "DEGRADED"
        return "OK"
