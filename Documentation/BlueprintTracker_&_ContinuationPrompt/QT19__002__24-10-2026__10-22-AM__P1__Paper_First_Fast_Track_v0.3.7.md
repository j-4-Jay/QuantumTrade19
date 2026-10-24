# QuantumTrade19 - Blueprint and Tracker (BRIDGE STARTER v0.1.0)

| This file | `QT19__002__24-10-2026__10-22-AM__P1__Paper_First_Fast_Track_v0.3.7.md` |
| Previous version | `QT19__001__23-10-2026__03-14-AM__P1__FT1_Confidence_Score_v0.3.6.md` (kept side by side) |
| Generated | 24-10-2026, 10:22 AM IST |
| Last file number issued | 083 |
| Tracker version | v0.3.7 (Record paper-first plan and decisions C-G; archive old A1) |
| Project | QuantumTrade19 (QT19) |
| Thread number | 002 |
| Status | BRIDGE STARTER - to be filled in during thread 001 from the old QT19 tracker |

## PART A

<!-- SECTION:A1 -->
<!-- CONTINUATION_PROMPT_START -->
this thread = 2
PROJECT: QuantumTrade19 (QT19). Tool: 4. Project_Operations v2.0.1. AI instruction v1.2.1 (Documentation\Instructions). Live status record: Documentation\Project_Status\QT19_Project_Status.csv (page: 4c. Open_Project_Status.bat). Task plan: Task Tree v02.html (paper-first order, Jay 24-10-2026). Task Tree v01.html is kept as history.
FOCUSED UNIT: Step 1 = FT-3 Alert system, Discord + Telegram (File 06, Project File 06_AlertMonitor_Prompt.md), starting with FT-3.8: the situation catalogue and message style guide (texts, icons, layout, human tone). Jay approves the samples before any code. Trade numbers join the messages after Step 2 (FT-3.11).
PLAN ORDER (Decision C): Step 1 FT-3 Alerts; Step 2 FT-2 Risk math; Step 3 FT-4 Paper account; Step 4 FT-6 Paper execution, trailing, auto paper trades; Step 5 FT-5 Paper journal and PnL; Step 6 FT-1 Confidence Score; Step 7 FT-7 Auto trade with Paper/Live. Stage ids keep their old numbers; the Step number is in each title.
DECISIONS (Jay, 24-10-2026): D = one sizing and TP selector (Fixed Risk: size from flat risk, TP by RRR; or Fixed RRR with a fixed margin), RRR is net of fees. E = alert levels Info / Important / Critical with routing, Critical ignores snooze. F = leverage 1 to 5000, default cap = the symbol's broker maximum plus an experiment switch (tagged not broker-realistic) and a liquidation-before-SL check; any symbol; flat balance and flat risk set in the Trading Panel; all five trailing methods in the first version; slippage v1 = fixed ticks plus taker fee, replaceable model. G = Confidence Score: all 20 filters default ON, partial points (AI proposes steps, Jay approves), any timeframe scored at its own confirmation, filters that cannot be scored are left out and the rest rescaled to 100.
CONFIRMED PROGRESS (Jay, 23-10-2026): Status page and Task Tree v01 LOCKED. Jay locked in the Status CSV: M01, M02 (incl. Deep History), M03, M031a-c, M04a-c. Decision A: SL source = both, with a switch, default setup candles. Decision B: fast-track plan first. App start fixed (request 058 stop script, 060 Debug in reload exclude). Office pull fixed 23-10-2026 (loose Status copies moved to Clutter\office_before_pull); app and Status page run at the office.
UNTESTED WORK: CSV changes and Task Tree v02 applied by requests 079 and 081 (24-10-2026); Jay's 7-point check list (page opens, v02 title, Step order, FT-3 and FT-2 tasks, decisions C-G DECIDED and DEC-H OPEN, locked rows unchanged, no red error) is pending. Nothing from this plan is built or locked.
LOCKED AREAS: as in the CSV (FT-0.2 and M01-M04 rows Jay-locked); the tool has no locked-path list registered yet.
OPEN: DEC-H Confidence rules (MTF filters 10-11, journal filters 15-17 without history, filters 13-14 without data) wait for Step 6; M031d drawings REOPENED; M04d, M04e unchecked; parents M031 and M04 PENDING; FT-0.1 waits for Jay's lock; PO-02 bridge: locked paths and Part B Blueprint (TRACKER has no key; the CSV and Task Tree v02 are the plan record). Candidate improvements: market data start-up blocks the main thread about 22 s on first page load; page progress bars follow the Docs column; 5. Pull_From_GitHub.ps1 prints Done even when the pull fails (check git log -1 after every pull).
SAFETY: no live trading, no broker credentials via this tool (rule 4.6). Webhooks and bot token go to secure key storage, never to data/settings.json (pushed to a public repo).
TOOL NOTE: REPLACE anchors are matched as WHOLE lines (leading spaces ignored); read the line first with SEARCH. Several ops in one REPLACE request work; INSERT_AFTER takes only the new lines.
NEXT REQUEST FILE NUMBER: 084. Request files are named 002__<number>__<MODE>_...
FIRST ACTIONS FOR THE AI:
1. Ask Jay for the 7-point check result if not given; after he confirms, LOCK push (CSV, Task Tree v02, tracker).
2. Write FT-3.8: the numbered situation catalogue (market watch, setup lifecycle, trade lifecycle, account and risk, system health, periodic) with sample Discord and Telegram messages for Jay to approve. No code before approval.
3. Read File 06 plan and SEARCH engines\monitors and ui\pages for any existing alert code; then write new-file requests with named tests and risks.
4. After Jay tests and confirms: update CSV rows (REPLACE), then TRACKER, then LOCK.
<!-- CONTINUATION_PROMPT_END -->
<!-- /SECTION:A1 -->

