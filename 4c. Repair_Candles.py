"""FT-H.23 - Repair old stored candles from the exchange (QT19).

REPORT mode (default): reads the database and the exchange, writes NOTHING to the
database, and saves a report in Debug/candle_repair_report_*.txt.
WRITE mode (--write): makes a backup copy of the database first, asks you to type
YES, then writes only closed exchange candles that are missing or different.
It never deletes rows. It never places orders and never touches broker keys.
Stop the app before WRITE mode.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engines.workers.market_data.candle_store_worker import CandleStoreWorker, TF_MS, DB_PATH
from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker

SETTLE_MS = 20_000
TIMEFRAMES = ("1m", "5m", "15m")


def fmt(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%d-%m-%Y %H:%M UTC")


def _close(a, b, rel):
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-12)


def same_candle(a, b):
    return (
        _close(a.open, b.open, 1e-9) and _close(a.high, b.high, 1e-9)
        and _close(a.low, b.low, 1e-9) and _close(a.close, b.close, 1e-9)
        and _close(a.volume, b.volume, 1e-6)
    )


def compare(stored, exchange):
    """stored and exchange are lists of candles. Returns (missing, different)."""
    have = {c.open_time: c for c in stored}
    missing, different = [], []
    for ex in exchange:
        cur = have.get(ex.open_time)
        if cur is None:
            missing.append(ex)
        elif not same_candle(cur, ex):
            different.append(ex)
    return missing, different


def list_symbols(store):
    with store.lock, store._connect() as conn:
        rows = conn.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol").fetchall()
    return [r[0] for r in rows]


def build_plan(store, loader, symbols, days, now_ms, log):
    plan = []
    for symbol in symbols:
        for tf in TIMEFRAMES:
            step = TF_MS[tf]
            end = ((now_ms - SETTLE_MS) // step) * step
            start = ((end - days * 86_400_000) // step) * step
            try:
                exchange = [c for c in loader.fetch_range(symbol, tf, start, end) if start <= c.open_time < end]
                stored = store.get_candles(symbol, tf, start, end)
            except Exception as exc:
                log(f"{symbol} {tf}: FAILED {exc!r}")
                continue
            missing, different = compare(stored, exchange)
            slots = (end - start) // step
            log(
                f"{symbol} {tf}: window {fmt(start)} to {fmt(end)} | slots {slots} | stored {len(stored)} "
                f"| exchange {len(exchange)} | missing in database {len(missing)} | different {len(different)}"
            )
            plan.append((symbol, tf, missing + different))
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--symbols", default="")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = ROOT / "Debug" / f"candle_repair_report_{stamp}.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []

    def log(text):
        print(text)
        lines.append(text)

    store = CandleStoreWorker()
    loader = HistoricalDataLoaderWorker(rate_limit_sleep_s=0.15)
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] or list_symbols(store)
    log(f"FT-H.23 candle repair | mode {'WRITE' if args.write else 'REPORT ONLY'} | days {args.days} | symbols {symbols}")
    plan = build_plan(store, loader, symbols, args.days, int(time.time() * 1000), log)
    total = sum(len(rows) for _, _, rows in plan)
    log(f"TOTAL rows to write if approved: {total}")

    if args.write and total:
        db = Path(DB_PATH)
        backup = ROOT / "Debug" / "Backups" / f"candles_db_before_repair_{stamp}.db"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db, backup)
        log(f"Backup saved: {backup}")
        try:
            answer = input("Type YES and press ENTER to write the rows to the database: ").strip()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer != "YES":
            log("Cancelled. Nothing written.")
        else:
            written = 0
            for symbol, tf, rows in plan:
                if rows:
                    written += store.save_candles(symbol, tf, rows)
            log(f"WRITTEN rows: {written}")
    elif args.write:
        log("Nothing to write.")
    else:
        log("REPORT ONLY: nothing was written to the database.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
