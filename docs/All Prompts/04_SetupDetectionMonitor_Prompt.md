# File 04 — Setup Detection Monitor Engine (Master Build Prompt)
**Depends on:** Files 02–03 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.
**Source of truth for all rules in this file:** `123Bull_Setup_Master_Prompt.md` and `123Bear_Setup_Master_Prompt.md` — implement exactly what those two files specify, with zero deviation.

## 1. Plain Explanation
This is the "pattern spotter" — it watches every closed candle on 1m/5m/15m, near every active POI, and finds the exact 3-candle Red+Green+Green (Bull) or Green+Red+Red (Bear) pattern, following the finite-state machine we locked earlier.

## 2. Tier 1 — Workers

1. **Candle_Color_Classifier_Worker** — tags every closed candle Red or Green using close-vs-open only.
2. **POI_Interaction_Detector_Worker** — for every closed candle, checks it against every active POI from POI_Monitor and tags Touch / Sweep / Cross, plus detects the Scenario-B retest case (post-breakout FVG retest, including the double-cross flip case).
3. **Bull123_FSM_Worker** — implements the full Candle 1/2/3 role-assignment machine from the 123Bull prompt, independently per timeframe (1m/5m/15m never share state).
4. **Bear123_FSM_Worker** — the mirrored machine from the 123Bear prompt.
5. **Engulfing_Detector_Worker** — checks whether Candle 2 fully engulfs Candle 1 at confirmation time, for confidence scoring.
6. **FVG_Confirmation_Detector_Worker** — checks whether Candle 3 forms an FVG with Candle 1 at confirmation time, for confidence scoring.
7. **MTF_Cascade_Worker** — implements the 15m/5m → 1m cascade: timeout window, proximity guard, directional match, early invalidation on HTF-extreme break, and the "no trade at all" fallback, exactly as locked.

**Check gate:** run each FSM against at least 10 hand-verified historical examples per setup type (5 Bull, 5 Bear) and confirm every confirmation, every invalidation, and every candle-recycling event matches manual analysis exactly; confirm no candle is ever reused across two confirmed setups; confirm the MTF cascade correctly cancels on timeout, on proximity breach, and on HTF-extreme break, and correctly tightens to the 1m SL when it succeeds.

## 3. Tier 2 — Setup_Detection_Monitor Assembly
Interface: `get_pending_setups(symbol, tf)`, `get_confirmed_setups(symbol, tf)` (emits the Confirmed Setup event onto the internal event bus for Confidence Monitor and, later, Execution Monitor's Opposite-Setup Exit Guard to consume).

**Check gate:** confirm a confirmed setup event fires exactly once per confirmation, with a unique event ID (supports the idempotency rule locked in the blueprint).

## 4. Deliverable
Lock this file once both gates pass. Version → v0.4.0-alpha. Proceed to file 05.