<!-- SECTION:A2 -->
## A2 - STATUS BOARD
<!-- STATUS_BOARD_START -->
| ID | Item | Status | Phase/Batch | Date | Source |
|---|---|---|---|---|---|
| PO-01 | Install Project Operations into QT19 | ✅ LOCKED | P0 | 21-10-2026 | install pack |
| PO-02 | Bridge the old QT19 tracker into this tracker | 🚧 IN_PROGRESS | P0 | 21-10-2026 | thread 001 |
| PO-03 | Pilot: one small unlocked change through REPLACE | ✅ LOCKED | P0 | 21-10-2026 | thread 001 |
| PO-04 | Turn on the watcher and VS Code auto-start task | ✅ LOCKED | P0 | 21-10-2026 | thread 001 |
| M-01 | File 01 UI/UX and App Shell (incl. Security) | ✅ LOCKED | Phase 1 | 23-10-2026 | Module01 gap-closure summary |
| M-02 | File 02 Market Data Monitor (incl. Deep History) | ✅ LOCKED | Phase 1 | 23-10-2026 | v0.2.0 summary |
| M-03 | File 03 POI Monitor | ✅ LOCKED | Phase 1 | 23-10-2026 | v0.3.0 summary |
| M-03.1 | File 03.1 Pre-File-04 Enhancement Patch | ⏸ PENDING | Phase 1 | 21-10-2026 | v0.5.0 tracker |
| M-03.2 | POI Chart Overlay Wiring v0.5.0 | ✅ LOCKED | Phase 1 | 23-10-2026 | v0.5.0 tracker |
| M-04 | File 04 Setup Detection Monitor | ⏸ PENDING | Phase 1 | 21-10-2026 | Jay decision; v0.4.0.3 v4 LOCKED tracker |
| M-05 | File 05 Confidence Monitor | ⏳ NOT_STARTED | Phase 1 | 21-10-2026 | Blueprint v6 |
| M-06 | File 06 Alert Monitor | ⏳ NOT_STARTED | Phase 1 | 21-10-2026 | Blueprint v6 |
| M-07 | File 07 Journal Monitor | ⏳ NOT_STARTED | Phase 1 | 21-10-2026 | Blueprint v6 |
| M-08 | File 08 System Health Monitor | ⏳ NOT_STARTED | Phase 1 | 21-10-2026 | Blueprint v6 |
| M-09 | File 09 Master Alert Engine (Phase 1 lock) | ⏳ NOT_STARTED | Phase 1 | 21-10-2026 | Blueprint v6 |
| M-10 | File 10 Risk Math Monitor | ⏳ NOT_STARTED | Phase 2 | 21-10-2026 | Blueprint v6 |
| M-11 | File 11 Execution Monitor (manual) | ⏳ NOT_STARTED | Phase 2 | 21-10-2026 | Blueprint v6 |
| M-12 | File 12 Master Trading Engine Manual (Phase 2 lock) | ⏳ NOT_STARTED | Phase 2 | 21-10-2026 | Blueprint v6 |
| M-13 | File 13 Execution Monitor Auto Upgrade | ⏳ NOT_STARTED | Phase 3 | 21-10-2026 | Blueprint v6 |
| M-14 | File 14 Master Trading Engine Auto (Phase 3 lock) | ⏳ NOT_STARTED | Phase 3 | 21-10-2026 | Blueprint v6 |
| M-15 | File 15 Learning Monitor | ⏳ NOT_STARTED | Phase 4 | 21-10-2026 | Blueprint v6 |
| M-16 | File 16 Master Learning Engine (Phase 4 lock) | ⏳ NOT_STARTED | Phase 4 | 21-10-2026 | Blueprint v6 |
| M-17 | File 17 Intelligence Monitor | ⏳ NOT_STARTED | Phase 5 | 21-10-2026 | Blueprint v6 |
| M-18 | File 18 Master Intelligence Engine (Phase 5 lock) | ⏳ NOT_STARTED | Phase 5 | 21-10-2026 | Blueprint v6 |
| M-19 | File 19 Packaging and Cross-Platform Distribution | ⏳ NOT_STARTED | Final | 21-10-2026 | Blueprint v6 |
<!-- STATUS_BOARD_END -->
<!-- /SECTION:A2 -->

