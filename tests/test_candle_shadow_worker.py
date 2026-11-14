"""Offline tests: Shadow cannot drive the trading pipeline."""
import ast
import json
import threading
from pathlib import Path
from types import SimpleNamespace
import pytest
from engines.workers.market_data.candle_shadow_worker import CandleShadowWorker, parse, matches
from engines.workers.market_data.shadow_evidence_log import EvidenceLog

OT = 1794432060000


def payload(tf="1m", symbol="B-ETH_USDT"):
    return {"pr": "futures", "i": tf, "channel": f"{symbol}_{tf}-futures", "Ets": OT+100,
            "data": [{"pair": symbol, "duration": tf, "open_time": OT/1000,
                      "open": "10", "high": "12", "low": "9", "close": "11", "volume": "3"}]}


class Sink:
    path = "test-only"
    def __init__(self):
        self.rows = []
    def append(self, row):
        self.rows.append(json.loads(json.dumps(row)))
        return True
    def close(self):
        pass


def worker():
    w = CandleShadowWorker()
    w.symbols = {"B-ETH_USDT"}
    w.sink = Sink()
    return w


def test_real_shape():
    rows = parse(payload(), {"B-ETH_USDT"})
    assert len(rows) == 1
    assert rows[0]["open_time"] == OT and rows[0]["volume"] == 3


@pytest.mark.parametrize("field,value", [("pr", "spot"), ("channel", "other"), ("i", "5m")])
def test_envelope_mismatch_rejected(field, value):
    p = payload(); p[field] = value
    assert parse(p, {"B-ETH_USDT"}) == []


def test_wrong_symbol_and_alignment_rejected():
    assert parse(payload(), {"B-BTC_USDT"}) == []
    p = payload(); p["data"][0]["open_time"] += 1
    assert parse(p, {"B-ETH_USDT"}) == []


@pytest.mark.parametrize("field,value", [("close", "nan"), ("volume", "-1"), ("high", "8"), ("low", "inf")])
def test_bad_values_rejected(field, value):
    p = payload(); p["data"][0][field] = value
    assert parse(p, {"B-ETH_USDT"}) == []


def test_snapshot_never_claims_finality_or_late_capture_accuracy():
    w = worker()
    w._handle(("stream", payload(), OT+60_100, 0))
    w._snapshots(OT+61_100)
    rows = [r for r in w.sink.rows if r["kind"] == "scheduled_snapshot"]
    assert len(rows) == 1 and rows[0]["capture_on_schedule"]
    assert rows[0]["reference_final"] is False
    w._snapshots(OT+80_000)
    rows = [r for r in w.sink.rows if r["kind"] == "scheduled_snapshot"]
    assert len(rows) == 3 and not rows[-1]["capture_on_schedule"]
    w._snapshots(OT+80_000)
    assert len([r for r in w.sink.rows if r["kind"] == "scheduled_snapshot"]) == 3


def test_observation_detached_and_compared():
    w = worker()
    w._handle(("stream", payload(), OT+60_100, 0))
    c = {"symbol": "B-ETH_USDT", "tf": "1m", "open_time": OT,
         "open": 10, "high": 12, "low": 9, "close": 11, "volume": 3}
    w._handle(("current_delivery", c, OT+69_000, 0))
    c["volume"] = 999
    row = w.sink.rows[-1]
    assert row["candle"]["volume"] == 3 and all(row["exact_matches"].values())
    assert not row["reference_final"]


def test_queue_overflow_nonblocking():
    w = worker()
    for i in range(5000):
        w._enqueue("current_close", None)
    assert w.events.qsize() == 4096 and w.dropped == 904


def test_log_cap_preserves_previous_lines(tmp_path):
    s = EvidenceLog(tmp_path, max_bytes=30)
    assert s.append({"a": 1})
    before = s.path.read_bytes()
    assert not s.append({"huge": "x"*100})
    s.close()
    assert s.path.read_bytes() == before


def test_total_cap_no_deletion(tmp_path):
    old = tmp_path/"shadow_old.jsonl"; old.write_text("x"*100)
    s = EvidenceLog(tmp_path, total_bytes=50)
    assert not s.append({"a": 1})
    s.close()
    assert old.read_text() == "x"*100 and len(list(tmp_path.iterdir())) == 1


def test_worker_has_no_mutating_pipeline_imports():
    src = Path(__import__(CandleShadowWorker.__module__, fromlist=["x"]).__file__).read_text()
    tree = ast.parse(src)
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert all(not any(t in (m or "") for t in ("builder", "store", "setup", "dispatcher")) for m in imports)
    assert "fetch_range" not in src and "add_candle_close_subscriber" not in src


def test_membership_and_stop_without_start():
    w = worker(); w.subscribe("B-BTC_USDT"); w.unsubscribe("B-ETH_USDT"); w.stop()
    assert w.symbols == {"B-BTC_USDT"} and w.stop_flag.is_set()
