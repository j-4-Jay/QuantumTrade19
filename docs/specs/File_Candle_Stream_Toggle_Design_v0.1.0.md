# File Candle Stream Toggle Design v0.1.0 (Blueprint extension, DESIGN ONLY)
Date: 12-11-2026 | Thread 009 | Status: PROPOSED for Jay review. Not approved, not implemented, no unlock requested yet.
Supersedes the 45-second readiness proposal as the normal decision path. Builds on File_Candle_Stream_Probe_Spec_v0.1.0.md and probe request 825/828 results.

## 1. Measured basis (single ETH sample, about 20 minutes, probe run 20261112_025110)
- Stream candle: 20 of 20 1m and 4 of 4 5m candles matched settled REST OHLC and volume at +1 s; 18 of 20 OHLC and 11 of 20 volume at +0 s.
- Last stream update after close: 1m median 276 ms, max 949 ms; 5m median 420 ms, max 673 ms (local clock; local is about 0.29 s behind exchange, so real values are up to about 0.3 s later).
- Trade-built 1m candles matched only 13 of 20 OHLC and 10 of 20 volume even at +10 s: not a decision source.
- Not proven: busy sessions, other symbols, 15m, reconnects, an explicit closed marker.

## 2. Current path facts (live reads 822, 824, 829)
- The builder closes a candle only when the first tick of the next bucket arrives, then the monitor holds 1m/5m/15m closes for 9 s (delayed_dispatch_worker). Tick volume is summed from field v, which the CoinDCX glossary defines as 24-hour volume; forming-candle volume is therefore unreliable until REST correction replaces it (consistent with the earlier large transient volume observation; cause unproved).
- REST reconcile runs every 10 s (1m) and 30 s (5m/15m) plus fetches at 1.5, 4 and 8 s after each close. apply_exchange_candles replaces forming values, corrects known closed candles in place without notifying subscribers, and closes a candle once with a callback only if the local forming candle still exists.
- Corrections to already-delivered closed candles do not re-notify setup subscribers. This matches the accepted no-automatic-replay rule.

## 3. Modes (one decision source at a time)
- CURRENT: unchanged default.
- SHADOW: CURRENT drives everything. The stream is recorded and compared; no effect on candles or setups.
- STREAM: the stream drives forming values and closed-candle delivery. Tick-path close notifications for 1m/5m/15m are suppressed (still persisted). REST reconcile keeps running as the correction and audit path.
Mode is chosen at startup (setting or environment value to be decided from live settings code); switching while running is not supported in v1.

## 4. Proposed components
- New worker stream_candle_worker.py (new file): its own CoinDCXSocketTransport instance and reconnect loop, so engines/workers/market_data/ws_feed_worker.py and coindcx_socket_transport.py stay untouched. Joins B-ETH-style futures channels for 1m and 5m per subscribed symbol; parses to Candle objects.
- Forming updates go through the existing apply_exchange_candles so volume and OHLC follow the exchange.
- Maturity rule (starting values, to be tuned on data): a closed 1m/5m candle is delivered once its boundary has passed in exchange time and either the next interval message has arrived or boundary + 1.25 s has elapsed, provided at least one update for that interval arrived in its final 2 s. Hard limit boundary + 3 s: otherwise symbol enters data-gap hold.
- 15m: derived from three exact stream 5m candles at the 15m boundary; any missing or unmatured constituent means hold for 15m only.
- Delivery: one detached immutable Candle copy per (symbol, timeframe, open_time), delivered once to existing close subscribers directly (no 9 s hold), with duplicate protection by that key.
- Evidence log: append-only record per delivery (source, exchange and local timestamps, values, mode). Later REST differences are appended as separate correction records linked to the delivery. No setup replay, no recalculation of delivered setups.
- Data-gap hold: stream disconnected or silent beyond the hard limit holds new setup output for that symbol until explicit recovery; chart, feed and reconcile continue. No silent fallback to CURRENT.

## 5. Files expected to change (each locked one needs Jay U + ENTER)
- New: engines/workers/market_data/stream_candle_worker.py, tests, evidence-log helper.
- Locked, small additive hooks: engines/monitors/market_data_monitor.py (mode, suppress tick-path notify in STREAM, start stream worker, direct delivery). candle_builder_worker.py only if a once-only close publish is needed after reading tests.
- Out of scope: ws_feed_worker.py, transport, delayed_dispatch_worker.py logic, chart files, strategy and cascade rules, the SetupDetectionMonitor same-FSM double-feed hazard (separate issue).

## 6. Open items before any implementation request
1. Settings location and startup-only mode selection.
2. Whether a closed marker exists; quiet-period tuning from the existing raw file (time from last old-interval message to first next-interval message).
3. 15m, busy-session and reconnect measurements (probe re-run in busy hours and over a 15m boundary).
4. Local clock offset: use exchange Ets for age checks; recommend OS time sync.
5. Whether SHADOW mode is built first (recommended) before STREAM.
6. Strategy decision pending from the cascade review: which 1m setup candles qualify after a higher-timeframe trigger.

## 7. Acceptance outline (Jay to run later)
SHADOW: no change in app behaviour, evidence log matches REST for a full session. STREAM: setup input within 3 s of close in healthy feed, no duplicate deliveries, deliberate disconnect produces visible hold and no fabricated candle, REST corrections logged without replay.
