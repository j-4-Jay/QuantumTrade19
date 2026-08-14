# File 07 — Journal Monitor Engine (Master Build Prompt)
**Depends on:** Files 01–06 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the "diary keeper" — it writes down everything that happens to every setup and every trade, for every symbol, so later the software (and you) can learn what actually works.

## 2. Tier 1 — Workers

1. **POI_Outcome_Logger_Worker** — for every confirmed setup (even in alert-only mode with no real trade yet), records: symbol, POI type/timeframe, setup type (Bull/Bear), all 20 filter readings at that moment, the confidence score and breakdown, and — once trading exists — the eventual result (SL hit / TP hit / trailing exit / opposite-setup exit).
2. **Trade_Logger_Worker** — for every real (or paper) trade: entry price/time, SL, TP, lot size, trailing method chosen and why, exit reason, exit price/time, realized PnL after fees, and a `trade_type` field set to `paper` or `live`.
3. **Journal_Aggregator_Worker** — rolls up the raw logs into per-symbol, per-POI-type, per-setup-type statistics: win/loss counts, SL/TP-hit counts, best/worst session, best/worst day-of-week, best/worst hour-of-day, and which individual filter correlates most with wins vs. losses.
4. **Report_Export_Worker** — exports any slice of the journal to CSV or PDF on demand.

**Check gate:** confirm every field listed above actually gets written for a simulated round-trip trade; confirm paper and live trades are tagged correctly and never mixed up; confirm the aggregator's session/day/hour stats recompute correctly as new trades are added, without needing a full recalculation from scratch each time (incremental update).

## 3. Tier 2 — Journal_Monitor Assembly
Interface: `log_setup_outcome(event)`, `log_trade(event)`, `get_symbol_stats(symbol, poi_type=None)`, `export_report(filters)`.

**Check gate:** confirm `get_symbol_stats` returns correctly separated paper vs. live numbers when filtered.

## 4. Deliverable
Lock this file once both gates pass. Version → v0.7.0-alpha. Proceed to file 09 (file 08/Security Monitor was already built in File 01).
