"""
FULL PATH: engines/monitors/market_data_monitor.py
File 02 — Market Data Monitor (Tier 2 Assembly)

Wires the 6 Tier-1 Workers behind ONE clean interface. Zero business logic lives
here — only sequencing and per-symbol WS<->REST failover routing. Never imported
directly by anything except a Master Engine (per the 3-tier hierarchy rule).
Verified via tests/test_market_data_monitor.py (5/5 passing, mocked data).
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from engines.workers.market_data.symbol_registry_worker import SymbolRegistryWorker
from engines.workers.market_data.ws_feed_worker import WSFeedWorker, SocketTransport
from engines.workers.market_data.rest_poll_fallback_worker import RestPollFallbackWorker
from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker
from engines.workers.market_data.tick_normalizer_worker import TickNormalizerWorker
from engines.workers.market_data.candle_builder_worker import (
    CandleBuilderWorker, Candle, TRADING_TFS, POI_TFS,
)


class MarketDataMonitor:
    def __init__(self, transport: SocketTransport) -> None:
        self._lock = threading.RLock()

        self.symbol_registry = SymbolRegistryWorker()
        self.candle_builder = CandleBuilderWorker(on_candle_closed=self._publish_candle_closed)
        self.historical_loader = HistoricalDataLoaderWorker()
        self.rest_fallback = RestPollFallbackWorker(on_tick=self._handle_rest_tick)
        self.ws_feed = WSFeedWorker(
            transport=transport,
            on_tick=self._handle_ws_tick,
            on_drop=self._handle_ws_drop,
            on_restore=self._handle_ws_restore,
        )

        self._subscribed: set = set()
        self._degraded: set = set()  # symbols currently on REST fallback

    # ================= public interface (the ONLY surface Masters may call) =================

    def start(self) -> None:
        self.ws_feed.start()
        for symbol in self.symbol_registry.get_active_symbols():
            self.subscribe(symbol)

    def subscribe(self, symbol: str) -> None:
        with self._lock:
            if symbol in self._subscribed:
                return
            self._subscribed.add(symbol)
        self._seed_baseline_history(symbol)
        self.ws_feed.subscribe(symbol)

    def unsubscribe(self, symbol: str) -> None:
        with self._lock:
            self._subscribed.discard(symbol)
            self._degraded.discard(symbol)
        self.ws_feed.unsubscribe(symbol)
        self.rest_fallback.disengage(symbol)

    def get_live_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        return self.candle_builder.get_live_candle(symbol, timeframe)

    def get_historical_candles(self, symbol: str, timeframe: str, days: int) -> List[Candle]:
        end_ms = self._now_ms()
        start_ms = end_ms - days * 24 * 60 * 60 * 1000
        return self.historical_loader.fetch_range(symbol, timeframe, start_ms, end_ms)

    def get_health(self) -> Dict[str, str]:
        """Returns OK / DEGRADED / DOWN per subscribed symbol based on WS vs fallback state."""
        report: Dict[str, str] = {}
        with self._lock:
            symbols = list(self._subscribed)
        for symbol in symbols:
            if self.ws_feed.is_healthy(symbol):
                report[symbol] = "OK"
            elif self.rest_fallback.is_engaged(symbol):
                report[symbol] = "DEGRADED"
            else:
                report[symbol] = "DOWN"
        return report

    # ================= internal wiring (never called from outside the Monitor) =================

    def _seed_baseline_history(self, symbol: str) -> None:
        baseline = self.historical_loader.backfill_baseline(symbol)
        for tf, candles in baseline.items():
            self.candle_builder.seed_historical(symbol, tf, candles)

    def _handle_ws_tick(self, symbol: str, payload: dict) -> None:
        tick = TickNormalizerWorker.from_ws_payload(symbol, payload)
        if TickNormalizerWorker.is_valid(tick):
            self.candle_builder.ingest(tick, timeframes=TRADING_TFS + POI_TFS)

    def _handle_rest_tick(self, symbol: str, payload: dict) -> None:
        tick = TickNormalizerWorker.from_rest_ticker(symbol, payload)
        if TickNormalizerWorker.is_valid(tick):
            self.candle_builder.ingest(tick, timeframes=TRADING_TFS + POI_TFS)

    def _handle_ws_drop(self, symbol: str) -> None:
        with self._lock:
            self._degraded.add(symbol)
        self.rest_fallback.engage(symbol)

    def _handle_ws_restore(self, symbol: str) -> None:
        with self._lock:
            self._degraded.discard(symbol)
        self.rest_fallback.disengage(symbol)

    def _publish_candle_closed(self, candle: Candle) -> None:
        # Placeholder hook: once event_bus/ is wired in, publish "candle.closed" here
        # for POI Monitor (file 03) to subscribe to. Left as a no-op stub intentionally
        # so file 02 has zero forward dependency on an unbuilt module.
        pass

    @staticmethod
    def _now_ms() -> int:
        import time
        return int(time.time() * 1000)
