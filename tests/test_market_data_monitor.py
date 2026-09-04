"""
PATH: tests/test_market_data_monitor.py (REPLACE ENTIRE FILE)

FIX: the WS-drop/REST-fallback test used fixed-duration `time.sleep()` calls
tuned to just barely clear `HEARTBEAT_TIMEOUT_S`. That duration happened to
land within a fraction of a second of ws_feed_worker.py's own independent
background reconnect retry timer (`RECONNECT_BACKOFF_START_S`), creating a
genuine timing race between the test's fixed sleep and a real production
background thread - sometimes passing, sometimes not, depending on thread
scheduling jitter. This is a test-design issue, not a production bug.

Replaced both fixed sleeps with a poll-until-condition helper with a
generous timeout. This removes the race entirely and is a more robust
pattern for testing any threaded/background system in general - never
guess a sleep duration against a concurrently running timer you don't
control.
"""
from __future__ import annotations
import time
import unittest
from typing import Callable, Dict, List

from engines.workers.market_data.candle_builder_worker import Candle
from engines.workers.market_data.tick_normalizer_worker import NormalizedTick
from engines.workers.market_data.ws_feed_worker import (
    AGGREGATE_UPDATE_EVENT, HEARTBEAT_TIMEOUT_S, HEARTBEAT_POLL_INTERVAL_S,
    RECONNECT_BACKOFF_START_S,
)
from engines.monitors.market_data_monitor import MarketDataMonitor


def _wait_until(condition: Callable[[], bool], timeout_s: float, poll_s: float = 0.1) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(poll_s)
    return False


class FakeSocketTransport:
    def __init__(self):
        self._handlers = {}
        self._connected = False
        self.emitted = []

    def connect(self, url):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def emit(self, event, data):
        self.emitted.append((event, data))

    def on(self, event, handler):
        self._handlers[event] = handler

    def connected(self):
        return self._connected

    def push_tick(self, symbol, price, ts_ms, volume=1.0):
        """Simulates one real CoinDCX aggregate-channel delta frame carrying
        a price-bearing row for exactly one symbol, matching the real
        `{"prices": {symbol: {...}}}` shape that ws_feed_worker.py actually
        parses."""
        handler = self._handlers.get(AGGREGATE_UPDATE_EVENT)
        if handler:
            handler({"prices": {symbol: {"ls": price, "q": volume, "T": ts_ms}}})


class FakeHttpResponse:
    def __init__(self, json_body):
        self._json_body = json_body

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_body


def make_fake_candle_http_get(candle_rows):
    """Real HistoricalDataLoaderWorker expects {"data": [...]} - see
    historical_data_loader_worker.py's verified response-shape docstring."""
    def _get(url, params=None, timeout=None):
        return FakeHttpResponse({"data": candle_rows})
    return _get


def make_fake_ticker_http_get(price_holder, symbol):
    """Real RestPollFallbackWorker._extract_row_for_symbol expects a dict
    with a "prices" (or "data") key, keyed by symbol - not a bare list."""
    def _get(url, timeout=None):
        return FakeHttpResponse({
            "prices": {
                symbol: {
                    "last_price": price_holder["price"],
                    "volume": 1.0,
                    "timestamp": int(time.time() * 1000),
                }
            }
        })
    return _get


class TestTradingPanelRenderData(unittest.TestCase):
    def test_closed_1m_bar_is_persisted_for_chart_render(self):
        transport = FakeSocketTransport()
        monitor = MarketDataMonitor(transport=transport)
        candle = Candle(
            symbol="B-BTC_USDT",
            timeframe="1m",
            open_time=1_700_000_000_000,
            close_time=1_700_000_059_999,
            open=100.0,
            high=101.0,
            low=99.5,
            close=100.75,
            volume=2.5,
            is_closed=True,
        )

        monitor._publish_candle_closed(candle)

        page = monitor.candle_store.get_recent_window(
            "B-BTC_USDT",
            "1m",
            end_ms=candle.close_time + 60_000,
            visible_days=1,
            older_buffer_days=0,
        )
        assert any(row.open_time == candle.open_time for row in page["candles"])


