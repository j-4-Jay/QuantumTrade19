# Project_Operations Recovery Guide v1.0.0 (QT19)

| Problem | What to do |
|---|---|
| I changed my mind after a change | Ask the AI for an UNDO_LAST request. Download it, double-click `4. Project_Operations.bat`, type 1, press ENTER, press ENTER at the plan |
| The AI sent a wrong change and it is applied | Same as above. Backups are in `Debug\Backups\batch_<date>` |
| A request says STOPPED | Nothing was changed. Paste the output into the chat and the AI will fix the request |
| Clipboard says BLOCKED | The Clipboard Guard found something that looks like a secret. Nothing was copied. Tell the AI; do not paste secrets |
| The new thread started without the pack | Double-click `4a. New_Thread__Bundle.bat`, then paste the clipboard into the new thread |
| Install went wrong | Double-click `UNINSTALL_Project_Operations.bat` in the install pack folder. It removes what it added and restores what it replaced. Your application files are never touched |
| Self-test fails | Do not use the tool. Send `Debug\Installation\Install_Report.txt` to the AI |
