# QuantumTrade19 — Decisions Log

Judgment calls made mid-build that aren't bugs and aren't features, but matter later. Append only — never edit a past entry; add a new entry if a decision is revisited.

---

### DEC-001 — App Lock Shares "Remember This Device" Trust With Initial Login
- **Module:** File 01 — UI/UX & App Shell (gap-closure round)
- **Date:** 2026-08-15
- **Context:** `SecurityMonitor.login()` is shared by both `attempt_login()` (initial login) and `unlock()` (App Lock re-entry). Trusting a device therefore skips TOTP on App Lock unlock too, not just initial login.
- **Decision:** Kept as one shared code path. Splitting the two flows for no clear benefit was judged worse than the shared behavior.
- **Flag for future revisit:** Decide explicitly whether App Lock should require TOTP even on a trusted device, once App Lock's UX is otherwise finalized.

### DEC-002 — Legacy Direct-Worker Construction Preserved During 03.1 Batch 1-2
- **Module:** File 03.1 — POI Matrix Enhancement (Batches 1-2)
- **Date:** 2026-08-18
- **Context:** The new zone source-timeframe matrix and display/strategy settings model were built at the Worker/data level, but `POIMonitor` still routes through the original legacy direct-worker construction path for backward compatibility with existing File 03 tests.
- **Decision:** Defer the actual `POIMonitor` wiring/switchover to Batch 3, rather than risk destabilizing the passing File 03 test suite mid-batch.
- **Flag for future revisit:** None — this is the explicit, planned next step in Batch 3, not an open question.
