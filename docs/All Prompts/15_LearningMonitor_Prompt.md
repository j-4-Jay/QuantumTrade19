# File 16 — Learning Monitor Engine (Master Build Prompt)
**Depends on:** File 15 locked, plus a minimum of several weeks of real Journal history per symbol. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the "coach" — it studies the diary (Journal) for each symbol and quietly suggests better settings, but never changes anything without proving the new settings actually work first.

## 2. Tier 1 — Workers

1. **Backtest_Replay_Worker** — replays Market_Data_Monitor's historical candle store through the exact same Setup_Detection_Monitor and Confidence_Monitor code (not a separate copy) to test alternate filter thresholds without touching live trading.
2. **WalkForward_Optimizer_Worker** — for each symbol, sweeps filter thresholds and the minimum-confidence cutoff across a rolling in-sample window, validates each candidate on the following out-of-sample window, and keeps only combinations that improve performance on both.
3. **Settings_Recommender_Worker** — packages a validated improvement as a proposed settings change, with a plain-language explanation of what changed and why, and starts it in shadow/canary mode (paper trades only, running alongside the current live settings) for a trial period before it can be promoted.

**Check gate:** confirm Backtest_Replay_Worker's simulated results match live-Journal results exactly for the same historical period (no drift between backtest math and live math — this proves it's really reusing the same code, not a second implementation); confirm the walk-forward optimizer never proposes a setting that only worked in-sample but failed out-of-sample; confirm a canary-mode proposal never places a single real order during its trial period.

## 3. Tier 2 — Learning_Monitor Assembly
Interface: `run_optimization(symbol)`, `get_pending_proposals()`, `promote_proposal(id)`, `reject_proposal(id)`.

**Check gate:** confirm every promoted proposal is saved as a new settings version (never an overwrite), and confirm `reject_proposal` cleanly discards a canary without any residual effect on live settings.

## 4. Deliverable
Lock this file once both gates pass. Version → v2.1.0-beta. Proceed to file 17.
