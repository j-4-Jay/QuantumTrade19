"""SQLite-backed candle storage and physical local-coverage truth.

TARGET PATH: D:\QuantumTrade19\engines\workers\market_data\candle_store_worker.py
REPLACE THE ENTIRE FILE.

FIX v0.4.21 - "progress bar is fake" root cause:

The Trading Panel and Deep Historical Data card were showing an animated
but meaningless progress indicator because nothing in the pipeline ever
computed a real percent/ETA against actual SQLite rows. This file adds
get_local_coverage() (physical row-counting against a requested window)
and get_missing_ranges() (exact gap list from real rows) so the
downloader and UI can report truthful, real-time progress instead of a
guess. Supersedes the v0.4.18 performance fix - includes the same
SQL-indexed lookups, plus the missing coverage/gap methods.

v0.4.8 (carried forward): local coverage is always calculated from
physical rows in candles.db. Manifest files remain metadata only and are
never trusted as proof that candles exist locally.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from engines.workers.market_data.candle_builder_worker import Candle

DB_PATH = Path("data") / "historical_candles.db"
TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000}
DAY_MS = 86_400_000


@dataclass(frozen=True)
class LocalCoverage:
    symbol: str
    timeframe: str
    row_count: int
    earliest_open_time: int | None
    latest_open_time: int | None
    contiguous_start_time: int | None
    contiguous_end_time: int | None
    contiguous_days: float
    requested_start_time: int | None = None
    requested_end_time: int | None = None
    requested_candles: int = 0
    present_candles: int = 0
    missing_candles: int = 0
    requested_range_complete: bool = False

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "row_count": self.row_count,
            "earliest_open_time": self.earliest_open_time,
            "latest_open_time": self.latest_open_time,
            "contiguous_start_time": self.contiguous_start_time,
            "contiguous_end_time": self.contiguous_end_time,
            "contiguous_days": self.contiguous_days,
            "requested_start_time": self.requested_start_time,
            "requested_end_time": self.requested_end_time,
            "requested_candles": self.requested_candles,
            "present_candles": self.present_candles,
            "missing_candles": self.missing_candles,
            "requested_range_complete": self.requested_range_complete,
        }


class CandleStoreWorker:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.lock = threading.RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _init_schema(self) -> None:
        with self.lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS candles (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open_time INTEGER NOT NULL,
                    close_time INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    PRIMARY KEY (symbol, timeframe, open_time)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles (symbol, timeframe, open_time)"
            )
            conn.commit()

    def save_candles(self, symbol: str, timeframe: str, candles: Iterable[Candle]) -> int:
        rows = [
            (symbol, timeframe, int(c.open_time), int(c.close_time),
             float(c.open), float(c.high), float(c.low), float(c.close), float(c.volume))
            for c in candles
        ]
        if not rows:
            return 0
        with self.lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO candles (symbol, timeframe, open_time, close_time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, timeframe, open_time) DO UPDATE SET
                    close_time=excluded.close_time,
                    open=excluded.open,
                    high=excluded.high,
                    low=excluded.low,
                    close=excluded.close,
                    volume=excluded.volume
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def get_candles(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> List[Candle]:
        with self.lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT open_time, close_time, open, high, low, close, volume
                FROM candles
                WHERE symbol = ? AND timeframe = ? AND open_time >= ? AND open_time <= ?
                ORDER BY open_time ASC
                """,
                (symbol, timeframe, int(start_ms), int(end_ms)),
            ).fetchall()
        return [
            Candle(
                symbol=symbol, timeframe=timeframe,
                open_time=int(row[0]), close_time=int(row[1]),
                open=float(row[2]), high=float(row[3]), low=float(row[4]),
                close=float(row[5]), volume=float(row[6]), is_closed=True,
            )
            for row in rows
        ]

    def get_all_timestamps(self, symbol: str, timeframe: str) -> list[int]:
        with self.lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT open_time FROM candles WHERE symbol = ? AND timeframe = ? ORDER BY open_time ASC",
                (symbol, timeframe),
            ).fetchall()
        return [int(row[0]) for row in rows]

    def get_local_coverage(
        self, symbol: str, timeframe: str,
        requested_days: int | None = None, end_ms: int | None = None,
    ) -> LocalCoverage:
        step = TF_MS[timeframe]
        end = int(end_ms) if end_ms is not None else int(time.time() * 1000)
        timestamps = self.get_all_timestamps(symbol, timeframe)
        if not timestamps:
            return LocalCoverage(symbol, timeframe, 0, None, None, None, None, 0.0)

        latest = timestamps[-1]
        contiguous_start = latest
        previous = latest
        for current in reversed(timestamps[:-1]):
            if previous - current != step:
                break
            contiguous_start = current
            previous = current
        contiguous_end = latest + step
        contiguous_days = round(max(0, contiguous_end - contiguous_start) / DAY_MS, 3)

        if requested_days is None or requested_days <= 0:
            return LocalCoverage(
                symbol, timeframe, len(timestamps), timestamps[0], latest,
                contiguous_start, contiguous_end, contiguous_days,
            )

        requested_start = end - int(requested_days) * DAY_MS
        aligned_start = (requested_start // step) * step
        aligned_end = (end // step) * step
        required = set(range(aligned_start, aligned_end + 1, step))
        present = sum(1 for stamp in timestamps if aligned_start <= stamp <= aligned_end)
        missing = max(0, len(required) - present)
        complete = missing == 0

        return LocalCoverage(
            symbol, timeframe, len(timestamps), timestamps[0], latest,
            contiguous_start, contiguous_end, contiguous_days,
            aligned_start, aligned_end, len(required), present, missing, complete,
        )

    def get_missing_ranges(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> list[tuple[int, int]]:
        step = TF_MS[timeframe]
        start = (int(start_ms) // step) * step
        end = (int(end_ms) // step) * step
        if end <= start:
            return []
        existing = set(self.get_all_timestamps(symbol, timeframe))
        missing = [stamp for stamp in range(start, end + 1, step) if stamp not in existing]
        if not missing:
            return []
        ranges: list[tuple[int, int]] = []
        range_start = previous = missing[0]
        for stamp in missing[1:]:
            if stamp != previous + step:
                ranges.append((range_start, previous + step))
                range_start = stamp
            previous = stamp
        ranges.append((range_start, previous + step))
        return ranges

    def get_physical_ranges(self, symbol: str, timeframe: str) -> list[tuple[int, int]]:
        step = TF_MS[timeframe]
        timestamps = self.get_all_timestamps(symbol, timeframe)
        if not timestamps:
            return []
        ranges: list[tuple[int, int]] = []
        start = previous = timestamps[0]
        for stamp in timestamps[1:]:
            if stamp != previous + step:
                ranges.append((start, previous + step))
                start = stamp
            previous = stamp
        ranges.append((start, previous + step))
        return ranges

    def get_recent_window(
        self, symbol: str, timeframe: str, end_ms: int,
        visible_days: int = 1, older_buffer_days: int = 2,
    ) -> dict:
        step = TF_MS[timeframe]
        end = int(end_ms)
        visible_days = max(1, int(visible_days))
        older_buffer_days = max(0, int(older_buffer_days))
        visible_start = end - visible_days * DAY_MS
        buffer_start = visible_start - older_buffer_days * DAY_MS
        rows = self.get_candles(symbol, timeframe, buffer_start, end)
        has_older = any(c.open_time < visible_start for c in rows) if rows else False
        return {
            "symbol": symbol, "timeframe": timeframe, "candles": rows,
            "start_ms": visible_start, "end_ms": end,
            "visible_start_ms": visible_start, "visible_end_ms": end,
            "older_start_ms": buffer_start, "has_older": has_older,
        }

    def get_chart_coverage_days(self, symbol: str, timeframe: str) -> float:
        return float(self.get_local_coverage(symbol, timeframe).contiguous_days)

    def delete_symbol_timeframe(self, symbol: str, timeframe: str) -> None:
        with self.lock, self._connect() as conn:
            conn.execute("DELETE FROM candles WHERE symbol = ? AND timeframe = ?", (symbol, timeframe))
            conn.commit()
