# QuantumTrade19 — Known Issues

Every discovered-but-not-yet-fixed defect goes here the moment it's found, regardless of which module it belongs to. Move an issue to CLOSED with the fix's build-log reference once resolved — never delete the row, so history isn't lost.

**Last updated:** August 20, 2026 — after unblocking ISSUE-001's collection error, a full `pytest -q` run surfaced 14 further failures across Module 01 and Module 02. All logged below, triaged by risk.

---

## OPEN — Category 2: Possibly Real Production Bugs (Highest Priority)

### ISSUE-007 — HistoricalDataLoaderWorker Assumes Wrong Response Shape
- **Module:** File 02 — Market Data Monitor (locked v0.2.0-alpha)
- **Discovered:** 2026-08-20, during full-suite regression after ISSUE-001 fix
- **File:** `engines/workers/market_data/historical_data_loader_worker.py`, line 128 (`_fetch_native`)
- **Symptom:** `body.get("data") or []` throws `AttributeError: 'list' object has no attribute 'get'`. Code assumes the Futures candlestick REST response is a dict with a `"data"` key; it appears to actually be a plain list.
- **Impact:** This is inside `backfill_baseline()` — the exact path that seeds a brand-new symbol's mandatory 5-day baseline on first subscribe. The original 24-hour soak only exercised BTC/ETH, which were likely already seeded before the soak began — this path may never have been exercised the same way in that soak. Potentially breaks subscribing to any genuinely new symbol right now.
- **Status:** OPEN — needs the real current file content to diagnose and fix. High priority.

### ISSUE-006 — MarketDataMonitor Health Reports DOWN Instead of OK
- **Module:** File 02 — Market Data Monitor (locked v0.2.0-alpha)
- **Discovered:** 2026-08-20
- **Tests:** `tests/test_market_data_monitor.py::TestWSDropAndRestFallback::test_fallback_engages_within_window_and_hands_back_on_restore`, `::TestPerSymbolIsolation::test_unsubscribe_one_symbol_does_not_affect_other`
- **Symptom:** After a tick arrives via WS with REST fallback configured, `get_health()[symbol]` returns `"DOWN"` where the test expects `"OK"`.
- **Impact:** Core health-status logic, not a naming mismatch. Needs investigation into whether this is a real regression or a test fixture timing issue.
- **Status:** OPEN — needs `engines/monitors/market_data_monitor.py` to diagnose.

### ISSUE-008 — MasterAppEngine Registration/Recovery Flow Mismatch
- **Module:** File 01 — UI/UX & App Shell (locked v0.1.10)
- **Discovered:** 2026-08-20
- **Tests:** `tests/engines/masters/test_master_app_engine.py::test_register_flow`, `::test_lock_unlock`, `::test_logout_to_splash`, `::test_forgot_password_end_to_end`
- **Symptom:** `finish_registration_without_totp()` returns a `bool`, but a test expects a recovery-code string containing `"-"`. Separately, `acknowledge_recovery_and_enter_shell()` doesn't exist on `MasterAppEngine` at all.
- **Impact:** Unclear yet whether this is a stale test or a dropped/unfinished recovery-code display feature from Module 01. Needs the real file to determine which.
- **Status:** OPEN — needs `engines/masters/master_app_engine.py`.

## OPEN — Category 1: Likely Stale Tests (Lower Risk)

### ISSUE-002 — SymbolRegistryWorker Test/API Mismatch
- **File:** `tests/workers/market_data/test_market_data_workers.py` vs `engines/workers/market_data/symbol_registry_worker.py`
- **Symptom:** Test calls `get_pinned_symbols()` and `add_symbol_manual()`; pytest's own error suggests `get_active_symbols` exists instead. Neither called method appears to exist on the real class.
- **Status:** OPEN — needs `symbol_registry_worker.py` to confirm real method names and rewrite the test.

### ISSUE-003 — TickNormalizerWorker Event Wiring Mismatch
- **File:** same test file vs `engines/workers/market_data/tick_normalizer_worker.py`
- **Symptom:** Test publishes `market_data.tick.raw_ws` and expects `market_data.tick.normalized` to fire; nothing is captured.
- **Status:** OPEN — needs the real file; could be a stale test OR a genuine wiring gap, undetermined yet.

### ISSUE-004 — CandleBuilderWorker Missing `_on_tick`
- **File:** same test file vs `engines/workers/market_data/candle_builder_worker.py`
- **Symptom:** Test calls `builder._on_tick(...)` directly; no such method exists on the real class.
- **Status:** OPEN — needs the real file to find the actual current tick-ingestion method name.

### ISSUE-005 — DeepHistoryDownloaderWorker Constructor Mismatch
- **File:** same test file vs `engines/workers/market_data/deep_history_downloader_worker.py`
- **Symptom:** Test constructs with `http_client=` keyword; real constructor doesn't accept it (same pattern as the original RestPollFallbackWorker fix).
- **Status:** OPEN — needs the real file to find the actual constructor signature.

### ISSUE-009 — SecurityMonitor Missing `skip_totp_enrollment`
- **File:** `tests/engines/monitors/test_security_monitor.py` vs `engines/monitors/security_monitor.py`
- **Symptom:** Method doesn't exist; pytest suggests `begin_totp_enrollment` instead.
- **Status:** OPEN — needs the real file.

## CLOSED

### ISSUE-001 — File 02 RESTPollFallbackWorker Import Mismatch
- **Module:** File 02 — Market Data Monitor (already locked at v0.2.0-alpha)
- **Discovered:** During File 03.1 Batch 1/2 regression testing (2026-08-18)
- **Root cause (confirmed):** `tests/workers/market_data/test_market_data_workers.py` imported the wrong casing (`RESTPollFallbackWorker`) AND assumed an entirely different design (async `http_client`, event-bus auto-engage, `is_active()`, `_on_ws_recovering()`) than the real, locked, soak-tested `RestPollFallbackWorker` (sync `http_get`, direct `engage()`/`disengage()`, `is_engaged()`, `on_tick` callback).
- **Fix:** Rewrote the one affected test to exercise the real synchronous interface. The real production Worker was left untouched, per the rule to preserve locked, soak-tested behavior.
- **Confirmed:** 2026-08-20 — the specific test now passes; collection no longer blocks the full suite.
- **Note:** Fixing this uncovered ISSUE-002 through ISSUE-009 below, previously hidden because the suite couldn't even collect.
