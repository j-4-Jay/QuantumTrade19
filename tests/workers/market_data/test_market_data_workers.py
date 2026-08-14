"""Check-gate tests for Module 02 Market Data Monitor -- all mocked/fabricated data, no live API calls."""
from __future__ import annotations
import asyncio
from pathlib import Path
import pytest

from engines.event_bus.bus import event_bus
from engines.workers.market_data.symbol_registry_worker import SymbolRegistryWorker
from engines.workers.market_data.tick_normalizer_worker import TickNormalizerWorker
from engines.workers.market_data.candle_builder_worker import CandleBuilderWorker
from engines.workers.market_data.candle_store import CandleStore
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker
from engines.workers.market_data.deep_history_downloader_worker import DeepHistoryDownloaderWorker
from engines.workers.market_data.rest_poll_fallback_worker import RESTPollFallbackWorker


@pytest.fixture
def tmp_registry(tmp_path: Path) -> SymbolRegistryWorker:
    return SymbolRegistryWorker(path=tmp_path / "symbol_registry.json")


@pytest.fixture
def tmp_manifest(tmp_path: Path) -> HistoryManifestWorker:
    return HistoryManifestWorker(manifest_dir=tmp_path / "manifests")


def test_symbol_registry_seeds_pinned_defaults_with_meta(tmp_registry: SymbolRegistryWorker) -> None:
    pinned = tmp_registry.get_pinned_symbols()
    assert set(pinned) == {"GOLD", "ETHUSD", "BTCUSD"}
    meta = tmp_registry.get_symbol_meta("BTCUSD")
    assert set(meta) == {"tick_size", "contract_size", "maker_fee", "taker_fee"}


def test_symbol_registry_manual_add_makes_deep_history_eligible(tmp_registry: SymbolRegistryWorker) -> None:
    tmp_registry.add_symbol_manual("SOLUSD")
    assert tmp_registry.is_deep_history_eligible("SOLUSD") is True


def test_tick_normalizer_emits_canonical_shape_with_both_timestamps() -> None:
    captured = []
    event_bus.subscribe("market_data.tick.normalized", lambda e: captured.append(e))
    TickNormalizerWorker()
    event_bus.publish("market_data.tick.raw_ws", {
        "symbol": "BTCUSD", "price": "65000.5", "quantity": "0.1", "exchange_timestamp_ms": 1000})
    tick = captured[-1]
    assert tick["price"] == 65000.5 and tick["source"] == "ws"
    assert tick["exchange_timestamp_ms"] == 1000 and tick["received_timestamp_ms"] > 0


def test_candle_builder_closes_1m_on_rollover_and_builds_poi_timeframes() -> None:
    closed = []
    event_bus.subscribe("market_data.candle.closed", lambda e: closed.append(e))
    builder = CandleBuilderWorker()
    builder._on_tick({"symbol": "BTCUSD", "price": 100.0, "volume": 1, "exchange_timestamp_ms": 0})
    builder._on_tick({"symbol": "BTCUSD", "price": 110.0, "volume": 1, "exchange_timestamp_ms": 30_000})
    builder._on_tick({"symbol": "BTCUSD", "price": 90.0, "volume": 1, "exchange_timestamp_ms": 65_000})
    one_min = [c for c in closed if c["timeframe"] == "1m"]
    assert one_min and one_min[0]["high"] == 110.0 and one_min[0]["low"] == 100.0
    daily = [k for k in builder._open if k[1] == "Daily"]
    weekly = [k for k in builder._open if k[1] == "Weekly"]
    monthly = [k for k in builder._open if k[1] == "Monthly"]
    assert daily and weekly and monthly


