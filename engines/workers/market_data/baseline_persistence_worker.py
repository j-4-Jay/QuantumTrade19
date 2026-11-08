"""Persist missing baseline candles only; never publish setup events."""
from datetime import datetime
from pathlib import Path
import sqlite3
import time

STEPS = {"1m": 60000, "5m": 300000, "15m": 900000}


def persist_missing_baseline(store, symbol, baseline, now_ms, backup_dir=None):
    """Back up before the first write; preserve existing rows under the store lock."""
    selected = {}
    five = {int(c.open_time) for c in baseline.get("5m", [])}
    for tf, candles in baseline.items():
        step = STEPS.get(tf)
        if step is None:
            continue
        good = {}
        for c in candles:
            t = int(c.open_time)
            if t % step or t + step > now_ms:
                continue
            if tf == "15m" and not all(t + offset in five for offset in (0, 300000, 600000)):
                continue
            good[t] = c
        selected[tf] = good
    counts = {}
    with store.lock:
        pending = {}
        for tf, good in selected.items():
            existing = set(store.get_all_timestamps(symbol, tf))
            pending[tf] = [good[t] for t in sorted(good) if t not in existing]
        if any(pending.values()) and not getattr(store, "_baseline_backup_done", False):
            db = Path(store.db_path).resolve()
            folder = Path(backup_dir) if backup_dir is not None else Path("Debug") / "Backups"
            folder.mkdir(parents=True, exist_ok=True)
            dest = folder / ("baseline_before_fill_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
            source = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=5)
            target = None
            try:
                target = sqlite3.connect(str(dest))
                deadline = time.monotonic() + 15
                def progress(status, remaining, total):
                    if time.monotonic() > deadline:
                        raise TimeoutError("Baseline backup exceeded 15 seconds; fill cancelled")
                source.backup(target, pages=256, progress=progress, sleep=0.05)
            finally:
                if target is not None:
                    target.close()
                source.close()
            store._baseline_backup_done = True
            store._baseline_backup_path = str(dest)
        for tf, candles in pending.items():
            counts[tf] = store.save_candles(symbol, tf, candles) if candles else 0
    return counts

