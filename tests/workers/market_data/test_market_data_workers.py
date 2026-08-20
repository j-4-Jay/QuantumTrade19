"""Check-gate tests for Module 02 Market Data Monitor -- all mocked/fabricated data, no live API calls.

PATH: tests/workers/market_data/test_market_data_workers.py (REPLACE ENTIRE FILE)

UPDATE: SymbolRegistryWorker now implements BOTH Blueprint Section 8 deep-
history eligibility paths (auto-live-traded once, OR manually added before
first trade). The manual-add test below now exercises the real, newly-added
add_symbol_manual()/is_deep_history_eligible() path instead of just flagging
it as a known gap.
"""
from __future__ import annotations
import time
from pathlib import Path
import pytest

from engines.workers.market_data.symbol_registry_worker import SymbolRegistryWorker
from engines.workers.market_data.tick_normalizer_worker import TickNormalizerWorker, NormalizedTick
from engines.workers.market_data.candle_builder_worker import CandleBuilderWorker
from engines.workers.market_data.candle_store import CandleStore
from engines.workers.market_data.history_manifest_worker import HistoryManifestWorker
from engines.workers.market_data.deep_history_downloader_worker import DeepHistoryDownloaderWorker
from engines.workers.market_data.rest_poll_fallback_worker import RestPollFallbackWorker
from engines.event_bus.bus import event_bus


@pytest.fixture
def tmp_registry(tmp_path: Path) -> SymbolRegistryWorker:
    return SymbolRegistryWorker(path=str(tmp_path / "symbol_registry.json"))


@pytest.fixture
def tmp_manifest(tmp_path: Path) -> HistoryManifestWorker:
    return HistoryManifestWorker(manifest_dir=tmp_path / "manifests")


def test_symbol_registry_seeds_default_futures_symbols_with_tick_metadata(tmp_registry: SymbolRegistryWorker) -> None:
    active = set(tmp_registry.get_active_symbols())
    assert active == {"B-BTC_USDT", "B-ETH_USDT", "B-XAU_USDT"}
    info = tmp_registry.get_symbol_info("B-BTC_USDT")
    assert info is not None
    assert info.tick_size == 0.1
    assert info.contract_size == 0.001
    assert info.maker_fee == 0.0005
    assert info.taker_fee == 0.001


def test_symbol_registry_add_and_mark_auto_live_traded_makes_deep_history_eligible(tmp_registry: SymbolRegistryWorker) -> None:
    tmp_registry.add_symbol("B-SOL_USDT", tick_size=0.01, contract_size=0.01,
                             maker_fee=0.0005, taker_fee=0.001, asset_class="crypto")
    assert tmp_registry.is_deep_history_eligible("B-SOL_USDT") is False
    tmp_registry.mark_auto_live_traded("B-SOL_USDT")
    assert tmp_registry.is_deep_history_eligible("B-SOL_USDT") is True
    assert "B-SOL_USDT" in tmp_registry.get_deep_history_eligible()


def test_symbol_registry_manual_add_makes_deep_history_eligible_immediately(tmp_registry: SymbolRegistryWorker) -> None:
    """Blueprint Section 8's second eligibility path: manually adding a
    symbol before its first trade must make it deep-history eligible right
    away, without waiting for mark_auto_live_traded()."""
    tmp_registry.add_symbol_manual("B-XRP_USDT", tick_size=0.001, contract_size=1.0,
                                    maker_fee=0.0005, taker_fee=0.001, asset_class="crypto")
    assert tmp_registry.is_deep_history_eligible("B-XRP_USDT") is True
    assert "B-XRP_USDT" in tmp_registry.get_deep_history_eligible()
    info = tmp_registry.get_symbol_info("B-XRP_USDT")
    assert info.auto_live_traded_once is False
    assert info.deep_history_manual_add is True


def test_tick_normalizer_from_ws_payload_returns_valid_normalized_tick() -> None:
    tick = TickNormalizerWorker.from_ws_payload("B-BTC_USDT", {"ls": "65000.5", "v": "0.1", "T": 1000})
    assert tick is not None
    assert TickNormalizerWorker.is_valid(tick) is True
    assert tick.price == 65000.5
    assert tick.volume == 0.1
    assert tick.source == "ws"
    assert tick.exchange_ts == 1000


def test_tick_normalizer_from_ws_payload_rejects_metadata_only_row() -> None:
    tick = TickNormalizerWorker.from_ws_payload("B-BTC_USDT", {"bmST": 1000, "cmRT": 1000})
    assert tick is None


