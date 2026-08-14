# QuantumTrade19 — Module 01 Gap-Closure — FINAL LOCKED SUMMARY

**Module:** 01 — UI/UX Design System & App Shell (Gap-Closure Round)
**Base version:** v0.1.9-module01-locked
**This round closes on top of that base and should be tagged/versioned as the next increment (e.g. `v0.1.10-module01-gapclosure-locked`) once you commit.**
**Status:** ALL ITEMS LOCKED — this round is fully closed.
**Date locked:** August 15, 2026

---

## 1. Purpose of This Round

Module 01 was previously locked at v0.1.9, but a finalized gap-closure plan identified 11 specific gaps left open from the original build (security hardening, UI polish, missing wiring between built-but-disconnected Workers, and one net-new feature). This document records exactly what was built, what was deliberately left alone as a confirmed decision, what was explicitly deferred to later modules, and every bug discovered and fixed along the way — so this is the single reference point when the full software's final blueprint gets assembled.

---

## 2. Full Gap-Closure Progress Table

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Argon2 password hashing (replaces SHA-256) | ✅ Locked | Breaking change — old accounts had to re-register |
| — | *(discovered)* Register button missing on Login screen | ✅ Locked | Bugfix, not originally planned |
| 2 | `SecurityMonitor.get_setting`/`set_setting` generic passthrough | ✅ Locked | Named methods left fully intact |
| 3 | `get_per_symbol_setting`/`set_per_symbol_setting` interface stubs | ✅ Locked | Interface-only; real exercise deferred to Module 02 |
| 4 | `data/settings.json` stays plain JSON (not encrypted) | ✅ Confirmed decision | No build needed — settings-only, not secrets |
| 5 | CSS cross-fade for theme switching | ✅ Locked | |
| — | *(discovered)* Pre-login screens missing `--qt19-*` theme CSS vars | ✅ Locked | Bugfix — vars were only set inside the authenticated shell |
| 6 | Sound Engine wired to real placeholder tones | ✅ Locked | 6 programmatically-generated `.wav` tones; swappable later |
| — | *(discovered)* Square hover-shadow on radius-full buttons | ✅ Locked | Bugfix — Radix internal state-layer radius mismatch |
| 7 | Animation_Choreographer_Worker / Page_Transition_Worker → real CSS | ✅ Locked | Selection logic moved out of AppState into the Workers |
| 8 | Tab-to-tab switch animation | ✅ Locked | Extended mid-build to be independently Settings-controlled |
| 9 | Custom cursor stays removed (plain OS cursor) | ✅ Confirmed decision | No build needed |
| 10 | "Remember this device" 60-day TOTP-skip toggle | ✅ Locked | Trust stored via OS keyring, machine-bound |
| 11 | Shake animation + error sound on failed login | ✅ Locked | Built immediately after item 6, per plan |
| — | Tray icon / minimize-to-tray | **Deferred → Module 19** | Do not attempt before then |
| — | Full per-symbol-settings testing | **Deferred → Module 02** | Interface exists (item 3); no real symbols to test against yet |

---

## 3. What Was Built, Item by Item

### Item 1 — Argon2 Password Hashing
- **Files:** `engines/workers/security/auth_login_worker.py`
- Replaced raw SHA-256 + manual salt with `argon2-cffi`'s `PasswordHasher`. Argon2 embeds its own random salt and parameters inside the returned hash string — the old manual salt-concatenation approach was removed entirely.
- Added `check_needs_rehash` auto-upgrade path so future parameter changes re-hash transparently on next successful login.
- **Breaking change, as flagged at the time:** any account hashed under the old SHA-256 format could no longer authenticate. Required re-registration.
- **Follow-on bug found:** the Login screen had no path to reach Registration except on first run — added `go_to_register()` to `MasterAppEngine` and `AppState`, plus a "New here? Create an account" link on Login. This became the practical fix that let re-registration actually happen.

### Item 2 — Generic Settings Passthrough
- **Files:** `engines/monitors/security_monitor.py`
- Added `get_setting(key, default)` / `set_setting(key, value)`, calling straight through to `SettingsPersistenceWorker.load()`/`save()`. Every existing named accessor (`is_totp_enabled`, `is_telegram_enabled`, etc.) untouched.

### Item 3 — Per-Symbol Setting Interface
- **Files:** `engines/workers/security/settings_persistence_worker.py`, `engines/monitors/security_monitor.py`
- Added `per_symbol_settings: {}` to persistence defaults, plus `get_per_symbol_setting`/`set_per_symbol_setting` on both the Worker and the Monitor passthrough. Symbol is currently a free-text key since no Symbol_Registry_Worker exists yet — Module 02 will exercise this for real.

### Item 4 — settings.json Stays Plain JSON
- Confirmed decision, no code change. Settings-only data, not secrets — secrets already route through the OS keyring via `SecureKeyStorageWorker`.

