"""Bounded, append-only public market-data evidence; never deletes or rotates history."""
import json
import os
from pathlib import Path
import threading
import uuid
from datetime import datetime, timezone


class EvidenceLog:
    def __init__(self, folder, max_bytes=20_000_000, total_bytes=100_000_000):
        self.folder = Path(folder)
        self.limit = max_bytes
        self.total_limit = total_bytes
        self.written = 0
        self.closed = False
        self.lock = threading.Lock()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.total = sum(p.stat().st_size for p in self.folder.glob("shadow_*.jsonl"))
        name = datetime.now(timezone.utc).strftime("shadow_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:10] + ".jsonl"
        self.path = self.folder / name
        self.file = None
        if self.total < self.total_limit:
            self.file = self.path.open("x", encoding="utf-8", newline="\n")

    def append(self, row):
        data = json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n"
        size = len(data.encode("utf-8"))
        with self.lock:
            if self.closed or self.file is None:
                return False
            if self.written + size > self.limit or self.total + size > self.total_limit:
                return False
            self.file.write(data)
            self.file.flush()
            self.written += size
            self.total += size
            return True

    def close(self):
        with self.lock:
            self.closed = True
            if self.file is not None:
                self.file.close()
