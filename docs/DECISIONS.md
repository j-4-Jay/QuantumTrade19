# QuantumTrade19 — Decisions Log

Judgment calls made mid-build that aren't bugs and aren't features, but matter later. Append only — never edit a past entry; add a new entry if a decision is revisited.

---

### DEC-001 — App Lock Shares "Remember This Device" Trust With Initial Login
- **Module:** File 01 — UI/UX & App Shell (gap-closure round)
- **Date:** 2026-08-15
- **Context:** `SecurityMonitor.login()` is shared by both `attempt_login()` and `unlock()`. Trusting a device skips TOTP on App Lock unlock too.
- **Decision:** Kept as one shared code path.
- **Flag for future revisit:** Decide explicitly whether App Lock should require TOTP even on a trusted device.

### DEC-002 — Legacy Direct-Worker Construction Preserved During 03.1 Batch 1-2
- **Module:** File 03.1 (Batches 1-2)
- **Date:** 2026-08-18
- **Context:** New settings model built but not yet wired to `POIMonitor`.
- **Decision:** Deferred the wiring to Batch 3.
- **Flag for future revisit:** None — resolved in Batch 3 (see DEC-007).

### DEC-003 — Fixed Stale Tests Instead of Changing Locked Production Code (ISSUE-001 Through 007)
- **Module:** File 02
- **Date:** 2026-08-20
- **Decision:** Fix every test to match the real code, never the reverse.

### DEC-004 — Implemented the SymbolRegistryWorker Manual-Add Gap Immediately Rather Than Deferring
- **Module:** File 02
- **Date:** 2026-08-20
- **Decision:** Implemented immediately as a pure addition.

### DEC-005 — Rewrote Tests Instead of Building a Recovery-Code-at-Registration Feature (ISSUE-008)
- **Module:** File 01
- **Date:** 2026-08-21
- **Decision:** Treated as an abandoned design; rewrote tests to match the real, locked, channel-based forgot-password flow.

### DEC-006 — Added `force_memory` Isolation to SettingsPersistenceWorker (ISSUE-010)
- **Module:** File 01
- **Date:** 2026-08-21
- **Decision:** Added the missing parameter, mirroring the keystore's existing pattern.

### DEC-007 — Corrected a Self-Introduced Bug in POIMonitor's Tick-Size Lookup
- **Module:** File 03.1 Batch 3 — POIMonitor wiring
- **Date:** 2026-08-21
- **Context:** When first reviewing the handed-over `poi_monitor.py`, `self.symbol_registry.get_tick_size(symbol)` was flagged as calling a nonexistent method, and was changed to `get_symbol_info(symbol).tick_size` on the assumption that `get_tick_size()` had never existed as part of the real interface contract. Running the actual File 03.1 test suite immediately proved this wrong: the suite's own `FakeSymbolRegistry` test double implements `get_tick_size()` directly, confirming that was always the intended, correct contract — the real gap was that the production `SymbolRegistryWorker` never implemented it.
- **Decision:** Reverted `poi_monitor.py`'s call back to `get_tick_size(symbol)`, and added that method to the real `SymbolRegistryWorker` instead (pure addition, wrapping the existing `tick_size` field).
- **Flag for future revisit:** None — resolved, and the whole-suite run afterward (110 passed, 0 failed, same total test count as the broken run) confirms this was the complete, correct fix. Lesson for future batches: when a "missing method" is flagged on a class that has a corresponding test fake, check what the fake actually implements before deciding which side is wrong.
