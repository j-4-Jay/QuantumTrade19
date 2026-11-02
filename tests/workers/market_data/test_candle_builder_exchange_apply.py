"""
FULL PATH: tests/workers/market_data/test_candle_builder_exchange_apply.py
Tests for CandleBuilderWorker.apply_exchange_candles (no network).
"""
from engines.workers.market_data.candle_builder_worker import Candle, CandleBuilderWorker, _TF_MS
from engines.workers.market_data.tick_normalizer_worker import NormalizedTick

SYM = "B-XAU_USDT"
STEP = _TF_MS["1m"]
T0 = 1_700_000_040_000 - (1_700_000_040_000 % STEP)


def cd(i, o, h, l, c, v=10.0, closed=True):
    t = T0 + i * STEP
    return Candle(SYM, "1m", t, t + STEP - 1, o, h, l, c, v, closed)


def tick(i, price, vol, sec=5):
    t = T0 + i * STEP + sec * 1000
    return NormalizedTick(SYM, price, vol, t, t, "ws")


def test_forming_candle_replaced_and_volume_locked():
    b = CandleBuilderWorker()
    b.ingest(tick(0, 100.0, 5_000_000_000.0), ["1m"])
    now = T0 + 20_000
    b.apply_exchange_candles(SYM, "1m", [cd(0, 100.0, 101.0, 99.0, 100.5, 7.0, False)], now)
    live = b.get_live_candle(SYM, "1m")
    assert (live.open, live.high, live.low, live.close, live.volume) == (100.0, 101.0, 99.0, 100.5, 7.0)
    b.ingest(tick(0, 100.2, 5_000_000_100.0, sec=25), ["1m"])
    live = b.get_live_candle(SYM, "1m")
    assert live.volume == 7.0
    assert live.close == 100.2


def test_closed_candle_corrected_without_new_close_callback():
    closed = []
    b = CandleBuilderWorker(on_candle_closed=closed.append)
    b.ingest(tick(0, 100.0, 1.0), ["1m"])
    b.ingest(tick(1, 100.5, 1.0), ["1m"])
    assert len(closed) == 1
    now = T0 + 2 * STEP + 5_000
    out = b.apply_exchange_candles(SYM, "1m", [cd(0, 100.0, 100.4, 99.9, 100.3, 12.0)], now)
    assert len(out) == 1 and out[0].close == 100.3 and out[0].volume == 12.0
    series = b.get_series(SYM, "1m")
    assert series[0].close == 100.3
    assert len(closed) == 1
    again = b.apply_exchange_candles(SYM, "1m", [cd(0, 100.0, 100.4, 99.9, 100.3, 12.0)], now)
    assert again == []


def test_gap_is_filled_in_order():
    b = CandleBuilderWorker()
    b.seed_historical(SYM, "1m", [cd(0, 1, 2, 0.5, 1.5), cd(3, 3, 4, 2.5, 3.5), cd(4, 4, 5, 3, 4, closed=False)])
    now = T0 + 4 * STEP + 10_000
    out = b.apply_exchange_candles(SYM, "1m", [cd(1, 1.5, 2, 1, 1.8), cd(2, 1.8, 3, 1.7, 3)], now)
    assert [c.open_time for c in out] == [T0 + STEP, T0 + 2 * STEP]
    times = [c.open_time for c in b.get_series(SYM, "1m")]
    assert times == sorted(times) and len(times) == len(set(times)) == 5


def test_missed_rollover_closes_once_and_publishes_once():
    closed = []
    b = CandleBuilderWorker(on_candle_closed=closed.append)
    b.ingest(tick(0, 100.0, 1.0), ["1m"])
    now = T0 + STEP + 8_000
    batch = [cd(0, 100.0, 101.0, 99.5, 100.8, 30.0), cd(1, 100.8, 100.9, 100.7, 100.8, 2.0, False)]
    out = b.apply_exchange_candles(SYM, "1m", batch, now)
    assert len(closed) == 1 and closed[0].close == 100.8 and closed[0].is_closed
    assert any(c.open_time == T0 for c in out)
    live = b.get_live_candle(SYM, "1m")
    assert live.open_time == T0 + STEP
    b.apply_exchange_candles(SYM, "1m", batch, now)
    assert len(closed) == 1
    times = [c.open_time for c in b.get_series(SYM, "1m")]
    assert len(times) == len(set(times)) == 2
