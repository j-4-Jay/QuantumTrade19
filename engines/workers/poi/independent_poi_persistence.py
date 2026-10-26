"""Saving and loading of Independent POI lines (stage FT-C, tasks FT-C.5 and FT-C.7).

PATH: engines/workers/poi/independent_poi_persistence.py (NEW FILE)

The lines are kept in sync_data/independent_pois.json. That file travels by git, so
Home and Office get the same lines. It holds prices and styles only, no secrets.
The "Allow live use" switch is NEVER saved and is always OFF after loading.
A file that cannot be read (for example a git merge conflict) is moved aside as
independent_pois.json.bad-<time> and the app starts with no lines.
"""
from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List

from engines.workers.poi.independent_poi_worker import (
    MAX_LINES_PER_SYMBOL, IndependentLine, _clean_style,
)

logger = logging.getLogger("poi_monitor.independent_poi_persistence")
FILE_VERSION = 1


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "sync_data" / "independent_pois.json"


def save_lines(path, lines_by_symbol: Dict[str, List[IndependentLine]]) -> None:
    symbols: Dict[str, list] = {}
    for symbol, lines in lines_by_symbol.items():
        symbols[symbol] = [
            {
                "uid": line.uid, "number": line.number, "price": line.price,
                "created_ts": line.created_ts, "updated_ts": line.updated_ts,
                "rev": line.rev, "style": dict(line.style),
            }
            for line in sorted(lines, key=lambda item: item.number)
        ]
    payload = {"version": FILE_VERSION, "symbols": symbols}
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle_fd, temp_name = tempfile.mkstemp(dir=str(target.parent), prefix=target.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def _line_from_entry(symbol: str, entry: dict):
    uid = entry.get("uid")
    number = int(entry.get("number"))
    price = float(entry.get("price"))
    if not isinstance(uid, str) or not uid:
        return None
    if not 1 <= number <= MAX_LINES_PER_SYMBOL:
        return None
    if not (math.isfinite(price) and price > 0):
        return None
    return IndependentLine(
        uid=uid, number=number, symbol=symbol, price=price,
        created_ts=float(entry.get("created_ts") or 0.0),
        rev=max(1, int(entry.get("rev") or 1)),
        allow_live=False,
        style=_clean_style(entry.get("style") or {}),
        updated_ts=float(entry.get("updated_ts") or 0.0),
    )


def load_lines(path) -> List[IndependentLine]:
    target = Path(path)
    if not target.exists():
        return []
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if data.get("version") != FILE_VERSION:
            raise ValueError(f"unknown file version {data.get('version')!r}")
        result: List[IndependentLine] = []
        for symbol, entries in (data.get("symbols") or {}).items():
            for entry in entries:
                try:
                    line = _line_from_entry(symbol, entry)
                except (TypeError, ValueError):
                    line = None
                if line is not None:
                    result.append(line)
        return result
    except Exception:  # noqa: BLE001
        backup = target.with_name(f"{target.name}.bad-{int(time.time())}")
        try:
            target.replace(backup)
        except OSError:
            pass
        logger.exception("independent_pois.json could not be read; moved aside as %s", backup.name)
        return []
