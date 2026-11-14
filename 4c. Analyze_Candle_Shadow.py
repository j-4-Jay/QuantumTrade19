"""Read-only summaries of the five identified QT19 Shadow recordings."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

FILES = (
    "shadow_20261111_224927_2775e5360d.jsonl",
    "shadow_20261112_001402_6c8c3a3247.jsonl",
    "shadow_20261112_035001_8ee3bab1a8.jsonl",
    "shadow_20261112_040317_db0794b0fd.jsonl",
    "shadow_20261112_040403_0bf6d1415e.jsonl",
)
FIELDS = ("open", "high", "low", "close", "volume")
STEPS = {"1m": 60000, "5m": 300000, "15m": 900000}


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def candle_key(row):
    c = row.get("candle")
    if not isinstance(c, dict):
        return None
    if c.get("tf") not in STEPS or not isinstance(c.get("symbol"), str):
        return None
    if not number(c.get("open_time")) or not all(number(c.get(f)) for f in FIELDS):
        return None
    return (c["symbol"], c["tf"], c["open_time"])


def same(a, b):
    return all(a[f] == b[f] for f in FIELDS)


def analyze(path):
    result = {"name": path.name, "kinds": Counter(), "coverage": defaultdict(set),
              "offsets": defaultdict(Counter), "delivery": Counter(), "examples": [],
              "controls": [], "malformed": 0, "unusable": 0, "stop": [],
              "first": None, "last": None, "complete": True, "max_drop": None}
    if not path.is_file() or path.is_symlink():
        result["error"] = "missing/nonregular/symlink input; not analyzed"
        return result
    before = path.stat()
    digest = hashlib.sha256()
    references = defaultdict(list)
    snapshots, deliveries = [], []
    observations = 0
    try:
        with path.open("rb") as handle:
            for line_no in range(1, 1000002):
                raw = handle.readline(1000001)
                if not raw:
                    break
                if line_no > 1000000 or len(raw) > 1000000:
                    result["complete"] = False
                    result["error"] = "safety bound reached; partial analysis"
                    break
                digest.update(raw)
                try:
                    row = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    result["malformed"] += 1
                    continue
                if not isinstance(row, dict):
                    result["malformed"] += 1
                    continue
                kind = row.get("kind", "unknown")
                if not isinstance(kind, str):
                    result["malformed"] += 1
                    continue
                result["kinds"][kind] += 1
                timestamp = row.get("local_ms")
                if number(timestamp):
                    result["first"] = timestamp if result["first"] is None else min(result["first"], timestamp)
                    result["last"] = timestamp if result["last"] is None else max(result["last"], timestamp)
                if kind in ("connected", "connection_lost", "connect_error", "clock_discontinuity"):
                    if len(result["controls"]) < 10000:
                        result["controls"].append((kind, timestamp, row.get("epoch")))
                    else:
                        result["complete"] = False
                if kind == "session_stop":
                    result["stop"].append((row.get("dropped"), row.get("rejected")))
                drop = row.get("queue_dropped")
                if number(drop):
                    result["max_drop"] = drop if result["max_drop"] is None else max(result["max_drop"], drop)
                if kind not in ("stream_update", "scheduled_snapshot", "current_delivery", "reconcile_observation"):
                    continue
                key = candle_key(row)
                if key is None:
                    result["unusable"] += 1
                    continue
                result["coverage"][(key[0], key[1])].add(key[2])
                if kind == "stream_update":
                    continue
                observations += 1
                if observations > 200000:
                    result["complete"] = False
                    result["error"] = "comparison-record bound reached; partial analysis"
                    break
                if kind == "reconcile_observation":
                    if number(row.get("received_ms")):
                        references[key].append(row)
                    else:
                        result["unusable"] += 1
                elif kind == "scheduled_snapshot":
                    snapshots.append((key, row))
                else:
                    deliveries.append((key, row))
    except OSError as exc:
        result["complete"] = False
        result["error"] = type(exc).__name__
    after = path.stat()
    result["changed_while_reading"] = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
    if result["changed_while_reading"]:
        result["complete"] = False
    result["bytes"] = after.st_size
    result["sha256_read"] = digest.hexdigest()
    for group in references.values():
        group.sort(key=lambda r: r["received_ms"])
    for key, row in snapshots:
        offset = row.get("offset_ms")
        counts = result["offsets"][str(offset)]
        counts["snapshots"] += 1
        counts["on_schedule" if row.get("capture_on_schedule") is True else "not_on_schedule"] += 1
        captured = row.get("captured_ms")
        received = row["candle"].get("received_ms")
        boundary = key[2] + STEPS[key[1]]
        if number(received) and number(captured):
            counts["last_rx_before_close"] += received < boundary
            counts["negative_age"] += captured < received
            counts["age_over_3s"] += captured - received > 3000
        else:
            counts["age_unknown"] += 1
        compare(result, counts, key, row, captured, references)
    for key, row in deliveries:
        compare(result, result["delivery"], key, row, row.get("received_ms"), references)
        result["delivery"]["deliveries"] += 1
    return result


def compare(result, counts, key, row, when, references):
    if not number(when):
        counts["timestamp_unknown"] += 1
        return
    later = [r for r in references.get(key, ()) if r["received_ms"] > when]
    if not later:
        counts["no_later_reference"] += 1
        return
    counts["with_later_reference"] += 1
    same_epoch = [r for r in later if r.get("epoch") == row.get("epoch")]
    if not same_epoch:
        counts["cross_epoch_only"] += 1
        return
    counts["with_same_epoch_reference"] += 1
    comparisons = [same(row["candle"], r["candle"]) for r in same_epoch]
    counts["match_all_later" if all(comparisons) else "differs_from_some_later"] += 1
    counts["match_last_later" if comparisons[-1] else "differs_last_later"] += 1
    counts["later_references_vary"] += any(not same(same_epoch[0]["candle"], r["candle"]) for r in same_epoch[1:])
    if not all(comparisons) and len(result["examples"]) < 8:
        last = same_epoch[-1]
        changed = [f for f in FIELDS if row["candle"][f] != last["candle"][f]]
        result["examples"].append({"kind": row["kind"], "key": key, "epoch": row.get("epoch"),
                                   "offset_ms": row.get("offset_ms"), "different_from_last_fields": changed,
                                   "last_reference_ms": last["received_ms"]})


def main():
    folder = Path(__file__).resolve().parent / "Debug" / "CandleShadow"
    print("QT19 READ-ONLY SHADOW REVIEW - no source/log/settings/database changes or network")
    print("Close Shadow normally first. Missing stop is NOT automatically a failure.")
    print("Exact OHLCV equality to later observations is NOT exchange finality or readiness.")
    print("Same-epoch comparisons do NOT prove no intra-epoch gap. No calibrated <=3s claim.")
    print("Reference counts are comparison rows, not independent trials. Missing references are not matches.")
    for name in FILES:
        r = analyze(folder / name)
        print("\nFILE:", name)
        if "bytes" not in r:
            print(r.get("error")); continue
        print("bytes/sha256_read:", r["bytes"], r["sha256_read"])
        print("complete_scan/changed_while_reading:", r["complete"], r["changed_while_reading"])
        print("first/last local_ms:", r["first"], r["last"])
        print("events:", dict(sorted(r["kinds"].items())))
        print("malformed/unusable:", r["malformed"], r["unusable"])
        print("stop dropped/rejected:", r["stop"][:5], "snapshot max observed queue_dropped:", r["max_drop"])
        coverage = sorted(r["coverage"].items())
        for (symbol, tf), candles in coverage[:12]:
            print("observed distinct candles:", symbol, tf, len(candles), "first/last:", min(candles), max(candles))
        if len(coverage) > 12:
            print("additional coverage groups:", len(coverage)-12)
        for offset, counts in sorted(r["offsets"].items()):
            print("offset_ms", offset, dict(sorted(counts.items())))
        print("current_delivery vs later references:", dict(sorted(r["delivery"].items())))
        print("control events first20/total:", r["controls"][:20], len(r["controls"]))
        print("difference examples max8:", r["examples"])
        if r.get("error"):
            print("WARNING:", r["error"])
    print("\nSend complete printed summary. No report file written; no completion/lock/push implied.")


if __name__ == "__main__":
    main()
