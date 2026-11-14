"""QT19 4c. Probe_Candle_Stream.py - standalone READ-ONLY CoinDCX candle/trade stream probe.

Purpose: measure how soon after each candle close the CoinDCX futures candlestick stream
(and the trade stream) deliver values, and how accurate those values are at +0/+1/+3/+10 s
compared with settled REST candles. Measurement only: no orders, no credentials, no database
writes, no import of the candle store, builder, dispatcher or any locked File 02 module
except the existing socket transport and the REST history loader (both read-only here).
Reports go to Debug/ (machine-local, never staged).

Usage:  python "4c. Probe_Candle_Stream.py" [--symbol B-ETH_USDT] [--minutes 20] [--alt]
        python "4c. Probe_Candle_Stream.py" --summarize Debug/candle_stream_probe_<stamp>_raw.jsonl
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

ROOT = Path(__file__).resolve().parent
STEP_MS = {"1m": 60_000, "5m": 300_000}
OFFSETS_MS = (0, 1_000, 3_000, 10_000)
MAX_MESSAGES = 200_000
MAX_RAW_CHARS = 1_500
OPEN_KEYS = ("o", "open")
HIGH_KEYS = ("h", "high")
LOW_KEYS = ("l", "low")
CLOSE_KEYS = ("c", "close")
VOL_KEYS = ("v", "volume")
TIME_KEYS = ("t", "start", "startTime", "open_time", "openTime", "time", "T")
INTERVAL_KEYS = ("i", "interval", "resolution", "duration")
PRICE_TOL = 1e-8


def _first(d: dict, keys) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _num(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_ms(v: Any) -> Optional[int]:
    n = _num(v)
    if n is None or n <= 0:
        return None
    return int(n * 1000) if n < 1e11 else int(n)


def norm_interval(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s in STEP_MS else None


def iter_dicts(obj: Any, depth: int = 0) -> Iterator[dict]:
    if depth > 6:
        return
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except (ValueError, TypeError):
            return
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            if isinstance(v, (dict, list, str)):
                yield from iter_dicts(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_dicts(v, depth + 1)


def extract_candles(payload: Any, default_tf: Optional[str] = None) -> List[dict]:
    if default_tf is None and isinstance(payload, dict):
        default_tf = norm_interval(payload.get("i"))
    out: List[dict] = []
    for d in iter_dicts(payload):
        o, h, l = _num(_first(d, OPEN_KEYS)), _num(_first(d, HIGH_KEYS)), _num(_first(d, LOW_KEYS))
        c, v = _num(_first(d, CLOSE_KEYS)), _num(_first(d, VOL_KEYS))
        if None in (o, h, l, c):
            continue
        tf = norm_interval(_first(d, INTERVAL_KEYS)) or default_tf
        t_ms = to_ms(_first(d, TIME_KEYS))
        open_time = (t_ms // STEP_MS[tf]) * STEP_MS[tf] if (tf and t_ms) else None
        out.append({"tf": tf, "open_time": open_time, "o": o, "h": h, "l": l, "c": c, "v": v})
    return out


def extract_trades(payload: Any) -> List[dict]:
    out: List[dict] = []
    for d in iter_dicts(payload):
        p, q = _num(d.get("p")), _num(d.get("q"))
        t = to_ms(d.get("T"))
        if p is not None and q is not None and t is not None and "o" not in d:
            out.append({"p": p, "q": q, "T": t})
    return out


def close_boundary(open_time: int, tf: str) -> int:
    return open_time + STEP_MS[tf]


def snapshot_at(updates: List[dict], boundary: int, offset_ms: int) -> Optional[dict]:
    """Last stream update received at or before boundary+offset (None if none)."""
    limit = boundary + offset_ms
    best = None
    for u in updates:
        if u["recv"] <= limit and (best is None or u["recv"] >= best["recv"]):
            best = u
    return best


def build_trade_candle(trades: List[dict], open_time: int, tf: str, boundary: int, offset_ms: int,
                       recv_by_index: List[int]) -> Optional[dict]:
    limit = boundary + offset_ms
    sel = [t for t, r in zip(trades, recv_by_index)
           if open_time <= t["T"] < open_time + STEP_MS[tf] and r <= limit]
    if not sel:
        return None
    sel.sort(key=lambda t: t["T"])
    return {"o": sel[0]["p"], "h": max(t["p"] for t in sel), "l": min(t["p"] for t in sel),
            "c": sel[-1]["p"], "v": sum(t["q"] for t in sel)}


def _close(a: Optional[float], b: Optional[float], tol: float = PRICE_TOL) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= tol * max(1.0, abs(b))


def compare_ohlcv(got: Optional[dict], ref: dict) -> Dict[str, bool]:
    if got is None:
        return {"present": False, "ohlc": False, "volume": False}
    ohlc = all(_close(got[k], ref[k]) for k in ("o", "h", "l", "c"))
    return {"present": True, "ohlc": ohlc, "volume": _close(got.get("v"), ref["v"], 1e-6)}


def pct(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def summarize(records: List[dict], reference: Dict[str, Dict[int, dict]]) -> dict:
    """records: raw jsonl rows. reference: tf -> open_time -> settled REST OHLCV."""
    updates: Dict[tuple, List[dict]] = {}
    trades: List[dict] = []
    trade_recv: List[int] = []
    unparsed = 0
    events: Dict[str, int] = {}
    for r in records:
        events[r["event"]] = events.get(r["event"], 0) + 1
        if r["event"] == "new-trade":
            for t in extract_trades(r.get("payload")):
                trades.append(t)
                trade_recv.append(r["recv"])
            continue
        found = extract_candles(r.get("payload"), default_tf=None)
        usable = [c for c in found if c["tf"] and c["open_time"]]
        if not usable:
            unparsed += 1
        for c in usable:
            updates.setdefault((c["tf"], c["open_time"]), []).append(dict(c, recv=r["recv"]))
    result: Dict[str, Any] = {"events": events, "unparsed_candle_messages": unparsed, "timeframes": {}}
    skew_c = [r["recv"] - r["payload"]["Ets"] for r in records if r["event"] == "candlestick"
              and isinstance(r.get("payload"), dict) and isinstance(r["payload"].get("Ets"), (int, float))]
    skew_t = [r["recv"] - t["T"] for r in records if r["event"] == "new-trade"
              for t in extract_trades(r.get("payload"))]
    result["local_minus_exchange_ms"] = {
        "candle_Ets_median": statistics.median(skew_c) if skew_c else None,
        "trade_T_median": statistics.median(skew_t) if skew_t else None,
        "note": "negative = local clock behind exchange; delay figures carry this error"}
    for tf in STEP_MS:
        keys = sorted(k for k in updates if k[0] == tf)
        ref = reference.get(tf, {})
        complete = [k for k in keys if k[1] in ref and close_boundary(k[1], tf) <= max(
            (u["recv"] for ups in updates.values() for u in ups), default=0)]
        delays = []
        stats = {f"+{o}ms": {"stream": {"n": 0, "present": 0, "ohlc": 0, "volume": 0},
                             "trades": {"n": 0, "present": 0, "ohlc": 0, "volume": 0}} for o in OFFSETS_MS}
        for k in complete:
            b = close_boundary(k[1], tf)
            ups = updates[k]
            delays.append(max(u["recv"] for u in ups) - b)
            for o in OFFSETS_MS:
                for src, got in (("stream", snapshot_at(ups, b, o)),
                                 ("trades", build_trade_candle(trades, k[1], tf, b, o, trade_recv) if tf == "1m" and trades else None)):
                    if src == "trades" and not (tf == "1m" and trades):
                        continue
                    cmp = compare_ohlcv(got, ref[k[1]])
                    s = stats[f"+{o}ms"][src]
                    s["n"] += 1
                    s["present"] += int(cmp["present"])
                    s["ohlc"] += int(cmp["ohlc"])
                    s["volume"] += int(cmp["volume"])
        result["timeframes"][tf] = {
            "candles_seen": len(keys), "candles_compared": len(complete),
            "last_update_after_close_ms": {"median": statistics.median(delays) if delays else None,
                                           "p95": pct(delays, 0.95), "max": max(delays) if delays else None,
                                           "min": min(delays) if delays else None},
            "accuracy_by_offset": stats}
    return result


class Recorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.count = 0
        self.fh = path.open("a", encoding="utf-8")

    def write(self, event: str, payload: Any) -> None:
        with self.lock:
            if self.count >= MAX_MESSAGES:
                return
            self.count += 1
            row = {"recv": int(time.time() * 1000), "event": event, "payload": payload}
            text = json.dumps(row, default=str)
            if len(text) > MAX_RAW_CHARS * 4:
                row["payload"] = text[:MAX_RAW_CHARS]
                text = json.dumps(row, default=str)
            self.fh.write(text + "\n")
            self.fh.flush()

    def close(self) -> None:
        with self.lock:
            self.fh.close()


def channel_list(symbol: str, alt: bool) -> List[str]:
    chans = [f"{symbol}_1m-futures", f"{symbol}_5m-futures", f"{symbol}@trades-futures"]
    if alt:
        chans += [f"{symbol}_1m", f"{symbol}_5m"]
    return chans


def load_records(path: Path) -> List[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def fetch_reference(symbol: str, records: List[dict]) -> Dict[str, Dict[int, dict]]:
    sys.path.insert(0, str(ROOT))
    from engines.workers.market_data.historical_data_loader_worker import HistoricalDataLoaderWorker
    times = [r["recv"] for r in records]
    if not times:
        return {}
    start, end = min(times) - 10 * 60_000, max(times) + 60_000
    loader = HistoricalDataLoaderWorker()
    ref: Dict[str, Dict[int, dict]] = {}
    for tf in STEP_MS:
        ref[tf] = {}
        for c in loader.fetch_range(symbol, tf, start, end):
            ref[tf][int(c.open_time)] = {"o": float(c.open), "h": float(c.high), "l": float(c.low),
                                         "c": float(c.close), "v": float(c.volume)}
    return ref


def run(symbol: str, minutes: float, alt: bool) -> Path:
    sys.path.insert(0, str(ROOT))
    from engines.workers.market_data.coindcx_socket_transport import CoinDCXSocketTransport
    debug = ROOT / "Debug"
    debug.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    raw = debug / f"candle_stream_probe_{stamp}_raw.jsonl"
    rec = Recorder(raw)
    transport = CoinDCXSocketTransport()
    transport.on("candlestick", lambda p: rec.write("candlestick", p))
    transport.on("new-trade", lambda p: rec.write("new-trade", p))
    transport.connect("wss://stream.coindcx.com")
    for ch in channel_list(symbol, alt):
        transport.emit("join", {"channelName": ch})
        rec.write("join_sent", {"channel": ch})
        print("joined request:", ch)
    deadline = time.time() + minutes * 60
    try:
        while time.time() < deadline:
            time.sleep(1)
            if not transport.connected():
                rec.write("disconnected", {})
                print("transport disconnected - stopping; partial data kept")
                break
    except KeyboardInterrupt:
        print("stopped by user")
    finally:
        transport.disconnect()
        rec.close()
    print("raw file:", raw, "messages:", rec.count)
    return raw


def summarize_file(raw: Path, symbol: str) -> Path:
    records = load_records(raw)
    ref = fetch_reference(symbol, records)
    out = summarize(records, ref)
    out["symbol"] = symbol
    out["raw_file"] = raw.name
    path = raw.with_name(raw.name.replace("_raw.jsonl", "_summary.json"))
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print("summary file:", path)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="QT19 read-only CoinDCX candle stream probe")
    ap.add_argument("--symbol", default="B-ETH_USDT")
    ap.add_argument("--minutes", type=float, default=20.0)
    ap.add_argument("--alt", action="store_true", help="also join spot-style names for naming comparison")
    ap.add_argument("--summarize", default=None, help="summarize an existing raw .jsonl file only")
    args = ap.parse_args(argv)
    if args.summarize:
        summarize_file(Path(args.summarize), args.symbol)
        return 0
    if not 1 <= args.minutes <= 120:
        print("minutes must be between 1 and 120")
        return 2
    raw = run(args.symbol, args.minutes, args.alt)
    summarize_file(raw, args.symbol)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
