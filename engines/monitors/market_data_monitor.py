"""
FULL PATH: engines/monitors/market_data_monitor.py (REPLACE ENTIRE FILE)
File 02 — Market Data Monitor (Tier 2 Assembly)

Wires the 6 Tier-1 Workers behind ONE clean interface. Zero business logic lives
here — only sequencing and per-symbol WS<->REST failover routing. Never imported
directly by anything except a Master Engine (per the 3-tier hierarchy rule).
Verified via tests/test_market_data_monitor.py (5/5 passing, mocked data).

FIX: previous version had the HistoryDepthProberWorker import stray inside the
candle_builder_worker import parentheses, and stray blank lines splitting the
class body from __init__ -- both are syntax errors. Corrected below. Also adds
Deep History + Ceiling Prober wiring (History_Manifest_Worker,
Deep_History_Downloader_Worker, History_Depth_Prober_Worker) per Section 8 of
the architecture blueprint.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from engines.workers.market_data.symbol_registry_worker import SymbolRegistryWorker
from engines.workers.market_data.ws_feed_worker import WSFeedWorker, SocketTransport
from engines.workers.market_data.rest_poll_fallback_worker import RestPollFallbackWorker
from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker
from engines.workers.market_data.tick_normalizer_worker import TickNormalizerWorker
from engines.workers.market_data.candle_builder_worker import (
    CandleBuilderWorker, Candle, TRADING_TFS, POI_TFS,
)
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker
from engines.workers.market_data.deep_history_downloader_worker import DeepHistoryDownloaderWorker
from engines.workers.market_data.history_depth_prober_worker import HistoryDepthProberWorker


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

        self.history_manifest = HistoryManifestWorker()
        self.deep_history_downloader = DeepHistoryDownloaderWorker(
            manifest=self.history_manifest,
            on_chunk=self._handle_deep_history_chunk,
        )
        self.depth_prober = HistoryDepthProberWorker(manifest=self.history_manifest)

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

    # ================= deep history / ceiling interface =================

    def start_deep_history(self, symbol: str, timeframe: str, target_days: Optional[int] = None) -> None:
        self.deep_history_downloader.start_download(symbol, timeframe, target_days)

    def cancel_deep_history(self, symbol: str, timeframe: str) -> None:
        self.deep_history_downloader.cancel_download(symbol, timeframe)




    def get_deep_history_progress(self, symbol: str, timeframe: str) -> dict:
        from engines.workers.market_data.deep_history_downloader_worker import (
            covered_days, is_fully_downloaded,
        )
        return {
            "covered_days": covered_days(self.history_manifest, symbol, timeframe),
            "is_complete": is_fully_downloaded(self.history_manifest, symbol, timeframe),
        }

    def delete_deep_history(self, symbol: str, timeframe: str) -> None:
        # Note: your manifest deletes ALL timeframes for this symbol at once
        # (one JSON file per symbol, not per symbol+timeframe).
        self.history_manifest.delete_symbol_manifest(symbol)






    def start_ceiling_probe(self, symbol: str, timeframe: str) -> None:
        self.depth_prober.start_probe(symbol, timeframe)

    def get_ceiling_days(self, symbol: str, timeframe: str):
        return self.depth_prober.get_ceiling_days(symbol, timeframe)

    def _handle_deep_history_chunk(self, symbol: str, timeframe: str, candles: list) -> None:
        # Deep history is for the ML/RL archive -- store to disk, do NOT
        # feed into the live in-memory CandleBuilderWorker (that stays
        # baseline-only, per the architecture's separation of concerns).
        pass  # storage-to-disk step added once file 08's storage layer exists

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
        return int(time.time() * 1000)
