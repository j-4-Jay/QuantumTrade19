"""
FULL PATH: tests/monitors/test_setup_callout_outcomes.py
FT-H.7: callouts take state, fade, LIVE and PEAK from the outcome worker.
"""
from types import SimpleNamespace

from engines.workers.setup.setup_callout_helper import build_setup_callouts
from engines.workers.setup.setup_outcome_worker import SetupOutcomeWorker
from engines.workers.setup.setup_types import SetupDirection

TICK = 0.1


def _candle(o, h, l, c, t=0, symbol="B-XAU_USDT", tf="5m"):
    return SimpleNamespace(
        symbol=symbol, timeframe=tf, open=o, high=h, low=l, close=c,
        open_time=t, close_time=t + 299_999,
    )


def _bull():
    c1 = _candle(101.0, 102.0, 100.0, 101.5, 0)
    c2 = _candle(101.5, 103.0, 101.0, 102.5, 300_000)
    c3 = _candle(102.5, 103.5, 101.8, 102.0, 600_000)
    return SimpleNamespace(
        event_id="E1", symbol="B-XAU_USDT", timeframe="5m", direction=SetupDirection.BULL,
        c1=c1, c2=c2, c3=c3,
    )


def _bear():
    c1 = _candle(101.0, 102.0, 100.0, 100.5, 0)
    c2 = _candle(100.5, 101.0, 99.0, 99.5, 300_000)
    c3 = _candle(99.5, 100.2, 98.5, 99.0, 600_000)
    return SimpleNamespace(
        event_id="E2", symbol="B-XAU_USDT", timeframe="5m", direction=SetupDirection.BEAR,
        c1=c1, c2=c2, c3=c3,
    )


def _worker_with(setup):
    w = SetupOutcomeWorker()
    w.track(setup, TICK, 7)
    return w


def _outcomes(w):
    return {o.event_id: o for o in w.all_outcomes()}


def test_without_outcomes_nothing_changes():
    co = build_setup_callouts([_bull()], TICK, 7)[0]
    assert co["state"] == "running"
    assert co["fade"] == 0.0
    assert co["live_text"] == co["peak_text"] == "\u2014"


def test_running_bull_fades_toward_sl_with_live_price():
    s = _bull()
    w = _worker_with(s)
    co = build_setup_callouts([s], TICK, 7, _outcomes(w), 101.0)[0]
    risk = 102.0 - (100.0 - 0.7)
    assert co["state"] == "running"
    assert co["fade"] == round((102.0 - 101.0) / risk, 2)
    assert co["live_text"] == f"{-(102.0 - 101.0) / risk:+.2f}R"
    assert co["peak_text"] == "0.00R"


def test_running_bull_price_above_entry_has_no_fade():
    s = _bull()
    w = _worker_with(s)
    co = build_setup_callouts([s], TICK, 7, _outcomes(w), 103.0)[0]
    assert co["fade"] == 0.0
    assert co["live_text"].startswith("+")
    assert co["peak_text"] == co["live_text"].lstrip("+")


def test_sl_hit_state():
    s = _bull()
    w = _worker_with(s)
    w.on_candle_closed(_candle(102.0, 102.2, 99.0, 99.5, 900_000))
    co = build_setup_callouts([s], TICK, 7, _outcomes(w), 99.5)[0]
    assert co["state"] == "sl_hit"
    assert co["fade"] == 1.0
    assert co["live_text"] == "-1.00R"


def test_win_reached_but_trade_still_open_shows_win_and_live_price():
    s = _bull()
    w = _worker_with(s)
    risk = 102.0 - 99.3
    w.on_candle_closed(_candle(102.0, 102.0 + 1.6 * risk, 101.9, 106.0, 900_000))
    co = build_setup_callouts([s], TICK, 7, _outcomes(w), 105.0)[0]
    assert co["state"] == "win"
    assert co["fade"] == 0.0
    assert co["live_text"] == f"{(105.0 - 102.0) / risk:+.2f}R"
    assert co["peak_text"] == "1.60R"


def test_closed_win_shows_fixed_live_and_peak():
    s = _bull()
    w = _worker_with(s)
    risk = 102.0 - 99.3
    w.on_candle_closed(_candle(102.0, 102.0 + 1.6 * risk, 101.9, 106.0, 900_000))
    w.on_candle_closed(_candle(106.0, 106.1, 101.0, 102.5, 1_200_000))
    co = build_setup_callouts([s], TICK, 7, _outcomes(w), 102.5)[0]
    assert co["state"] == "win"
    assert co["live_text"] == "+1.50R"
    assert co["peak_text"] == "1.60R"


def test_bear_running_fade_uses_price_above_entry():
    s = _bear()
    w = _worker_with(s)
    co = build_setup_callouts([s], TICK, 7, _outcomes(w), 99.5)[0]
    risk = (102.0 + 0.7) - 99.0
    assert co["state"] == "running"
    assert co["fade"] == round(0.5 / risk, 2)
    assert co["live_text"] == f"{-0.5 / risk:+.2f}R"


def test_unknown_event_keeps_defaults():
    s = _bull()
    other = {"OTHER": object()}
    co = build_setup_callouts([s], TICK, 7, other, 101.0)[0]
    assert co["state"] == "running" and co["live_text"] == "\u2014"


def test_no_live_price_keeps_live_text_dash():
    s = _bull()
    w = _worker_with(s)
    co = build_setup_callouts([s], TICK, 7, _outcomes(w), None)[0]
    assert co["live_text"] == "\u2014"
    assert co["fade"] == 0.0
