# File Candle Stream Probe Spec v0.1.0 (Blueprint extension)
Date: 12-11-2026 | Thread 009 | Status: PROPOSED, not applied, not accepted, not locked

## Purpose
Measure, before any toggle design, how soon after each close CoinDCX futures candlestick and trade streams deliver values and how accurate they are compared with settled REST candles. Supports Jay's direction of 3-second decisions via the stream with later corrections tracked separately. No decision-path change.

## Scope
- New standalone script `4c. Probe_Candle_Stream.py` with launcher `4c. Probe_Candle_Stream.bat` and tests `tests/test_candle_stream_probe.py`.
- Reuses the existing socket transport and REST history loader read-only. No locked file is modified.
- Joins `B-ETH_USDT_1m-futures`, `B-ETH_USDT_5m-futures` and `B-ETH_USDT@trades-futures` (names from public documentation copies that disagree with other sources; the probe records what actually arrives). Optional `--alt` also joins spot-style names for naming comparison only.
- Listens to events `candlestick` and `new-trade`. Raw messages go to Debug JSONL (capped at 200000 messages), machine-local, never staged.
- After the run it fetches settled REST candles once per timeframe and compares stream snapshots at +0/+1/+3/+10 seconds after each close. Trade-built 1m candles are compared the same way.

## Reported results
Per timeframe: candles seen/compared, delay of the last stream update after close (min/median/p95/max), and OHLC/volume match counts at each offset for the stream and for trade-built candles. Unparsed candle messages are counted, never guessed. Timestamps are floored to the interval; messages without a recognised interval or time are not used.

## Not in scope / not proven
No database writes, orders, credentials, dispatcher or builder changes. A sample does not prove a close flag exists, universal latency, 15m behaviour (15m remains derived from three 5m candles) or busy-session behaviour. Network drops end the run with partial data.

## Acceptance (software checks, Jay to run)
1. Focused tests pass.
2. A 20-minute ETH run completes without touching the app or database.
3. Summary file lists received events, delays and accuracy; failures to receive candlestick messages are reported plainly.
