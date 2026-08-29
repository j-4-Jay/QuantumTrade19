"""Candle_Store_Worker: persistent SQLite storage for deep-downloaded historical candles.

PATH: engines/workers/market_data/candle_store_worker.py  (NEW FILE)

This is the missing piece that makes Deep Historical Data actually usable.
Previously, DeepHistoryDownloaderWorker's on_chunk callback only logged
downloaded candles and threw them away - MarketDataMonitor.get_chart_candles()
only ever read CandleBuilderWorker's in-memory RAM series (baseline 5-day
window + live ticks since app start), so downloaded deep-history data could
never reach the Trading Panel chart no matter how long a download ran.

This worker gives deep-downloaded candles a real, durable home
(data/historical/candles.db) that get_chart_candles() can merge with the
live in-memory series.
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List

from engines.workers.market_data.candle_builder_worker import Candle

_DB_PATH = Path("data") / "historical" / "candles.db"


class CandleStoreWorker:
    def __init__(self, db_path: Path = _DB_PATH) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), timeout=30)

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
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

    def save_candles(self, symbol: str, timeframe: str, candles: List[Candle]) -> None:
        if not candles:
            return
        rows = [
            (symbol, timeframe, c.open_time, c.close_time, c.open, c.high, c.low, c.close, c.volume)
            for c in candles
        ]
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO candles (symbol, timeframe, open_time, close_time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol, timeframe, open_time) DO UPDATE SET
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

    def get_candles(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> List[Candle]:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT open_time, close_time, open, high, low, close, volume
                FROM candles
                WHERE symbol = ? AND timeframe = ? AND open_time >= ? AND open_time <= ?
                ORDER BY open_time ASC
                """,
                (symbol, timeframe, start_ms, end_ms),
            )
            rows = cursor.fetchall()
        return [
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                open_time=row[0],
                close_time=row[1],
                open=row[2],
                high=row[3],
                low=row[4],
                close=row[5],
                volume=row[6],
                is_closed=True,
            )
            for row in rows
        ]

    def delete_symbol_timeframe(self, symbol: str, timeframe: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "DELETE FROM candles WHERE symbol = ? AND timeframe = ?",
                (symbol, timeframe),
            )
            conn.commit()
