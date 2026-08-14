"""Deep_History_Downloader_Worker: slow, chunked, opt-in backfill of full historical depth per symbol/timeframe.
Drives the Deep Historical Data Settings card (locked 11th mockup). Never competes with live trading for priority.
"""
from __future__ import annotations
import asyncio
import time
from engines.event_bus.bus import event_bus
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker
from engines.workers.market_data.rate_limit_gate import rate_limit_gate

CHUNK_SPAN_MS = 7 * 86_400_000
EARLIEST_POSSIBLE_MS = 0
TIMEFRAMES = ("1m", "5m", "15m")


class DeepHistoryDownloaderWorker:
    def __init__(self, manifest: HistoryManifestWorker, http_client=None) -> None:
        self._manifest = manifest
        self._http = http_client
        self._active_tasks: dict[str, asyncio.Task] = {}

    def start_symbol(self, symbol: str) -> None:
        if symbol in self._active_tasks:
            return
        self._active_tasks[symbol] = asyncio.create_task(self._backfill_symbol(symbol))
        event_bus.publish("market_data.deep_history.started", {"symbol": symbol})

    def stop_symbol(self, symbol: str) -> None:
        task = self._active_tasks.pop(symbol, None)
        if task:
            task.cancel()
        event_bus.publish("market_data.deep_history.stopped", {"symbol": symbol})

    def delete_symbol_data(self, symbol: str) -> None:
        self.stop_symbol(symbol)
        self._manifest.delete_symbol_manifest(symbol)
        event_bus.publish("market_data.deep_history.deleted", {"symbol": symbol})

    async def _backfill_symbol(self, symbol: str) -> None:
        try:
            for timeframe in TIMEFRAMES:
                await self._backfill_timeframe(symbol, timeframe)
            event_bus.publish("market_data.deep_history.symbol_complete", {"symbol": symbol})
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            event_bus.publish("market_data.deep_history.error", {"symbol": symbol, "error": str(exc)})

    async def _backfill_timeframe(self, symbol: str, timeframe: str) -> None:
        cursor_end = int(time.time() * 1000)
        while cursor_end > EARLIEST_POSSIBLE_MS:
            cursor_start = max(EARLIEST_POSSIBLE_MS, cursor_end - CHUNK_SPAN_MS)
            gaps = self._manifest.find_gaps(symbol, timeframe, cursor_start, cursor_end)
            if not gaps:
                cursor_end = cursor_start
                continue
            for gap_start, gap_end in gaps:
                await rate_limit_gate.acquire("deep_history")
                candles = await self._fetch_chunk(symbol, timeframe, gap_start, gap_end)
                if not candles:
                    self._manifest.mark_covered(symbol, timeframe, EARLIEST_POSSIBLE_MS, gap_end)
                    return
                for candle in candles:
                    event_bus.publish("market_data.deep_history.candle_loaded", {
                        "symbol": symbol, "timeframe": timeframe, **candle,
                    })
                self._manifest.mark_covered(symbol, timeframe, gap_start, gap_end)
                event_bus.publish("market_data.deep_history.progress", {
                    "symbol": symbol, "timeframe": timeframe,
                    "coverage_percent": self._manifest.coverage_percent(
                        symbol, timeframe, EARLIEST_POSSIBLE_MS, int(time.time() * 1000)),
                })
            cursor_end = cursor_start

    async def _fetch_chunk(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> list[dict]:
        if self._http is None:
            raise RuntimeError("no HTTP client injected")
        from engines.workers.market_data.historical_data_loader_worker import REST_CANDLES_URL
        return await self._http.get_json(
            REST_CANDLES_URL, params={"symbol": symbol, "interval": timeframe, "startTime": start_ms, "endTime": end_ms}
        )
