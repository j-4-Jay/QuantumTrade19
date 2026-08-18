"""
FULL PATH: tests/monitors/test_poi_monitor_assembly.py (NEW FILE)

Tier 2 integration checks for POIMonitor. Uses real File 03 Workers wired
through the real assembly, with mocked File 02 public interface + fake symbol
registry. No network calls.

Covers:
- get_active_pois(symbol) returns only that symbol's independently-built POIs
- get_poi_state(symbol, poi_id) returns state without cross-symbol leakage
- set_poi_type_enabled(type, bool) fans out over active symbols
- all 13 POIType toggles route to the appropriate Worker live

Run:
    pytest tests/monitors/test_poi_monitor_assembly.py -v
"""
from __future__ import annotations

import pytest

from engines.monitors.poi_monitor import POIMonitor
from engines.workers.poi.poi_types import DEFAULT_ENABLED, POI, POIState, POIStateRecord, POIType
from tests.workers.poi.poi_test_helpers import FakeMarketDataMonitor, FakeSymbolRegistry, candle, flat_candles



from pathlib import Path

from engines.workers.poi.poi_settings import POISettingsStore
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker


















SYMBOLS = ("B-BTC_USDT", "B-ETH_USDT")


def _populate_minimal_htf_data(mdm: FakeMarketDataMonitor) -> None:
    """Supply enough candles for availability gates while making all detector
    types deterministic/no-op by default. The final 1D/4H row is treated as
    forming by POILevelCalculatorWorker, so index -2 becomes the known POI."""
    mdm.set_series("1H", flat_candles(30))
    mdm.set_series("4H", [
        candle(100, 102, 98, 101), candle(101, 103, 99, 102),
        candle(102, 104, 100, 103), candle(103, 105, 101, 104),
        candle(104, 106, 102, 105), candle(105, 107, 103, 106),
        candle(106, 112, 108, 110),  # completed (index -2): 4H H/L=112/108
        candle(110, 113, 109, 111),  # forming, excluded
    ])
    mdm.set_series("1D", [
        candle(100, 102, 98, 101),
        candle(101, 105, 95, 100),  # completed (index -2): PDH/PDL=105/95
        candle(100, 103, 99, 102),  # forming, excluded
    ])
    mdm.set_series("1W", [
        candle(100, 110, 90, 105), candle(105, 112, 95, 108),
    ])
    mdm.set_series("1M", [
        candle(100, 115, 85, 110), candle(110, 120, 90, 112),
    ])
    mdm.set_live("1H", candle(100, 101, 99, 100))
    mdm.set_live("4H", candle(110, 113, 109, 111))
    mdm.set_live("1D", candle(100, 103, 99, 102))
    mdm.set_live("1W", candle(105, 112, 95, 108))
    mdm.set_live("1M", candle(110, 120, 90, 112))


@pytest.fixture
def monitor(tmp_path: Path):
    mdm = FakeMarketDataMonitor()
    _populate_minimal_htf_data(mdm)
    registry = FakeSymbolRegistry(SYMBOLS)

    isolated_settings = POISettingsStore(
        SettingsPersistenceWorker(tmp_path / "settings.json")
    )
    return POIMonitor(
        mdm,
        registry,
        settings_store=isolated_settings,
    )

def test_get_active_pois_returns_default_line_pois_for_each_symbol_independently(monitor):
    btc = monitor.get_active_pois("B-BTC_USDT")
    eth = monitor.get_active_pois("B-ETH_USDT")

    expected_types = {POIType.PDH, POIType.PDL, POIType.H4_HIGH, POIType.H4_LOW}
    assert {p.poi_type for p in btc} == expected_types
    assert {p.poi_type for p in eth} == expected_types
    assert all(p.symbol == "B-BTC_USDT" for p in btc)
    assert all(p.symbol == "B-ETH_USDT" for p in eth)

    btc_prices = {p.poi_type: p.price for p in btc}
    assert btc_prices == {
        POIType.PDH: 105,
        POIType.PDL: 95,
        POIType.H4_HIGH: 112,
        POIType.H4_LOW: 108,
    }


