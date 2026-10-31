"""PATH: tests/monitors/test_setup_callout_helper.py  (NEW FILE)
FT-H.4 Step 1 tests for engines/workers/setup/setup_callout_helper.py. Run with pytest."""
from types import SimpleNamespace as NS

from engines.workers.setup.setup_callout_helper import build_setup_callouts, poi_short_names


def candle(o, h, l, c, t=1_700_000_000):
    return NS(open=o, high=h, low=l, close=c, open_time=t)


def setup(direction, c1, c2, c3, eid="e1", tf="5m"):
    return NS(event_id=eid, direction=direction, timeframe=tf, c1=c1, c2=c2, c3=c3)


def bull():
    return setup("SetupDirection.BULL", candle(100, 101, 99, 100.5), candle(100.5, 102, 98.5, 101), candle(101, 103, 100.5, 102.5))


def bear():
    return setup("Bear", candle(100, 101, 99, 99.5), candle(99.5, 101.5, 98, 99), candle(99, 99.5, 97, 97.5))


def test_bull_values():
    out = build_setup_callouts([bull()], 0.1, 7)[0]
    assert out["name"] == "123Bull" and out["is_bull"] is True
    assert out["entry"] == 102.5
    assert out["sl"] == 97.8
    assert out["risk_ticks"] == 47
    assert out["anchor_price"] == 100.2
    assert out["border_color"] == "#0E9464"


def test_bear_values():
    out = build_setup_callouts([bear()], 0.1, 7)[0]
    assert out["name"] == "123Bear" and out["is_bull"] is False
    assert out["sl"] == 102.2
    assert out["anchor_price"] == 99.8
    assert out["risk_ticks"] == 47
    assert out["border_color"] == "#990000"


def test_text_fields_and_placeholders():
    out = build_setup_callouts([bull()], 0.1, 7)[0]
    assert out["uid"] == "e1" and out["timeframe"] == "5m"
    assert out["entry_text"] == "102.5"
    assert out["sl_text"] == "97.8"
    assert out["ticks_text"] == "47"
    for key in ("qty_text", "risk_text", "live_text", "peak_text"):
        assert out[key] == "\u2014"
    assert out["confidence_text"] == "Confidence: File 05 pending"


def test_colours():
    bull_out = build_setup_callouts([bull()], 0.1, 7)[0]
    bear_out = build_setup_callouts([bear()], 0.1, 7)[0]
    assert bull_out["fill_from"] == bear_out["fill_from"] == "#4188FF"
    assert bull_out["fill_win"] == "#9FE2BF" and bull_out["fill_to"] == "#FF6200"
    assert bull_out["state"] == "running"
    assert bull_out["text_color"] == "#FFFFFF"
    assert bull_out["glow_color"] == "#1FE0A0" and bear_out["glow_color"] == "#FF3B3B"


def test_bad_tick_or_missing_candle_gives_nothing():
    assert build_setup_callouts([bull()], 0, 7) == []
    broken = bull()
    broken.c2 = None
    assert build_setup_callouts([broken], 0.1, 7) == []


def test_empty_input():
    assert build_setup_callouts([], 0.1, 7) == []
    assert build_setup_callouts(None, 0.1, 7) == []


def poi(poi_id, poi_type, source_tf="1m", chart_label="X"):
    return NS(poi_id=poi_id, poi_type=poi_type, source_tf=source_tf, chart_label=chart_label)


def test_poi_short_names_lines_zones_and_prefix():
    names = poi_short_names([
        poi("a", "PDH", "1D", "PDH"),
        poi("b", "FVG", "4H", "FVG"),
        poi("c", "ORDER_BLOCK", "1M", "OB"),
        poi("d", "INVERSE_FVG", "1m", "iFVG"),
        poi("e", "RESISTANCE_FLIP", "15m", "Resistance Flip"),
        poi("f", "4H_HIGH", "4H", "P4H H"),
    ])
    assert names["a"] == "PDH"
    assert names["b"] == "4H FVG"
    assert names["c"] == "1Mo OB"
    assert names["d"] == "1m iFVG"
    assert names["e"] == "15m R-Flip"
    assert names["f"] == "P4H H"


def test_poi_short_names_enum_independent_and_empty():
    from enum import Enum

    class Kind(str, Enum):
        FVG = "FVG"

    assert poi_short_names([poi("x", Kind.FVG, "1H")])["x"] == "1H FVG"
    assert poi_short_names([poi("i", "INDEPENDENT", "", "Custom")])["i"] == "IND"
    assert poi_short_names(None) == {}
    assert poi_short_names([poi("", "FVG")]) == {}


def test_callout_gets_poi_name_and_profit_dash():
    out = build_setup_callouts([bull()], 0.1, 7, {"p1": "4H FVG"})[0]
    assert out["poi_short"] == ""
    item = bull()
    item.poi_id = "p1"
    out = build_setup_callouts([item], 0.1, 7, {"p1": "4H FVG"})[0]
    assert out["poi_short"] == "4H FVG"
    assert out["profit_text"] == "\u2014"
