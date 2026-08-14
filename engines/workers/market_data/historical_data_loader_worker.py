
import time
from typing import Callable, List, Optional
import requests
from engines.workers.market_data.candle_builder_worker import Candle

CANDLES_URL = "https://public.coindcx.com/market_data/candles/"
BASELINE_DAYS = 5
MAX_LIMIT_PER_CALL = 1000
_INTERVAL_MAP = {"1m": "1m", "5m": "5m", "15m": "15m"}

class HistoricalDataLoaderWorker:
    def __init__(self, http_get=None, rate_limit_sleep_s=0.25):
        self._http_get = http_get or requests.get
        self._rate_limit_sleep_s = rate_limit_sleep_s

    def fetch_range(self, pair, timeframe, start_ms, end_ms):
        interval = _INTERVAL_MAP.get(timeframe, timeframe)
        out = []
        cursor_end = end_ms
        while cursor_end > start_ms:
            resp = self._http_get(CANDLES_URL, params={"pair": pair, "interval": interval,
                                                          "startTime": start_ms, "endTime": cursor_end,
                                                          "limit": MAX_LIMIT_PER_CALL}, timeout=10)
            resp.raise_for_status()
            rows = resp.json() or []
            if not rows:
                break
            for row in rows:
                out.append(Candle(symbol=pair, timeframe=timeframe,
                                   open_time=int(row["time"]),
                                   close_time=int(row["time"]) + self._tf_ms(timeframe) - 1,
                                   open=float(row["open"]), high=float(row["high"]),
                                   low=float(row["low"]), close=float(row["close"]),
                                   volume=float(row.get("volume", 0.0) or 0.0), is_closed=True))
            oldest = min(int(row["time"]) for row in rows)
            if oldest >= cursor_end:
                break
            cursor_end = oldest - 1
            time.sleep(self._rate_limit_sleep_s)
        out.sort(key=lambda c: c.open_time)
        deduped, seen = [], set()
        for c in out:
            if c.open_time not in seen:
                seen.add(c.open_time)
                deduped.append(c)
        return deduped

    @staticmethod
    def _tf_ms(tf):
        return {"1m": 60_000, "5m": 300_000, "15m": 900_000}[tf]

    def backfill_baseline(self, pair, days=BASELINE_DAYS):
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - days * 24 * 60 * 60 * 1000
        result = {}
        for tf in ("1m", "5m", "15m"):
            result[tf] = self.fetch_range(pair, tf, start_ms, end_ms)
        return result
