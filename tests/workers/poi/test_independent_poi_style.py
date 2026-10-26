"""Tests for the style of Independent POI lines (FT-C.4).

PATH: tests/workers/poi/test_independent_poi_style.py (NEW FILE)
"""
from engines.workers.poi.independent_poi_worker import (
    DEFAULT_LINE_STYLE, IndependentPOIStore, build_chart_items, hex_to_rgba,
)

SYM = "B-BTC_USDT"


def make_store():
    calls = []
    store = IndependentPOIStore(on_change=lambda sym, pois: calls.append(sym), clock=lambda: 1000.0)
    return store, calls


def test_hex_to_rgba_uses_the_opacity_percent():
    assert hex_to_rgba("#F59E0B", 100) == "rgba(245,158,11,1)"
    assert hex_to_rgba("#000000", 50) == "rgba(0,0,0,0.5)"
    assert hex_to_rgba("#FFFFFF", 0) == "rgba(255,255,255,0)"


def test_set_style_changes_only_the_given_values():
    store, _ = make_store()
    line = store.add(SYM, 100.0, 0.1)
    store.set_style(SYM, line.uid, color="#22c55e", width="4", opacity=40, line_style="dotted")
    item = build_chart_items(store.lines(SYM))[0]
    assert item["color"] == "#22C55E" and item["width"] == 4 and item["opacity"] == 40
    assert item["line_style"] == "dotted" and item["dashed"] is True
    assert item["line_color"] == "rgba(34,197,94,0.4)"


def test_set_style_solid_is_not_dashed():
    store, _ = make_store()
    line = store.add(SYM, 100.0, 0.1)
    store.set_style(SYM, line.uid, line_style="solid")
    assert build_chart_items(store.lines(SYM))[0]["dashed"] is False


def test_bad_values_are_ignored():
    store, calls = make_store()
    line = store.add(SYM, 100.0, 0.1)
    calls.clear()
    store.set_style(SYM, line.uid, color="red", width=9, opacity=-1, line_style="wavy")
    item = build_chart_items(store.lines(SYM))[0]
    assert item["color"] == DEFAULT_LINE_STYLE["color"]
    assert item["width"] == DEFAULT_LINE_STYLE["width"]
    assert item["opacity"] == DEFAULT_LINE_STYLE["opacity"]
    assert item["line_style"] == DEFAULT_LINE_STYLE["line_style"]
    assert calls == []


def test_unknown_line_returns_none():
    store, _ = make_store()
    assert store.set_style(SYM, "nope", width=3) is None


def test_style_belongs_to_one_line_and_keeps_the_poi_id():
    store, calls = make_store()
    first = store.add(SYM, 100.0, 0.1)
    second = store.add(SYM, 105.0, 0.1)
    old_id = first.poi_id
    calls.clear()
    store.set_style(SYM, first.uid, width=5)
    items = build_chart_items(store.lines(SYM))
    assert items[0]["width"] == 5 and items[1]["width"] == DEFAULT_LINE_STYLE["width"]
    assert first.poi_id == old_id and second.rev == 1
    assert calls == [SYM]
