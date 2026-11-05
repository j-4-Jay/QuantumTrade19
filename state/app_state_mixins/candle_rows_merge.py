"""FT-H.34: merge corrected closed-candle rows into the chart candle list.

FULL PATH: state/app_state_mixins/candle_rows_merge.py
Pure function, no imports from the app. Returns None when nothing changed.
"""
from typing import Dict, List, Optional

_PRICE_KEYS = ("open", "high", "low", "close", "volume")


def merge_rows_by_timestamp(existing: List[dict], patch: List[dict]) -> Optional[List[dict]]:
    if not existing or not patch:
        return None
    by_ts: Dict[object, dict] = {r["timestamp"]: r for r in existing}
    last_ts = max(by_ts)
    changed = False
    for row in patch:
        ts = row["timestamp"]
        old = by_ts.get(ts)
        if old is None:
            if ts <= last_ts:
                continue
            by_ts[ts] = dict(row)
            changed = True
        elif any(old.get(k) != row.get(k) for k in _PRICE_KEYS):
            by_ts[ts] = {**old, **row}
            changed = True
    if not changed:
        return None
    return [by_ts[t] for t in sorted(by_ts)]
