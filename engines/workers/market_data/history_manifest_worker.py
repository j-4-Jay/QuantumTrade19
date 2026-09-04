"""Local download manifest metadata.

TARGET PATH: D:\QuantumTrade19\engines\workers\market_data\history_manifest_worker.py
REPLACE THE ENTIRE FILE.

v0.4.8: A manifest can describe only successfully persisted local download
ranges. Broker depth probes never call this worker. SQLite remains the truth
for all Trading Panel coverage decisions.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import List, Tuple

_MANIFEST_DIR = Path("data") / "historical" / "manifests"


class HistoryManifestWorker:
    def __init__(self, manifest_dir: Path = _MANIFEST_DIR) -> None:
        self._dir = Path(manifest_dir)
        self._lock = threading.RLock()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, symbol: str) -> Path:
        return self._dir / f"{symbol}.json"

    def _load(self, symbol: str) -> dict:
        path = self._path_for(symbol)
        if not path.exists():
            return {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            return loaded if isinstance(loaded, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, symbol: str, data: dict) -> None:
        path = self._path_for(symbol)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    def get_covered_ranges(self, symbol: str, timeframe: str) -> List[Tuple[int, int]]:
        with self._lock:
            data = self._load(symbol)
            ranges = data.get(timeframe, [])
        result: list[tuple[int, int]] = []
        for item in ranges:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            start, end = int(item[0]), int(item[1])
            if end > start:
                result.append((start, end))
        return result

    def mark_covered(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> None:
        start, end = int(start_ms), int(end_ms)
        if end <= start:
            return
        with self._lock:
            data = self._load(symbol)
            ranges = list(data.get(timeframe, []))
            ranges.append([start, end])
            normalized = sorted(
                ([int(item[0]), int(item[1])] for item in ranges if len(item) == 2 and int(item[1]) > int(item[0])),
                key=lambda item: item[0],
            )
            merged: list[list[int]] = []
            for range_start, range_end in normalized:
                if merged and range_start <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], range_end)
                else:
                    merged.append([range_start, range_end])
            data[timeframe] = merged
            self._save(symbol, data)

    def replace_covered_ranges(self, symbol: str, timeframe: str, ranges: List[Tuple[int, int]]) -> None:
        with self._lock:
            data = self._load(symbol)
            data[timeframe] = [[int(start), int(end)] for start, end in ranges if int(end) > int(start)]
            self._save(symbol, data)

    def find_gaps(self, symbol: str, timeframe: str, full_start_ms: int, full_end_ms: int) -> List[Tuple[int, int]]:
        start, end = int(full_start_ms), int(full_end_ms)
        if end <= start:
            return []
        covered = sorted(self.get_covered_ranges(symbol, timeframe), key=lambda item: item[0])
        gaps: list[tuple[int, int]] = []
        cursor = start
        for covered_start, covered_end in covered:
            if covered_end <= cursor:
                continue
            if covered_start >= end:
                break
            if covered_start > cursor:
                gaps.append((cursor, min(covered_start, end)))
            cursor = max(cursor, min(covered_end, end))
            if cursor >= end:
                break
        if cursor < end:
            gaps.append((cursor, end))
        return [(gap_start, gap_end) for gap_start, gap_end in gaps if gap_end > gap_start]

    def coverage_percent(self, symbol: str, timeframe: str, full_start_ms: int, full_end_ms: int) -> float:
        total = int(full_end_ms) - int(full_start_ms)
        if total <= 0:
            return 100.0
        gap_total = sum(end - start for start, end in self.find_gaps(symbol, timeframe, full_start_ms, full_end_ms))
        return round(max(0.0, min(100.0, 100.0 * (1.0 - gap_total / total))), 2)

    def delete_symbol_manifest(self, symbol: str) -> None:
        path = self._path_for(symbol)
        with self._lock:
            if path.exists():
                path.unlink()
