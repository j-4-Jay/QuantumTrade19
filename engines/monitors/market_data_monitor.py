"""Market Data Monitor (Tier 2 Assembly).

TARGET PATH: D:\\QuantumTrade19\\engines\\monitors\\market_data_monitor.py
REPLACE THE ENTIRE FILE.

FIX (File 04.1 wiring gap) - added a minimal, additive candle-close
subscriber list: add_candle_close_subscriber(callback) lets OTHER
monitors (specifically SetupDetectionMonitor, File 04) register to be
called with every closed Candle, on every timeframe, the moment it closes
- something nothing in File 02 previously exposed. _publish_candle_closed()
now calls every registered subscriber (wrapped in try/except so a
subscriber's exception can never break candle persistence or the
websocket/tick pipeline itself) IN ADDITION to its original persistence
job, which is completely unchanged. No existing method signature, return
value, or behavior changed - this is purely additive.

Everything else - WS/REST/health-report logic, get_historical_candles(),
chart candle merging, deep history - is UNCHANGED from the previously
locked version.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, List, Optional

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
from engines.workers.market_data.candle_store_worker import CandleStoreWorker

logger = logging.getLogger("market_data.monitor")

DAY_MS = 86_400_000


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
        self.candle_store = CandleStoreWorker()
        self.deep_history_downloader = DeepHistoryDownloaderWorker(
            manifest=self.history_manifest,
            on_chunk=self._handle_deep_history_chunk,
            get_missing_ranges=self.candle_store.get_missing_ranges,
            get_coverage=self.sqlite_coverage_payload,
        )
        self.depth_prober = HistoryDepthProberWorker(manifest=self.history_manifest)
        self._reconcile_worker = None
        self._reconcile_loader = None

        self._subscribed: set[str] = set()
        self._degraded: set[str] = set()
        self._last_health: Dict[str, str] = {}

        # FIX (File 04.1 wiring gap): other monitors (SetupDetectionMonitor)
        # register here to receive every closed Candle on every timeframe.
        # Purely additive - candle persistence below is unchanged either way.
        self._candle_close_subscribers: List[Callable[[Candle], None]] = []

        logger.info("market_data_monitor_created")

    # ================= public interface =================

    def add_candle_close_subscriber(self, callback: Callable[[Candle], None]) -> None:
        """Registers `callback(candle)` to be invoked for every candle this
        monitor closes, on every timeframe (1m/5m/15m/1H/4H/1D/1W/1M).
        Safe to call multiple times; duplicates are not de-duplicated by
        design (callers are expected to register exactly once, same as
        every other lazy-singleton monitor in this engine)."""
        self._candle_close_subscribers.append(callback)

    def start(self) -> None:
        active_symbols = self.symbol_registry.get_active_symbols()
        logger.info("market_data_monitor_start active_symbols=%s", active_symbols)
        self.ws_feed.start()
        for symbol in active_symbols:
            self.subscribe(symbol)
        self._start_reconcile()

    def stop(self) -> None:
        logger.info("market_data_monitor_stop subscribed_count=%d", len(self._subscribed))
        with self._lock:
            symbols = list(self._subscribed)
        for symbol in symbols:
            self.unsubscribe(symbol)
        self._stop_reconcile()
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

    def get_correction_seq(self, symbol: str, timeframe: str) -> int:
        return self.__dict__.get("_correction_seq", {}).get((symbol, timeframe), 0)

    def get_recent_closed(self, symbol: str, timeframe: str, count: int = 30) -> List[Candle]:
        series = self.candle_builder.get_series(symbol, timeframe, limit=count + 1)
        return [c for c in series if c.is_closed][-count:]

    def get_historical_candles(self, symbol: str, timeframe: str, days: int) -> List[Candle]:
        """Explicit broker-history read. Not permitted for Trading Panel
        rendering or chart polling. Use get_chart_candles() for chart data."""
        end_ms = self._now_ms()
        start_ms = end_ms - days * 24 * 60 * 60 * 1000
        candles = self.historical_loader.fetch_range(symbol, timeframe, start_ms, end_ms)
        logger.debug(
            "market_data_historical_fetch symbol=%s timeframe=%s days=%d candles=%d",
            symbol, timeframe, days, len(candles),
        )
        return candles

    def get_chart_candles(self, symbol: str, timeframe: str, days: int) -> List[Candle]:
        """Return local-only chart candles, oldest to newest. Merges
        CandleStoreWorker (persistent SQLite) with CandleBuilderWorker's
        in-memory RAM series - RAM wins on any timestamp collision (it
        always has the current forming candle). Deliberately continues to
        include the RAM baseline window even after a deep-history Delete -
        see module docstring."""
        if days <= 0:
            return []

        cutoff_ms = self._now_ms() - days * 24 * 60 * 60 * 1000
        now_ms = self._now_ms()

        merged: Dict[int, Candle] = {}

        persisted = self.candle_store.get_candles(symbol, timeframe, cutoff_ms, now_ms)
        for candle in persisted:
            merged[candle.open_time] = candle

        series = self.candle_builder.get_series(symbol, timeframe)
        for candle in series:
            if candle.open_time >= cutoff_ms:
                merged[candle.open_time] = candle

        result = [merged[open_time] for open_time in sorted(merged)]

        logger.debug(
            "market_data_chart_local_read symbol=%s timeframe=%s requested_days=%d persisted=%d ram=%d merged=%d",
            symbol, timeframe, days, len(persisted), len(series), len(result),
        )
        return result

    def get_recent_window(
        self, symbol: str, timeframe: str, end_ms: Optional[int] = None,
        visible_days: int = 1, older_buffer_days: int = 2,
    ) -> dict:
        if end_ms is None:
            end_ms = self._now_ms()
        return self.candle_store.get_recent_window(
            symbol, timeframe, int(end_ms), visible_days=visible_days, older_buffer_days=older_buffer_days,
        )

    def get_local_coverage(self, symbol: str, timeframe: str, requested_days: Optional[int] = None) -> dict:
        coverage = self.candle_store.get_local_coverage(symbol, timeframe, requested_days, self._now_ms())
        return coverage.to_dict()

    def sqlite_coverage_payload(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> dict:
        """Real-time coverage callback wired into DeepHistoryDownloaderWorker."""
        requested_days = max(1, int((end_ms - start_ms) / DAY_MS))
        return self.candle_store.get_local_coverage(symbol, timeframe, requested_days, end_ms).to_dict()

    def get_chart_coverage_days(self, symbol: str, timeframe: str) -> float:
        return self.candle_store.get_chart_coverage_days(symbol, timeframe)

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
        status = self.deep_history_downloader.get_status(symbol, timeframe)
        coverage = self.candle_store.get_local_coverage(symbol, timeframe)
        return {
            "state": status["state"],
            "error": status["error"],
            "percent": status["percent"],
            "present_candles": status["present_candles"],
            "required_candles": status["required_candles"],
            "missing_candles": status["missing_candles"],
            "eta_seconds": status["eta_seconds"],
            "broker_ceiling_reached": status["broker_ceiling_reached"],
            "covered_days": coverage.contiguous_days,
            "is_complete": status["state"] == "complete",
        }

    def delete_deep_history(self, symbol: str, timeframe: str) -> None:
        logger.warning("deep_history_delete_requested symbol=%s timeframe=%s", symbol, timeframe)
        self.history_manifest.delete_symbol_manifest(symbol)
        self.candle_store.delete_symbol_timeframe(symbol, timeframe)
        self.deep_history_downloader.reset_status(symbol, timeframe)

    def start_ceiling_probe(self, symbol: str, timeframe: str) -> None:
        logger.info("history_ceiling_probe_started symbol=%s timeframe=%s", symbol, timeframe)
        self.depth_prober.start_probe(symbol, timeframe)

    def get_ceiling_days(self, symbol: str, timeframe: str):
        return self.depth_prober.get_ceiling_days(symbol, timeframe)

    # ================= internal wiring =================

    # ================= candle truth (thread 007) =================

    def _start_reconcile(self) -> None:
        import os
        if os.environ.get("QT19_DISABLE_RECONCILE") or os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("candle_reconcile_skipped_by_environment")
            return
        if self._reconcile_worker is not None:
            return
        try:
            import requests
            from engines.workers.market_data.candle_reconcile_worker import CandleReconcileWorker

            def short_get(url, **kwargs):
                kwargs["timeout"] = 6
                return requests.get(url, **kwargs)

            self._reconcile_loader = HistoricalDataLoaderWorker(http_get=short_get, rate_limit_sleep_s=0.1)
            self._reconcile_worker = CandleReconcileWorker(
                fetch_range=self._reconcile_loader.fetch_range,
                apply=self._apply_exchange_candles,
                get_symbols=self._reconcile_symbols,
            )
            self._reconcile_worker.start()
        except Exception:
            self._reconcile_worker = None
            logger.exception("candle_reconcile_start_failed")

    def _stop_reconcile(self) -> None:
        worker = self._reconcile_worker
        self._reconcile_worker = None
        if worker is not None:
            try:
                worker.stop()
            except Exception:
                logger.exception("candle_reconcile_stop_failed")

    def _reconcile_symbols(self) -> List[str]:
        with self._lock:
            return list(self._subscribed)

    def _apply_exchange_candles(self, symbol: str, timeframe: str, candles: list, now_ms: int) -> list:
        corrected = self.candle_builder.apply_exchange_candles(symbol, timeframe, candles, now_ms)
        if corrected:
            seqs = self.__dict__.setdefault("_correction_seq", {})
            seqs[(symbol, timeframe)] = seqs.get((symbol, timeframe), 0) + 1
        step = {"1m": 60_000, "5m": 300_000, "15m": 900_000}.get(timeframe, 60_000)
        to_save = {c.open_time: c for c in candles if c.open_time + step <= now_ms}
        for c in corrected:
            to_save[c.open_time] = c
        if to_save:
            try:
                self.candle_store.save_candles(symbol, timeframe, [to_save[k] for k in sorted(to_save)])
            except Exception:
                logger.exception("candle_reconcile_persist_failed symbol=%s timeframe=%s", symbol, timeframe)
        return corrected

    def _seed_baseline_history(self, symbol: str) -> None:
        started = time.monotonic()
        logger.info("baseline_seed_started symbol=%s timeframes=%s", symbol, TRADING_TFS)
        baseline = self.historical_loader.backfill_baseline(symbol)
        counts: Dict[str, int] = {}
        from engines.workers.market_data.baseline_persistence_worker import persist_missing_baseline

        saved = persist_missing_baseline(self.candle_store, symbol, baseline, self._now_ms())
        logger.info("baseline_missing_rows_saved symbol=%s counts=%s backup=%s", symbol, saved,
                    getattr(self.candle_store, "_baseline_backup_path", "not needed"))
        for timeframe, candles in baseline.items():
            self.candle_builder.seed_historical(symbol, timeframe, candles)
            counts[timeframe] = len(candles)
        logger.info(
            "baseline_seed_complete symbol=%s counts=%s duration_s=%.3f",
            symbol, counts, time.monotonic() - started,
        )

    def _handle_ws_tick(self, symbol: str, payload: dict) -> None:
        tick = TickNormalizerWorker.from_ws_payload(symbol, payload)
        if TickNormalizerWorker.is_valid(tick):
            self.candle_builder.ingest(tick, timeframes=TRADING_TFS + POI_TFS)
        else:
            logger.warning(
                "ws_price_bearing_delta_rejected_by_normalizer symbol=%s keys=%s",
                symbol, sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__,
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
        saved = self.candle_store.save_candles(symbol, timeframe, candles)
        logger.debug(
            "deep_history_chunk_persisted symbol=%s timeframe=%s rows=%d",
            symbol, timeframe, saved,
        )

    def _publish_candle_closed(self, candle: Candle) -> None:
        try:
            self.candle_store.save_candles(candle.symbol, candle.timeframe, [candle])
        except Exception:
            logger.exception(
                "candle_close_persist_failed symbol=%s timeframe=%s open_time=%d",
                candle.symbol, candle.timeframe, candle.open_time,
            )
        logger.debug(
            "candle_closed symbol=%s timeframe=%s open_time=%d close=%s",
            candle.symbol, candle.timeframe, candle.open_time, candle.close,
        )
        # FIX (File 04.1 wiring gap): fan the same closed candle out to any
        # registered subscriber (e.g. SetupDetectionMonitor.on_candle_closed).
        # Wrapped so a subscriber's own bug can NEVER break candle
        # persistence or the tick pipeline above.
        if not self._defer_close_notification(candle):
            self._notify_close_subscribers(candle)

    def _notify_close_subscribers(self, candle: Candle) -> None:
        for callback in self._candle_close_subscribers:
            try:
                callback(candle)
            except Exception:
                logger.exception(
                    "candle_close_subscriber_failed symbol=%s timeframe=%s open_time=%d callback=%r",
                    candle.symbol, candle.timeframe, candle.open_time, callback,
                )

    def _defer_close_notification(self, candle: Candle) -> bool:
        """FT-H.33: hold a closed 1m/5m/15m candle about 9 s so the exchange corrections
        arrive before the setup monitor sees it. Other timeframes and a stopped reconcile
        worker are notified at once."""
        import os
        from engines.workers.market_data.delayed_dispatch_worker import (
            DelayedDispatchWorker, SETTLE_TIMEFRAMES, SETUP_SETTLE_DELAY_S,
        )
        if candle.timeframe not in SETTLE_TIMEFRAMES:
            return False
        if self._reconcile_worker is None or os.environ.get("QT19_DISABLE_RECONCILE"):
            return False
        with self._lock:
            dispatcher = self.__dict__.get("_close_dispatcher")
            if dispatcher is None:
                dispatcher = DelayedDispatchWorker(self._notify_close_subscribers)
                self._close_dispatcher = dispatcher
                dispatcher.start()
        dispatcher.submit(candle, SETUP_SETTLE_DELAY_S)
        return True

    def _log_health_transition(self, symbol: str, health: str) -> None:
        with self._lock:
            previous = self._last_health.get(symbol)
            self._last_health[symbol] = health
        if previous != health:
            level = logging.INFO if health == "OK" else logging.WARNING
            logger.log(
                level, "market_data_health_transition symbol=%s previous=%s current=%s",
                symbol, previous or "UNSET", health,
            )

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)
