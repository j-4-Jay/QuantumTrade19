# File 14 — Execution Monitor Auto-Trade Upgrade (Master Build Prompt)
**Depends on:** File 13 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This upgrade lets the software click Buy/Sell by itself, the instant a confirmed setup passes its confidence threshold — no human needed — but with extra safety nets since real money can now move without you watching every second.

## 2. What Changes in Execution Monitor
1. **Auto-Trigger Wiring** — Execution_Mode_Router_Worker gains a second dimension alongside Paper/Live: a global Manual/Auto switch. In Auto mode, a passing confidence score automatically calls the same `submit_manual_order`-equivalent path (renamed internally to `submit_order`, source tagged `auto` vs `manual` for the journal) with zero human click.
2. **Circuit Breaker Worker (new)** — monitors each Monitor Engine's health flag; if Confidence_Monitor, Risk_Math_Monitor, or Market_Data_Monitor reports DEGRADED or DOWN, Auto mode immediately and automatically falls back to alert-only (Phase 1 behavior) until health recovers — protecting your capital from trading on broken data.
3. **Max Concurrent Trades Guard (new)** — enforces the "any number of setups up to balance permits" rule from the locked setup prompts by checking available margin before every auto-entry, rejecting (and logging) any auto-entry that would exceed available balance.
4. **Dry-Run Toggle (new)** — a master switch, separate from Paper/Live, that when ON routes every single order (even ones marked Live) into the Paper simulator regardless — a full safety rehearsal mode for testing Auto before trusting it with real Live capital.

**Check gate:** verify Auto mode correctly enters a trade with zero manual click the instant a confidence-passing setup confirms; verify a deliberately degraded Confidence_Monitor correctly halts auto-entries and reverts to alert-only, with a clear alert telling you why; verify the max-concurrent-trades guard correctly rejects an entry that would over-leverage the account; verify Dry-Run mode never places a single real order even when the Live/Paper toggle says Live.

## 3. Deliverable
Lock this file once the gate passes. Version → v1.1.0-beta. Proceed to file 15.
