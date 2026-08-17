"""
FULL PATH: engines/workers/market_data/historical_data_loader_worker.py (REPLACE ENTIRE FILE)

FIX (reverts the NY-session-boundary experiment): confirmed with real data
via debug_temp/compare_utc_vs_ny_boundary.py that CoinDCX's futures
terminal uses plain UTC daily boundaries, NOT NY/EDT session boundaries --
the UTC-day bucket for Aug 14 (High=63595.1, Low=62484.2) matched the
terminal's own PDH/PDL line exactly; the NY-day bucket did not (High was
short by ~145, because it excluded 4 real UTC hours that belong to the
true UTC calendar day). The earlier NY-session version happened to also
match on 4H purely because NY is currently on EDT (UTC-4), and 4 is a
multiple of the 4H block size -- that would have silently broken again
every winter once NY switches to EST (UTC-5). Back to UTC, permanently,
with no DST-dependent landmine.

NO SPOT DATA, EVER. Every fetch goes through CoinDCX's real FUTURES
candlesticks endpoint (pcode=f) -- confirmed live:
    GET https://public.coindcx.com/market_data/candlesticks
        ?pair=B-BTC_USDT&from=<epoch SECONDS>&to=<epoch SECONDS>
        &resolution=<1|5|60|1D>&pcode=f
Response: {"s": ..., "data": [{open,high,low,close,volume,time(ms)}]}.
`from`/`to` MUST be seconds -- ms silently returns an empty data list.

Timeframe -> fetch strategy (all UTC-aligned):
    1m, 5m, 1H, 1D  -> native (CoinDCX futures supports these 4 resolutions
                       directly: "1", "5", "60", "1D")
    15m             -> derived, fixed UTC-epoch-aligned bucketing of 5m
                       (group_size=3)
    4H              -> derived, fixed UTC-epoch-aligned bucketing of 1H
                       (group_size=4)
    1W              -> derived, UTC calendar-week bucketing of 1D
                       (Monday 00:00 UTC start)
    1M              -> derived, UTC calendar-month bucketing of 1D
"""
from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import requests

from engines.workers.market_data.candle_builder_worker import Candle

FUTURES_CANDLESTICKS_URL = "https://public.coindcx.com/market_data/candlesticks"
BASELINE_DAYS = 5
PCODE_FUTURES = "f"

# Timeframes CoinDCX's futures endpoint can serve directly.
_NATIVE_RESOLUTION: Dict[str, str] = {
    "1m": "1",
    "5m": "5",
    "1H": "60",
    "1D": "1D",
}

# Timeframes built locally, all UTC-epoch-aligned -- no timezone concept,
# no DST-dependent behavior, correct year-round.
# ("fixed", base_tf, group_size) -> fixed-size epoch-aligned bucketing.
# ("calendar_week"/"calendar_month", base_tf, None) -> UTC calendar bucketing.
_DERIVED: Dict[str, tuple] = {
    "15m": ("fixed", "5m", 3),
    "4H": ("fixed", "1H", 4),
    "1W": ("calendar_week", "1D", None),
    "1M": ("calendar_month", "1D", None),
}

_BASE_MS: Dict[str, int] = {"1m": 60_000, "5m": 300_000, "1H": 3_600_000, "1D": 86_400_000}

# Max span per single HTTP call, keyed by CoinDCX resolution string.
_MAX_SPAN_MS: Dict[str, int] = {
    "1": 1 * 86_400_000,
    "5": 5 * 86_400_000,
    "60": 20 * 86_400_000,
    "1D": 300 * 86_400_000,
}


