"""FT-H.37 bounded 5m/15m observer v1.0.0. No DB writes or orders."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import math
import sqlite3
import time

VERSION = "1.0.0"
OFFSETS = (1, 5, 9, 10, 15, 20, 30, 55)
PERIODS = {"5m": 300, "15m": 900}
PAIR = "B-ETH_USDT"
URL = "https://public.coindcx.com/market_data/candlesticks"
ROOT = Path(__file__).resolve().parent


def schedule(now, count=3):
    events = []
    for tf, period in PERIODS.items():
        first = (int(now) // period + 1) * period
        for i in range(count):
            close = first + i * period
            for offset in OFFSETS:
                events.append((close + offset, tf, close, offset))
    return sorted(events)


def values(row):
    result = tuple(float(row[k]) for k in ("open", "high", "low", "close", "volume"))
    if not all(math.isfinite(x) for x in result) or result[4] < 0:
        raise ValueError("Invalid OHLCV")
    return result


def exchange_values(rows, tf, open_ms):
    stamps = [open_ms] if tf == "5m" else [open_ms + i * 300000 for i in range(3)]
    found = {}
    for row in rows:
        stamp = int(row["time"])
        if stamp in stamps:
            if stamp in found:
                raise ValueError("Duplicate source timestamp")
            found[stamp] = values(row)
    if set(found) != set(stamps):
        raise ValueError("Missing required closed 5m constituent(s)")
    group = [found[s] for s in stamps]
    return (group[0][0], max(x[1] for x in group), min(x[2] for x in group),
            group[-1][3], sum(x[4] for x in group))


def same(a, b):
    return (a is not None and b is not None and len(a) == len(b) == 5
            and all(math.isfinite(x) and math.isfinite(y) and abs(x-y) < 1e-6
                    for x, y in zip(a, b)))


def read_db(db, tf, open_ms):
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)
    try:
        row = con.execute("SELECT open,high,low,close,volume FROM candles "
                          "WHERE symbol=? AND timeframe=? AND open_time=?",
                          (PAIR, tf, open_ms)).fetchone()
        return tuple(float(x) for x in row) if row else None
    finally:
        con.close()


def fetch(tf, open_ms):
    import requests
    period = PERIODS[tf] * 1000
    response = requests.get(URL, params={"pair": PAIR, "from": open_ms // 1000,
        "to": (open_ms + period) // 1000, "resolution": "5", "pcode": "f"}, timeout=3)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("data"), list):
        raise ValueError("Invalid exchange response")
    return exchange_values(body["data"], tf, open_ms)


def classify(before, exchange, after, late, error):
    if error:
        return "ERROR"
    if late:
        return "LATE_INCONCLUSIVE"
    if before is None or after is None:
        return "MISSING_DB"
    return "MATCH" if same(before, exchange) and same(after, exchange) else "DIFFERENT"


def observe(event, db):
    due, tf, close, target = event
    started = time.time()
    result = dict(timeframe=tf, open_ms=(close-PERIODS[tf])*1000, close_epoch=close,
        target_offset=target, start_epoch=started, start_offset=started-close,
        before=None, exchange=None, after=None, error="")
    mono = time.monotonic()
    if started-due > 2:
        result.update(status="SKIPPED_LATE", complete_epoch=started,
                      complete_offset=started-close, duration=0)
        return result
    try:
        result["before"] = read_db(db, tf, result["open_ms"])
        result["exchange"] = fetch(tf, result["open_ms"])
        result["after"] = read_db(db, tf, result["open_ms"])
    except Exception as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)
    ended = time.time()
    elapsed = time.monotonic()-mono
    clock_jump = abs((ended-started)-elapsed) > 0.5
    if clock_jump:
        result["error"] = "CLOCK_CHANGE: " + result["error"]
    result.update(complete_epoch=ended, complete_offset=ended-close, duration=elapsed)
    result["status"] = classify(result["before"], result["exchange"], result["after"],
                                 ended-due > 2, result["error"])
    return result


def summary(records):
    groups = {}
    for record in records:
        key = (record["timeframe"], record["open_ms"])
        groups.setdefault(key, []).append(record)
    output = []
    for (tf, stamp), group in sorted(groups.items()):
        final = group[-1]
        suffix = []
        for record in reversed(group):
            if record["status"] != "MATCH" or not same(record["exchange"], final["exchange"]):
                break
            suffix.append(record)
        output.append(dict(timeframe=tf, open_ms=stamp,
            complete_observations=len(group), final_status=final["status"],
            matching_suffix_start_complete_offset=suffix[-1]["complete_offset"] if suffix else None,
            all_scheduled_observations_matched=all(r["status"] == "MATCH" for r in group),
            note="Observed sample only; not exact settlement or dispatch safety proof."))
    return output


def main():
    db = ROOT / "data" / "historical_candles.db"
    if not db.is_file():
        raise SystemExit("Database absent. Stop; start the app normally first.")
    events = schedule(time.time())
    folder = ROOT / "Debug"
    folder.mkdir(exist_ok=True)
    prefix = folder / ("settle_5m15m_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    records = []
    print("FT-H.37 observer v" + VERSION + " | ETH | 3 x 5m and 3 x 15m")
    print("App must stay running. Do not run other measurement helpers concurrently.")
    print("15m exchange reference is derived from THREE exact native 5m candles.")
    print("No chart measurement. No safe-delay recommendation. Up to about 46 minutes.")
    print("Reports:", prefix)
    try:
        with open(str(prefix)+".csv", "x", newline="", encoding="utf-8") as stream:
            writer = None
            for event in events:
                wait = event[0]-time.time()
                if wait > 0:
                    time.sleep(wait)
                record = observe(event, db)
                records.append(record)
                if writer is None:
                    writer = csv.DictWriter(stream, fieldnames=list(record))
                    writer.writeheader()
                writer.writerow({k: json.dumps(v) if isinstance(v, tuple) else v for k,v in record.items()})
                stream.flush()
                opened = datetime.fromtimestamp(record["open_ms"]/1000).astimezone().isoformat()
                print(record["timeframe"], opened, "+"+str(record["target_offset"]),
                      record["status"], "completed +%.3fs" % record["complete_offset"], flush=True)
    except KeyboardInterrupt:
        print("Stopped by user; partial report retained.")
    finally:
        with open(str(prefix)+"_summary.json", "x", encoding="utf-8") as stream:
            json.dump(dict(version=VERSION, pair=PAIR, observations=len(records),
                candles=summary(records), limitations=["Not chart acceptance", "Not busy-session certification",
                "Not 9-second dispatch safety proof", "15m derived from native 5m", "Public requests add load"]), stream, indent=2)
        print("Reports saved:", prefix)


if __name__ == "__main__":
    main()
