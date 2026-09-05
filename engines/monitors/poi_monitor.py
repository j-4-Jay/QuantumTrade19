"""File 03.1 POI Monitor: persistent display, strategy and zone-source controls.

PATH: engines/monitors/poi_monitor.py (REPLACE ENTIRE FILE)

FIX (Timezone Mode toggle) - added set_poi_timezone_mode(mode). Passed
explicitly ONLY to POILevelCalculatorWorker's constructor/setter (NOT
added to the shared `kwargs` dict passed to all four workers, since
FVGDetectorWorker/OrderBlockDetectorWorker/InverseFVGDetectorWorker do
not declare a `timezone_mode` parameter and would raise TypeError if it
were - see poi_level_calculator_worker.py's docstring for why zones stay
UTC-only in this pass).

FIX 1 (corrected, carried forward): tick_size lookup uses
`self.symbol_registry.get_tick_size(symbol)`.

FIX 2 (unchanged, carried forward): set_poi_display_enabled() also
updates the display_enabled dict directly on the three zone workers.
"""
from __future__ import annotations


import asyncio
from typing import Dict, List, Optional


from engines.workers.poi.htf_availability import MarketDataMonitorLike
from engines.workers.poi.poi_types import POI, POIStateRecord, POIType
from engines.workers.poi.poi_settings import POISettingsStore
from engines.workers.poi.poi_level_calculator_worker import POILevelCalculatorWorker
from engines.workers.poi.fvg_detector_worker import FVGDetectorWorker
from engines.workers.poi.orderblock_detector_worker import OrderBlockDetectorWorker
from engines.workers.poi.inverse_fvg_detector_worker import InverseFVGDetectorWorker
from engines.workers.poi.poi_state_tracker_worker import POIStateTrackerWorker



