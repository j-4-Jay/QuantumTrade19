# File 12 — Execution Monitor Engine, Manual Mode (Master Build Prompt)
**Depends on:** File 11 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the "hands" of the software — the part that actually clicks Buy or Sell. In this file, only a human click triggers it; the software itself does not decide to trade yet (that's Phase 3). But once a trade opens, SL/TP/Trailing/Opposite-Exit are all fully automatic from that instant on.

## 2. Tier 1 — Workers

1. **Execution_Mode_Router_Worker** — reads the top-bar Live/Paper toggle (from Settings_Persistence_Worker) and routes every trade instruction to either Order_Placement_Worker or Paper_Trading_Simulator_Worker, completely transparently to everything else.
2. **Order_Placement_Worker** — sends the real market Buy/Sell order to CoinDCX's API when a user clicks the Trading Panel's Buy/Sell button, using the Risk Math Monitor's calculated entry.
3. **Paper_Trading_Simulator_Worker** — fills the same order instantly against the real live price feed but only updates a virtual ledger and virtual balance (from the Paper Trading settings card), never touching the real broker.
4. **Order_Fill_Worker** — confirms the fill price and checks it against the Slippage_Guard_Worker's 50%-of-candle-body limit; if breached, the trade is rejected and logged as a rejected entry (with its own alert and journal entry).
5. **Slippage_Guard_Worker** — computes the max-allowed-slippage value per the locked rule and exposes a simple pass/fail check to Order_Fill_Worker.
6. **Position_Manager_Worker** — tracks every open position (symbol, side, entry, current SL, current TP, trailing method active, trade_type: paper/live), and is the single source of truth Trailing SL and the Opposite-Setup Exit Guard both read from and write to.
7. **Opposite_Setup_Exit_Guard_Worker** — subscribes to Setup_Detection_Monitor's Confirmed Setup events; for every confirmation, checks Position_Manager_Worker for any open position on that symbol in the opposite direction, and if found, immediately sends a market-close instruction, logging exit reason `OPPOSITE_SETUP_EXIT`.

**Check gate:** verify a manual Buy correctly reserves margin, places the order, and fills within the slippage guard; verify a deliberately excessive-slippage scenario correctly rejects the entry; verify flipping the Live/Paper toggle mid-session correctly routes the next trade to the right Worker without needing an app restart; verify a live, deliberately-triggered opposite setup correctly force-closes an open position at the exact candle-3 confirmation moment, before the trailing SL would have caught up, and logs the correct exit reason.

## 3. Tier 2 — Execution_Monitor Assembly
Interface: `submit_manual_order(symbol, side)`, `get_open_positions()`, `close_position(id, reason)`.

**Check gate:** confirm closing one position never affects any other open position (per-symbol/per-trade isolation).

## 4. Deliverable
Lock this file once both gates pass. Version → v1.0.0-beta. Proceed to file 13.
