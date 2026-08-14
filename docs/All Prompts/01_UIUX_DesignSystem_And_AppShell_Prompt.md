# File 01 — UI/UX Design System & App Shell (Master Build Prompt)
**Software:** QuantumTrade19 — by Jayprakash Pattnaik
**Scope of this file:** UI Experience Monitor Engine + Security Monitor Engine + Master App Engine
**Platform order:** Build and lock on Windows first. macOS packaging comes later in file 20 — do not write any OS-specific code here except where explicitly marked.
**Pipeline for every single item below:** build → check → debug → re-check → lock → proceed. Do not move to the next Worker until the current one is locked.

> **Note on reordering:** Security Monitor was originally planned as file 08, but the Master App Engine (splash, login, app-lock) cannot function without it, so its Workers are built here instead. File 08 in the original plan is now merged into this file and can be skipped later.

---

## 1. What This File Builds (Plain Explanation)

This file builds the "shell" of the app — everything you see and touch before any trading logic runs. Think of it as building an empty, beautiful house first: the front door (splash + login), the rooms (tabs), the light switches (theme), the doorbell sound (UI sounds), and the door lock (app lock) — before any furniture (trading engines) moves in.

---

## 2. Tier 1 — Security Monitor Workers (Build & Lock First)

Build each Worker below one at a time. Each one is a separate, isolated file with its own error handling.

1. **Auth_Login_Worker** — takes a username/password (or PIN) pair, checks it against a securely hashed local credential (never store plain-text passwords — use bcrypt or argon2). Returns pass/fail only; never leaks whether the username or the password was wrong (prevents guessing attacks).
2. **TOTP_2FA_Worker** — uses `pyotp` to generate the secret key (shown once as a QR code during first-time setup, scannable by the real Google Authenticator app) and to verify the 6-digit code the user types in at login. Allow a small time-drift window (±30 seconds) so slightly-off device clocks still work.
3. **Secure_KeyStorage_Worker** — stores any sensitive value (API keys added in later files, the TOTP secret) using the OS-native keyring (Windows Credential Manager via the `keyring` library), never in a plain file.
4. **Settings_Persistence_Worker** — reads/writes all app settings to a local SQLite database or encrypted JSON file. Exposes one simple function each for "get setting," "set setting," "get per-symbol setting," "set per-symbol setting" — every other Worker in the whole app will eventually call through this one Worker, never touch the file directly.
5. **App_Lock_Worker** — freezes only the UI layer (shows a lock screen requiring the password or TOTP code again) while leaving every background engine (once they exist in later files) running untouched. This Worker only ever talks to the UI layer — it must never be able to pause, stop, or block any Monitor/Master engine.

**Check gate before locking this group:** verify login rejects wrong password, login rejects wrong TOTP code, login accepts correct password + correct TOTP code, settings persist correctly across an app restart, and the API key storage round-trips correctly through the OS keyring.

---

## 3. Tier 1 — UI Experience Monitor Workers (Build & Lock Second)

1. **Theme_Engine_Worker** — defines 6 theme tokens (Yellow-Day, Yellow-Night, Saffron-Day, Saffron-Night, Blue-Day, Blue-Night), each a set of CSS variables (background gradient, glass card tint, accent glow color, text color). Switching themes must apply instantly across every open page with a smooth cross-fade, not a hard flash.
2. **Cursor_Glow_Worker** — replaces the OS cursor with a small circular glass element that follows the mouse with a slight physics-based lag (not 1:1, a tiny smoothed delay), pulses its glow softly at rest, and brightens/expands slightly when hovering any clickable card or button.
3. **Sound_Engine_Worker** — loads and plays short audio clips for: click, page-change, tab-slide, card-flip, error, success. It exposes one function, `play(event_name)`, and obeys a single master ON/OFF setting read from Settings_Persistence_Worker. (Trading-specific sounds like "SL hit" get wired in later files — this Worker just needs to be ready to play any named sound clip handed to it.)
4. **Animation_Choreographer_Worker** — defines the reusable spring-physics presets (stiffness, damping, mass values) for: card entrance/exit, modal open/close, tab switch slide, chart zoom. Every animated component in the app pulls its motion values from here instead of each page inventing its own — this is what keeps the whole app feeling consistent.
5. **Page_Transition_Worker** — handles the actual page-to-page and tab-to-tab transition sequencing (fade out old page → slide in new page → settle), using the presets from Animation_Choreographer_Worker.

**Check gate before locking this group:** theme switch works with no flash of unstyled content, cursor tracks smoothly with no jitter at high mouse speed, sound plays correctly and respects the master mute switch, and every transition preset feels smooth at both 60Hz and 144Hz monitors (no dropped frames).

---

## 4. Tier 2 — Assemble the Two Monitors

- **Security_Monitor** imports and wires the 5 Security Workers above behind one interface: `login(username, password, totp_code)`, `lock_app()`, `unlock_app(password_or_totp)`, `get_setting(key)`, `set_setting(key, value)`, `store_secret(name, value)`, `get_secret(name)`.
- **UI_Experience_Monitor** imports and wires the 5 UI Workers above behind one interface: `set_theme(name)`, `play_sound(event_name)`, `get_cursor_component()`, `get_transition(kind)`.

**Check gate:** call every function on both Monitor interfaces from a throwaway test script and confirm each one works in isolation, without needing any other part of the app to exist yet.

---

## 5. Tier 3 — Master App Engine (Build Last in This File)

The Master App Engine boots the two Monitors above and drives this exact screen flow:

1. **Splash Screen** — QuantumTrade19 logo, "by Jayprakash Pattnaik" subheading, version tag (starts at v0.1.0-alpha), a subtle glass-shimmer loading animation, shown for a short fixed time or until initial engine boot completes, whichever is longer.
2. **Login Page** — username/password fields + 6-digit TOTP field + "Remember this device" toggle, calling Security_Monitor.login(). Wrong credentials shake the card gently (using the Animation Choreographer's error preset) and play the error sound.
3. **Main App Shell** — once logged in, render the persistent top bar (logo, Live/WebSocket status placeholder, theme selector, sound mute icon, app-lock icon, and the Live/Paper toggle placeholder — its real trading behavior comes in a later file, but the toggle UI and its persisted ON/OFF state must exist and work now) and the 4-tab navigation (Dashboard, Trading Panel, Journal & Reports, Settings). For this file, each tab can render as an empty placeholder page — the real content of each tab is built in later files. Tab switching must use Page_Transition_Worker.
4. **App Lock** — clicking the lock icon calls Security_Monitor.lock_app(), which shows a lock overlay requiring the password or TOTP again, without unmounting or pausing anything else in the app shell underneath it.
5. **Tray Icon / Minimize** — minimizing the window sends it to the system tray (Windows notification area) instead of the taskbar, with a right-click menu offering "Show QuantumTrade19" and "Exit."

**Check gate before locking this file:** full flow works end to end — splash appears, login rejects bad credentials and accepts good ones, all 4 tabs are reachable and animate smoothly between each other, theme switching works from any tab, sound mutes correctly, app-lock freezes only the UI and correctly unfreezes on correct re-entry, minimizing goes to tray and restores correctly, and the Live/Paper toggle visually flips and remembers its state after a full app restart.

---

## 6. Deliverable

Once every Worker, both Monitors, and the Master App Engine pass their check gates above, this file is **locked**. Version bumps to `v0.1.1-alpha`. Proceed to file `02_MarketDataMonitor_Prompt.md` next — do not begin it before this file's lock is confirmed.