def test_candle_builder_closes_1m_on_rollover_and_builds_poi_timeframes() -> None:
    closed = []
    builder = CandleBuilderWorker(on_candle_closed=lambda c: closed.append(c))
    ticks = [
        NormalizedTick(symbol="BTCUSD", price=100.0, volume=1.0, exchange_ts=0, received_ts=0, source="ws"),
        NormalizedTick(symbol="BTCUSD", price=110.0, volume=1.0, exchange_ts=30_000, received_ts=30_000, source="ws"),
        NormalizedTick(symbol="BTCUSD", price=90.0, volume=1.0, exchange_ts=65_000, received_ts=65_000, source="ws"),
    ]
    for tick in ticks:
        builder.ingest(tick, timeframes=["1m", "1D", "1W", "1M"])
    one_min = [c for c in closed if c.timeframe == "1m"]
    assert one_min and one_min[0].high == 110.0 and one_min[0].low == 100.0
    assert builder.get_live_candle("BTCUSD", "1D") is not None
    assert builder.get_live_candle("BTCUSD", "1W") is not None
    assert builder.get_live_candle("BTCUSD", "1M") is not None


def test_candle_builder_never_emits_duplicate_for_same_bucket() -> None:
    closed = []
    builder = CandleBuilderWorker(on_candle_closed=lambda c: closed.append(c))
    for ts in (0, 10_000, 20_000, 61_000):
        builder.ingest(
            NormalizedTick(symbol="ETHUSD", price=50.0, volume=1.0, exchange_ts=ts, received_ts=ts, source="ws"),
            timeframes=["1m"],
        )
    builder.ingest(
        NormalizedTick(symbol="ETHUSD", price=51.0, volume=1.0, exchange_ts=5_000, received_ts=5_000, source="ws"),
        timeframes=["1m"],
    )
    one_min_bucket0 = [c for c in closed if c.timeframe == "1m" and c.open_time == 0]
    assert len(one_min_bucket0) == 1


def test_manifest_find_gaps_and_coverage(tmp_manifest: HistoryManifestWorker) -> None:
    assert tmp_manifest.find_gaps("BTCUSD", "1m", 0, 1000) == [(0, 1000)]
    tmp_manifest.mark_covered("BTCUSD", "1m", 0, 500)
    tmp_manifest.mark_covered("BTCUSD", "1m", 500, 1000)
    assert tmp_manifest.find_gaps("BTCUSD", "1m", 0, 1000) == []
    assert tmp_manifest.coverage_percent("BTCUSD", "1m", 0, 1000) == 100.0


class _FakeSyncCandlesResponse:
    def __init__(self, rows) -> None:
        self._rows = rows

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._rows


def test_deep_history_downloader_stops_when_exchange_has_no_more_data(tmp_manifest: HistoryManifestWorker) -> None:
    call_count = {"n": 0}

    def fake_http_get(url, params=None, timeout=None):
        call_count["n"] += 1
        return _FakeSyncCandlesResponse([])

    worker = DeepHistoryDownloaderWorker(tmp_manifest, http_get=fake_http_get)
    worker.start_download("BTCUSD", "1m")

    deadline = time.time() + 2.0
    while worker.is_downloading("BTCUSD", "1m") and time.time() < deadline:
        time.sleep(0.05)

    assert call_count["n"] >= 1
    assert tmp_manifest.get_covered_ranges("BTCUSD", "1m") != []


def test_manifest_persists_across_restart(tmp_manifest: HistoryManifestWorker) -> None:
    tmp_manifest.mark_covered("ETHUSD", "15m", 0, 900_000)
    reloaded = HistoryManifestWorker(manifest_dir=tmp_manifest._dir)
    assert reloaded.get_covered_ranges("ETHUSD", "15m") == [(0, 900_000)]


class _FakeSyncHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_rest_fallback_engages_only_for_the_degraded_symbol_never_others() -> None:
    ticks_received = []

    def fake_http_get(url, timeout=5):
        return _FakeSyncHTTPResponse({"prices": {"BTCUSD": {"last_price": 100.0}}})

    worker = RestPollFallbackWorker(
        on_tick=lambda symbol, tick: ticks_received.append((symbol, tick)),
        http_get=fake_http_get,
        poll_interval_s=0.05,
    )

    worker.engage("BTCUSD")
    time.sleep(0.2)

    engaged_btc = worker.is_engaged("BTCUSD")
    engaged_eth = worker.is_engaged("ETHUSD")

    worker.disengage("BTCUSD")
    time.sleep(0.1)
    disengaged_btc = worker.is_engaged("BTCUSD")

    assert engaged_btc is True
    assert engaged_eth is False
    assert disengaged_btc is False
    assert len(ticks_received) >= 1
    assert ticks_received[0][0] == "BTCUSD"
    assert ticks_received[0][1]["last_price"] == 100.0
    assert worker.get_last_cached("BTCUSD")["last_price"] == 100.0


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
