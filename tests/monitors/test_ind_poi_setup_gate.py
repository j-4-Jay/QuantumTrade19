"""Stage gate FT-C.6: a candle touching an Independent POI line behaves like a real POI.

PATH: tests/monitors/test_ind_poi_setup_gate.py (NEW FILE)

Same candles go through a real POI and an Independent POI line. The interactions
(Touch / Sweep / Cross, Bull and Bear) and the setup chain must be equal.
No network calls. Reuses the fakes of the existing File 04 tests.

Run:
    python -m pytest tests/monitors/test_ind_poi_setup_gate.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engines.monitors.poi_monitor import POIMonitor
from engines.monitors.setup_detection_monitor import SetupDetectionMonitor
from engines.workers.poi.independent_poi_worker import IndependentPOIStore
from engines.workers.poi.poi_settings import POISettingsStore
from engines.workers.poi.poi_types import POI
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from engines.workers.setup.poi_interaction_detector_worker import POIInteractionDetectorWorker
from engines.workers.setup.setup_types import SetupDirection
from tests.monitors.test_poi_monitor_assembly import SYMBOLS, _populate_minimal_htf_data
from tests.test_setup_detection_monitor import Candle, _FakePOIMonitor, _FakeSymbolRegistry
from tests.workers.poi.poi_test_helpers import FakeMarketDataMonitor, FakeSymbolRegistry

BTC = SYMBOLS[0]
LEVEL = 100.0

SHAPES = {
    "touch": (100.0, 106.0, 99.0, 103.0),
    "same_side": (105.0, 106.0, 99.0, 103.0),
    "cross": (105.0, 106.0, 94.0, 95.0),
}
MISS = (110.0, 120.0, 108.0, 115.0)


@pytest.fixture
def poi_monitor(tmp_path: Path):
    mdm = FakeMarketDataMonitor()
    _populate_minimal_htf_data(mdm)
    registry = FakeSymbolRegistry(SYMBOLS)
    isolated = POISettingsStore(SettingsPersistenceWorker(tmp_path / "settings.json"))
    return POIMonitor(mdm, registry, settings_store=isolated)


@pytest.fixture
def store(poi_monitor):
    return IndependentPOIStore(on_change=poi_monitor.set_independent_pois)


def _candle(shape, number=1, tf="5m"):
    o, h, l, c = shape
    return Candle(BTC, tf, number, o, h, l, c)


def _real_poi():
    return POI("real1", BTC, "PDL", "support", "1D", price=LEVEL)


def _ind_interactions(poi_monitor, line, candle):
    pois = [p for p in poi_monitor.get_active_pois(BTC) if p.poi_id == line.poi_id]
    states = {p.poi_id: poi_monitor.get_poi_state(BTC, p.poi_id) for p in pois}
    return POIInteractionDetectorWorker().detect(candle, pois, states)


def _real_interactions(candle):
    return POIInteractionDetectorWorker().detect(candle, [_real_poi()], {})


def _key(items):
    return sorted((str(i.interaction_type), str(i.search_direction), i.is_retest) for i in items)


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_line_gives_same_interactions_as_real_poi_for_bull_and_bear(poi_monitor, store, name):
    line = store.add(BTC, LEVEL, 0.1)
    candle = _candle(SHAPES[name])
    ind = _ind_interactions(poi_monitor, line, candle)
    assert _key(ind) == _key(_real_interactions(candle))
    assert {i.search_direction for i in ind} == {SetupDirection.BULL, SetupDirection.BEAR}


def test_touch_sweep_and_cross_are_three_different_interaction_types(poi_monitor, store):
    line = store.add(BTC, LEVEL, 0.1)
    types = [_ind_interactions(poi_monitor, line, _candle(SHAPES[n]))[0].interaction_type for n in sorted(SHAPES)]
    assert len(set(types)) == 3


def test_candle_that_misses_the_line_gives_no_interaction(poi_monitor, store):
    line = store.add(BTC, LEVEL, 0.1)
    assert _ind_interactions(poi_monitor, line, _candle(MISS)) == []


def _run_chain(setup_monitor):
    c1 = Candle(BTC, "5m", 1, 105, 106, 100, 101)
    c2 = Candle(BTC, "5m", 2, 101, 110, 100, 109)
    c3 = Candle(BTC, "5m", 3, 109, 115, 108, 111)
    setup_monitor.on_candle_closed(c1)
    setup_monitor.on_candle_closed(c2)
    pending = sorted((str(p.direction), str(p.stage)) for p in setup_monitor.get_pending_setups(BTC, "5m"))
    confirmed = setup_monitor.on_candle_closed(c3)
    return pending, sorted(str(s.direction) for s in confirmed)


def test_three_candle_chain_on_a_line_matches_a_real_poi(poi_monitor, store):
    store.add(BTC, LEVEL, 0.1)
    ind_monitor = SetupDetectionMonitor(poi_monitor, FakeSymbolRegistry(SYMBOLS))
    real_monitor = SetupDetectionMonitor(_FakePOIMonitor(_real_poi()), _FakeSymbolRegistry())
    ind_pending, ind_confirmed = _run_chain(ind_monitor)
    real_pending, real_confirmed = _run_chain(real_monitor)
    assert len(ind_pending) == 2
    assert ind_pending == real_pending
    assert len(ind_confirmed) == 1
    assert ind_confirmed == real_confirmed


def test_deleted_line_starts_no_chain(poi_monitor, store):
    line = store.add(BTC, LEVEL, 0.1)
    store.delete(BTC, line.uid)
    setup_monitor = SetupDetectionMonitor(poi_monitor, FakeSymbolRegistry(SYMBOLS))
    pending, confirmed = _run_chain(setup_monitor)
    assert pending == [] and confirmed == []
