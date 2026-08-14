"""Temporary rate-limit gate for Deep_History_Downloader_Worker until Module 08's RateLimit_Guard_Worker exists.
Same `async acquire(priority)` shape so swapping it in later needs no call-site changes.
"""
from __future__ import annotations
import asyncio
import time


class _TemporaryRateLimitGate:
    def __init__(self, deep_history_min_interval_seconds: float = 1.5) -> None:
        self._deep_history_min_interval = deep_history_min_interval_seconds
        self._last_deep_history_call = 0.0

    async def acquire(self, priority: str) -> None:
        if priority == "live":
            return
        elapsed = time.monotonic() - self._last_deep_history_call
        wait = self._deep_history_min_interval - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_deep_history_call = time.monotonic()


rate_limit_gate = _TemporaryRateLimitGate()