def test_get_poi_state_returns_only_requested_symbol_state(monitor):
    btc_pdh = next(p for p in monitor.get_active_pois("B-BTC_USDT") if p.poi_type == POIType.PDH)
    eth_pdh = next(p for p in monitor.get_active_pois("B-ETH_USDT") if p.poi_type == POIType.PDH)

    # Force distinct values into the assembly-owned state registry, then use
    # public retrieval only. This proves no poi_id/symbol namespace collision.
    monitor._states["B-BTC_USDT"][btc_pdh.poi_id] = POIStateRecord(
        poi_id=btc_pdh.poi_id, symbol="B-BTC_USDT", distance_ticks=5,
        state=POIState.APPROACHING, last_touch_ts=None, last_price=100,
    )
    monitor._states["B-ETH_USDT"][eth_pdh.poi_id] = POIStateRecord(
        poi_id=eth_pdh.poi_id, symbol="B-ETH_USDT", distance_ticks=0,
        state=POIState.HIT, last_touch_ts=123.0, last_price=105,
    )

    btc_state = monitor.get_poi_state("B-BTC_USDT", btc_pdh.poi_id)
    eth_state = monitor.get_poi_state("B-ETH_USDT", eth_pdh.poi_id)
    assert btc_state.state == POIState.APPROACHING
    assert eth_state.state == POIState.HIT
    assert monitor.get_poi_state("B-BTC_USDT", eth_pdh.poi_id) is None
    assert monitor.get_poi_state("UNKNOWN", btc_pdh.poi_id) is None


@pytest.mark.parametrize("poi_type", list(POIType))
def test_every_poi_type_toggle_fans_out_to_all_symbols(monitor, poi_type):
    """Literal File 03 check gate: every one of the 13 Settings toggles must
    turn its calculation on/off live across every currently active symbol."""
    monitor.set_poi_type_enabled(poi_type, True)
    for symbol in SYMBOLS:
        assert monitor._enabled_types[symbol][poi_type] is True

    monitor.set_poi_type_enabled(poi_type, False)
    for symbol in SYMBOLS:
        assert monitor._enabled_types[symbol][poi_type] is False
        assert not any(p.poi_type == poi_type for p in monitor.get_active_pois(symbol))


def test_disabling_one_line_type_removes_only_that_type_and_preserves_others(monitor):
    monitor.set_poi_type_enabled(POIType.PDH, False)
    for symbol in SYMBOLS:
        types = {p.poi_type for p in monitor.get_active_pois(symbol)}
        assert POIType.PDH not in types
        assert {POIType.PDL, POIType.H4_HIGH, POIType.H4_LOW}.issubset(types)


def test_set_fvg_enabled_routes_to_fvg_worker_and_updates_both_symbols(monitor):
    monitor.set_poi_type_enabled(POIType.FVG, True)
    for symbol in SYMBOLS:
        assert monitor._fvg_workers[symbol].enabled_types[POIType.FVG] is True

    monitor.set_poi_type_enabled(POIType.FVG, False)
    for symbol in SYMBOLS:
        assert monitor._fvg_workers[symbol]._pois == {}


def test_set_order_block_enabled_routes_to_orderblock_worker_and_updates_both_symbols(monitor):
    monitor.set_poi_type_enabled(POIType.ORDER_BLOCK, True)
    for symbol in SYMBOLS:
        assert monitor._ob_workers[symbol].enabled_types[POIType.ORDER_BLOCK] is True

    monitor.set_poi_type_enabled(POIType.ORDER_BLOCK, False)
    for symbol in SYMBOLS:
        assert monitor._ob_workers[symbol]._pois == {}


def test_set_inverse_fvg_enabled_routes_to_inverse_worker_and_updates_both_symbols(monitor):
    monitor.set_poi_type_enabled(POIType.INVERSE_FVG, True)
    for symbol in SYMBOLS:
        assert monitor._inv_workers[symbol].enabled_types[POIType.INVERSE_FVG] is True

    monitor.set_poi_type_enabled(POIType.INVERSE_FVG, False)
    for symbol in SYMBOLS:
        assert monitor._inv_workers[symbol]._pois == {}


def test_unknown_symbol_has_no_pois_or_health(monitor):
    assert monitor.get_active_pois("UNKNOWN") == []
    assert monitor.get_health("UNKNOWN") == "DOWN"
