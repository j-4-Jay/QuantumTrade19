"""PATH: engines/workers/setup/setup_buffer_view.py  (NEW FILE)

FT-H.3 Step B - builds the rows of the SL buffer table for the Settings card.
Pure function, no screen and no engine. One row per active symbol (in the order given), then any
symbol that has a saved override but is not in the active list (sorted).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List


def _symbol_name(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("symbol") or "")
    return str(getattr(item, "symbol", "") or "")


def buffer_rows(settings: Any, symbols: Iterable[Any]) -> List[Dict[str, str]]:
    names: List[str] = []
    seen = set()
    for item in symbols or []:
        name = _symbol_name(item).strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    for name in sorted(settings.overrides()):
        if name not in seen:
            seen.add(name)
            names.append(name)
    return [
        {
            "symbol": name,
            "ticks": str(settings.get_buffer_ticks(name)),
            "custom": "yes" if settings.has_override(name) else "no",
        }
        for name in names
    ]
