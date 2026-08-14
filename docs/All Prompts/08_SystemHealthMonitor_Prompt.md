# File 09 — System Health Monitor Engine (Master Build Prompt)
**Depends on:** Files 01–07 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the "night watchman" — it quietly makes sure every other engine stays alive, reconnects when things drop, never gets the app banned from CoinDCX for calling too fast, and keeps the app running smoothly in the background.

## 2. Tier 1 — Workers

1. **Heartbeat_Watchdog_Worker** — every Worker in the whole app pings this Worker on a timer; if any single Worker misses 2–3 consecutive pings, this Worker restarts just that one Worker (via its owning Monitor) and logs the incident — never restarts anything else.
2. **Reconnect_Worker** — handles automatic API reconnection with exponential backoff (wait 1s, then 2s, then 4s, etc., capped at a sane max) whenever any live connection drops.
3. **RateLimit_Guard_Worker** — a shared token-bucket limiter that every Worker making an external API call (CoinDCX, Telegram, Discord) must pass its request through, so the app can never trigger an IP ban during volatile market swings.
4. **Startup_Registry_Worker** — manages "Run on Startup": on Windows, adds/removes a Registry Run key; the macOS equivalent (a LaunchAgent plist) is added later in file 20 behind the same interface.
5. **Tray_Icon_Worker** — manages the system tray icon, its right-click menu, and minimize-to-tray behavior (already wired into the shell in File 01; this Worker is where its actual OS integration lives).
6. **Version_Tag_Worker** — reads/writes the current app version string, auto-bumping it every time a file in this build sequence gets locked, per the versioning rule in the blueprint.

**Check gate:** simulate a dropped connection and confirm Reconnect_Worker recovers with correct backoff timing; simulate a Worker that stops responding and confirm Heartbeat_Watchdog_Worker restarts only that Worker; simulate a burst of 100 rapid API calls and confirm RateLimit_Guard_Worker throttles them safely; confirm the startup registry entry actually appears/disappears correctly when toggled.

## 3. Tier 2 — System_Health_Monitor Assembly
Interface: `get_all_worker_health()`, `restart_worker(name)`, `set_startup_enabled(bool)`.

**Check gate:** confirm `get_all_worker_health()` correctly reflects OK/DEGRADED/DOWN for every Worker across every Monitor built so far.

## 4. Deliverable
Lock this file once both gates pass. Version → v0.9.0-alpha. Proceed to file 10 — the Master Alert Engine, which completes and locks Phase 1.
