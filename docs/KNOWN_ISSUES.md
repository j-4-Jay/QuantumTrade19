# QuantumTrade19 — Known Issues

Every discovered-but-not-yet-fixed defect goes here the moment it's found, regardless of which module it belongs to. Move an issue to CLOSED with the fix's build-log reference once resolved — never delete the row, so history isn't lost.

**Last updated:** August 21, 2026 — ISSUE-008, 009, and 010 addressed. Awaiting final confirming `pytest -q` run.

---

## OPEN

*(none — pending final confirmation run)*

## CLOSED

### ISSUE-001 — File 02 RESTPollFallbackWorker Import Mismatch
- **Fix confirmed:** 2026-08-20. Test rewritten to match the real synchronous interface. No production file changed.

### ISSUE-002 — SymbolRegistryWorker Test/API Mismatch (+ Manual-Add Gap)
- **Fix confirmed:** 2026-08-20. Test rewritten; manual-add deep-history eligibility path (Blueprint Section 8) implemented as a pure addition.

### ISSUE-003 — TickNormalizerWorker Event Wiring Mismatch
- **Fix confirmed:** 2026-08-20. Test rewritten to call the real static methods directly.

### ISSUE-004 — CandleBuilderWorker Missing `_on_tick`
- **Fix confirmed:** 2026-08-20. Test rewritten to use the real `ingest()` method.

### ISSUE-005 — DeepHistoryDownloaderWorker Constructor Mismatch
- **Fix confirmed:** 2026-08-20. Test rewritten to use the real synchronous interface.

### ISSUE-006 — MarketDataMonitor Health Reports DOWN Instead of OK
- **Fix confirmed:** 2026-08-20. Stale fake transport protocol, plus a genuine test-timing race against a real background timer, both fixed test-side only.

### ISSUE-007 — HistoricalDataLoaderWorker Assumes Wrong Response Shape
- **Fix confirmed:** 2026-08-20. Stale fake HTTP response shape, fixed test-side only.

### ISSUE-008 — MasterAppEngine Registration/Recovery Flow Mismatch
- **Root cause confirmed:** tests assumed an entire recovery-code-at-registration subsystem (`acknowledge_recovery_and_enter_shell()`, a recovery code returned from registration) that does not exist anywhere in the real code and is not documented in the locked `Module01_GapClosure_FINAL_LOCKED_Summary.md`. The real, working, already-locked flow transitions straight to SHELL on success and uses the existing channel-based (TOTP/Telegram/Discord) forgot-password flow, which is already live in the UI.
- **Fix:** Rewrote `tests/engines/masters/test_master_app_engine.py` to match the real flow. No production file changed. See `DECISIONS.md` DEC-005.
- **Fix confirmed:** 2026-08-21, pending final full-suite run.

### ISSUE-009 — SecurityMonitor Missing `skip_totp_enrollment`
- **Root cause confirmed:** stale test call to a method that never existed — skipping TOTP is simply never calling `begin_totp_enrollment()`/`confirm_totp_enrollment()`.
- **Fix:** Rewrote `tests/engines/monitors/test_security_monitor.py` to remove the nonexistent call. No production file changed.
- **Fix confirmed:** 2026-08-21, pending final full-suite run.

### ISSUE-010 — SettingsPersistenceWorker Not Isolated by `force_memory`
- **Module:** File 01 — UI/UX & App Shell (locked v0.1.10)
- **Discovered:** 2026-08-21, while fixing ISSUE-009 — `test_forgot_password_via_recovery` found `has_any_recovery_method()` returning `True` on a completely fresh registration.
- **Root cause confirmed:** `SecurityMonitor.__init__` forwards `force_memory` to `SecureKeyStorageWorker` but never to `SettingsPersistenceWorker`, which had no such parameter at all — every test using `SecurityMonitor(force_memory=True)` was silently sharing and mutating the one real `data/settings.json` file across every test run, letting settings like `totp_enabled` leak between unrelated tests.
- **Fix:** Added a `force_memory` parameter to `SettingsPersistenceWorker` (mirroring the keystore's existing pattern — pure in-memory operation when True, zero disk I/O). Forwarded it from `SecurityMonitor.__init__`. Default is `False`, so every existing call site is completely unaffected — this is a pure, backward-compatible addition, not a behavior change to already-locked functionality.
- **Fix confirmed:** 2026-08-21, pending final full-suite run.
