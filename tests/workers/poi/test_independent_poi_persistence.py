"""Tests for saving Independent POI lines (FT-C.5 and FT-C.7).

PATH: tests/workers/poi/test_independent_poi_persistence.py (NEW FILE)
"""
import json

from engines.workers.poi.independent_poi_persistence import load_lines, save_lines
from engines.workers.poi.independent_poi_worker import (
    MAX_LINES_PER_SYMBOL, IndependentPOIStore, build_chart_items,
)

BTC = "B-BTC_USDT"
ETH = "B-ETH_USDT"


def make_store(calls=None):
    callback = (lambda sym, pois: calls.append(sym)) if calls is not None else None
    return IndependentPOIStore(on_change=callback, clock=lambda: 1000.0)


def test_save_and_load_round_trip(tmp_path):
    store = make_store()
    first = store.add(BTC, 100.0, 0.1)
    store.add(BTC, 105.0, 0.1)
    store.add(ETH, 50.0, 0.01)
    store.set_style(BTC, first.uid, color="#22C55E", width=4, opacity=60, line_style="dotted")
    path = tmp_path / "independent_pois.json"
    save_lines(path, store.all_lines())

    loaded = load_lines(path)
    again = make_store()
    assert again.restore(loaded) == 3
    assert [l.number for l in again.lines(BTC)] == [1, 2]
    restored = again.lines(BTC)[0]
    assert restored.uid == first.uid and restored.price == 100.0 and restored.rev == 1
    assert restored.created_ts == first.created_ts
    item = build_chart_items([restored])[0]
    assert item["color"] == "#22C55E" and item["width"] == 4
    assert item["opacity"] == 60 and item["line_style"] == "dotted"
    assert [l.price for l in again.lines(ETH)] == [50.0]


def test_missing_file_gives_no_lines(tmp_path):
    assert load_lines(tmp_path / "nothing.json") == []


def test_allow_live_is_never_saved_and_always_off_after_loading(tmp_path):
    store = make_store()
    line = store.add(BTC, 100.0, 0.1)
    store.set_allow_live(BTC, line.uid, True)
    path = tmp_path / "independent_pois.json"
    save_lines(path, store.all_lines())
    assert "allow_live" not in path.read_text(encoding="utf-8")

    data = json.loads(path.read_text(encoding="utf-8"))
    data["symbols"][BTC][0]["allow_live"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    again = make_store()
    again.restore(load_lines(path))
    assert again.lines(BTC)[0].allow_live is False


def test_unreadable_file_is_moved_aside_and_gives_no_lines(tmp_path):
    path = tmp_path / "independent_pois.json"
    path.write_text("<<<<<<< HEAD\n{not json", encoding="utf-8")
    assert load_lines(path) == []
    assert not path.exists()
    assert len(list(tmp_path.glob("independent_pois.json.bad-*"))) == 1


def test_wrong_version_is_treated_as_unreadable(tmp_path):
    path = tmp_path / "independent_pois.json"
    path.write_text(json.dumps({"version": 99, "symbols": {}}), encoding="utf-8")
    assert load_lines(path) == []
    assert len(list(tmp_path.glob("independent_pois.json.bad-*"))) == 1


def test_invalid_entries_are_skipped_and_good_ones_kept(tmp_path):
    path = tmp_path / "independent_pois.json"
    good = {"uid": "aaa", "number": 1, "price": 10.0, "created_ts": 1.0, "rev": 1, "style": {"width": 3}}
    data = {"version": 1, "symbols": {BTC: [
        good,
        {"uid": "bbb", "number": 11, "price": 10.0},
        {"uid": "ccc", "number": 2, "price": -5.0},
        {"uid": "", "number": 3, "price": 10.0},
        {"uid": "ddd", "number": "x", "price": 10.0},
        {"uid": "eee", "number": 4, "price": 12.0, "style": {"color": "red", "width": 99}},
    ]}}
    path.write_text(json.dumps(data), encoding="utf-8")
    store = make_store()
    assert store.restore(load_lines(path)) == 2
    lines = store.lines(BTC)
    assert [l.uid for l in lines] == ["aaa", "eee"]
    assert lines[0].style == {"width": 3}
    assert lines[1].style == {}


def test_restore_keeps_cap_and_unique_numbers_and_does_not_notify():
    calls = []
    store = make_store(calls)
    source = make_store()
    for i in range(MAX_LINES_PER_SYMBOL):
        source.add(BTC, 100.0 + i, 0.1)
    extra = make_store()
    extra.add(BTC, 500.0, 0.1)
    lines = source.lines(BTC) + extra.lines(BTC)
    assert store.restore(lines) == MAX_LINES_PER_SYMBOL
    assert len(store.lines(BTC)) == MAX_LINES_PER_SYMBOL
    assert calls == []


def test_save_is_stable_and_leaves_no_temporary_file(tmp_path):
    store = make_store()
    store.add(BTC, 100.0, 0.1)
    store.add(BTC, 101.0, 0.1)
    path = tmp_path / "independent_pois.json"
    save_lines(path, store.all_lines())
    first = path.read_text(encoding="utf-8")
    save_lines(path, store.all_lines())
    assert path.read_text(encoding="utf-8") == first
    assert first.endswith("\n")
    assert [p.name for p in tmp_path.iterdir()] == ["independent_pois.json"]


def test_all_lines_and_symbols_skip_empty_symbols():
    store = make_store()
    line = store.add(BTC, 100.0, 0.1)
    store.add(ETH, 50.0, 0.01)
    store.delete(ETH, store.lines(ETH)[0].uid)
    assert store.symbols() == [BTC]
    assert list(store.all_lines().keys()) == [BTC]
    assert store.all_lines()[BTC][0].uid == line.uid


def test_set_allow_live_changes_the_chart_badge():
    store = make_store()
    line = store.add(BTC, 100.0, 0.1)
    assert build_chart_items(store.lines(BTC))[0]["chart_label"] == "Ind. POI 1  |  PAPER"
    store.set_allow_live(BTC, line.uid, True)
    item = build_chart_items(store.lines(BTC))[0]
    assert item["chart_label"] == "Ind. POI 1  |  LIVE" and item["allow_live"] is True
    assert store.pois(BTC)[0].metadata["allow_live"] is True
    assert store.set_allow_live(BTC, "nope", True) is None
