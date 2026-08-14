# File 15 — Master Trading Engine, Auto Mode (Phase 3 Lock)
**Depends on:** Files 01–14 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the moment the software becomes a real, self-driving trader — everything built so far now runs completely on its own, end to end, from watching price to closing a trade, with you just supervising.

## 2. What Changes at This Level
Master Trading Engine now defaults new symbols to Manual, but exposes a per-symbol Auto/Manual switch (a symbol only trades itself once you explicitly flip it to Auto) — this prevents an accidental "auto-trade everything" moment right after upgrading. The Dashboard table gains an Auto/Manual indicator per symbol row.

## 3. Wiring Logic
1. Everything from Phase 1 and Phase 2 continues unchanged.
2. For any symbol flipped to Auto, a passing confidence score triggers Execution_Monitor's new auto-trigger path directly — no Trading Panel needs to be open.
3. Circuit breakers, the max-concurrent-trades guard, and Dry-Run all apply globally regardless of per-symbol Auto/Manual state.
4. The Opposite-Setup Exit Guard and Trailing SL apply identically to auto-entered and manually-entered trades — no special-casing.

## 4. Check Gate (Phase 3 Full Acceptance Test)
Run a minimum 1-week Dry-Run soak test with at least 3 symbols flipped to Auto, covering both Bull and Bear setups, and confirm: every auto-entry matches what a manual trader would have done given the same data, no circuit-breaker false-positive halts trading unnecessarily, no real order is placed during Dry-Run, and the Journal correctly tags every trade's source as `auto` vs `manual`. Only after this soak test passes cleanly should Dry-Run be turned off for real Live capital, and even then, start with the smallest possible risk-amount setting for at least one more week before trusting full-size positions.

## 5. Deliverable — Phase 3 Lock
Version → **v2.0.0 (Phase 3 stable)**. Proceed to file 16 to begin Phase 4 (auto-learning).
