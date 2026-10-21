# Project_Operations Workflow Steps v1.0.1 (help source DOC-01)

Status: DRAFT written for the v2.0.1 corrective build. AWAITING Jay's lock together with the tool.

## Everyday loop
1. Tell the AI the feature you want.
2. Download the request file the AI generates (it goes to your Downloads folder).
3. The watcher (`4b. Watch_Requests.bat`) runs read-only requests by itself and puts the output on the clipboard. Without the watcher, double-click `4. Project_Operations.bat` and choose 1.
4. Paste the output into the chat.
5. Download the REPLACE request the AI returns.
6. Look at the summary in the terminal and press ENTER. Locked areas need U then ENTER. Deletion needs Y then ENTER. Any other key cancels, and nothing changes.
7. Read the automatic test result, then test the application yourself.
8. Say "Lock" when you are happy. A LOCK request names the exact files to save, so nothing else is committed.

## Starting a new thread
The AI suggests it when a unit is LOCKED or after 25 requests. Say "New thread". Download the one NEW_THREAD request, approve the plan with ENTER, then press ENTER for each relay part, paste every part into the SAME new chat message and send it once. If the old thread is unusable, run `4a. New_Thread__Bundle.bat`; it rebuilds the pack and never changes the tracker.

## If something goes wrong
- Wrong change applied: request UNDO_LAST (restores the whole last batch).
- One file broken: request RESTORE with its path.
- Back to a locked version: request ROLLBACK with the tag (U then ENTER; git history is not touched).
- Output blocked by the Clipboard Guard: nothing was copied. The raw output stays in `Debug\Blocked_Output\` on this PC; review it there and never paste it.
- Tool problem: run `4c. Test_And_Check.bat`, and keep the watcher closed until it passes.

## Tool updates
Use a SELFUPDATE request; never copy the core by hand. The tool tests the new version in a temporary folder first and keeps the previous one.