class TestCandleBuilderContinuity(unittest.TestCase):
    def test_no_gap_no_duplicate_across_synthetic_soak(self):
        from engines.workers.market_data.candle_builder_worker import CandleBuilderWorker
        builder = CandleBuilderWorker()
        symbol = "B-BTC_USDT"
        start = 1_700_000_000_000
        step = 60_000
        for i in range(500):
            ts = start + i * step + 30_000
            tick = NormalizedTick(symbol=symbol, price=100.0 + i, volume=1.0,
                                   exchange_ts=ts, received_ts=ts, source="ws")
            builder.ingest(tick, timeframes=["1m"])
        report = builder.check_continuity(symbol, "1m")
        self.assertTrue(report["clean"], msg=report)
        self.assertEqual(len(report["gaps"]), 0)
        self.assertEqual(len(report["duplicates"]), 0)

    def test_late_out_of_order_tick_never_rewrites_closed_candle(self):
        from engines.workers.market_data.candle_builder_worker import CandleBuilderWorker
        builder = CandleBuilderWorker()
        symbol = "B-ETH_USDT"
        start = 1_700_000_000_000
        t1 = NormalizedTick(symbol, 10.0, 1.0, start, start, "ws")
        t2 = NormalizedTick(symbol, 11.0, 1.0, start + 70_000, start + 70_000, "ws")
        builder.ingest(t1, ["1m"])
        builder.ingest(t2, ["1m"])
        stale = NormalizedTick(symbol, 9999.0, 1.0, start + 5_000, start + 5_000, "ws")
        builder.ingest(stale, ["1m"])
        history = builder.get_series(symbol, "1m")
        closed = [c for c in history if c.is_closed]
        self.assertEqual(closed[0].close, 10.0)


class TestWSDropAndRestFallback(unittest.TestCase):
    def test_fallback_engages_within_window_and_hands_back_on_restore(self):
        transport = FakeSocketTransport()
        monitor = MarketDataMonitor(transport=transport)
        symbol = "B-BTC_USDT"

        price_holder = {"price": 101.0}
        monitor.historical_loader._http_get = make_fake_candle_http_get([])
        monitor.rest_fallback._http_get = make_fake_ticker_http_get(price_holder, symbol)

        monitor.ws_feed.start()
        monitor.subscribe(symbol)

        transport.push_tick(symbol, 100.0, int(time.time() * 1000))
        self.assertEqual(monitor.get_health()[symbol], "OK")

        degraded = _wait_until(
            lambda: monitor.get_health().get(symbol) == "DEGRADED" and monitor.rest_fallback.is_engaged(symbol),
            timeout_s=HEARTBEAT_TIMEOUT_S + RECONNECT_BACKOFF_START_S + 3.0,
        )
        self.assertTrue(degraded, "symbol never transitioned to DEGRADED with REST fallback engaged")

        transport.push_tick(symbol, 105.0, int(time.time() * 1000))
        restored = _wait_until(
            lambda: not monitor.rest_fallback.is_engaged(symbol) and monitor.get_health().get(symbol) == "OK",
            timeout_s=RECONNECT_BACKOFF_START_S + 3.0,
        )
        self.assertTrue(restored, "rest fallback did not disengage / health did not return to OK after a fresh tick")

        monitor.ws_feed.stop()


class TestFreshSymbolHasHistoryImmediately(unittest.TestCase):
    def test_backfill_seeds_candle_builder_on_subscribe(self):
        transport = FakeSocketTransport()
        monitor = MarketDataMonitor(transport=transport)
        symbol = "B-ETH_USDT"

        now = int(time.time() * 1000)
        fake_rows = [{"time": now - i * 60_000, "open": 10, "high": 11, "low": 9,
                      "close": 10.5, "volume": 5} for i in range(200)]
        monitor.historical_loader._http_get = make_fake_candle_http_get(fake_rows)
        monitor.rest_fallback._http_get = make_fake_ticker_http_get({"price": 10.5}, symbol)

        monitor.ws_feed.start()
        monitor.subscribe(symbol)

        series = monitor.candle_builder.get_series(symbol, "1m")
        self.assertGreater(len(series), 0)
        monitor.ws_feed.stop()


class TestPerSymbolIsolation(unittest.TestCase):
    def test_unsubscribe_one_symbol_does_not_affect_other(self):
        transport = FakeSocketTransport()
        monitor = MarketDataMonitor(transport=transport)
        s1, s2 = "B-BTC_USDT", "B-ETH_USDT"

        monitor.historical_loader._http_get = make_fake_candle_http_get([])
        monitor.rest_fallback._http_get = make_fake_ticker_http_get({"price": 1.0}, s1)

        monitor.ws_feed.start()
        monitor.subscribe(s1)
        monitor.subscribe(s2)

        transport.push_tick(s1, 50.0, int(time.time() * 1000))
        transport.push_tick(s2, 60.0, int(time.time() * 1000))

        monitor.unsubscribe(s1)

        self.assertNotIn(s1, monitor.get_health())
        self.assertIn(s2, monitor.get_health())
        self.assertEqual(monitor.get_health()[s2], "OK")
        monitor.ws_feed.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
