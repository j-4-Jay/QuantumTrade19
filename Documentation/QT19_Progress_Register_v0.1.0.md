# QT19 Progress Register v0.1.0 (thread 001, 21-10-2026)

Purpose: one table of every phase and sub-phase. The column "Documents say" is what the old files claim. It is NOT confirmed. Only Jay's own check in the software, written in the last two columns, makes a row final.

Status words: LOCKED, NOT_STARTED, DESIGN LOCKED, REOPENED, NO LOCK RECORD FOUND. Final statuses use the tool words (LOCKED, IN_PROGRESS, PENDING and so on) after Jay confirms.

Build order from the roadmap (docs/specs, 08-09-2026): 1 File 04 Core Correction (awaiting final live re-validation), 2 Visual bug fixes, 3 File 02.2 Scanner v2, 4 File 04.1b callouts, 5 File 04.3 multi-window, 6 Historical Setup Backfill.

| ID | Phase | Sub-phase | Documents say | Evidence | Jay checked in software | Jay verdict |
|---|---|---|---|---|---|---|
| R-01 | Phase 1 | File 01 UI/UX and App Shell (incl. Security) | LOCKED | docs/build_log/Module01_GapClosure_FINAL_LOCKED_Summary.md (15-08-2026) |  |  |
| R-02 | Phase 1 | File 02 Market Data Monitor | LOCKED | docs/build_log/v0.2.0_MarketDataMonitor_Summary.md (17-08-2026, 24h soak passed) |  |  |
| R-02a | Phase 1 | File 02 import fix v0.2.1 | LOCKED | docs/build_log/v0.2.1_MarketDataMonitor_ImportFix_Summary.md |  |  |
| R-02b | Phase 1 | File 02 data integrity patch v0.4.8 (SQLite truth) | LOCKED | tracker_files/v0.4.8_TradingPanel_DataIntegrity_Tracker.md |  |  |
| R-02c | Phase 1 | File 02 Deep History work v0.4.9 to v0.4.21 (hotfix, card redesign, gap auto-heal, probe, ETA, progress) | NO LOCK RECORD FOUND | each tracker says do not lock until steps are confirmed; no later lock line found |  |  |
| R-03 | Phase 1 | File 03 POI Monitor | LOCKED | docs/build_log/v0.3.0_POIMonitor_Summary.md (17-08-2026, 41 tests) |  |  |
| R-03a | Phase 1 | File 03.1 Scope A: POI matrix and controls | LOCKED | docs/build_log/v0.3.1_POIMatrixAndControls_Summary.md |  |  |
| R-03b | Phase 1 | File 03.1 Trading Panel live chart and UI polish v0.4.62 | LOCKED | tracker_files/v0.4.62_...Tracker.md (05-09-2026) |  |  |
| R-03c | Phase 1 | File 03.1 POI chart overlay wiring v0.5.0 | LOCKED | tracker_files/v0.5.0_POIChartOverlayWiring_Tracker.md (06-09-2026) |  |  |
| R-03d | Phase 1 | File 03.1 persistent drawings, undo/redo and motion (Scopes D, G) | NO LOCK RECORD FOUND | v0.4.1 tracker said no lock summary for Scopes B to G; only B/C/E/F work is later covered |  |  |
| R-04 | Phase 1 | File 04 Setup Detection Monitor v0.4.0-alpha | LOCKED | docs/build_log/v0.4.0-alpha_SetupDetectionMonitor_Summary.md (26/26 tests, real-chart gate) |  |  |
| R-04a | Phase 1 | File 04.1 Trading Panel setup visualization patch | NO LOCK RECORD FOUND | tracker_files/v0.4.0.1_...Tracker_v1 and v2 |  |  |
| R-04b | Phase 1 | File 04 Core Correction v0.4.0.3 | LOCKED | tracker_files/v0.4.0.3_File04_CoreCorrection_Tracker_v4_LOCKED.md |  |  |
| R-04c | Phase 1 | File 04 Recycle/Touch Gate v0.4.0.4 (reopened File 04) | REOPENED - RE-LOCK NOT FOUND | tracker_files/v0.4.0.4_RecycleTouchGate_Tracker_v1.md; roadmap v2 says awaiting final live re-validation |  |  |
| R-04d | Phase 1 | File 04.1b Custom POI levels and persistent callouts (Track 4 and 7) | DESIGN LOCKED, BUILD NOT CONFIRMED | docs/specs/File_04.1b_CustomPOI_And_Callouts_Spec_Lock_v1.md (08-09-2026) |  |  |
| R-05 | Phase 1 | File 05 Confidence Monitor | NOT_STARTED | no confidence folder under engines/workers in the file map |  |  |
| R-06 | Phase 1 | File 06 Alert Monitor | NOT_STARTED | no alert workers in the file map |  |  |
| R-07 | Phase 1 | File 07 Journal Monitor | NOT_STARTED | no journal workers in the file map |  |  |
| R-08 | Phase 1 | File 08 System Health Monitor | NOT_STARTED | no system_health workers in the file map |  |  |
| R-09 | Phase 1 | File 09 Master Alert Engine (Phase 1 lock) | NOT_STARTED | engines/masters has 3 files; alert master not confirmed |  |  |
| R-10 | Phase 2 | File 10 Risk Math Monitor | NOT_STARTED | no risk_math workers in the file map |  |  |
| R-11 | Phase 2 | File 11 Execution Monitor (manual) | NOT_STARTED | no execution workers in the file map |  |  |
| R-12 | Phase 2 | File 12 Master Trading Engine Manual (Phase 2 lock) | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-13 | Phase 3 | File 13 Execution Monitor Auto Upgrade | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-14 | Phase 3 | File 14 Master Trading Engine Auto (Phase 3 lock) | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-15 | Phase 4 | File 15 Learning Monitor | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-16 | Phase 4 | File 16 Master Learning Engine (Phase 4 lock) | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-17 | Phase 5 | File 17 Intelligence Monitor | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-18 | Phase 5 | File 18 Master Intelligence Engine (Phase 5 lock) | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-19 | Final | File 19 Packaging and Cross-Platform Distribution | NOT_STARTED | Blueprint v6 plan only |  |  |
| R-T2 | Post-04 roadmap | Track 2 visual bug fixes (overlay leakage, zone edges, wick lines, droplet dot) | DESIGN LOCKED | docs/specs/QuantumTrade19_Master_Roadmap_PostFile04_v2.md |  |  |
| R-T3 | Post-04 roadmap | Track 3 File 02.2 Multi-Symbol Opportunity Scanner v2 | DESIGN LOCKED | same roadmap v2 |  |  |
| R-T5 | Post-04 roadmap | Track 5 File 04.3 Multi-Window Chart Workspace | DESIGN LOCKED | same roadmap v2 |  |  |
| R-T6 | Post-04 roadmap | Track 6 Historical Setup Backfill (added 08-09-2026) | DESIGN LOCKED | same roadmap v2 |  |  |

Notes:
- The file map (335 files) shows worker folders only for market_data, poi, security, setup and ui_experience, so Files 05 to 19 have no worker code yet.
- Rows R-04c and R-04d decide what comes next; check them first.
