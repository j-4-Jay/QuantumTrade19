"""Live_Data_Archiver_Worker: every 3 days, rolls the live-trading hot table's older rows into the historical
archive and trims the hot table -- nothing lost, live queries stay fast.
"""
from __future__ import annotations
import asyncio
import time
from pathlib import Path
from engines.event_bus.bus import event_bus

ARCHIVE_DIR = Path("data") / "historical" / "archive"
ROLL_INTERVAL_SECONDS = 3 * 86_400
HOT_TABLE_RETENTION_SECONDS = 3 * 86_400


class LiveDataArchiverWorker:
    def __init__(self, hot_store, archive_store=None) -> None:
        self._hot_store = hot_store
        self._archive_store = archive_store
        self._running = False
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        self._running = True
        while self._running:
            await self._roll_once()
            await asyncio.sleep(ROLL_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False

    async def _roll_once(self) -> None:
        cutoff_ms = int((time.time() - HOT_TABLE_RETENTION_SECONDS) * 1000)
        rows = await self._hot_store.read_older_than(cutoff_ms)
        if not rows:
            event_bus.publish("market_data.archive.rolled", {"rows_moved": 0, "cutoff_ms": cutoff_ms})
            return
        await self._archive_store.append(rows)
        await self._hot_store.delete_older_than(cutoff_ms)
        event_bus.publish("market_data.archive.rolled", {"rows_moved": len(rows), "cutoff_ms": cutoff_ms})
