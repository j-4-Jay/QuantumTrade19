"""Data_Integrity_Worker: periodic scan for candle gaps and corruption across both the 5-day baseline and
the deep-history archive. Read-only -- reports findings, never mutates data itself.
"""
from __future__ import annotations
import asyncio
from typing import Iterable
from engines.event_bus.bus import event_bus
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker

SCAN_INTERVAL_SECONDS = 6 * 3600
TIMEFRAMES = ("1m", "5m", "15m")


class DataIntegrityWorker:
    def __init__(self, manifest: HistoryManifestWorker, candle_store) -> None:
        self._manifest = manifest
        self._store = candle_store
        self._running = False

    async def start(self, symbols: Iterable[str]) -> None:
        self._running = True
        while self._running:
            await self.scan_once(symbols)
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False

    async def scan_once(self, symbols: Iterable[str]) -> None:
        findings = []
        for symbol in symbols:
            for timeframe in TIMEFRAMES:
                for start_ms, end_ms in self._manifest.get_covered_ranges(symbol, timeframe):
                    expected = self._expected_candle_count(timeframe, start_ms, end_ms)
                    actual_candles = self._store.get_historical_candles(symbol, timeframe, days=36500)
                    actual = len([c for c in actual_candles if start_ms <= c["bucket_start_ms"] < end_ms])
                    if actual < expected:
                        findings.append({
                            "symbol": symbol, "timeframe": timeframe, "start_ms": start_ms, "end_ms": end_ms,
                            "expected": expected, "actual": actual, "missing": expected - actual,
                        })
        event_bus.publish("market_data.integrity.report", {"findings": findings})

    @staticmethod
    def _expected_candle_count(timeframe: str, start_ms: int, end_ms: int) -> int:
        span_seconds = {"1m": 60, "5m": 300, "15m": 900}[timeframe]
        return max(0, (end_ms - start_ms) // (span_seconds * 1000))
