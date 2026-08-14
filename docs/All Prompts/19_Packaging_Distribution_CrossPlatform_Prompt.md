# File 20 — Packaging & Cross-Platform Distribution (Master Build Prompt)
**Depends on:** File 19 locked (full software complete and stable on Windows). **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
The software itself is finished at this point. This file only wraps it into a box you can carry from one computer to another with a double-click install — first for Windows, then the exact same box reshaped for macOS.

## 2. Windows Packaging (Build & Lock First)
1. Compile the Reflex app into static frontend files, then wrap the whole app (frontend + Python backend) using PyInstaller + PyWebView into a single native executable, per the standard Reflex-desktop packaging pattern.
2. Bundle a Windows installer (e.g., Inno Setup or NSIS) that installs the exe, registers the Startup_Registry_Worker's Run key only if the user opts in during install, creates a Start Menu and Desktop shortcut, and sets up the local SQLite/encrypted-JSON data folder on first run.
3. Verify the installer produces a fully working, instantly-runnable app on a **clean** Windows machine with no Python or dependencies pre-installed — this is the real test of "instant function when taken from one PC to another."

**Check gate:** install on at least 2 separate clean Windows machines and confirm identical behavior; confirm uninstalling removes the app cleanly without orphaning the Startup registry key; confirm the tray icon, notifications, and TOTP login all work identically to the development environment.

## 3. macOS Packaging (Build & Lock Second, After Windows Is Fully Verified)
1. Reuse the exact same Reflex/Python engine code — no engine file changes allowed at this stage, only the packaging layer.
2. Package using PyInstaller/py2app into a `.app` bundle, then wrap into a `.dmg` installer.
3. Swap only the two OS-specific Workers flagged back in file 09: Startup_Registry_Worker's macOS branch writes a LaunchAgent plist instead of a Registry key; System_Notification_Worker's macOS branch already works automatically since the cross-platform notifier library covers both OSes from file 06 with zero code change needed there.
4. Handle macOS Gatekeeper/notarization so the app opens without a security warning on first launch.

**Check gate:** install on a clean macOS machine and confirm every feature (notifications, tray-equivalent menu-bar icon, TOTP login, startup toggle, sounds, theme, trading) behaves identically to the Windows version, with the only observable differences being native OS chrome (Notification Center style, menu bar instead of tray).

## 4. Final Deliverable
Both installers pass their check gates → the full 5-phase build sequence (files 00–20) is complete and locked. Version → **v4.0.0 (Windows + macOS, institutional-grade, full pipeline stable)**.
