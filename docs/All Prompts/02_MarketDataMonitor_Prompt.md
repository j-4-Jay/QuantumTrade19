# File 02 — Market Data Monitor Engine (Master Build Prompt)
**Depends on:** File 01 locked. **Pipeline:** build → check → debug → re-check → lock → proceed for every item.

## 1. Plain Explanation
This is the "ears" of the software — it listens to CoinDCX (and later forex/commodity feeds) and turns raw price ticks into clean, ready-to-use candles for every timeframe, for every active symbol, live and historical, without ever dropping a beat even if the internet blinks.

## 2. Tier 1 — Workers (build & lock one at a time)

1. **Symbol_Registry_Worker** — the master list of every symbol the app knows about (CoinDCX futures pairs + forex/commodity/metal symbols added later), each with its tick size, contract size, maker/taker fee, and ON/OFF active flag. Every other Worker in this Monitor asks this Worker "what symbols am I watching?" — never hardcodes a list.
2. **WS_Feed_Worker** — opens and maintains a WebSocket connection per active symbol to CoinDCX's live ticker stream. Emits every raw tick the moment it arrives. Must detect a dropped connection within 2–3 seconds.
3. **REST_Poll_Fallback_Worker** — the moment WS_Feed_Worker reports a drop, this Worker takes over via REST polling (a safe, slightly slower interval, e.g. every 1–2 seconds) so no candle ever goes completely dark. Hands control back the instant WS reconnects.
4. **Historical_Data_Loader_Worker** — on symbol activation, backfills a minimum of 5 days of 1m, 5m, and 15m candles via REST, so the Trading Panel chart never opens empty.
5. **Tick_Normalizer_Worker** — converts every tick (live or fallback) into one consistent shape: symbol, price, volume, exchange timestamp, received timestamp. This is the one and only shape every downstream Worker in the whole app will ever see — no Worker outside this Monitor is allowed to read a "raw" tick.
6. **Candle_Builder_Worker** — aggregates normalized ticks into 1m, 5m, 15m (trading timeframes) and 1H/4H/Daily/Weekly/Monthly (POI timeframes) candles, stitching historical backfill and live ticks into one continuous series with no gap and no duplicate candle.

**Check gate:** simulate a WS disconnect mid-stream and confirm REST fallback engages within the drop-detection window with zero missing candles; confirm a freshly-activated symbol shows 5 days of history immediately; confirm no duplicate or gapped candles across a 24-hour soak test.

## 3. Tier 2 — Market_Data_Monitor Assembly
Wires the 6 Workers behind one interface: `get_live_candle(symbol, tf)`, `get_historical_candles(symbol, tf, days)`, `subscribe(symbol)`, `unsubscribe(symbol)`, `get_health()` (returns OK/DEGRADED/DOWN based on WS vs fallback state).

**Check gate:** call every interface function from a standalone test harness with two symbols active simultaneously; confirm subscribing/unsubscribing a symbol never affects any other active symbol's stream (proves per-symbol isolation).

## 4. Deliverable
Lock this file once both gates pass. Version → v0.2.0-alpha. Proceed to file 03.
