"""History_Manifest_Worker: tracks exactly which date ranges are already downloaded, per symbol per timeframe.
Drives Deep_History_Downloader_Worker's skip-logic and the Settings-card progress bars.
"""
from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import List, Tuple

_MANIFEST_DIR = Path("data") / "historical" / "manifests"


class HistoryManifestWorker:
    def __init__(self, manifest_dir: Path = _MANIFEST_DIR) -> None:
        self._dir = manifest_dir
        self._lock = threading.Lock()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, symbol: str) -> Path:
        return self._dir / f"{symbol}.json"

    def _load(self, symbol: str) -> dict:
        path = self._path_for(symbol)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return {}

    def _save(self, symbol: str, data: dict) -> None:
        self._path_for(symbol).write_text(json.dumps(data, indent=2))

    def get_covered_ranges(self, symbol: str, timeframe: str) -> List[Tuple[int, int]]:
        with self._lock:
            data = self._load(symbol)
            return [tuple(r) for r in data.get(timeframe, [])]

    def mark_covered(self, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> None:
        with self._lock:
            data = self._load(symbol)
            ranges = data.setdefault(timeframe, [])
            ranges.append([start_ms, end_ms])
            ranges.sort(key=lambda r: r[0])
            merged: List[list] = []
            for r in ranges:
                if merged and r[0] <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], r[1])
                else:
                    merged.append(list(r))
            data[timeframe] = merged
            self._save(symbol, data)

    def find_gaps(self, symbol: str, timeframe: str, full_start_ms: int, full_end_ms: int) -> List[Tuple[int, int]]:
        covered = self.get_covered_ranges(symbol, timeframe)
        gaps: List[Tuple[int, int]] = []
        cursor = full_start_ms
        for start, end in covered:
            if end <= cursor:
                continue
            if start > cursor:
                gaps.append((cursor, min(start, full_end_ms)))
            cursor = max(cursor, end)
            if cursor >= full_end_ms:
                break
        if cursor < full_end_ms:
            gaps.append((cursor, full_end_ms))
        return [g for g in gaps if g[0] < g[1]]

    def coverage_percent(self, symbol: str, timeframe: str, full_start_ms: int, full_end_ms: int) -> float:
        total_span = full_end_ms - full_start_ms
        if total_span <= 0:
            return 100.0
        gap_span = sum(end - start for start, end in self.find_gaps(symbol, timeframe, full_start_ms, full_end_ms))
        return round(max(0.0, min(100.0, (1 - gap_span / total_span) * 100)), 2)

    def delete_symbol_manifest(self, symbol: str) -> None:
        path = self._path_for(symbol)
        with self._lock:
            if path.exists():
                path.unlink()
