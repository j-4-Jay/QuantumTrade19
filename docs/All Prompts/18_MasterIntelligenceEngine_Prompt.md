# File 19 — Master Intelligence Engine (Phase 5 Lock)
**Depends on:** Files 01–18 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This final boss connects the AI advisor to everyone else — it listens to every engine's live stream, thinks in the background, and hands its suggestions to the same approval flow you already trust from Phase 4, never taking control directly.

## 2. Wiring Logic
1. Master Intelligence Engine subscribes read-only to the internal event bus — every candle, POI, setup, score, and trade event flows to it, but nothing flows back except advisory suggestions.
2. ML_Signal_Worker's advisory score appears as an extra badge next to the rule-based Confidence Score in the Symbol Detail overlay and Trading Panel, clearly labeled "AI Advisory" in a visually distinct color.
3. RL_Policy_Worker's suggestions enter the same Journal & Reports "Auto-Learning Suggestions" panel from Phase 4, indistinguishable in workflow from a walk-forward-optimizer proposal — same canary trial, same Accept/Reject, same audit log, same rollback.
4. A single Settings switch ("AI Advisory: ON/OFF") can fully disable this entire Master Engine at any time with zero impact on Phase 1–4 functionality.

## 3. Check Gate (Phase 5 Full Acceptance Test)
Run the full software with AI Advisory ON for at least 2 weeks alongside normal Auto trading, confirm the AI's advisory scores and RL suggestions never once caused an unapproved change to live behavior, confirm the resource governor kept CPU/RAM for this engine capped and never caused any UI stutter or execution delay, and confirm toggling AI Advisory OFF mid-session instantly and cleanly removes its badges/panels with no residual effect.

## 4. Deliverable — Phase 5 Lock
Version → **v4.0.0 (Phase 5 stable — full institutional-grade system complete on Windows)**. Proceed to file 20 for cross-platform packaging.
