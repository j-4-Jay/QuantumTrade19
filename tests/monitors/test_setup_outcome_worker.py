"""PATH: tests/monitors/test_setup_outcome_worker.py  (NEW FILE)

FT-H.2 tests for engines/workers/setup/setup_outcome_worker.py, with made-up candles.
Bull example: entry 100, tick 0.5, buffer 4 ticks, lowest OHLC 98 -> SL 96, risk 4 (8 ticks).
Prices: 0.5R=102, 1R=104, 1.5R=106, 2R=108.
Bear example mirror: entry 100, highest OHLC 102 -> SL 104, risk 4. 1.5R price = 94.
"""
from types import SimpleNamespace

from engines.workers.setup.setup_outcome_worker import SetupOutcomeWorker
from engines.workers.setup.setup_types import ConfirmedSetup, SetupDirection

STEP_MS = 300_000


def candle(n, o, h, l, c, tf="5m", symbol="B-BTC_USDT"):
    open_time = n * STEP_MS
    return SimpleNamespace(
        symbol=symbol, timeframe=tf, open_time=open_time, close_time=open_time + STEP_MS - 1,
        open=o, high=h, low=l, close=c, volume=1.0, is_closed=True,
    )


def bull_setup(event_id="E1"):
    return ConfirmedSetup(
        event_id=event_id, symbol="B-BTC_USDT", timeframe="5m", poi_id="P1",
        direction=SetupDirection.BULL,
        c1=candle(1, 101, 102, 99, 100), c2=candle(2, 100, 101, 98, 99), c3=candle(3, 99, 101, 98.5, 100),
        confirmed_at=0.0,
    )


def bear_setup(event_id="E2"):
    return ConfirmedSetup(
        event_id=event_id, symbol="B-BTC_USDT", timeframe="5m", poi_id="P2",
        direction=SetupDirection.BEAR,
        c1=candle(1, 99, 101, 98, 100), c2=candle(2, 100, 102, 99, 101), c3=candle(3, 101, 101.5, 99, 100),
        confirmed_at=0.0,
    )


def new_bull(buffer_ticks=4):
    w = SetupOutcomeWorker()
    o = w.track(bull_setup(), tick_size=0.5, buffer_ticks=buffer_ticks)
    return w, o


def new_bear(buffer_ticks=4):
    w = SetupOutcomeWorker()
    o = w.track(bear_setup(), tick_size=0.5, buffer_ticks=buffer_ticks)
    return w, o


def test_bull_entry_sl_risk():
    w, o = new_bull()
    assert (o.entry, o.sl, o.risk, o.risk_ticks, o.win_price) == (100, 96, 4, 8, 106)
    assert o.status == "OPEN" and not o.win_reached


def test_bear_entry_sl_risk():
    w, o = new_bear()
    assert (o.entry, o.sl, o.risk, o.risk_ticks, o.win_price) == (100, 104, 4, 8, 94)


def test_default_buffer_is_seven_ticks():
    w = SetupOutcomeWorker()
    o = w.track(bull_setup(), tick_size=0.5)
    assert o.sl == 98 - 3.5


def test_bull_sl_hit_by_wick_only():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 101, 96, 100))
    assert o.status == "SL_HIT"
    assert o.sl_time == 4 * STEP_MS
    assert o.max_adverse_r == 1.0
    assert w.open_count() == 0


def test_bull_one_tick_above_sl_stays_open():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 101, 96.5, 100))
    assert o.status == "OPEN"
    assert o.max_adverse_r == 0.875


def test_bear_sl_hit_by_wick_only():
    w, o = new_bear()
    w.on_candle_closed(candle(4, 100, 104, 99, 100))
    assert o.status == "SL_HIT" and o.sl_time == 4 * STEP_MS


def test_bear_one_tick_below_sl_stays_open():
    w, o = new_bear()
    w.on_candle_closed(candle(4, 100, 103.5, 99, 100))
    assert o.status == "OPEN"


def test_bull_full_win_flow_levels_peak_and_close():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 103, 99.5, 102))
    assert o.status == "OPEN" and not o.win_reached
    assert o.peak_rrr == 0.75 and o.level_times == {0.5: 4 * STEP_MS}
    assert o.max_adverse_r == 0.125

    w.on_candle_closed(candle(5, 102, 107, 101, 106))
    assert o.win_reached and o.status == "OPEN"
    assert o.win_time == 5 * STEP_MS
    assert o.peak_rrr == 1.75
    assert o.level_times == {0.5: 4 * STEP_MS, 1.0: 5 * STEP_MS, 1.5: 5 * STEP_MS}

    w.on_candle_closed(candle(6, 107, 109, 107, 108))
    assert o.status == "OPEN" and o.peak_rrr == 2.25
    assert o.level_times[2.0] == 6 * STEP_MS

    w.on_candle_closed(candle(7, 108, 110, 105.9, 106))
    assert o.status == "WIN"
    assert o.peak_rrr == 2.25
    assert o.close_time == 7 * STEP_MS + STEP_MS - 1
    assert o.sl_time is None
    assert w.open_count() == 0


