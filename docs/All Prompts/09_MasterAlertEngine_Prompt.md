# File 10 — Master Alert Engine (Phase 1 Lock)
**Depends on:** Files 01–09 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the first "big boss." It doesn't do any small job itself — it just wakes up every Monitor built so far, tells them to start watching, and passes their findings along the chain until an alert reaches your phone or screen. No real money moves in this file — Phase 1 is alerts only.

## 2. What Master Alert Engine Wires Together
Market_Data_Monitor → POI_Monitor → Setup_Detection_Monitor → Confidence_Monitor → Alert_Monitor, with Journal_Monitor and System_Health_Monitor watching everything in parallel. Data flows strictly one direction: ticks become candles, candles become POIs and setups, setups get scored, scored setups above the confidence threshold generate alerts, and every step gets journaled regardless of score.

## 3. Wiring Logic (Step by Step)
1. For every active symbol (Symbol_Registry_Worker's list), Market_Data_Monitor streams candles.
2. POI_Monitor recomputes active POIs for that symbol on every new HTF candle close.
3. Setup_Detection_Monitor checks every new 1m/5m/15m candle close against the active POIs and emits a Confirmed Setup event when a 123Bull/123Bear pattern completes (including MTF cascade logic).
4. Confidence_Monitor scores every confirmed setup.
5. Journal_Monitor logs the setup outcome regardless of score.
6. If the score passes the minimum threshold, Alert_Monitor fires the full chain: tick-distance alerts as price approaches, a "setup found" alert at Candle 2, a "setup confirmed" alert at Candle 3 with the calculated (but not executed) Entry/SL/TP as if a real trade were being tracked, and ongoing simulated SL/Trail/TP alerts computed by the Risk Math logic even though no order is placed yet (Risk Math Monitor itself is built in file 11 — for Phase 1, borrow just its pure calculation functions, not its Execution wiring, to compute these "as-if" levels).
7. System_Health_Monitor watches every Worker's heartbeat throughout.

## 4. Check Gate (Phase 1 Full Acceptance Test)
Run the app for a full trading session on at least 3 live symbols and confirm: every tick-distance band alert fires at the correct distance, every setup confirmation alert matches manual chart analysis, the confidence score shown matches a manual recalculation, every alert reaches System + Telegram + Discord (all enabled recipients) correctly, the Journal contains a complete record of every setup found/discarded/confirmed with full filter breakdowns, and no Worker ever silently dies without System_Health_Monitor catching and restarting it.

## 5. Deliverable — Phase 1 Lock
Once the full acceptance test passes, Phase 1 is complete and locked. Version → **v0.10.0 (Phase 1 stable)**. Proceed to file 11 to begin Phase 2 (manual trading).
