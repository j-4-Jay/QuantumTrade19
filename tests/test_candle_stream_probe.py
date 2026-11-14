"""Tests for 4c. Probe_Candle_Stream.py (pure logic only; no network)."""
import importlib.util
import json
from pathlib import Path

PROBE = Path(__file__).resolve().parents[1] / "4c. Probe_Candle_Stream.py"
spec = importlib.util.spec_from_file_location("probe", PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

M = 60_000
BASE = 1_700_000_100_000  # multiple of 5 minutes


def test_extract_candle_variants_and_nested_json_string():
    p = {"data": json.dumps({"o": "1", "h": "3", "l": "0.5", "c": "2", "v": "10", "i": "1m", "t": BASE + 5})}
    c = probe.extract_candles(p)
    assert len(c) == 1 and c[0]["tf"] == "1m" and c[0]["open_time"] == BASE
    q = probe.extract_candles([{"open": 1, "high": 2, "low": 1, "close": 2, "interval": "5m", "T": BASE + 299_999}])
    assert q[0]["open_time"] == BASE


def test_seconds_timestamps_are_converted():
    assert probe.to_ms(1_700_000_100) == 1_700_000_100_000
    assert probe.to_ms(BASE) == BASE
    assert probe.to_ms("bad") is None


def test_unknown_interval_not_usable_and_no_guess():
    c = probe.extract_candles({"o": 1, "h": 1, "l": 1, "c": 1, "t": BASE})
    assert c[0]["tf"] is None and c[0]["open_time"] is None


def test_trade_extract():
    t = probe.extract_trades({"data": [{"p": "10", "q": "2", "T": BASE}]})
    assert t == [{"p": 10.0, "q": 2.0, "T": BASE}]


def test_snapshot_uses_only_updates_before_offset():
    ups = [{"recv": 100, "c": 1}, {"recv": 1100, "c": 2}, {"recv": 5000, "c": 3}]
    assert probe.snapshot_at(ups, 0, 0) is None
    assert probe.snapshot_at(ups, 0, 100)["c"] == 1
    assert probe.snapshot_at(ups, 1000, 0)["c"] == 1
    assert probe.snapshot_at(ups, 1000, 3000)["c"] == 2
    assert probe.snapshot_at(ups, 1000, 10_000)["c"] == 3


def test_trade_candle_and_compare():
    trades = [{"p": 5, "q": 1, "T": BASE + 10}, {"p": 7, "q": 2, "T": BASE + 20}, {"p": 4, "q": 1, "T": BASE + 30}]
    recv = [BASE + 11, BASE + 21, BASE + M + 90_000]
    c = probe.build_trade_candle(trades, BASE, "1m", BASE + M, 0, recv)
    assert c == {"o": 5, "h": 7, "l": 5, "c": 7, "v": 3}
    ref = {"o": 5, "h": 7, "l": 5, "c": 7, "v": 3}
    assert probe.compare_ohlcv(c, ref) == {"present": True, "ohlc": True, "volume": True}
    assert probe.compare_ohlcv(None, ref)["present"] is False


def test_summarize_reports_delay_and_accuracy():
    ref = {"1m": {BASE: {"o": 1, "h": 2, "l": 1, "c": 2, "v": 10}}, "5m": {}}
    b = BASE + M
    rows = [
        {"recv": b - 5000, "event": "candlestick", "payload": {"o": 1, "h": 2, "l": 1, "c": 1.5, "v": 8, "i": "1m", "t": BASE}},
        {"recv": b + 500, "event": "candlestick", "payload": {"o": 1, "h": 2, "l": 1, "c": 2, "v": 10, "i": "1m", "t": BASE}},
        {"recv": b + 20_000, "event": "candlestick", "payload": {"o": 2, "h": 2, "l": 2, "c": 2, "v": 1, "i": "1m", "t": b}},
        {"recv": b + 30, "event": "candlestick", "payload": {"junk": 1}},
    ]
    s = probe.summarize(rows, ref)
    tf = s["timeframes"]["1m"]
    assert s["unparsed_candle_messages"] == 1
    assert tf["candles_compared"] == 1
    assert tf["last_update_after_close_ms"]["max"] == 500
    a = tf["accuracy_by_offset"]
    assert a["+0ms"]["stream"]["ohlc"] == 0
    assert a["+1000ms"]["stream"]["ohlc"] == 1 and a["+1000ms"]["stream"]["volume"] == 1


def test_channel_list():
    assert probe.channel_list("B-ETH_USDT", False) == [
        "B-ETH_USDT_1m-futures", "B-ETH_USDT_5m-futures", "B-ETH_USDT@trades-futures"]
    assert len(probe.channel_list("B-ETH_USDT", True)) == 5


def test_probe_is_read_only_by_source():
    src = PROBE.read_text(encoding="utf-8").lower()
    for banned in ("save_candles", "sqlite3", "candle_builder_worker", "delayed_dispatch", "api_key", "place_order"):
        assert banned not in src, banned


def test_recorder_writes_jsonl(tmp_path):
    r = probe.Recorder(tmp_path / "x.jsonl")
    r.write("candlestick", {"a": 1})
    r.close()
    rows = probe.load_records(tmp_path / "x.jsonl")
    assert rows[0]["event"] == "candlestick" and rows[0]["payload"] == {"a": 1}


REAL_1M = {"data": [{"open": "2078.94", "close": "2078.94", "high": "2079.35", "low": "2078.94", "volume": "125.535",
                     "open_time": 1794432060, "close_time": 1794432119.999, "pair": "B-ETH_USDT", "duration": "1m",
                     "symbol": "ETHUSDT", "quote_volume": "261008.15521"}],
           "ecode": "B", "Ets": 1794432072644, "pts": 1794432072719, "i": "1m",
           "channel": "B-ETH_USDT_1m-futures", "pr": "futures"}
REAL_5M = {"data": [{"open": "2079.51", "close": "2078.94", "high": "2079.57", "low": "2078.72", "volume": "575.968",
                     "open_time": 1794432000, "close_time": 1794432299.999, "duration": "5m"}],
           "ecode": "B", "Ets": 1794432072644, "i": "5m"}
REAL_TRADE = {"T": 1794432072643, "RT": 1794432116963.7285, "p": "2078.94", "q": "0.051", "m": 1,
              "s": "B-ETH_USDT", "pr": "f"}


def test_real_coindcx_candlestick_shape_parses():
    c = probe.extract_candles(REAL_1M)
    assert len(c) == 1 and c[0]["tf"] == "1m" and c[0]["open_time"] == 1794432060000
    assert c[0]["c"] == 2078.94 and c[0]["v"] == 125.535
    d = probe.extract_candles(REAL_5M)
    assert d[0]["tf"] == "5m" and d[0]["open_time"] == 1794432000000


def test_real_trade_shape_and_not_mistaken_for_candle():
    t = probe.extract_trades(REAL_TRADE)
    assert len(t) == 1 and t[0]["q"] == 0.051 and t[0]["T"] == 1794432072643
    assert probe.extract_candles(REAL_TRADE) == []
    assert probe.extract_trades(REAL_1M) == []


def test_summarize_reports_clock_offset():
    rows = [{"recv": 1794432072358, "event": "candlestick", "payload": REAL_1M},
            {"recv": 1794432072497, "event": "new-trade", "payload": REAL_TRADE}]
    s = probe.summarize(rows, {"1m": {}, "5m": {}})
    off = s["local_minus_exchange_ms"]
    assert off["candle_Ets_median"] == -286 and off["trade_T_median"] == -146
    assert s["unparsed_candle_messages"] == 0
