"""Tests: POIMonitor carries Independent POI lines (FT-C.2).

PATH: tests/monitors/test_poi_monitor_independent.py (NEW FILE)

Uses the same fake market data and fake symbol registry as
tests/monitors/test_poi_monitor_assembly.py. No network calls.

Run:
    pytest tests/monitors/test_poi_monitor_independent.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engines.monitors.poi_monitor import POIMonitor
from engines.workers.poi.independent_poi_worker import IND_POI_TYPE, IndependentPOIStore
from engines.workers.poi.poi_settings import POISettingsStore
from engines.workers.poi.poi_types import POI, POIState, POIType
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from tests.monitors.test_poi_monitor_assembly import SYMBOLS, _populate_minimal_htf_data
from tests.workers.poi.poi_test_helpers import FakeMarketDataMonitor, FakeSymbolRegistry

BTC, ETH = SYMBOLS


@pytest.fixture
def monitor(tmp_path: Path):
    mdm = FakeMarketDataMonitor()
    _populate_minimal_htf_data(mdm)
    registry = FakeSymbolRegistry(SYMBOLS)
    isolated_settings = POISettingsStore(SettingsPersistenceWorker(tmp_path / "settings.json"))
    return POIMonitor(mdm, registry, settings_store=isolated_settings)


def _ind_ids(monitor, symbol):
    return [p.poi_id for p in monitor.get_active_pois(symbol) if p.poi_type == IND_POI_TYPE]


def test_independent_lines_join_the_active_list_of_their_symbol_only(monitor):
    store = IndependentPOIStore(on_change=monitor.set_independent_pois)
    line = store.add(BTC, 100.0, 0.1)
    assert _ind_ids(monitor, BTC) == [line.poi_id]
    assert _ind_ids(monitor, ETH) == []


def _inject_real_poi(monitor, symbol):
    """Put one ordinary POI into the level store so these tests do not depend on market data."""
    real = POI(
        poi_id=f"{symbol}:TEST_REAL", symbol=symbol, poi_type=POIType.PDH, role="resistance",
        source_tf="1D", price=105.0, formed_at_ts=1.0, strategy_enabled=True,
    )
    monitor._level_pois[symbol] = {real.poi_id: real}
    return real


def test_empty_independent_set_leaves_the_real_pois_unchanged(monitor):
    real = _inject_real_poi(monitor, BTC)
    before = sorted(p.poi_id for p in monitor.get_active_pois(BTC))
    monitor.set_independent_pois(BTC, [])
    after = sorted(p.poi_id for p in monitor.get_active_pois(BTC))
    assert before == after == [real.poi_id]


def test_real_pois_are_still_returned_next_to_the_independent_line(monitor):
    real = _inject_real_poi(monitor, BTC)
    store = IndependentPOIStore(on_change=monitor.set_independent_pois)
    line = store.add(BTC, 100.0, 0.1)
    ids = {p.poi_id for p in monitor.get_active_pois(BTC)}
    assert ids == {real.poi_id, line.poi_id}


def test_state_tracker_gives_the_line_a_state_like_any_poi(monitor):
    store = IndependentPOIStore(on_change=monitor.set_independent_pois)
    line = store.add(BTC, 100.0, 0.1)
    record = monitor.get_poi_state(BTC, line.poi_id)
    assert record is not None
    assert record.state == POIState.HIT


def test_delete_removes_the_line_and_its_state(monitor):
    store = IndependentPOIStore(on_change=monitor.set_independent_pois)
    line = store.add(BTC, 100.0, 0.1)
    store.delete(BTC, line.uid)
    assert _ind_ids(monitor, BTC) == []
    assert monitor.get_poi_state(BTC, line.poi_id) is None


def test_move_replaces_the_poi_id_and_drops_the_old_state(monitor):
    store = IndependentPOIStore(on_change=monitor.set_independent_pois)
    line = store.add(BTC, 100.0, 0.1)
    old_id = line.poi_id
    moved = store.move(BTC, line.uid, 90.0, 0.1)
    assert _ind_ids(monitor, BTC) == [moved.poi_id]
    assert moved.poi_id != old_id
    assert monitor.get_poi_state(BTC, old_id) is None


def test_unknown_symbol_still_has_no_pois(monitor):
    assert monitor.get_active_pois("UNKNOWN") == []
