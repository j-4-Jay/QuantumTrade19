"""Tests for the chart items of Independent POI lines (FT-C.3, step 1).

PATH: tests/workers/poi/test_independent_poi_chart_items.py (NEW FILE)
"""
from engines.workers.poi.independent_poi_worker import (
    DEFAULT_LINE_STYLE, IndependentPOIStore, build_chart_items,
)

SYM = "B-BTC_USDT"


def make_store():
    return IndependentPOIStore(clock=lambda: 1000.0)


def test_chart_items_describe_each_line():
    store = make_store()
    first = store.add(SYM, 100.0, 0.1)
    store.add(SYM, 105.0, 0.1)
    items = build_chart_items(store.lines(SYM))
    assert [i["label"] for i in items] == ["Ind. POI 1", "Ind. POI 2"]
    assert items[0]["kind"] == "ind_line" and items[0]["uid"] == first.uid
    assert items[1]["price"] == 105.0
    assert items[0]["color"] == DEFAULT_LINE_STYLE["color"]


def test_chart_item_uses_style_overrides_and_keeps_other_defaults():
    store = make_store()
    line = store.add(SYM, 100.0, 0.1)
    line.style = {"color": "#FF0000", "width": 4}
    item = build_chart_items([line])[0]
    assert item["color"] == "#FF0000" and item["width"] == 4
    assert item["dashed"] is True


def test_no_lines_gives_no_items():
    assert build_chart_items([]) == []


def test_pois_use_independent_source_tf_so_the_old_poi_chart_code_skips_them():
    store = make_store()
    store.add(SYM, 100.0, 0.1)
    assert store.pois(SYM)[0].source_tf == "independent"
