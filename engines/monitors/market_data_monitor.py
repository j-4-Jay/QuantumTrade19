"""Market Data Monitor (Tier 2 Assembly).

PATH: engines/monitors/market_data_monitor.py (REPLACE ENTIRE FILE)

PATCH v5 — local-only Trading Panel reader:
- Adds get_chart_candles(symbol, timeframe, days).
- This chart-specific API reads ONLY CandleBuilderWorker's in-memory series.
- It never calls HistoricalDataLoaderWorker, REST, WebSocket, or CoinDCX.
- The returned series includes the current forming candle exactly once because
  CandleBuilderWorker.get_series() already returns closed candles plus current.
- get_chart_coverage_days() reports actual retained in-memory candle span;
  it does not use the deep-history manifest because that manifest currently
  records coverage metadata, not locally readable candle storage.

The existing get_historical_candles() remains intentionally unchanged for
explicit broker-history operations outside the Trading Panel. The UI chart
must use get_chart_candles(), never get_historical_candles().
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Optional

from engines.workers.market_data.symbol_registry_worker import SymbolRegistryWorker
from engines.workers.market_data.ws_feed_worker import WSFeedWorker, SocketTransport
from engines.workers.market_data.rest_poll_fallback_worker import RestPollFallbackWorker
from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker
from engines.workers.market_data.tick_normalizer_worker import TickNormalizerWorker
from engines.workers.market_data.candle_builder_worker import (
    CandleBuilderWorker,
    Candle,
    TRADING_TFS,
    POI_TFS,
)
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker
from engines.workers.market_data.deep_history_downloader_worker import DeepHistoryDownloaderWorker
from engines.workers.market_data.history_depth_prober_worker import HistoryDepthProberWorker


logger = logging.getLogger("market_data.monitor")


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

        self._subscribed: set[str] = set()
        self._degraded: set[str] = set()
        self._last_health: Dict[str, str] = {}
        logger.info("market_data_monitor_created")

    # ================= public interface =================

    def start(self) -> None:
        active_symbols = self.symbol_registry.get_active_symbols()
        logger.info("market_data_monitor_start active_symbols=%s", active_symbols)
        self.ws_feed.start()
        for symbol in active_symbols:
            self.subscribe(symbol)

    def stop(self) -> None:
        logger.info("market_data_monitor_stop subscribed_count=%d", len(self._subscribed))
        with self._lock:
            symbols = list(self._subscribed)
        for symbol in symbols:
            self.unsubscribe(symbol)
        self.ws_feed.stop()

    def subscribe(self, symbol: str) -> None:
        with self._lock:
            if symbol in self._subscribed:
                logger.debug("market_data_subscribe_ignored_already_subscribed symbol=%s", symbol)
                return
            self._subscribed.add(symbol)
        logger.info("market_data_subscribe_started symbol=%s", symbol)
        try:
            self._seed_baseline_history(symbol)
            self.ws_feed.subscribe(symbol)
            logger.info("market_data_subscribe_complete symbol=%s", symbol)
        except Exception:
            with self._lock:
                self._subscribed.discard(symbol)
            logger.exception("market_data_subscribe_failed symbol=%s", symbol)
            raise

    def unsubscribe(self, symbol: str) -> None:
        with self._lock:
            was_subscribed = symbol in self._subscribed
            self._subscribed.discard(symbol)
            self._degraded.discard(symbol)
            self._last_health.pop(symbol, None)
        self.ws_feed.unsubscribe(symbol)
        self.rest_fallback.disengage(symbol)
        if was_subscribed:
            logger.info("market_data_unsubscribed symbol=%s", symbol)

    def get_live_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        return self.candle_builder.get_live_candle(symbol, timeframe)

    def get_historical_candles(self, symbol: str, timeframe: str, days: int) -> List[Candle]:
        """Explicit broker-history read.

        This method may call CoinDCX through HistoricalDataLoaderWorker.
        It is not permitted for Trading Panel rendering or chart polling.
        Use get_chart_candles() for chart data.
        """
        end_ms = self._now_ms()
        start_ms = end_ms - days * 24 * 60 * 60 * 1000
        candles = self.historical_loader.fetch_range(symbol, timeframe, start_ms, end_ms)
        logger.debug(
            "market_data_historical_fetch symbol=%s timeframe=%s days=%d candles=%d",
            symbol,
            timeframe,
            days,
            len(candles),
        )
        return candles

    def get_chart_candles(self, symbol: str, timeframe: str, days: int) -> List[Candle]:
        """Return local-only chart candles, oldest to newest.

        Reads CandleBuilderWorker's retained RAM series only. It makes no
        network request and never reaches HistoricalDataLoaderWorker. The
        worker's get_series() result already has the current forming candle
        as its final item, so no caller should append get_live_candle().
        """
        if days <= 0:
            return []

        series = self.candle_builder.get_series(symbol, timeframe)
        if not series:
            logger.debug(
                "market_data_chart_local_read symbol=%s timeframe=%s requested_days=%d candles=0",
                symbol,
                timeframe,
                days,
            )
            return []

        cutoff_ms = self._now_ms() - days * 24 * 60 * 60 * 1000
        filtered = [candle for candle in series if candle.open_time >= cutoff_ms]

        # Defensive deduplication: CandleBuilderWorker already guarantees this,
        # but the chart boundary must never emit duplicate timestamps.
        unique: Dict[int, Candle] = {}
        for candle in filtered:
            unique[candle.open_time] = candle
        result = [unique[open_time] for open_time in sorted(unique)]

        logger.debug(
            "market_data_chart_local_read symbol=%s timeframe=%s requested_days=%d candles=%d",
            symbol,
            timeframe,
            days,
            len(result),
        )
        return result

    def get_chart_coverage_days(self, symbol: str, timeframe: str) -> float:
        """Return actual in-memory chart coverage in days.

        This deliberately measures retained CandleBuilderWorker data rather
        than manifest coverage. A manifest can describe broker/download
        coverage even when that candle payload is not locally readable yet.
        """
        series = self.candle_builder.get_series(symbol, timeframe)
        if len(series) < 2:
            return 0.0
        span_ms = max(0, series[-1].open_time - series[0].open_time)
        return round(span_ms / (24 * 60 * 60 * 1000), 1)

    def get_health(self) -> Dict[str, str]:
        report: Dict[str, str] = {}
        with self._lock:
            symbols = list(self._subscribed)
        for symbol in symbols:
            if self.ws_feed.is_healthy(symbol):
                health = "OK"
            elif self.rest_fallback.is_engaged(symbol):
                health = "DEGRADED"
            else:
                health = "DOWN"
            report[symbol] = health
            self._log_health_transition(symbol, health)
        return report

    # ================= deep history / ceiling interface =================

    def start_deep_history(self, symbol: str, timeframe: str, target_days: Optional[int] = None) -> None:
        logger.info("deep_history_started symbol=%s timeframe=%s target_days=%s", symbol, timeframe, target_days)
        self.deep_history_downloader.start_download(symbol, timeframe, target_days)

    def cancel_deep_history(self, symbol: str, timeframe: str) -> None:
        logger.info("deep_history_cancel_requested symbol=%s timeframe=%s", symbol, timeframe)
        self.deep_history_downloader.cancel_download(symbol, timeframe)

    def get_deep_history_progress(self, symbol: str, timeframe: str) -> dict:
        from engines.workers.market_data.deep_history_downloader_worker import (
            covered_days,
            is_fully_downloaded,
        )

        return {
            "covered_days": covered_days(self.history_manifest, symbol, timeframe),
            "is_complete": is_fully_downloaded(self.history_manifest, symbol, timeframe),
        }

    def delete_deep_history(self, symbol: str, timeframe: str) -> None:
        logger.warning("deep_history_delete_requested symbol=%s timeframe=%s", symbol, timeframe)
        self.history_manifest.delete_symbol_manifest(symbol)

    def start_ceiling_probe(self, symbol: str, timeframe: str) -> None:
        logger.info("history_ceiling_probe_started symbol=%s timeframe=%s", symbol, timeframe)
        self.depth_prober.start_probe(symbol, timeframe)

    def get_ceiling_days(self, symbol: str, timeframe: str):
        return self.depth_prober.get_ceiling_days(symbol, timeframe)

    # ================= internal wiring =================

    def _seed_baseline_history(self, symbol: str) -> None:
        started = time.monotonic()
        logger.info("baseline_seed_started symbol=%s timeframes=%s", symbol, TRADING_TFS)
        baseline = self.historical_loader.backfill_baseline(symbol)
        counts: Dict[str, int] = {}
        for timeframe, candles in baseline.items():
            self.candle_builder.seed_historical(symbol, timeframe, candles)
            counts[timeframe] = len(candles)
        logger.info(
            "baseline_seed_complete symbol=%s counts=%s duration_s=%.3f",
            symbol,
            counts,
            time.monotonic() - started,
        )

    def _handle_ws_tick(self, symbol: str, payload: dict) -> None:
        """Handle only price-bearing aggregate deltas from WSFeedWorker."""
        tick = TickNormalizerWorker.from_ws_payload(symbol, payload)
        if TickNormalizerWorker.is_valid(tick):
            self.candle_builder.ingest(tick, timeframes=TRADING_TFS + POI_TFS)
        else:
            logger.warning(
                "ws_price_bearing_delta_rejected_by_normalizer symbol=%s keys=%s",
                symbol,
                sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__,
            )

    def _handle_rest_tick(self, symbol: str, payload: dict) -> None:
        tick = TickNormalizerWorker.from_rest_ticker(symbol, payload)
        if TickNormalizerWorker.is_valid(tick):
            self.candle_builder.ingest(tick, timeframes=TRADING_TFS + POI_TFS)
        else:
            logger.debug("rest_tick_rejected_by_normalizer symbol=%s", symbol)

    def _handle_ws_drop(self, symbol: str) -> None:
        with self._lock:
            already_degraded = symbol in self._degraded
            self._degraded.add(symbol)
        if not already_degraded:
            logger.warning("ws_drop_rest_fallback_engaging symbol=%s", symbol)
        self.rest_fallback.engage(symbol)

    def _handle_ws_restore(self, symbol: str) -> None:
        with self._lock:
            was_degraded = symbol in self._degraded
            self._degraded.discard(symbol)
        self.rest_fallback.disengage(symbol)
        if was_degraded:
            logger.info("ws_restored_rest_fallback_disengaged symbol=%s", symbol)

    def _handle_deep_history_chunk(self, symbol: str, timeframe: str, candles: list) -> None:
        logger.debug(
            "deep_history_chunk_received symbol=%s timeframe=%s candles=%d",
            symbol,
            timeframe,
            len(candles),
        )

    def _publish_candle_closed(self, candle: Candle) -> None:
        logger.debug(
            "candle_closed symbol=%s timeframe=%s open_time=%d close=%s",
            candle.symbol,
            candle.timeframe,
            candle.open_time,
            candle.close,
        )

    def _log_health_transition(self, symbol: str, health: str) -> None:
        with self._lock:
            previous = self._last_health.get(symbol)
            self._last_health[symbol] = health
        if previous != health:
            level = logging.INFO if health == "OK" else logging.WARNING
            logger.log(
                level,
                "market_data_health_transition symbol=%s previous=%s current=%s",
                symbol,
                previous or "UNSET",
                health,
            )

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)
