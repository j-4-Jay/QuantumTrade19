# QuantumTrade19 - Blueprint and Tracker (BRIDGE STARTER v0.1.0)

| This file | `QT19__001__20-10-2026__11-25-PM__P0__Adopt_Project_Operations_v0.2.0.md` |
| Previous version | `QT19__001__19-10-2026__12-01-AM__P0__Adopt_Project_Operations_v0.1.0.md` (kept side by side) |
| Generated | 20-10-2026, 11:25 PM IST |
| Last file number issued | 007 |
| Tracker version | v0.2.0 (Bridge old tracker v0.5.0 into new tracker (A1, A3-A6, log). A2, LOCKED_PATHS, Blueprint wait for SPEC.) |
| Project | QuantumTrade19 (QT19) |
| Thread number | 001 |
| Status | BRIDGE STARTER - to be filled in during thread 001 from the old QT19 tracker |

## PART A

<!-- SECTION:A1 -->
<!-- CONTINUATION_PROMPT_START -->
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
<!-- CONTINUATION_PROMPT_END -->
<!-- /SECTION:A1 -->

<!-- SECTION:A2 -->
## A2 - STATUS BOARD
<!-- STATUS_BOARD_START -->
| ID | Item | Status | Phase/Batch | Date | Source |
|---|---|---|---|---|---|
| PO-01 | Install Project Operations into QT19 | ⏳ NOT_STARTED | P0 | 19-10-2026 | install pack |
| PO-02 | Bridge the old QT19 tracker into this tracker | ⏳ NOT_STARTED | P0 | 19-10-2026 | thread 001 |
| PO-03 | Pilot: one small unlocked change through REPLACE | ⏳ NOT_STARTED | P0 | 19-10-2026 | thread 001 |
| PO-04 | Turn on the watcher and VS Code auto-start task | ⏳ NOT_STARTED | P0 | 19-10-2026 | thread 001 |
<!-- STATUS_BOARD_END -->
<!-- /SECTION:A2 -->

<!-- SECTION:A3 -->
Phase: P0 - Adopt Project Operations. Bridging the old QT19 tracker (newest: v0.5.0 POI Chart Overlay Wiring, LOCKED 2026-09-06) into this tracker. No code change in this phase.
<!-- /SECTION:A3 -->

<!-- SECTION:A4 -->
Open decisions:
1. Old v0.5.0 tracker says next module is File 04 Setup Detection Monitor, but older trackers show File 04 as LOCKED. Jay confirms which is correct.
2. Pick one small unlocked pilot change.
Open or deferred work carried from v0.5.0 (not blockers):
- True 3D-rendered candlesticks (needs a custom renderer).
- Zone timezone-awareness (zones stay UTC only).
- Dashboard, Journal and Reports, Alerts page polish (later polish phase).
- Diagnostic console logging cleanup.
- Buffered and infinite chart scroll-back history.
Still to bridge: A2 status board, LOCKED_PATHS, Blueprint (waiting for tool SPEC).
<!-- /SECTION:A4 -->

<!-- SECTION:A5 -->
Jay now: run request 007 with Project_Operations, press ENTER at the gate, and paste the Output here. Then answer open decision 1.
<!-- /SECTION:A5 -->

<!-- SECTION:A6 -->
Next thread needs: this tracker (new version), the 007 output showing RESULT OK, the answer to open decision 1, and the SPEC reading for A2, LOCKED_PATHS and Blueprint. No source files are needed.
<!-- /SECTION:A6 -->

<!-- SECTION:C-INDEX -->
## C-INDEX
- C-PROMPT-HISTORY: every earlier continuation prompt, kept in full.
- Old QT19 trackers: `tracker_files\` (historical, unchanged).
<!-- /SECTION:C-INDEX -->

<!-- SECTION:C-LOG-T001 -->
### C-LOG-T001 - thread log
20-10-2026 Thread 001: Requests 004-006 read old tracker v0.5.0 (newest of 202 heading hits in tracker_files). Request 007 bridged A1, A3-A6. Old A1 archived as H-001.
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
