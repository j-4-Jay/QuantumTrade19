# QuantumTrade19 — Deliverables Ledger

Cumulative, module-by-module record of every deliverable against the Architecture Blueprint and each module's own spec. Unlike `CURRENT_STATUS.md` (latest snapshot only), this file never shrinks — new modules are appended below the last one, and existing rows are only edited to flip a status (Not Done → Done), never deleted.

**Status key:** ✅ Done · ⚠️ Partial · ❌ Not Done

**Last updated:** August 19, 2026

---

## File 01 — UI/UX Design System & App Shell
**Status:** LOCKED — `v0.1.10-module01-gapclosure-locked` — 2026-08-15

| Deliverable | Status | Notes |
|---|---|---|
| Argon2 password hashing (replaces SHA-256) | ✅ Done | Breaking change — old accounts required re-registration |
| Generic settings `get_setting`/`set_setting` passthrough | ✅ Done | Named accessors left intact |
| Per-symbol setting interface stubs | ✅ Done | Interface-only; real exercise deferred to Module 02 |
| `settings.json` stays plain JSON | ✅ Done | Confirmed decision — settings only, not secrets |
| CSS cross-fade for theme switching | ✅ Done | |
| Sound engine wired to real placeholder tones | ✅ Done | 6 generated `.wav` tones, swappable later |
| Animation_Choreographer_Worker / Page_Transition_Worker connected | ✅ Done | Selection logic moved out of AppState into the Workers |
| Tab-to-tab switch animation | ✅ Done | Independently Settings-controlled |
| Custom cursor stays removed | ✅ Done | Confirmed decision, no build needed |
| "Remember this device" 60-day TOTP-skip toggle | ✅ Done | OS-keyring, machine-bound |
| Shake animation + error sound on failed login | ✅ Done | |
| Register path reachable from Login | ✅ Done | Bugfix discovered mid-round |
| Pre-login screens theme CSS variables | ✅ Done | Bugfix — vars were shell-only, now app-root |
| Square hover-shadow on rounded buttons | ✅ Done | Bugfix — Radix state-layer overlay clipping |
| Tray icon / minimize-to-tray | ❌ Not Done | Deferred to Module 19 |
| Full per-symbol-settings exercise/testing | ❌ Not Done | Deferred to Module 02 (needs real Symbol Registry) |

## File 02 — Market Data Monitor
**Status:** LOCKED — `v0.2.0-alpha` — 2026-08-17

| Deliverable | Status | Notes |
|---|---|---|
| `MarketDataMonitor` public interface | ✅ Done | `get_live_candle`, `get_historical_candles`, `subscribe`, `unsubscribe`, `get_health` |
| `SymbolRegistryWorker` | ✅ Done | Active symbols, Futures identities, tick metadata, favorites |
| `WSFeedWorker` + `curl_cffi` Chrome TLS/JA3 impersonation | ✅ Done | Required by CoinDCX gateway fingerprint filtering |
| Aggregated-stream partial-delta handling | ✅ Done | No false-tick warnings on metadata-only rows |
| `RestPollFallbackWorker` | ⚠️ Partial | Functionally working, but has an unresolved import-name defect — see `KNOWN_ISSUES.md` ISSUE-001 |
| `TickNormalizerWorker` | ✅ Done | |
| `HistoricalDataLoaderWorker` — Futures `pcode=f` correction | ✅ Done | |
| Native/derived timeframe support (1m/5m/1H/1D native; 15m/4H/1W/1M derived) | ✅ Done | |
| `CandleBuilderWorker` seed/live stitching fix | ✅ Done | Fixed one-time 5m/15m duplicate seam |
| Deep History extras: manifest, downloader, depth prober, ceiling/progress APIs | ✅ Done | |
| Persistent runtime logging (`quantumtrade19.log`, `errors.log`) | ✅ Done | UTC timestamps, daily rotation, 30-day retention |
| 24-hour BTC+ETH soak test | ✅ Done | 0 gaps, 0 duplicates across 1m/5m/15m |
| System Health Monitor reconnect/backoff accounting refinement | ❌ Not Done | Deferred to File 08, not a File 02 lock blocker |

## File 03 — POI Monitor
**Status:** LOCKED — `v0.3.0-alpha` — 2026-08-17