### Item 5 — CSS Cross-Fade for Theme Switching
- **Files:** `ui/theme/glass.py`, `quantumtrade19/quantumtrade19.py`
- Added a uniform `_THEME_CROSSFADE` transition (`background`, `border-color`, `box-shadow`, `color`, 0.9s ease) to every style dict driven by `--qt19-*` vars: `GLASS_CARD_STYLE`, `GLASS_CARD_3XL_STYLE`, `PILL_BUTTON_STYLE`, `GLOW_RING_STYLE`, `PAGE_BG_STYLE`.
- **Bug found mid-build:** the `--qt19-*` custom properties were only ever set inside `page_shell.py` (the authenticated shell), so every pre-login screen (splash, login, register, forgot-password, manage-security, app-lock) never actually received themed colors — they were rendering on invalid/fallback custom-property values the whole time. Fixed by moving the variable binding to the app-root wrapper in `quantumtrade19.py`, which wraps every screen.

### Item 6 — Sound Engine Wired to Real Audio
- **Files:** `engines/workers/ui_experience/sound_engine_worker.py`, `engines/monitors/ui_experience_monitor.py`, `state/app_state.py`, standalone `generate_placeholder_sounds.py`
- Generated 6 placeholder sine-wave tones (click, page_change, tab_slide, card_flip, error, success) into `assets/sounds/*.wav` via a one-time local script.
- `SoundEngineWorker.play(event_name)` resolves an event name to a clip URL, gated by the master mute setting. `UIExperienceMonitor.play_sound()` exposes it upward. `AppState.play_sound()` triggers actual browser playback via `rx.call_script` + `new Audio().play()`, since Python has no direct browser audio access.
- **Bug found mid-build:** a squared hover-glow appeared behind pill-shaped buttons (Logout/Cancel) in light themes. Root cause: Radix Themes' internal hover/press state-layer overlay used its own corner-radius token instead of inheriting the button's `radius="full"` prop. Fixed with a global `[data-radius="full"] { overflow: hidden !important; }` rule in `global_css.py`, clipping any mismatched internal overlay to the button's own rounded shape — a general fix protecting every full-radius button app-wide, not just the one dialog.

### Item 7 — Connect Animation_Choreographer_Worker / Page_Transition_Worker
- **Files:** `engines/workers/ui_experience/animation_choreographer_worker.py`, `engines/workers/ui_experience/page_transition_worker.py`, `state/app_state.py`
- These two Workers previously existed only as empty stubs while the real single/sequential/shuffle transition-selection logic lived inline inside `AppState`, completely bypassing them. Moved that logic into `PageTransitionWorker.pick()`, with `AnimationChoreographerWorker` now owning the canonical list of transition effect names and their CSS class mapping. `AppState._pick_transition_effect()` now routes through the engine instead of reimplementing the pool logic.
- Also added `AnimationChoreographerWorker.error_preset()` returning the `qt19-shake` class name, formally connecting the "error preset" language from the original spec to the actual shake animation (item 11).

### Item 8 — Tab-to-Tab Switch Animation
- **Files:** `ui/theme/global_css.py`, `quantumtrade19/quantumtrade19.py`, `state/app_state.py`, `engines/workers/security/settings_persistence_worker.py`, `ui/pages/settings.py`
- Initially built as a fast, fixed fade+slide (`qt19-tab-switch`, 0.35s) applied via the same remount-via-`key` technique used for screen transitions.
- **Extended per your request mid-build**, before locking: tab animation is now independently Settings-controlled, reusing the same 10-effect catalog and single/sequential/shuffle mode pattern as the screen-entrance transitions, but with its own separate pool/mode/persisted state (`tab_transition_effects_enabled`, `tab_transition_mode`) — fully independent from the Login→Dashboard transition settings. New "Tab Switch Animation" card added to the Settings page.
- Also wired the previously-unused `tab-slide` sound (from item 6) into every tab click.

### Item 9 — Custom Cursor Stays Removed
- Confirmed decision, no code change. `qt19_cursor_glow()` is a deliberate no-op (verified during bug investigation — see below), restoring the plain OS cursor everywhere it's still imported for backward compatibility.

### Item 10 — "Remember This Device" 60-Day Toggle
- **Files:** `engines/monitors/security_monitor.py`, `engines/masters/master_app_engine.py`, `ui/pages/login.py`, `state/app_state.py`
- Added `is_device_trusted()` / `trust_this_device()` / `clear_device_trust()` to `SecurityMonitor`, storing a `device_trust_until` epoch timestamp via the OS keyring (`SecureKeyStorageWorker`) — machine-bound by the same mechanism as the TOTP secret, so trust never crosses devices.
- `SecurityMonitor.login()` now skips the TOTP check entirely when the device is currently trusted, regardless of whether TOTP is enabled.
- Username + password remain **always required** — only TOTP is skippable, per your explicit confirmation.
- **Scope note recorded at build time:** `login()` is shared by both `attempt_login` (initial login) and `unlock()` (App Lock re-entry), so trusting a device also skips TOTP on App Lock unlock. This was a deliberate architectural choice (splitting the code paths for no clear benefit was judged worse) — flag it if App Lock should behave differently later.
- Added the "Remember this device (skip 2FA for 60 days)" checkbox on Login, shown only when the TOTP field itself is visible.