<!-- SECTION:A3 -->
Phase: P1 - paper-first fast track (Task Tree v02). Step 1 = FT-3 Alert system (Discord + Telegram). FT-0 foundation is done except FT-0.1 (Jay's lock) and the open items in A4. Live status: Documentation/Project_Status/QT19_Project_Status.csv. Progress Register v0.1.0 is frozen history.
<!-- /SECTION:A3 -->

<!-- SECTION:A4 -->
Open decisions: DEC-H (Confidence Score rules for MTF filters 10-11, journal filters 15-17 without history, filters 13-14 without data) waits for Step 6. Decided 24-10-2026: C paper-first order, D sizing/TP selector and net RRR, E alert levels, F leverage cap and trailing and slippage v1, G Confidence rules.
Open work: Jay's 7-point check of Task Tree v02 and the CSV; M031d drawings (no drawing tool in the chart); M04d and M04e unchecked; parents M031 and M04 PENDING; FT-0.1 waits for Jay's lock; PO-02 bridge (locked paths and Part B Blueprint).
Candidate improvements: move the market data start-up off the main thread (about 22 s freeze on first page load); 5. Pull_From_GitHub.ps1 reports Done even when the pull fails.
<!-- /SECTION:A4 -->

<!-- SECTION:A5 -->
Jay now: (1) run the 7-point check of the Status page and Task Tree v02 and tell the AI pass or fail; (2) after that, approve the LOCK push so the office gets the new plan; (3) review the Step 1 alert samples when the AI delivers them.
<!-- /SECTION:A5 -->

<!-- SECTION:A6 -->
Next thread needs: the New Thread Pack, tracker v0.3.7 or newer, the Status CSV and Task Tree v02. No source files.
<!-- /SECTION:A6 -->

<!-- SECTION:C-INDEX -->
## C-INDEX
- C-PROMPT-HISTORY: every earlier continuation prompt, kept in full.
- Old QT19 trackers: `tracker_files\` (historical, unchanged).
<!-- /SECTION:C-INDEX -->

<!-- SECTION:C-LOG-T002 -->
### C-LOG-T002 - thread log
24-10-2026 thread 002: Jay re-ordered the fast track to paper-first (Decision C) and decided D, E, F, G. Requests 079 and 081 changed the Status CSV (11 rows replaced, 21 rows added, FT row updated) and created Task Tree v02.html; v01 kept. DEC-H open. Not yet checked by Jay. Part B Blueprint not updated: the TRACKER mode has no key for it.
<!-- /SECTION:C-LOG-T002 -->

<!-- SECTION:C-LOG-T001 -->
### C-LOG-T001 - thread log
20-10-2026 Thread 001: Requests 004-006 read old tracker v0.5.0 (newest of 202 heading hits in tracker_files). Request 007 bridged A1, A3-A6. Old A1 archived as H-001.
21-10-2026: Jay locked PO-01, set PO-04 to testing, PO-02 in progress. Decision: File 04 LOCKED, next File 05. SPEC read for ADD_ITEM, LOCKED_PATHS, SELFUPDATE and the watcher idle line.
21-10-2026: Request 017 added the quiet watcher (4c files, core untouched); tests 3/3 passed on Jay's machine; Jay confirmed PO-03 and PO-04 as LOCKED. Note: A1 still shows the earlier prompt (next request 017); it will be refreshed with a prompt-history entry at the next SET_A1 or NEW_THREAD.
23-10-2026: Fast-track plan FT-0 to FT-7 approved by Jay (Task Tree v01). Decision A: SL source = both with a switch, default setup candles. Decision B: fast-track plan goes before the older roadmap order in A4.
23-10-2026: Status CSV and pages live in Documentation\Project_Status (launcher 4c. Open_Project_Status.bat, quiet server 4c. Project_Status_Server.py). Progress Register v0.1.0 is frozen; the CSV replaces it. Project instruction v1.2.1 pasted by Jay (no full progress table in replies).
23-10-2026: App start problem. Backend restarted itself every ~2 s for minutes at start. Fixes applied: 2. Stop_QuantumTrade19.ps1 now ends the whole process tree (request 058); Debug added to the reload exclude list in rxconfig.py (request 060). Exact trigger not proven; Jay reports the app runs well now. Market data start-up still blocks the main thread for about 22 s on first page load (candidate improvement).
23-10-2026: Jay locked M01, M02, M03, M031a-c, M04a-c in the Status CSV. M031d (drawings) REOPENED: no drawing tool in the chart. M04d and M04e not yet checked.
--- END TEXT ---
23-10-2026: Hand-over H-004 from thread 001 to thread 002 for FT-1. Old A1 archived in C-PROMPT-HISTORY. Stray END TEXT lines in A3 to A5 replaced by this update.
Automatic operations log (thread 001):
- 001 PREFLIGHT - OK (0 file(s))
- 002 REPLACE - OK (1 file(s))
- 003 UNDO_LAST - OK (1 file(s))
- 004 SEARCH - OK (0 file(s))
- 005 SEARCH - OK (0 file(s))
- 006 COLLECT - OK (0 file(s))
- 007 TRACKER - OK (1 file(s))
- 008 COLLECT - OK (0 file(s))
- 010 COLLECT - OK (0 file(s))
- 011 SEARCH - OK (0 file(s))
- 009 SEARCH - OK (0 file(s))
- 012 COLLECT - OK (0 file(s))
- 013 COLLECT - OK (0 file(s))
- 014 SEARCH - OK (0 file(s))
- 015 SEARCH - OK (0 file(s))
- 016 TRACKER - OK (1 file(s))
- 017 REPLACE - OK (4 file(s))
- 018 TRACKER - OK (1 file(s))
- 019 TRACKER - OK (1 file(s))
- 020 COLLECT - OK (0 file(s))
- 021 TRACKER - OK (1 file(s))
- 022 SEARCH - OK (0 file(s))
- 023 COLLECT - OK (0 file(s))
- 024 SEARCH - OK (0 file(s))
- 025 SEARCH - OK (0 file(s))
- 026 PREFLIGHT - OK (0 file(s))
- 027 SEARCH - OK (0 file(s))
- 028 COLLECT - OK (0 file(s))
- 029 REPLACE - OK (1 file(s))
- 030 LOCK - OK (17 file(s))
- 031 LOCK - OK (8 file(s))
- 032 LOCK - OK (2 file(s))
- 033 COLLECT - OK (0 file(s))
- 034 REPLACE - OK (1 file(s))
- 035 LOCK - OK (2 file(s))
- 048 PREFLIGHT - OK (0 file(s))
- 050 REPLACE - STOPPED (0 file(s))
- 051 SEARCH - OK (0 file(s))
- 052 REPLACE - STOPPED (0 file(s))
- 053 SEARCH - OK (0 file(s))
- 054 COLLECT - OK (0 file(s))
- 055 SEARCH - OK (0 file(s))
- 056 COLLECT - OK (0 file(s))
- 057 COLLECT - OK (0 file(s))
- 058 REPLACE - OK (1 file(s))
- 059 SEARCH - OK (0 file(s))
- 060 REPLACE - OK (1 file(s))
- 061 REPLACE - OK (2 file(s))
- 062 SEARCH - OK (0 file(s))
- 063 REPLACE - OK (1 file(s))
- 064 REPLACE - OK (1 file(s))
- 065 TRACKER - OK (1 file(s))
- 066 REPLACE - OK (1 file(s))
- 067 LOCK - OK (11 file(s))
- 068 COLLECT - OK (0 file(s))
- 069 SEARCH - OK (0 file(s))
<!-- /SECTION:C-LOG-T001 -->

<!-- SECTION:C-PROMPT-HISTORY -->
## C-PROMPT-HISTORY - every earlier continuation prompt (never delete)
Rule: before a new current prompt replaces the one in A1, the AI adds the old prompt here in full with AMEND. Newest entries go at the bottom.
- 19-10-2026, HANDOVER H-000 | from: install pack v1.0.0 | to: thread 001 | the first prompt is the one now in A1 (nothing earlier exists).
- 20-10-2026, HANDOVER H-001 | from: thread 001 | to: thread 001
[PROMPT-START]
this thread = 1
PROJECT: QuantumTrade19 (QT19). Tool: 4. Project_Operations installed and self-tested. Next request file number: 004 (001-003 were used by the install tests).
FOCUSED UNIT: Adopt Project Operations - bridge the old QT19 tracker into this tracker.
FIRST ACTIONS FOR THE AI:
1. Read Jay's Master rules and the Request Format Card. Do not ask Jay to upload source files.
2. Create one COLLECT request that reads the newest OLD tracker in `tracker_files` (sections only: current phase, locked work, pending work, blueprint).
3. Create one TRACKER request that fills A2 (status board), A3 to A6, LOCKED_PATHS and the Blueprint from that old tracker. Keep the old tracker files unchanged.
4. Before replacing this prompt, archive it into C-PROMPT-HISTORY (see section C-PROMPT-HISTORY).
5. Ask Jay for one small unlocked QT19 change as the pilot.
[PROMPT-END]
- 21-10-2026, - 21-10-2026, HANDOVER H-002 | from: thread 001 | to: thread 001
[PROMPT-START]
this thread = 1
PROJECT: QuantumTrade19 (QT19). Tool: 4. Project_Operations v2.0.1, installed and self-tested.
FOCUSED UNIT: Adopt Project Operations - bridge the old QT19 tracker into this tracker (in progress).
CONFIRMED PROGRESS: Requests 004 and 005 (SEARCH) listed all 202 headings in tracker_files. Request 006 (COLLECT) read the newest old tracker: tracker_files/v0.5.0_POIChartOverlayWiring_Tracker.md, STATUS LOCKED as of 2026-09-06, base v0.4.62 (LOCKED). Request 007 (this TRACKER) records the bridge: A1, A3 to A6 and one log entry.
LOCKED AREAS (from the old v0.5.0 tracker, Jay-confirmed there, not re-verified): POI chart overlay wiring (lines, zones, markers, droplets, bulk controls, candle style, crosshair, chart background, sidebar 3-stage collapse, settings persistence); File 03 POI Monitor v0.3.0-alpha plus 03.1 patch; File 02 Market Data Monitor. The tool has no locked paths registered yet.
UNTESTED WORK: none.
NOT YET BRIDGED: A2 status board, LOCKED_PATHS and the Part B Blueprint. The Request Format Card gives no key for them (ADD_ITEM ROW format and LOCKED_PATHS are not in the card).
OPEN DECISIONS: (1) The old v0.5.0 tracker says the next module is File 04 Setup Detection Monitor, but older trackers show File 04 as LOCKED (v0.4.0-alpha_SetupDetectionMonitor_Tracker_v2 and v0.4.0.3_File04_CoreCorrection_Tracker_v4_LOCKED). Jay must say which is correct. (2) Choose the pilot change.
NEXT REQUEST FILE NUMBER: 008.
FIRST ACTIONS FOR THE AI:
1. Create a SEARCH or COLLECT request to read the tool SPEC for TRACKER (status board row format, LOCKED_PATHS, Blueprint) from the Project_Operations core file. Do not guess syntax.
2. Create a TRACKER request that fills A2, LOCKED_PATHS and the Blueprint from the old trackers, after Jay settles open decision 1.
3. Keep all old tracker files unchanged.
4. Ask Jay for one small unlocked QT19 change as the pilot.
[PROMPT-END]
- 21-10-2026, - 21-10-2026, HANDOVER H-003 | from: thread 001 | to: thread 001
[PROMPT-START]
this thread = 1
PROJECT: QuantumTrade19 (QT19). Tool: 4. Project_Operations v2.0.1, installed and self-tested.
FOCUSED UNIT: Adopt Project Operations - finish the bridge of the old QT19 tracker (PO-02, in progress).
CONFIRMED PROGRESS: Requests 004-005 listed the old tracker headings; 006/008 read the newest old tracker (tracker_files/v0.5.0_POIChartOverlayWiring_Tracker.md, LOCKED 2026-09-06) and the new tracker matched it; 007 wrote tracker v0.2.0; 009 and 014 read the tool SPEC (ADD_ITEM rows have 6 columns; LOCKED_PATHS is a tracker block with no TRACKER key; SELFUPDATE needs the whole core file); 010-012 read the watcher (4b. Watch_Requests.bat only starts the core; the repeated idle line comes from cmd_run in 4. Project_Operations_Core.py, looped every 2 seconds by cmd_watch). Jay decided 21-10-2026: File 04 is LOCKED and the next module is File 05 Confidence Monitor; PO-01 is LOCKED by Jay; PO-04 is being tested by Jay; the watcher is to be quieted with a new launcher file, core untouched.
LOCKED AREAS (from old trackers, Jay-confirmed there, not re-verified): File 01 UI/UX and App Shell plus gap-closure (15-08-2026); File 02 Market Data Monitor v0.2.0-alpha (17-08-2026); File 03 POI Monitor v0.3.0-alpha (17-08-2026) plus 03.1 patch; File 04 Setup Detection Monitor (per Jay, 21-10-2026); POI chart overlay wiring v0.5.0. The tool has no locked paths registered yet.
UNTESTED WORK: none applied. The quiet watcher launcher is not built yet.
NOT YET BRIDGED: A2 rows for modules 01-19, LOCKED_PATHS, Part B Blueprint. TRACKER has no key for LOCKED_PATHS or the Blueprint; a way must be found from the SPEC.
OPEN DECISIONS: (1) Which file paths to register as locked (small list, Jay approves each). (2) Pick the pilot change (PO-03). (3) Whether the watcher fix lives in a new launcher file only.
NEXT REQUEST FILE NUMBER: 017.
FIRST ACTIONS FOR THE AI:
1. Read the output of request 015 (core main and make_ctx) and write the quiet watcher launcher as new files only via WRITE_FILE; never edit the core.
2. Add A2 rows for modules 01-19 with ADD_ITEM (6 columns: ID, Item, Status, Phase/Batch, Date, Source), statuses only from evidence.
3. Find the route for LOCKED_PATHS and the Blueprint; do not guess.
4. Ask Jay for one small unlocked QT19 change as the pilot.
5. When Jay approves, run NEW_THREAD for File 05 Confidence Monitor.
[PROMPT-END]
- 23-10-2026, 23-10-2026, HANDOVER H-004 | from: thread 001 | to: thread 002
[PROMPT-START]
this thread = 1
PROJECT: QuantumTrade19 (QT19). Tool: 4. Project_Operations v2.0.1.
FOCUSED UNIT: Adopt Project Operations - finish PO-02 (bridge) in thread 001.
CONFIRMED PROGRESS (Jay-confirmed 21-10-2026): PO-01, PO-03, PO-04 LOCKED. Quiet watcher = 4 new 4c files (core untouched), tests 3/3. A2 now has module rows M-01..M-19 (04 per Jay decision). Old tracker v0.5.0 bridged. File 04 is LOCKED; next module is File 05 Confidence Monitor (new thread).
LOCKED AREAS: Files 01-04, 03.1 and POI chart overlay v0.5.0 (from old trackers). Tool has no locked paths registered yet. 4c files are not locked (Jay chose to wait).
UNTESTED WORK: none.
NOT YET BRIDGED: LOCKED_PATHS and Part B Blueprint (TRACKER has no key for them; route must come from the SPEC).
OPEN DECISIONS: which paths to register as locked (Jay approves each); when to lock the 4c files.
NEXT REQUEST FILE NUMBER: 022.
FIRST ACTIONS FOR THE AI:
1. SEARCH the core for how TRACKER/AMEND reaches LOCKED_PATHS and Part B; do not guess.
2. Fill LOCKED_PATHS and the Blueprint from the old trackers once Jay approves the path list.
3. When Jay approves, COLLECT A1, then NEW_THREAD for File 05.
[PROMPT-END]
- 24-10-2026, HANDOVER H-005 | from: thread 002 | to: thread 002 (24-10-2026, paper-first plan)
[PROMPT-START]
this thread = 2
PROJECT: QuantumTrade19 (QT19). Tool: 4. Project_Operations v2.0.1. AI instruction v1.2.1 (Documentation\Instructions). Live status record: Documentation\Project_Status\QT19_Project_Status.csv (page: 4c. Open_Project_Status.bat). Task plan: Task Tree v01.html (FT-0 to FT-7, approved by Jay 22-10-2026).
FOCUSED UNIT: FT-1 Confidence Score (File 05, Project File 05_ConfidenceMonitor_Prompt.md), starting with FT-1.1.
CONFIRMED PROGRESS (Jay, 23-10-2026): Status page and Task Tree LOCKED. Jay locked in the Status CSV: M01, M02 (incl. Deep History), M03, M031a-c, M04a-c. Decision A: SL source = both, with a switch, default setup candles. Decision B: fast-track plan first. App start problem fixed by the stop script (ends the process tree, request 058) and Debug in the reload exclude list (rxconfig.py, request 060); Jay says the app runs well.
UNTESTED WORK: none.
LOCKED AREAS: as listed above; the tool has no locked-path list registered yet.
OPEN: M031d drawings REOPENED (no drawing tool in the chart); M04d visualization patch and M04e design unchecked; parents M031 and M04 PENDING; FT-0.1 waits for Jay's lock; PO-02 bridge (locked paths, Blueprint) in progress. Candidate improvements: market data start-up blocks the main thread about 22 s on first page load; page progress bars follow the Docs column, not Jay's lock.
TOOL NOTE: REPLACE anchors are matched as WHOLE lines (leading spaces ignored); a part of a line gives "anchor not found". Read the line first with SEARCH.
NEXT REQUEST FILE NUMBER: 071. Request files are named 002__<number>__<MODE>_...
FIRST ACTIONS FOR THE AI:
1. Read the Request Format Card and the README in Documentation\Project_Status. SEARCH the Status CSV for the FT-1 rows. Do not ask Jay to upload anything.
2. Read the File 05 plan from the Project Files, then SEARCH the local engines folder for any existing confidence code.
3. Write the numbered check list for FT-1.1 (pattern filters), then new-file requests with named tests and risks.
4. After Jay tests and confirms: update the CSV rows (REPLACE), then TRACKER, then LOCK.
[PROMPT-END]
<!-- /SECTION:C-PROMPT-HISTORY -->

<!-- CLUTTER_PROTECT_START -->
<!-- CLUTTER_PROTECT_END -->
<!-- LOCKED_PATHS_START -->
<!-- LOCKED_PATHS_END -->
<!-- SCAN_ALLOW_START -->
<!-- SCAN_ALLOW_END -->
<!-- REQUIRED_SCRIPTS_START -->
| Slot | File | Purpose | Level |
|---|---|---|---|
<!-- REQUIRED_SCRIPTS_END -->

## PART B
Blueprint (phase and subphase tree): to be written into this section in thread 001 from the old QT19 tracker and Jay's description. Any new feature updates this Blueprint in the same work cycle.
