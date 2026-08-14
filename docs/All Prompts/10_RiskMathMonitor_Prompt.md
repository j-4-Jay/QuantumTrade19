# File 11 — Risk Math Monitor Engine (Master Build Prompt)
**Depends on:** File 10 locked (Phase 1). **Pipeline:** build → check → debug → re-check → lock → proceed.
**Source of truth:** Sections 9–11 of the 123Bull/123Bear master prompts.

## 1. Plain Explanation
This is the "calculator" — once a setup confirms, it works out exactly where to put the stop-loss, the take-profit, how big the trade should be, and how to walk the stop-loss forward as the trade wins, including every fee CoinDCX will ever charge.

## 2. Tier 1 — Workers

1. **Fee_Estimator_Worker** — per symbol, computes round-trip (open+close) fee cost including GST, using each symbol's live maker/taker rates.
2. **TickTable_Worker** — maintains the locally stored, regularly-refreshed tick-size table per symbol; notifies the user if a tick size changes.
3. **SL_Calculator_Worker** — takes the 3 setup candles, finds the extreme (low for Bull, high for Bear), adds the fee-converted-to-ticks buffer + volatility cushion + leverage adjustment + optional manual tick add (default 0).
4. **TP_Calculator_Worker** — implements both TP methods: fixed RRR, and fixed-risk-amount (with its two sub-modes: flat amount or % of equity, toggled in settings), using the per-symbol saved currency and leverage.
5. **LotSize_Calculator_Worker** — backs out the correct position size from the chosen risk amount and the SL distance.
6. **TrailingSL_Worker** — implements all 5 trailing methods (ATR, Structure, Fixed-Step, Chandelier, Breakeven-then-ATR) and the dynamic selector (ATR percentile + timeframe + trade duration), always computing true fee-inclusive breakeven.

**Check gate:** verify SL buffer calculation matches a hand-worked example including fees, leverage, and volatility cushion; verify both TP methods produce correct numbers against hand-worked examples; verify lot size calculation respects the per-symbol fixed leverage; verify all 5 trailing methods produce sensible, correctly-directioned stop movements on a simulated price path, and that the dynamic selector picks a different method under deliberately different ATR-percentile/timeframe/duration scenarios.

## 3. Tier 2 — Risk_Math_Monitor Assembly
Interface: `calculate_trade_plan(confirmed_setup, symbol_settings) -> {entry, sl, tp, lot_size}`, `get_trailing_update(open_trade) -> new_sl`.

**Check gate:** confirm this Monitor's pure calculation functions (used stand-alone in Phase 1's "as-if" alerts) produce identical numbers when later wired into real Execution in file 12 — no drift between the "alert-only" math and the "real trade" math.

## 4. Deliverable
Lock this file once both gates pass. Version → v1.0.0-alpha (Phase 2 in progress). Proceed to file 12.
