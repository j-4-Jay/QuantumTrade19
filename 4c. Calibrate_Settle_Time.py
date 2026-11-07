"""4c. Calibrate_Settle_Time.py - FT-H.37 read-only calibration (QT19).
Run from the project folder while the app is running.
For each closed 1m candle it polls once a second, from the close to +20 s:
  - our saved candle (data/historical_candles.db)
  - the CoinDCX public candle
It finds the SETTLE TIME: the first second after which our candle equals the
CoinDCX candle (open, high, low, close, volume) on every later poll.
It only READS. It never writes to the database and never places orders.
Usage: python "4c. Calibrate_Settle_Time.py" B-ETH_USDT 20
Report: Debug/settle_<pair>_<time>.txt and .csv
"""
import sqlite3
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PAIR = sys.argv[1] if len(sys.argv) > 1 else "B-ETH_USDT"
CANDLES = int(sys.argv[2]) if len(sys.argv) > 2 else 20
WINDOW_S = 20
DB = ROOT / "data" / "historical_candles.db"


def same(a, b):
    if not isinstance(a, tuple) or not isinstance(b, tuple):
        return False
    return all(abs(x - y) < 1e-6 for x, y in zip(a, b))


def settle_time(polls):
    """polls: list of (offset_seconds, matched_bool). Returns offset or None."""
    if not polls or not polls[-1][1]:
        return None
    first = polls[-1][0]
    for off, ok in reversed(polls):
        if not ok:
            break
        first = off
    return first


def main():
    from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker
    loader = HistoricalDataLoaderWorker(rate_limit_sleep_s=0.0)
    stamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    out_txt = ROOT / "Debug" / ("settle_%s_%s.txt" % (PAIR, stamp))
    out_csv = ROOT / "Debug" / ("settle_%s_%s.csv" % (PAIR, stamp))
    out_txt.parent.mkdir(exist_ok=True)

    def say(text):
        print(text)
        with open(out_txt, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def read_db(open_ms):
        try:
            con = sqlite3.connect("file:%s?mode=ro" % DB.as_posix(), uri=True, timeout=5)
            try:
                return con.execute(
                    "SELECT open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe='1m' AND open_time=?",
                    (PAIR, open_ms)).fetchone()
            finally:
                con.close()
        except Exception:
            return None

    def read_exchange(open_ms):
        try:
            for c in loader.fetch_range(PAIR, "1m", open_ms - 60000, open_ms + 120000):
                if c.open_time == open_ms:
                    return (c.open, c.high, c.low, c.close, c.volume)
        except Exception:
            return None
        return None

    with open(out_csv, "w", encoding="utf-8") as f:
        f.write("candle_open,settle_seconds,volume_db_at_first_poll,volume_exchange_final,note\n")
    say("FT-H.37 settle-time calibration | %s | %d candles | started %s" % (PAIR, CANDLES, datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")))
    say("Each candle is polled every second for %d s after its close. Leave the app running." % WINDOW_S)
    results = []
    for n in range(CANDLES):
        boundary = (int(time.time() // 60) + 1) * 60
        open_ms = (boundary - 60) * 1000
        delay = boundary - time.time()
        if delay > 0:
            time.sleep(delay)
        polls, first_db_vol, last_ex = [], None, None
        t = 0.0
        while t <= WINDOW_S:
            wait = boundary + t - time.time()
            if wait > 0:
                time.sleep(wait)
            off = round(time.time() - boundary, 1)
            ex = read_exchange(open_ms)
            db = read_db(open_ms)
            if first_db_vol is None and db is not None:
                first_db_vol = db[4]
            if ex is not None:
                last_ex = ex
            polls.append((off, same(db, ex)))
            t += 1.0
        s = settle_time(polls)
        label = datetime.fromtimestamp(open_ms / 1000).strftime("%I:%M %p")
        note = "" if s is not None else "NOT SETTLED within %d s" % WINDOW_S
        say("Candle %2d/%d %s : settled at %s" % (n + 1, CANDLES, label, ("+%.1f s" % s) if s is not None else note))
        with open(out_csv, "a", encoding="utf-8") as f:
            f.write("%s,%s,%s,%s,%s\n" % (label, "" if s is None else s, first_db_vol, last_ex[4] if last_ex else "", note))
        results.append(s)
    ok = [r for r in results if r is not None]
    say("")
    say("SUMMARY for %d candles" % len(results))
    say("  settled: %d | not settled: %d" % (len(ok), len(results) - len(ok)))
    if ok:
        say("  fastest %.1f s | median %.1f s | slowest %.1f s" % (min(ok), statistics.median(ok), max(ok)))
        say("  Safe wait for this sample = slowest + 2 s = %.1f s" % (max(ok) + 2))
    say("Reports: %s and %s" % (out_txt, out_csv))


if __name__ == "__main__":
    main()