| Deliverable | Status | Notes |
|---|---|---|
| `POIMonitor` public interface | ✅ Done | `get_active_pois`, `get_poi_state`, `set_poi_type_enabled` |
| `POILevelCalculatorWorker` | ✅ Done | 1M/1W H/L, PDH/PDL, 4H H/L, Resistance/Support Flip |
| `FVGDetectorWorker` | ✅ Done | |
| `OrderBlockDetectorWorker` | ✅ Done | |
| `InverseFVGDetectorWorker` | ✅ Done | Role-flip per 123Bull/123Bear Scenario B rules |
| `POIStateTrackerWorker` | ✅ Done | Approaching → Hit → Crossed → Retesting |
| Shared support (`poi_types.py`, `candle_access.py`, `htf_availability.py`) | ✅ Done | |
| Default strategy-active POIs (PDH/PDL, 4H H/L) | ✅ Done | |
| Automated test suite | ✅ Done | 41/41 passed |
| Real CoinDCX Futures validation | ✅ Done | PDH/PDL/4H matched live terminal |
| Previous H/L lines for 1m/5m/15m/1H | ❌ Not Done | Out of File 03's original scope — deferred to 03.1 |
| Zone source-timeframe matrix | ❌ Not Done | Deferred to 03.1 |
| Display-vs-strategy independent settings | ❌ Not Done | Deferred to 03.1 |
| Trading Panel chart rendering | ❌ Not Done | Deferred to 03.1 |
| Persistent drawing workspace / undo-redo | ❌ Not Done | Deferred to 03.1 |
| Deep Historical Data UI extension | ❌ Not Done | Deferred to 03.1 |

## File 03.1 — Pre-File-04 Enhancement Patch
**Status:** IN PROGRESS — not locked. Do not start File 04 until this is fully locked.

### Scope A — POI Matrix Enhancement

| Deliverable | Status | Notes |
|---|---|---|
| A1 — Previous completed H/L for all 8 timeframes (1m/5m/15m/1H/4H/1D/1W/1M) | ✅ Done | Current-forming-candle exclusion confirmed |
| A2 — Zone source-TF matrix: FVG, Order Block, Inverse FVG | ✅ Done | Default 1m=ON, 15m=ON confirmed |
| A2 — Zone source-TF matrix: Resistance Flip, Support Flip | ❌ Not Done | Explicit gap flagged in Batch 1-2 progress note |
| A3 — `display_enabled`/`strategy_enabled` data model + persistence foundation | ✅ Done | |
| A3 — `POIMonitor` wiring to actually apply/persist the new settings | ❌ Not Done | Detectors still run through legacy direct-worker path for backward compatibility |
| A4 — New deterministic tests (matrix/settings/detector) | ✅ Done | 22 + 22 targeted tests passed |
| A4 — Full whole-repository regression confirmation | ⚠️ Partial | 67 passed on last targeted run, but whole-repo `pytest` currently can't even collect — blocked by ISSUE-001 |
| UTC source metadata added to FVG/OB/Inverse-FVG outputs | ✅ Done | |

### Scope B — Trading Panel Chart Foundation
| Deliverable | Status |
|---|---|
| B1 — Futures-only TradingView-style chart | ❌ Not Done |
| B2 — Chart-only Night/Day theme control + POI palettes | ❌ Not Done |
| B3 — Per-symbol chart display window (X/A/B days) | ❌ Not Done |

### Scope C — POI Chart Overlay and Inspection
| Deliverable | Status |
|---|---|
| C1 — System POI rendering (lines + zones) | ❌ Not Done |
| C2 — Logical labels and tooltips | ❌ Not Done |
| C3 — Trading Panel temporary POI filters | ❌ Not Done |

### Scope D — Persistent User Chart Workspace
| Deliverable | Status |
|---|---|
| D1 — Auto-saved workspace per symbol+timeframe | ❌ Not Done |
| D2 — Full drawing toolset | ❌ Not Done |
| D3 — 50-step undo/redo | ❌ Not Done |

### Scope E — Settings UI
| Deliverable | Status |
|---|---|
| "POI Engine & Chart Visibility" Settings card | ❌ Not Done |

### Scope F — Deep Historical Data Card Upgrade
| Deliverable | Status |
|---|---|
| A/B day counters + download/cancel/clear controls | ❌ Not Done |

### Scope G — Premium UI/UX Motion
| Deliverable | Status |
|---|---|
| Purposeful motion set + reduced-motion support | ❌ Not Done |

### Final Lock
| Deliverable | Status |
|---|---|
| All applicable validation gates passed end-to-end | ❌ Not Done |
| Immutable build-log summary/summaries written | ❌ Not Done |

---

## Cross-Cutting Blocker

**ISSUE-001** (see `KNOWN_ISSUES.md`) — File 02's `RESTPollFallbackWorker` import mismatch blocks any genuinely whole-repository green test run. Must be fixed and locked as its own versioned entry before File 03.1 Batch 3's A4 full-regression item can be marked ✅ Done.