def test_bear_full_win_flow():
    w, o = new_bear()
    w.on_candle_closed(candle(4, 100, 100.5, 98, 99))
    assert o.level_times == {0.5: 4 * STEP_MS} and o.max_adverse_r == 0.125
    w.on_candle_closed(candle(5, 99, 99, 93, 94))
    assert o.win_reached and o.status == "OPEN" and o.peak_rrr == 1.75
    w.on_candle_closed(candle(6, 92, 92, 91, 91))
    assert o.status == "OPEN" and o.peak_rrr == 2.25
    w.on_candle_closed(candle(7, 91, 94.1, 90, 94))
    assert o.status == "WIN" and o.peak_rrr == 2.25


def test_same_candle_touching_sl_and_target_counts_sl_first():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 107, 96, 100))
    assert o.status == "SL_HIT"
    assert not o.win_reached
    assert o.level_times == {} and o.peak_rrr == 0.0


def test_candle_reaching_target_does_not_close_the_trade():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 107, 105, 106))
    assert o.win_reached and o.status == "OPEN"
    w.on_candle_closed(candle(5, 106, 107, 105.5, 106))
    assert o.status == "WIN"


def test_sl_is_ignored_after_target_was_reached():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 107, 105, 106))
    w.on_candle_closed(candle(5, 106, 106, 95, 96))
    assert o.status == "WIN" and o.sl_time is None


def test_adverse_dip_is_the_deepest_before_resolution():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 101, 97, 100))
    w.on_candle_closed(candle(5, 100, 101, 98, 100))
    assert o.max_adverse_r == 0.75


def test_other_symbol_or_timeframe_is_ignored():
    w, o = new_bull()
    assert w.on_candle_closed(candle(4, 100, 101, 90, 100, tf="15m")) == []
    assert w.on_candle_closed(candle(4, 100, 101, 90, 100, symbol="B-ETH_USDT")) == []
    assert o.status == "OPEN"


def test_old_and_repeated_candles_are_ignored():
    w, o = new_bull()
    w.on_candle_closed(candle(3, 100, 101, 90, 100))
    assert o.status == "OPEN"
    w.on_candle_closed(candle(4, 100, 103, 100, 102))
    before = dict(o.level_times)
    assert w.on_candle_closed(candle(4, 100, 110, 100, 102)) == []
    assert o.level_times == before


def test_closed_outcome_does_not_change_any_more():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 101, 96, 100))
    assert w.on_candle_closed(candle(5, 100, 120, 100, 119)) == []
    assert o.status == "SL_HIT" and o.peak_rrr == 0.0


def test_same_event_id_is_tracked_once():
    w = SetupOutcomeWorker()
    first = w.track(bull_setup("X"), tick_size=0.5, buffer_ticks=4)
    again = w.track(bull_setup("X"), tick_size=0.5, buffer_ticks=4)
    assert first is again and len(w.all_outcomes()) == 1


def test_zero_risk_or_bad_tick_is_not_tracked():
    flat = ConfirmedSetup(
        event_id="Z", symbol="B-BTC_USDT", timeframe="5m", poi_id="P",
        direction=SetupDirection.BULL,
        c1=candle(1, 100, 100, 100, 100), c2=candle(2, 100, 100, 100, 100), c3=candle(3, 100, 100, 100, 100),
        confirmed_at=0.0,
    )
    w = SetupOutcomeWorker()
    assert w.track(flat, tick_size=0.5, buffer_ticks=0) is None
    assert w.track(bull_setup("T"), tick_size=0, buffer_ticks=4) is None
    assert w.all_outcomes() == []


def test_to_dict_has_text_keys_and_filters_work():
    w, o = new_bull()
    w.on_candle_closed(candle(4, 100, 103, 99.5, 102))
    d = o.to_dict()
    assert d["level_times"] == {"0.5": 4 * STEP_MS}
    assert d["direction"] == "123Bull" and d["status"] == "OPEN"
    assert len(w.all_outcomes(symbol="B-BTC_USDT", timeframe="5m")) == 1
    assert w.all_outcomes(timeframe="1m") == []
