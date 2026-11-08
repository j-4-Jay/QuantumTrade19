"""FT-H.39 read-only office candle storage diagnosis. No network or database writes."""
from pathlib import Path
from datetime import datetime, timezone
import sqlite3
import time


def stamp(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat() if ms is not None else "none"


def main():
    root = Path(__file__).resolve().parent
    db = root / "data" / "historical_candles.db"
    lines = ["QT19 popup database diagnosis (read-only)", "UTC now: " + stamp(int(time.time() * 1000)), "DB: " + str(db), "Exists: " + str(db.exists())]
    if db.exists():
        try:
            con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
            try:
                con.execute("PRAGMA query_only=ON")
                now = int(time.time() * 1000)
                for sym in ("B-BTC_USDT", "B-ETH_USDT", "B-XAU_USDT"):
                    for tf, step in (("1m", 60000), ("5m", 300000), ("15m", 900000)):
                        end = (now // step) * step - step
                        start = end - 3 * 86400000 + step
                        count, earliest, latest = con.execute("SELECT COUNT(*), MIN(open_time), MAX(open_time) FROM candles WHERE symbol=? AND timeframe=?", (sym, tf)).fetchone()
                        rows = con.execute("SELECT open_time FROM candles WHERE symbol=? AND timeframe=? AND open_time BETWEEN ? AND ? ORDER BY open_time", (sym, tf, start, end)).fetchall()
                        present = {int(r[0]) for r in rows}
                        missing = [t for t in range(start, end + 1, step) if t not in present]
                        lines.append(f"{sym} {tf}: total={count}; earliest UTC={stamp(earliest)}; latest UTC={stamp(latest)}; last-3-days missing={len(missing)}")
                        lines.append("  Latest expected closed UTC=" + stamp(end) + "; last 10 missing UTC=" + ", ".join(stamp(t) for t in missing[-10:]))
                        last = con.execute("SELECT open_time,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY open_time DESC LIMIT 3", (sym, tf)).fetchall()
                        for r in last:
                            lines.append("  Saved UTC=" + stamp(r[0]) + "; OHLCV=" + repr(r[1:]))
                lines.append("Stored symbol/timeframe keys:")
                for row in con.execute("SELECT DISTINCT symbol,timeframe FROM candles ORDER BY symbol,timeframe"):
                    lines.append("  " + repr(row))
            finally:
                con.close()
        except Exception as exc:
            lines.append("READ ERROR: " + type(exc).__name__ + ": " + str(exc))
    out = root / "Debug" / "popup_db_diagnosis.txt"
    out.parent.mkdir(exist_ok=True)
    text = "\n".join(lines)
    out.write_text(text, encoding="utf-8")
    print(text)
    print("Report: " + str(out))


if __name__ == "__main__":
    main()

