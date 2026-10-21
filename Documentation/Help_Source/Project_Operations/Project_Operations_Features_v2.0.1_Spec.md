# Project_Operations Features v2.0.1 (help source DOC-02)

Status: DRAFT written for the v2.0.1 corrective build. AWAITING Jay's lock together with the tool.

## What it is
One universal, standard-library Python tool, started by `4. Project_Operations.bat` / `.ps1` (menu), `4a. New_Thread__Bundle.bat`, `4b. Watch_Requests.bat` (watcher) and `4c. Test_And_Check.bat` (regression suite). It carries no project name and no hard-coded path: the project root is the folder its BAT sits in, the project code is read from `Documentation\Project_Code.txt`, and project facts (REQUIRED_SCRIPTS, CLUTTER_PROTECT, LOCKED_PATHS, SCAN_ALLOW) come from tracker Part B.

## Modes (16)
SEARCH, COLLECT, REPLACE, PLACE, MAP, TEST, PREFLIGHT, TRACKER, NEW_THREAD, UNDO_LAST, RESTORE, LOCK, ROLLBACK, CLEAN, UNCLUTTER, SELFUPDATE.

- Run by themselves: SEARCH, COLLECT, MAP, TEST, PREFLIGHT, TRACKER.
- Need ENTER: REPLACE, PLACE (when replacing code), UNDO_LAST, RESTORE, LOCK, CLEAN, UNCLUTTER, SELFUPDATE, and NEW_THREAD (one approval gate, Jay's decision 14-10-2026).
- Need U + ENTER: any change inside a LOCKED area, and every ROLLBACK.
- Need Y + ENTER: permanent deletion (only files already inside Clutter).

## Safety rules
- All-or-nothing per request: anchors are checked before any write; a refused request leaves every file byte-identical.
- Automatic backup of every touched file into `Debug\Backups\batch_<stamp>`, atomic write, hash verification, post-check, and UNDO_LAST for the whole batch.
- Indentation echo, duplicate-definition warning, restart hint, "already applied" detection, strict request parsing, no commands inside requests.
- LOCK stages only the files listed in STAGE blocks (never "git add -A"), refuses machine-local files, ignored files and files holding possible secrets, stops if the index already holds staged files or GitHub is ahead, and never forces a push.
- ROLLBACK restores files from a tag without touching git history; current files are backed up first and UNDO_LAST reverses it.
- Clipboard Guard: every clipboard write is scanned. A finding blocks the whole output or relay (nothing is redacted and copied). A SCAN_ALLOW allowlist can waive only email and phone patterns, never keys or passwords.
- Never moved by clutter handling: Documentation, Debug_Scripts, Debug\Restore_Maintenance, the tracker folder, tool files, and everything on the tracker's CLUTTER_PROTECT list.

## Relay and New Thread Pack
NEW_THREAD runs PREFLIGHT, tracker update, optional LOCK, auto-clutter (report-only for the first 2 runs), map, pack and relay. Parts are at most 15,000 characters (calibrate with menu item 6). Append all parts in ONE chat message and send once. ENTER = next part, R = repeat, B = back, Q = stop.

## Self-update
SELFUPDATE writes the new core to a temporary folder, compiles it, runs the whole regression suite there, then swaps it in atomically. The previous core is kept as `4. Project_Operations_Core_prev.py` and UNDO_LAST can reverse the swap.
