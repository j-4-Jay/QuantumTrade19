"""FT-H.39 candle popup server side: database read and exchange pick."""
import sqlite3
import types

from state.app_state_mixins import candle_popup_mixin as m


def _make_db(path):
    con = sqlite3.connect(str(path))
    con.execute(
        "CREATE TABLE candles (symbol TEXT, timeframe TEXT, open_time INTEGER, close_time INTEGER, "
        "open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (symbol, timeframe, open_time))"
    )
    con.execute("INSERT INTO candles VALUES ('B-ETH_USDT','1m',1000,1999,1.0,2.0,0.5,1.5,308.652)")
    con.commit()
    con.close()


def test_read_db_candle_returns_the_row(tmp_path):
    db = tmp_path / "c.db"
    _make_db(db)
    assert m.read_db_candle("B-ETH_USDT", "1m", 1000, db) == {
        "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 308.652}


def test_read_db_candle_none_when_no_row(tmp_path):
    db = tmp_path / "c.db"
    _make_db(db)
    assert m.read_db_candle("B-ETH_USDT", "1m", 61000, db) is None


def test_read_db_candle_none_when_file_missing(tmp_path):
    assert m.read_db_candle("B-ETH_USDT", "1m", 1000, tmp_path / "nope.db") is None


def test_read_db_candle_never_writes(tmp_path):
    db = tmp_path / "c.db"
    _make_db(db)
    before = db.read_bytes()
    m.read_db_candle("B-ETH_USDT", "1m", 1000, db)
    assert db.read_bytes() == before


def test_fetch_exchange_candle_picks_the_matching_open_time(monkeypatch):
    from engines.workers.market_data import historical_data_loader_worker as h

    def c(t, v):
        return types.SimpleNamespace(open_time=t, open=1, high=2, low=0.5, close=1.5, volume=v)

    class Fake:
        def __init__(self, *a, **k):
            pass

        def fetch_range(self, pair, tf, start, end):
            return [c(0, 1.0), c(60000, 211.154), c(120000, 3.0)]

    monkeypatch.setattr(h, "HistoricalDataLoaderWorker", Fake)
    assert m.fetch_exchange_candle("B-ETH_USDT", "1m", 60000)["volume"] == 211.154
    assert m.fetch_exchange_candle("B-ETH_USDT", "1m", 180000) is None