def test_candle_builder_never_emits_duplicate_for_same_bucket() -> None:
    closed = []
    event_bus.subscribe("market_data.candle.closed", lambda e: closed.append(e))
    builder = CandleBuilderWorker()
    for ts in (0, 10_000, 20_000, 61_000):
        builder._on_tick({"symbol": "ETHUSD", "price": 50.0, "volume": 1, "exchange_timestamp_ms": ts})
    builder._on_tick({"symbol": "ETHUSD", "price": 51.0, "volume": 1, "exchange_timestamp_ms": 5_000})
    one_min_bucket0 = [c for c in closed if c["timeframe"] == "1m" and c["bucket_start_ms"] == 0]
    assert len(one_min_bucket0) == 1


def test_manifest_find_gaps_and_coverage(tmp_manifest: HistoryManifestWorker) -> None:
    assert tmp_manifest.find_gaps("BTCUSD", "1m", 0, 1000) == [(0, 1000)]
    tmp_manifest.mark_covered("BTCUSD", "1m", 0, 500)
    tmp_manifest.mark_covered("BTCUSD", "1m", 500, 1000)
    assert tmp_manifest.find_gaps("BTCUSD", "1m", 0, 1000) == []
    assert tmp_manifest.coverage_percent("BTCUSD", "1m", 0, 1000) == 100.0


class _FakeHTTP:
    def __init__(self, rows_per_call=None) -> None:
        self.calls = 0
        self._rows_per_call = rows_per_call

    async def get_json(self, url, params=None):
        self.calls += 1
        if self._rows_per_call is not None:
            return self._rows_per_call
        if self.calls > 1:
            return []
        return [{"open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "bucket_start_ms": params["startTime"]}]


def test_deep_history_downloader_stops_when_exchange_has_no_more_data(tmp_manifest: HistoryManifestWorker) -> None:
    async def run():
        http = _FakeHTTP()
        worker = DeepHistoryDownloaderWorker(tmp_manifest, http_client=http)
        await worker._backfill_timeframe("BTCUSD", "1m")
        return http.calls
    calls = asyncio.run(run())
    assert calls >= 1
    assert tmp_manifest.get_covered_ranges("BTCUSD", "1m") != []


def test_manifest_persists_across_restart(tmp_manifest: HistoryManifestWorker) -> None:
    tmp_manifest.mark_covered("ETHUSD", "15m", 0, 900_000)
    reloaded = HistoryManifestWorker(manifest_dir=tmp_manifest._dir)
    assert reloaded.get_covered_ranges("ETHUSD", "15m") == [(0, 900_000)]


def test_rest_fallback_engages_only_for_the_degraded_symbol_never_others() -> None:
    async def run():
        http = _FakeHTTP(rows_per_call=[{"last_price": 100, "volume": 1}])
        worker = RESTPollFallbackWorker(http_client=http)
        event_bus.publish("market_data.feed.degraded", {"symbol": "BTCUSD", "reason": "stall"})
        await asyncio.sleep(0.05)
        engaged_btc = worker.is_active("BTCUSD")
        engaged_eth = worker.is_active("ETHUSD")
        worker._on_ws_recovering({"symbol": "BTCUSD"})
        return engaged_btc, engaged_eth
    engaged_btc, engaged_eth = asyncio.run(run())
    assert engaged_btc is True
    assert engaged_eth is False


def test_candle_store_serves_live_and_historical_candles() -> None:
    store = CandleStore()
    event_bus.publish("market_data.candle.closed", {
        "symbol": "BTCUSD", "timeframe": "1m", "open": 1, "high": 2, "low": 0.5, "close": 1.5,
        "volume": 10, "bucket_start_ms": 1_000_000_000})
    event_bus.publish("market_data.candle.closed", {
        "symbol": "BTCUSD", "timeframe": "1m", "open": 1.5, "high": 2.5, "low": 1, "close": 2,
        "volume": 5, "bucket_start_ms": 1_000_060_000})
    live = store.get_live_candle("BTCUSD", "1m")
    assert live is not None and live["close"] == 2
    history = store.get_historical_candles("BTCUSD", "1m", days=5)
    assert len(history) == 2
