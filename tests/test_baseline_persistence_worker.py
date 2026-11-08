"""Baseline missing-row persistence: real temporary SQLite, no network."""
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import threading
import pytest
from engines.workers.market_data.baseline_persistence_worker import persist_missing_baseline


class Store:
    def __init__(self, path):
        self.db_path = path
        self.lock = threading.RLock()
        with sqlite3.connect(path) as con:
            con.execute("CREATE TABLE candles (symbol TEXT, timeframe TEXT, open_time INTEGER, close REAL, PRIMARY KEY(symbol,timeframe,open_time))")
    def get_all_timestamps(self, sym, tf):
        with sqlite3.connect(self.db_path) as con:
            return [r[0] for r in con.execute("SELECT open_time FROM candles WHERE symbol=? AND timeframe=?", (sym,tf))]
    def save_candles(self, sym, tf, candles):
        with sqlite3.connect(self.db_path) as con:
            con.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?)", [(sym,tf,c.open_time,c.close) for c in candles])
        return len(candles)


def c(t, value=1):
    return SimpleNamespace(open_time=t, close=value)


def test_closed_saved_forming_excluded(tmp_path):
    s = Store(tmp_path / "a.db")
    assert persist_missing_baseline(s,"ETH",{"1m":[c(0),c(60000)]},60000,tmp_path/"backup") == {"1m":1}
    assert s.get_all_timestamps("ETH","1m") == [0]


def test_existing_value_is_preserved(tmp_path):
    s = Store(tmp_path / "a.db")
    s.save_candles("ETH","1m",[c(0,99)])
    persist_missing_baseline(s,"ETH",{"1m":[c(0),c(60000)]},120000,tmp_path/"backup")
    with sqlite3.connect(s.db_path) as con:
        assert con.execute("SELECT close FROM candles WHERE open_time=0").fetchone()[0] == 99


def test_backup_precedes_fill_and_is_reused(tmp_path):
    s = Store(tmp_path / "a.db")
    persist_missing_baseline(s,"ETH",{"1m":[c(0)]},60000,tmp_path/"backup")
    with sqlite3.connect(s._baseline_backup_path) as con:
        assert con.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 0
    persist_missing_baseline(s,"BTC",{"1m":[c(0)]},60000,tmp_path/"backup")
    assert len(list((tmp_path/"backup").glob("*.db"))) == 1


def test_partial_15m_is_not_saved(tmp_path):
    s = Store(tmp_path / "a.db")
    counts = persist_missing_baseline(s,"ETH",{"5m":[c(300000),c(600000)],"15m":[c(0)]},900000,tmp_path/"backup")
    assert counts["15m"] == 0


def test_complete_15m_is_saved_and_unaligned_rejected(tmp_path):
    s = Store(tmp_path / "a.db")
    counts = persist_missing_baseline(s,"ETH",{"5m":[c(0),c(300000),c(600000)],"15m":[c(0)],"1m":[c(1)]},900000,tmp_path/"backup")
    assert counts["15m"] == 1
    assert counts["1m"] == 0


def test_backup_failure_prevents_writes(tmp_path):
    s = Store(tmp_path / "a.db")
    blocked = tmp_path / "not_a_directory"
    blocked.write_text("x")
    with pytest.raises(OSError):
        persist_missing_baseline(s,"ETH",{"1m":[c(0)]},60000,blocked)
    assert s.get_all_timestamps("ETH","1m") == []