class POIMonitor:
    """Tier-2 orchestration layer; workers own calculations, monitor owns wiring."""


    def __init__(self, market_data_monitor: MarketDataMonitorLike, symbol_registry, settings_store: Optional[POISettingsStore] = None) -> None:
        self.mdm = market_data_monitor
        self.symbol_registry = symbol_registry
        self._settings_store = settings_store or POISettingsStore()
        self._settings = self._settings_store.get()
        self._level_pois: Dict[str, Dict[str, POI]] = {}
        self._fvg_pois: Dict[str, Dict[str, POI]] = {}
        self._ob_pois: Dict[str, Dict[str, POI]] = {}
        self._inv_fvg_pois: Dict[str, Dict[str, POI]] = {}
        self._states: Dict[str, Dict[str, POIStateRecord]] = {}
        self._enabled_types: Dict[str, Dict[str, bool]] = {}
        self._level_workers: Dict[str, POILevelCalculatorWorker] = {}
        self._fvg_workers: Dict[str, FVGDetectorWorker] = {}
        self._ob_workers: Dict[str, OrderBlockDetectorWorker] = {}
        self._inv_workers: Dict[str, InverseFVGDetectorWorker] = {}
        self._state_workers: Dict[str, POIStateTrackerWorker] = {}
        self._tasks: List[asyncio.Task] = []
        for symbol in self.symbol_registry.get_active_symbols():
            self._wire_symbol(symbol)


    def _wire_symbol(self, symbol: str) -> None:
        strategy = self._settings.strategy_enabled
        self._enabled_types[symbol] = strategy
        self._level_pois[symbol], self._fvg_pois[symbol] = {}, {}
        self._ob_pois[symbol], self._inv_fvg_pois[symbol], self._states[symbol] = {}, {}, {}


        def level_update(sym: str, pois: List[POI]) -> None: self._level_pois[sym] = {p.poi_id: p for p in pois}
        def fvg_update(sym: str, pois: List[POI]) -> None: self._fvg_pois[sym] = {p.poi_id: p for p in pois}
        def ob_update(sym: str, pois: List[POI]) -> None: self._ob_pois[sym] = {p.poi_id: p for p in pois}
        def inverse_update(sym: str, pois: List[POI]) -> None: self._inv_fvg_pois[sym] = {p.poi_id: p for p in pois}
        def state_update(sym: str, states: Dict[str, POIStateRecord]) -> None: self._states[sym] = states


        kwargs = {"display_enabled": self._settings.display_enabled, "strategy_enabled": strategy, "zone_source_tf_enabled": self._settings.zone_source_tf_enabled}
        self._level_workers[symbol] = POILevelCalculatorWorker(self.mdm, symbol, strategy, level_update, timezone_mode=self._settings.timezone_mode, **kwargs)
        self._fvg_workers[symbol] = FVGDetectorWorker(self.mdm, symbol, strategy, fvg_update, **kwargs)
        self._ob_workers[symbol] = OrderBlockDetectorWorker(self.mdm, symbol, strategy, ob_update, **kwargs)
        self._inv_workers[symbol] = InverseFVGDetectorWorker(self.mdm, symbol, strategy, lambda sym=symbol: list(self._fvg_pois[sym].values()), inverse_update, **kwargs)
        self._state_workers[symbol] = POIStateTrackerWorker(self.mdm, symbol, self.symbol_registry.get_tick_size(symbol), lambda sym=symbol: self._collect_all_pois(sym), state_update)
        self._recompute_symbol(symbol)


    def _recompute_symbol(self, symbol: str) -> None:
        self._level_workers[symbol].recompute()
        self._fvg_workers[symbol].recompute()
        self._ob_workers[symbol].recompute()
        self._inv_workers[symbol].recompute()
        self._state_workers[symbol].recompute()


    def _collect_all_pois(self, symbol: str) -> List[POI]:
        merged: Dict[str, POI] = {}
        for registry in (self._level_pois, self._fvg_pois, self._ob_pois, self._inv_fvg_pois):
            merged.update(registry.get(symbol, {}))
        return [poi for poi in merged.values() if poi.active]


    def start(self) -> None:
        for symbol in self.symbol_registry.get_active_symbols():
            self._tasks.extend([
                asyncio.create_task(self._level_workers[symbol].run_forever()),
                asyncio.create_task(self._fvg_workers[symbol].run_forever()),
                asyncio.create_task(self._ob_workers[symbol].run_forever()),
                asyncio.create_task(self._inv_workers[symbol].run_forever()),
                asyncio.create_task(self._state_workers[symbol].run_forever()),
            ])


    async def stop(self) -> None:
        for task in self._tasks: task.cancel()
        self._tasks.clear()


    def get_active_pois(self, symbol: str) -> List[POI]:
        return self._collect_all_pois(symbol)


    def get_poi_state(self, symbol: str, poi_id: str) -> Optional[POIStateRecord]:
        return self._states.get(symbol, {}).get(poi_id)


    def get_poi_settings(self) -> dict:
        return self._settings.to_dict()


    def set_poi_display_enabled(self, poi_type: str, enabled: bool) -> None:
        self._settings_store.set_display_enabled(poi_type, enabled)
        self._settings = self._settings_store.get()
        for symbol in self.symbol_registry.get_active_symbols():
            self._level_workers[symbol].set_display_enabled(poi_type, enabled)
            # The three zone workers have no set_display_enabled() method of
            # their own - each holds an independent display_enabled dict
            # that only ever gets read at scan time, so it must be updated
            # directly here to actually take effect.
            self._fvg_workers[symbol].display_enabled[poi_type] = bool(enabled)
            self._ob_workers[symbol].display_enabled[poi_type] = bool(enabled)
            self._inv_workers[symbol].display_enabled[poi_type] = bool(enabled)
            self._recompute_symbol(symbol)


    def set_poi_strategy_enabled(self, poi_type: str, enabled: bool) -> None:
        self._settings_store.set_strategy_enabled(poi_type, enabled)
        self._settings = self._settings_store.get()
        for symbol in self.symbol_registry.get_active_symbols():
            if poi_type == POIType.FVG: self._fvg_workers[symbol].set_enabled(enabled)
            elif poi_type == POIType.ORDER_BLOCK: self._ob_workers[symbol].set_enabled(enabled)
            elif poi_type == POIType.INVERSE_FVG: self._inv_workers[symbol].set_enabled(enabled)
            else: self._level_workers[symbol].set_type_enabled(poi_type, enabled)
            self._state_workers[symbol].recompute()


    def set_poi_type_enabled(self, poi_type: str, enabled: bool) -> None:
        """Legacy File 03 API. Equivalent to set_poi_strategy_enabled."""
        self.set_poi_strategy_enabled(poi_type, enabled)


    def set_zone_source_tf_enabled(self, timeframe: str, enabled: bool) -> None:
        self._settings_store.set_zone_source_tf_enabled(timeframe, enabled)
        self._settings = self._settings_store.get()
        for symbol in self.symbol_registry.get_active_symbols():
            self._level_workers[symbol].set_source_tf_enabled(timeframe, enabled)
            self._fvg_workers[symbol].set_source_tf_enabled(timeframe, enabled)
            self._ob_workers[symbol].set_source_tf_enabled(timeframe, enabled)
            self._inv_workers[symbol].set_source_tf_enabled(timeframe, enabled)
            self._state_workers[symbol].recompute()


    def set_poi_timezone_mode(self, mode: str) -> None:
        """Only affects POILevelCalculatorWorker (4H/1D/1W/1M line POIs).
        Zone workers (FVG/Order Block/Flip) are unaffected - see
        poi_level_calculator_worker.py's docstring."""
        self._settings_store.set_timezone_mode(mode)
        self._settings = self._settings_store.get()
        for symbol in self.symbol_registry.get_active_symbols():
            self._level_workers[symbol].set_timezone_mode(self._settings.timezone_mode)
            self._state_workers[symbol].recompute()


    def get_health(self, symbol: str) -> str:
        worker = self._level_workers.get(symbol)
        if worker is None: return "DOWN"
        for poi_type, enabled in self._settings.strategy_enabled.items():
            if enabled and not worker.is_type_ready(poi_type) and poi_type in worker.enabled_types:
                if worker.availability.candle_counts: return "DEGRADED"
        return "OK"
