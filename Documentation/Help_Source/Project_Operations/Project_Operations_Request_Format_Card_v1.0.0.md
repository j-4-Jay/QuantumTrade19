# Project_Operations Request Format Card v1.0.0 (QT19)
Source: tool `4. Project_Operations_Core.py` v2.0.1 SPEC. The AI reads this card before writing any request. If this card and the tool disagree, the tool wins: create a COLLECT request for the tool's SPEC and report the difference.

## 1. File name (exact)
`<THREAD 3 digits>__<FILE NUMBER 3 digits>__<MODE>_v<X.Y.Z>__<DD-MM-YYYY>__<HH-MM-AM/PM>.md`
Example: `002__005__COLLECT_v1.0.0__20-10-2026__09-15-AM.md`
Rules: MODE in the name equals `MODE:` inside the file. THREAD equals the thread in the tracker's continuation prompt (`this thread = N`). FILE NUMBER is the next unused number, even after a failed request. Jay saves it in `Downloads`.

## 2. File layout
Header: only `KEY: value` lines (`MODE`, `PROJECT`, `THREAD`, optional `NOTE`, `DRYRUN`). PROJECT is `QT19`. A plain line in the header stops the request.
Then blocks: `=== NAME ===`, then `KEY: value` lines and optional `--- SECTION ---` text, then `=== END ===`.
Text outside a block is an error. A key or section given twice is an error. Operations only, never commands.

## 3. Modes
| Mode | Blocks and keys |
|---|---|
| SEARCH | `=== FIND ===` per search word: TERM, EXT, FOLDER, CONTEXT, MAX, ROOT |
| COLLECT | `=== READ ===` with exactly ONE of: FULL, PARTIAL, FUNC, SECTION, ITEM, or FILE + HEADING. Extra keys: LINES (`10-40`), FROM, TO, ROOT (`KIT` reads the Build Kit). FUNC value is `path::name` (Python). SECTION reads a tracker section (e.g. `A1`, `C-PROMPT-HISTORY`). ITEM reads one status-board row |
| REPLACE | `=== OP ===`: KIND (REPLACE, INSERT_AFTER, WRITE_FILE), FILE, OVERWRITE, EOL, FINAL_NEWLINE, SHA256. Sections `--- ANCHOR ---` (exact old text, must be unique) and `--- NEW ---`; WRITE_FILE uses `--- CONTENT ---`. The tool refuses to change its own core (use SELFUPDATE) |
| UNDO_LAST | no blocks. Undoes the last applied batch |
| RESTORE | `=== FILE ===`: PATH, BACKUP |
| PLACE | `=== FILE ===`: PROJECT_PATH, KIT_PATH, SHA256, SOURCE_DOWNLOAD, EOL, FINAL_NEWLINE; section CONTENT |
| MAP, PREFLIGHT | no blocks |
| TEST | `=== RUN ===`: SET or CHECK. Names come from `Documentation\Checks.json`. With no Checks.json only the built-in syntax check runs. Never guess check names |
| LOCK | header MESSAGE, TAG, PUSH (yes); `=== STAGE ===` blocks (FILE), one per file |
| ROLLBACK | header TAG; `=== FILE ===` (PATH) |
| CLEAN | `=== MOVE ===` (FILE, REASON) and `=== DELETE ===` (FILE) |
| UNCLUTTER | `=== BACK ===` (THREAD, FILE) |
| TRACKER | header BUMP (patch/minor/major), PHASE, PHASE_NAME; blocks STATUS (ID, STATUS, DATE, NOTE), ADD_ITEM (ROW), LOG (section TEXT), AMEND (SECTION; section TEXT), SET_A1 to SET_A6 (section TEXT) |
| NEW_THREAD | header LOCK, LOCK_MESSAGE, LOCK_TAG, LOCK_PUSH, NEXT_THREAD, plus BUMP/PHASE/PHASE_NAME; blocks RELAY (FILE, ROOT), STAGE (FILE) and all TRACKER blocks |
| SELFUPDATE | `=== FILE ===`: SHA256; section CONTENT |

Status words: NOT_STARTED, IN_PROGRESS, APPROVED, APPLIED_UNTESTED, LOCKED, PENDING, REVISED, DISCARDED.

## 4. Examples (short, tested on the install pack)
Read one tracker section and one line range:
```
MODE: COLLECT
PROJECT: QT19
THREAD: 001

=== READ ===
SECTION: A1
=== END ===

=== READ ===
PARTIAL: ui/app.py
LINES: 10-40
=== END ===
```
Create a new file:
```
MODE: REPLACE
PROJECT: QT19
THREAD: 001

=== OP ===
KIND: WRITE_FILE
FILE: Documentation/Example.txt
--- CONTENT ---
Hello
=== END ===
```
Archive the old prompt, then set the new one (tracker prompt history rule):
```
MODE: TRACKER
PROJECT: QT19
THREAD: 001
BUMP: minor

=== AMEND ===
SECTION: C-PROMPT-HISTORY
--- TEXT ---
HANDOVER H-001 | from: thread 001 | to: thread 002
[PROMPT-START]
(old prompt text, in full)
[PROMPT-END]
=== END ===

=== SET_A1 ===
--- TEXT ---
<!-- CONTINUATION_PROMPT_START -->
this thread = 2
(new prompt text)
<!-- CONTINUATION_PROMPT_END -->
=== END ===
```

## 5. Reading the old QT19 tracker
Old trackers live in `tracker_files\` and are not in the tool's tracker folder. Read them with COLLECT: `FILE: tracker_files/<name>.md` plus `HEADING: <heading text>` for one part at a time, or `PARTIAL` with `LINES`. Never FULL-read a very large old tracker; read only the headings needed.

## 6. Gates (Jay at the tool)
ENTER continues an ordinary change. Any other key then ENTER cancels. `U` + ENTER unlocks a locked path. `Y` + ENTER confirms a delete. Read-only requests need no confirmation.

## 7. Output
The tool writes `<THREAD>__<NUMBER>__Output__<MODE>_...md` next to the request and copies the output to the clipboard (split in parts if large; wait for RELAY END). Output ends `RESULT: OK` or `RESULT: STOPPED - <reason> - files changed: none`. The Clipboard Guard blocks secrets from being copied; blocked text is never copied.
