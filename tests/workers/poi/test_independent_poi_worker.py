"""Tests for Independent POI lines (FT-C.2).

PATH: tests/workers/poi/test_independent_poi_worker.py (NEW FILE)
"""
from engines.workers.poi.independent_poi_worker import (
    IND_POI_TYPE, MAX_LINES_PER_SYMBOL, IndependentPOIStore, snap_to_tick,
)

BTC = "B-BTC_USDT"
ETH = "B-ETH_USDT"


class FakeClock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now


def make_store():
    clock = FakeClock()
    calls = []
    store = IndependentPOIStore(on_change=lambda sym, pois: calls.append((sym, list(pois))), clock=clock)
    return store, clock, calls


def test_snap_to_tick_rounds_to_nearest_tick():
    assert snap_to_tick(100.04, 0.1) == 100.0
    assert snap_to_tick(100.06, 0.1) == 100.1
    assert snap_to_tick(67123.4, 0.5) == 67123.5


def test_add_numbers_lines_one_two_and_builds_ordinary_pois():
    store, _, _ = make_store()
    first = store.add(BTC, 100.0, 0.1)
    second = store.add(BTC, 101.0, 0.1)
    assert (first.number, second.number) == (1, 2)
    assert first.label == "Ind. POI 1"
    pois = store.pois(BTC)
    assert [p.metadata["number"] for p in pois] == [1, 2]
    poi = pois[0]
    assert poi.poi_type == IND_POI_TYPE
    assert poi.price == 100.0 and poi.active is True
    assert poi.strategy_enabled is True and poi.metadata["independent"] is True
    assert poi.metadata["allow_live"] is False


def test_cap_of_ten_per_symbol_refuses_the_eleventh():
    store, _, _ = make_store()
    for i in range(MAX_LINES_PER_SYMBOL):
        assert store.add(BTC, 100.0 + i, 0.1) is not None
    assert store.add(BTC, 200.0, 0.1) is None
    assert len(store.lines(BTC)) == 10
    assert store.add(ETH, 50.0, 0.01) is not None


def test_delete_frees_number_and_next_add_reuses_lowest_free_number():
    store, _, _ = make_store()
    one = store.add(BTC, 100.0, 0.1)
    two = store.add(BTC, 101.0, 0.1)
    three = store.add(BTC, 102.0, 0.1)
    assert store.delete(BTC, two.uid) is True
    assert [l.number for l in store.lines(BTC)] == [1, 3]
    again = store.add(BTC, 103.0, 0.1)
    assert again.number == 2
    assert again.uid != two.uid
    assert one.number == 1 and three.number == 3


def test_delete_unknown_line_returns_false():
    store, _, _ = make_store()
    assert store.delete(BTC, "nope") is False


def test_move_creates_new_poi_id_new_creation_time_same_uid_and_number():
    store, clock, _ = make_store()
    line = store.add(BTC, 100.0, 0.1)
    old_id, old_ts = line.poi_id, line.created_ts
    clock.now = 2000.0
    moved = store.move(BTC, line.uid, 105.04, 0.1)
    assert moved.uid == line.uid and moved.number == line.number
    assert moved.price == 105.0
    assert moved.poi_id != old_id
    assert moved.created_ts == 2000.0 and moved.created_ts != old_ts
    poi = store.pois(BTC)[0]
    assert poi.poi_id == moved.poi_id and poi.formed_at_ts == 2000.0


def test_symbols_do_not_leak_into_each_other():
    store, _, _ = make_store()
    store.add(BTC, 100.0, 0.1)
    assert store.pois(ETH) == []
    assert len(store.pois(BTC)) == 1


def test_callback_receives_the_symbols_pois_after_every_change():
    store, _, calls = make_store()
    line = store.add(BTC, 100.0, 0.1)
    store.move(BTC, line.uid, 101.0, 0.1)
    store.delete(BTC, line.uid)
    assert [c[0] for c in calls] == [BTC, BTC, BTC]
    assert [len(c[1]) for c in calls] == [1, 1, 0]


def test_invalid_prices_are_refused():
    store, _, calls = make_store()
    assert store.add(BTC, 0, 0.1) is None
    assert store.add(BTC, -5, 0.1) is None
    assert store.add(BTC, float("nan"), 0.1) is None
    assert store.add(BTC, "abc", 0.1) is None
    assert calls == []
