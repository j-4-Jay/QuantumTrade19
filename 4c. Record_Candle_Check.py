"""4c. Record_Candle_Check.py - FT-H.37 read-only recorder (QT19).
Run from the project folder while the app is running.
For 3 closed ETH 1m candles it records, at 1 s, 10 s, 30 s and 55 s after the close:
  - the candle saved in our database (data/historical_candles.db)
  - the candle from the CoinDCX public candle feed
It only READS. It never writes to the database and never places orders.
Report: Debug/candle_check_<pair>_<time>.txt
"""
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker  # noqa: E402

PAIR = sys.argv[1] if len(sys.argv) > 1 else "B-ETH_USDT"
CANDLES = int(sys.argv[2]) if len(sys.argv) > 2 else 3
OFFSETS = (1, 10, 30, 55)
DB = ROOT / "data" / "historical_candles.db"
OUT = ROOT / "Debug" / ("candle_check_%s_%s.txt" % (PAIR, datetime.now().strftime("%d-%m-%Y_%H-%M-%S")))
OUT.parent.mkdir(exist_ok=True)
loader = HistoricalDataLoaderWorker(rate_limit_sleep_s=0.1)


def say(text):
    print(text)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def hhmm(ms):
    return datetime.fromtimestamp(ms / 1000).strftime("%I:%M %p")


def read_db(open_ms):
    try:
        con = sqlite3.connect("file:%s?mode=ro" % DB.as_posix(), uri=True, timeout=5)
        try:
            row = con.execute(
                "SELECT open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe='1m' AND open_time=?",
                (PAIR, open_ms)).fetchone()
        finally:
            con.close()
        return row
    except Exception as exc:
        return "DB error: %s" % exc


def read_exchange(open_ms):
    try:
        for c in loader.fetch_range(PAIR, "1m", open_ms - 60000, open_ms + 120000):
            if c.open_time == open_ms:
                return (c.open, c.high, c.low, c.close, c.volume)
        return None
    except Exception as exc:
        return "feed error: %s" % exc


def fmt(r):
    if r is None:
        return "not found"
    if isinstance(r, str):
        return r
    return "O %s  H %s  L %s  C %s  V %s" % r


say("FT-H.37 candle check | pair %s | candles %d | started %s" % (PAIR, CANDLES, datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")))
say("Times are this computer's clock. Take your chart screenshot at the +30s line.")
for n in range(CANDLES):
    boundary = (int(time.time() // 60) + 1) * 60
    open_ms = (boundary - 60) * 1000
    say("")
    say("Candle %d of %d: opens %s, closes at %s" % (n + 1, CANDLES, hhmm(open_ms), hhmm(boundary * 1000)))
    for off in OFFSETS:
        wait = boundary + off - time.time()
        if wait > 0:
            time.sleep(wait)
        stamp = datetime.now().strftime("%I:%M:%S %p")
        say("  +%2ds (%s)" % (off, stamp))
        say("     OUR DB   : " + fmt(read_db(open_ms)))
        say("     COINDCX  : " + fmt(read_exchange(open_ms)))
say("")
say("Done. Report saved: %s" % OUT)