class HistoricalDataLoaderWorker:
    def __init__(self, http_get=None, rate_limit_sleep_s: float = 0.25) -> None:
        self._http_get = http_get or requests.get
        self._rate_limit_sleep_s = rate_limit_sleep_s

    # ------------------------------------------------------------------ public
    def fetch_range(self, pair: str, timeframe: str, start_ms: int, end_ms: int) -> List[Candle]:
        if timeframe in _NATIVE_RESOLUTION:
            return self._fetch_native(pair, timeframe, start_ms, end_ms)
        if timeframe in _DERIVED:
            return self._fetch_derived(pair, timeframe, start_ms, end_ms)
        raise ValueError(
            f"Unknown timeframe '{timeframe}' -- add it to _NATIVE_RESOLUTION or "
            f"_DERIVED in historical_data_loader_worker.py before requesting it."
        )

    def backfill_baseline(self, pair: str, days: int = BASELINE_DAYS) -> Dict[str, List[Candle]]:
        """Baseline stays 1m/5m/15m, per the architecture's 'always-on
        minimum' rule. 15m is transparently derived from 5m underneath."""
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - days * 24 * 60 * 60 * 1000
        result: Dict[str, List[Candle]] = {}
        for tf in ("1m", "5m", "15m"):
            result[tf] = self.fetch_range(pair, tf, start_ms, end_ms)
        return result

    # ------------------------------------------------------------------ native fetch (futures only)
    def _fetch_native(self, pair: str, timeframe: str, start_ms: int, end_ms: int) -> List[Candle]:
        resolution = _NATIVE_RESOLUTION[timeframe]
        max_span_ms = _MAX_SPAN_MS.get(resolution, 90 * 86_400_000)

        rows: List[dict] = []
        cursor_start = start_ms
        while cursor_start < end_ms:
            cursor_end = min(cursor_start + max_span_ms, end_ms)
            resp = self._http_get(
                FUTURES_CANDLESTICKS_URL,
                params={
                    "pair": pair,
                    "from": cursor_start // 1000,   # SECONDS -- ms silently returns empty data
                    "to": cursor_end // 1000,
                    "resolution": resolution,
                    "pcode": PCODE_FUTURES,
                },
                timeout=10,
            )
            resp.raise_for_status()
            body = resp.json() or {}
            batch = body.get("data") or []
            rows.extend(batch)
            cursor_start = cursor_end
            if cursor_start < end_ms:
                time.sleep(self._rate_limit_sleep_s)

        rows.sort(key=lambda r: int(r["time"]))
        deduped, seen = [], set()
        for row in rows:
            t = int(row["time"])
            if t not in seen:
                seen.add(t)
                deduped.append(row)

        return self._rows_to_candles(pair, timeframe, deduped)

    def _rows_to_candles(self, pair: str, timeframe: str, rows: List[dict]) -> List[Candle]:
        """close_time derived from the ACTUAL next row's open_time where
        possible; only the very last row falls back to a static estimate."""
        candles: List[Candle] = []
        base_ms = _BASE_MS.get(timeframe, 86_400_000)
        for i, row in enumerate(rows):
            open_time = int(row["time"])
            close_time = int(rows[i + 1]["time"]) - 1 if i + 1 < len(rows) else open_time + base_ms - 1
            candles.append(Candle(
                symbol=pair, timeframe=timeframe,
                open_time=open_time, close_time=close_time,
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]),
                volume=float(row.get("volume", 0.0) or 0.0),
                is_closed=True,
            ))
        return candles

    # ------------------------------------------------------------------ derived (UTC-aligned) fetch
    def _fetch_derived(self, pair: str, timeframe: str, start_ms: int, end_ms: int) -> List[Candle]:
        mode, base_tf, group_size = _DERIVED[timeframe]
        base_candles = self.fetch_range(pair, base_tf, start_ms, end_ms)
        if not base_candles:
            return []

        if mode == "fixed":
            period_ms = _BASE_MS[base_tf] * group_size
            key_fn = lambda c: (c.open_time // period_ms) * period_ms
        elif mode == "calendar_week":
            key_fn = _week_start_ms
        elif mode == "calendar_month":
            key_fn = _month_start_ms
        else:
            raise ValueError(f"Unknown aggregation mode '{mode}' for timeframe '{timeframe}'")

        buckets: "OrderedDict[int, List[Candle]]" = OrderedDict()
        for c in base_candles:
            buckets.setdefault(key_fn(c), []).append(c)

        aggregated: List[Candle] = []
        for bucket_start, group in buckets.items():
            aggregated.append(Candle(
                symbol=pair, timeframe=timeframe,
                open_time=bucket_start, close_time=group[-1].close_time,
                open=group[0].open,
                high=max(c.high for c in group),
                low=min(c.low for c in group),
                close=group[-1].close,
                volume=sum(c.volume for c in group),
                is_closed=True,
            ))
        return aggregated


def _week_start_ms(c: Candle) -> int:
    dt = datetime.fromtimestamp(c.open_time / 1000, tz=timezone.utc)
    monday = dt - timedelta(days=dt.weekday())
    monday_midnight = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(monday_midnight.timestamp() * 1000)


def _month_start_ms(c: Candle) -> int:
    dt = datetime.fromtimestamp(c.open_time / 1000, tz=timezone.utc)
    month_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(month_start.timestamp() * 1000)
