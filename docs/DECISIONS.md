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

### DEC-003 — Fixed Stale Tests Instead of Changing Locked Production Code (ISSUE-001 Through 007)
- **Module:** File 02 — Market Data Monitor (locked v0.2.0-alpha)
- **Date:** 2026-08-20
- **Context:** Seven separate test/code mismatches surfaced while chasing the original import bug. In every case, the real, soak-tested production Worker was confirmed correct, and the test was the stale side.
- **Decision:** Fix every test to match the real code, never the reverse — consistent with the rule to preserve existing File 02 behavior.
- **Flag for future revisit:** None — pattern held consistently across all seven issues with no exceptions.

### DEC-004 — Implemented the SymbolRegistryWorker Manual-Add Gap Immediately Rather Than Deferring
- **Module:** File 02 — Market Data Monitor (locked v0.2.0-alpha)
- **Date:** 2026-08-20
- **Context:** A genuine missing feature against the locked Architecture Blueprint (Section 8's second deep-history eligibility path).
- **Decision:** Implemented immediately as a pure addition, since it was small, clearly specified by an already-locked source-of-truth document, and additive only.
- **Flag for future revisit:** None — closes the gap as specified.

### DEC-005 — Rewrote Tests Instead of Building a Recovery-Code-at-Registration Feature (ISSUE-008)
- **Module:** File 01 — UI/UX & App Shell (locked v0.1.10)
- **Date:** 2026-08-21
- **Context:** `tests/engines/masters/test_master_app_engine.py` and `tests/engines/monitors/test_security_monitor.py` assumed an entire recovery-code-at-registration subsystem: a code returned from registration, a `SecurityMonitor.recovery` sub-object with `generate_recovery_code()`, and a single-argument `verify_identity_for_reset(code)` distinct from the real, two-argument, channel-based version. None of this exists in the real code, and `Module01_GapClosure_FINAL_LOCKED_Summary.md` — the authoritative, locked record of everything actually built in Module 01 — never mentions a recovery code anywhere. Meanwhile, a complete, working, channel-based (TOTP/Telegram/Discord) forgot-password flow already exists and is already wired into the live UI (`app_state.py`).
- **Decision:** Treated this the same as DEC-003's pattern — rewrote both test files to match the real, working, locked flow. Did not build any new recovery-code feature, since there was no blueprint or locked-summary evidence it was ever intended to survive past an early design iteration, and a complete working alternative already exists.
- **Flag for future revisit:** If a recovery-code-at-registration feature is genuinely still wanted as new work, it needs to be scoped, designed, and built deliberately — not inferred from a stale test and quietly added to already-locked, security-critical code.

### DEC-006 — Added `force_memory` Isolation to SettingsPersistenceWorker (ISSUE-010)
- **Module:** File 01 — UI/UX & App Shell (locked v0.1.10)
- **Date:** 2026-08-21
- **Context:** `SecurityMonitor.__init__` already forwards `force_memory` to `SecureKeyStorageWorker` but had no way to forward it to `SettingsPersistenceWorker`, which had no such parameter at all. Every test using `SecurityMonitor(force_memory=True)` was silently sharing and mutating the one real `data/settings.json` file across every test run, letting state like `totp_enabled` leak between unrelated tests.
- **Decision:** Added the missing `force_memory` parameter to `SettingsPersistenceWorker`, mirroring the keystore's existing pattern exactly. Default `False` preserves all existing behavior for every real call site with zero risk.
- **Flag for future revisit:** None — this is a pure test-isolation fix with no production behavior change, since `force_memory=True` is never used outside test code.
