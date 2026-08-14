# File 06 — Alert Monitor Engine (Master Build Prompt)
**Depends on:** Files 01–05 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the "town crier" — whenever anything important happens (price nearing a POI, a setup confirming, an entry, an SL/TP event), it shouts the news through three megaphones: a popup on your screen, a Telegram message, and a Discord message — to as many phones/channels as you've added, for free.

## 2. Tier 1 — Workers

1. **Alert_Template_Worker** — turns any raw event (tick-distance alert, setup-found, setup-discarded, entry, SL moved, SL hit, TP hit, opposite-setup exit) into one consistent, readable message shape: title, short body, bias tag, risk tag, timestamp — the same shape feeds all three channels below.
2. **System_Notification_Worker** — uses a cross-platform notifier library so the same call posts to Windows Action Center now and macOS Notification Center later with no code change.
3. **Telegram_Notifier_Worker** — holds a list of chat IDs; sends the same formatted message to every enabled recipient, paced to respect Telegram's free-tier pacing limits.
4. **Discord_Notifier_Worker** — holds a list of webhook URLs; sends the same formatted message to every enabled channel, paced to respect Discord's free per-webhook rate limit.
5. **Snooze_Worker** — a timed suppression: when snoozed, all three notifier Workers above skip sending (but Alert_Template_Worker still fires internally so the Journal never misses an event) until the snooze timer expires.

**Check gate:** verify the 100/50/30/20/10/5-tick distance bands and the "hit" alert each fire independently per their own ON/OFF switch; verify adding a 2nd and 3rd Telegram recipient and Discord webhook both work and don't duplicate/drop messages; verify snoozing suppresses all 3 channels but the Journal still logs the underlying event; verify a burst of 20 simultaneous alerts never trips a 429 rate-limit error thanks to the internal pacing queue.

## 3. Tier 2 — Alert_Monitor Assembly
Interface: `fire_alert(event)`, `snooze(minutes)`, `add_recipient(channel, target)`, `remove_recipient(channel, target)`.

**Check gate:** confirm removing one recipient never affects delivery to the others.

## 4. Deliverable
Lock this file once both gates pass. Version → v0.6.0-alpha. Proceed to file 07.