### Item 11 — Shake Animation + Error Sound on Failed Login
- **Files:** `ui/theme/global_css.py`, `engines/workers/ui_experience/animation_choreographer_worker.py`, `ui/pages/login.py`, `state/app_state.py`
- Added the `qt19-shake` keyframe (0.4s horizontal shake). `submit_login()` now increments `login_error_seq` on both failure branches (empty fields, wrong credentials), forcing a fresh remount via `key=` so the shake replays on every consecutive failed attempt, not just the first. Error sound (from item 6) plays on the same failure branches.

---

## 4. Bugs Found and Fixed During This Round

These were not part of the original 11-item plan but were discovered and resolved while building it. Recorded here for the historical record and to prevent regression in later modules.

1. **Missing Register path from Login.** No way to reach the Registration screen except on first-run — critical since item 1's Argon2 migration required re-registration. Fixed with `go_to_register()` end-to-end.
2. **Pre-login screens missing theme CSS variables.** `--qt19-*` custom properties were scoped only to the authenticated shell, silently breaking themed glass styling on Splash/Login/Register/Forgot-Password/Manage-Security/App-Lock. Fixed by moving the binding to the app root.
3. **Square hover-shadow on rounded buttons.** Radix Themes' internal state-layer overlay ignored the button's own border-radius. Fixed with a global overflow-clipping CSS rule tied to Radix's `data-radius="full"` attribute.
4. **Recurring stale-frontend-bundle issue.** Reflex's dev-server hot-reload does not reliably pick up brand-new `State` methods — repeatedly caused "nothing happens" symptoms (sound not playing, buttons appearing to do nothing) that were actually just old cached bundles. Resolution pattern established: full server restart (`Ctrl+C` + `reflex run`) + hard browser refresh (`Ctrl+Shift+R`) after any new state method or root-file change — this should be treated as standard procedure for all future modules, not just this one.
5. **Whitespace corruption when large files pass through chat.** Several multi-hundred-line files lost indentation when relayed through this conversation, causing at least one real `IndentationError` (`settings_persistence_worker.py`). Established practice going forward: for files larger than ~100 lines, prefer the user pasting the actual current file content directly (preserving real indentation) over reconstructing from a lossy transcript.

---

## 5. File Manifest — Every File Touched This Round

**Security / Engines:**
- `engines/workers/security/auth_login_worker.py`
- `engines/workers/security/settings_persistence_worker.py`
- `engines/monitors/security_monitor.py`
- `engines/masters/master_app_engine.py`

**UI Experience Engines:**
- `engines/workers/ui_experience/sound_engine_worker.py`
- `engines/workers/ui_experience/animation_choreographer_worker.py`
- `engines/workers/ui_experience/page_transition_worker.py`
- `engines/monitors/ui_experience_monitor.py`

**Theme / Global CSS:**
- `ui/theme/glass.py`
- `ui/theme/global_css.py`

**Pages / Components:**
- `ui/pages/login.py`
- `ui/pages/settings.py`
- `ui/components/logout_dialog.py`

**State / App Entry:**
- `state/app_state.py`
- `quantumtrade19/quantumtrade19.py`

**Standalone / One-Time Scripts:**
- `generate_placeholder_sounds.py` (run once locally; not part of the running app)

**New Assets:**
- `assets/sounds/click.wav`, `page_change.wav`, `tab_slide.wav`, `card_flip.wav`, `error.wav`, `success.wav`

---

## 6. Forward Notes for the Final Blueprint

- **Module 02 owes two things back to this module:** (a) real exercise of the per-symbol settings interface (item 3) once `Symbol_Registry_Worker` exists, and (b) it should be the first place that actually calls `SecurityMonitor.get_per_symbol_setting`/`set_per_symbol_setting` for something real, validating the interface built here.
- **Module 19 owes:** tray icon / minimize-to-tray, deferred cleanly with zero UI Shell dependencies blocking it.
- **App Lock + "Remember this device" interaction** (see item 10 scope note) should be revisited once App Lock's UX is finalized — decide explicitly whether a trusted device should also skip TOTP on unlock, or whether that needs its own separate trust flag.
- **The sound placeholder tones are intentionally simple** and explicitly designed to be swapped for branded audio later — swapping is a pure asset replacement (same filenames in `assets/sounds/`), no code changes required.
- **Established engineering conventions from this round**, worth carrying forward into every future module: full-server-restart + hard-refresh after any state/root-file change; prefer direct file pastes over transcript reconstruction for large files; the remount-via-`key` technique (screen transitions, tab switches, login shake) is now the standard pattern for any future one-shot CSS animation tied to a Reflex state change.

---

**Module 01 (UI/UX & App Shell) — Gap-Closure Round: CLOSED.**
