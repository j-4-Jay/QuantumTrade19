# QT19 Project Status and Task Tree - README (v1.3.0, 22-10-2026)

## Files (folder `Documentation\Project_Status\`)
- `QT19_Project_Status.csv` - the single status record.
- `QT19_Project_Status.html` - Project Status page: tree, hover tips, details panel, progress bars.
- `Task Tree v01.html` - fast-track plan FT-0 to FT-7. A structure change creates `Task Tree v02.html`, v03 ... (old ones stay). Status comes live from the CSV.
- Project root: `4c. Open_Project_Status.bat` and `4c. Project_Status_Server.py` (quiet local server).

## Open it (Jay)
1. Double-click `4c. Open_Project_Status.bat`. Two lines appear and the page opens once. A second double-click only reopens the page.
2. The pill at the top-left switches between "Click to view Task Tree" and "Click to view Project Status". It opens the highest-numbered Task Tree file.
3. "Last updated" is the save time of the CSV on this computer (after a git pull it shows the pull time).
4. The page reloads the CSV every 5 seconds. To stop, close the black window (do not press Ctrl+C).
5. Double-clicking an HTML file directly shows a red message; use the launcher, or the "Load CSV file" button.

## Rules for the AI (read before the first CSV change)
- Columns, in this order: id,parent,type,docs,jay,by,date,title,area,explain,evidence,depends.
- `docs` = what documents and tests show. `jay` = Jay-confirmed status; write it only after Jay's explicit confirmation in chat. `by` = Jay or AI. `date` = DD-MM-YYYY.
- Status words: LOCKED, PENDING, IN_PROGRESS, NOT_STARTED, DESIGN LOCKED, NO LOCK RECORD, REOPENED, DEFERRED, SUGGESTED, DECIDED, OPEN. Never write rollups; the page computes them.
- Edit one row per REPLACE. The anchor must be the WHOLE row line exactly as in the CSV. The tool matches whole lines and ignores leading spaces; a part of a line gives 'anchor not found'. Read the row first with SEARCH (TERM = the id plus a comma). The same rule holds for HTML and script files.
- New row: INSERT_AFTER the last row of its branch. Never rewrite the whole CSV.
- Batch order: REPLACE CSV, TRACKER, LOCK (stage the CSV, the tracker and any changed file).
- Task Tree: every id in a `Task Tree vNN.html` must exist in the CSV. A new version is a new file (WRITE_FILE).
- Never edit the HTML to change a status.

## Office and home
Pull before starting; push once at session end. The CSV, HTML files and this README travel by git.
