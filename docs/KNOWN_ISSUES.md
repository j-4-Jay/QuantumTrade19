# QuantumTrade19 — Known Issues

Every discovered-but-not-yet-fixed defect goes here the moment it's found, regardless of which module it belongs to. Move an issue to CLOSED with the fix's build-log reference once resolved — never delete the row, so history isn't lost.

## OPEN

### ISSUE-001 — File 02 RESTPollFallbackWorker Import Mismatch
- **Module:** File 02 — Market Data Monitor (already locked at v0.2.0-alpha)
- **Discovered:** During File 03.1 Batch 1/2 regression testing (2026-08-18)
- **Symptom:** Repository-wide `python -m pytest -q` fails at collection with:
  ```text
  ImportError: cannot import name 'RESTPollFallbackWorker'
  from engines.workers.market_data.rest_poll_fallback_worker
  ```
- **Impact:** Blocks any genuinely whole-repository test run. Targeted test files still run fine, so this has not blocked File 03.1 batch-level checks, but it means no "everything green" claim is currently trustworthy repo-wide.
- **Scope note:** Outside File 03.1's own scope. Must be fixed and recorded as its own separate patch-versioned build-log entry (e.g. `v0.2.1_MarketDataMonitor_ImportFix_Summary.md`) — not folded silently into either File 02's original lock record or File 03.1's record.
- **Next action:** Request current real content of `engines/workers/market_data/rest_poll_fallback_worker.py` plus whichever file contains the failing import, diagnose whether the class was renamed without updating callers (or vice versa), fix, and confirm with a full `pytest -q` run actually completing.
- **Status:** OPEN — this is the mandatory next step before File 03.1 Batch 3 begins.

## CLOSED

*(none yet)*
