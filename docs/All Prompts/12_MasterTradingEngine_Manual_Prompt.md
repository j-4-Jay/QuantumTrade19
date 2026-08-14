# File 13 — Master Trading Engine, Manual Mode (Phase 2 Lock)
**Depends on:** Files 01–12 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This boss takes everything Master Alert Engine already does and adds real (or paper) buying and selling on top, plus builds the actual Trading Panel tab so you can click the buttons.

## 2. What Gets Wired On Top of Phase 1
Master Trading Engine = Master Alert Engine's full chain + Risk_Math_Monitor + Execution_Monitor, plus the Trading Panel UI page (chart, Risk & Execution sidebar with auto-saving Per-Symbol Risk Defaults, Trailing SL status card, Confidence Score card, Trade Details table) and the Journal & Reports tab's real content (previously a placeholder from File 01).

## 3. Wiring Logic
1. Everything from Phase 1 continues exactly as locked (alerts still fire the same way).
2. When a setup's confidence score passes the minimum threshold and the Trading Panel is open for that symbol, the calculated Entry/SL/TP/Lot from Risk_Math_Monitor populate the "Planned" fields in the sidebar.
3. User clicks Buy/Sell → Execution_Monitor takes over completely: routes through Paper or Live per the toggle, places/simulates the order, and from that instant, Trailing SL and the Opposite-Setup Exit Guard run with zero further manual input.
4. Every trade event (entry, SL move, SL hit, TP hit, trailing update, opposite-setup exit) fires an alert through Alert_Monitor and a log entry through Journal_Monitor, tagged with trade_type.
5. The Journal & Reports tab now renders real data: summary cards, equity curve, session/day/hour breakdowns, filter-contribution table, with a working Live/Paper/Both filter and visually distinct row coloring.

## 4. Check Gate (Phase 2 Full Acceptance Test)
Run at least 20 manual trades (mix of paper and live, mix of Bull and Bear, across at least 3 symbols) end to end and confirm: every trade's SL/TP match Risk Math's calculation exactly, trailing SL updates automatically without any manual input, at least one deliberately-engineered opposite-setup scenario correctly force-exits a trade, the Journal correctly separates and color-codes paper vs. live, and every alert channel fires correctly for every trade event.

## 5. Deliverable — Phase 2 Lock
Version → **v1.0.0 (Phase 2 stable)**. Proceed to file 14 to begin Phase 3 (full automation).
