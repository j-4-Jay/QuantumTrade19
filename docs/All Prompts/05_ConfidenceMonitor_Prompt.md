# File 05 — Confidence Monitor Engine (Master Build Prompt)
**Depends on:** Files 02–04 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.
**Source of truth:** the 20-filter table locked in the Architecture Blueprint (Section 13 of the original blueprint, carried into v3).

## 1. Plain Explanation
This is the "referee" — every time a setup confirms, this Monitor asks 20 small judges (filters) to each give their opinion, adds up their scores out of 100, and decides if the setup is good enough to act on.

## 2. Tier 1 — Workers (each Worker outputs a 0-to-its-max-points score plus a short reason string)

Pattern Structure group: **WickRejection_Worker** (5pt), **POIStackConfluence_Worker** (6pt), **POITierWeight_Worker** (5pt) — Engulfing and FVG-confirmation scores are passed through directly from Setup Detection Monitor's own detectors (7pt + 7pt) rather than recomputed here.
Momentum & Trend group: **Momentum_Worker** (RSI/MACD, 6pt), **TrendStrength_Worker** (ADX/EMA slope, 6pt), **OverboughtOversold_Worker** (6pt).
Volatility group: **Volatility_Worker** (ATR percentile, 6pt).
MTF Confluence group: reads the cascade outcome directly from MTF_Cascade_Worker's event data (1m-aligned-with-15m 7pt, 1m-aligned-with-5m 5pt) — no separate Worker needed, just consumed here.
Volume & Liquidity group: **VolumeSpike_Worker** (6pt), **OrderBookImbalance_Worker** (4pt, auto-disables with no order-book feed), **FundingRate_Worker** (4pt, auto-disables for forex/commodities/metals).
Time-Based Edge group: **SessionEdge_Worker** (5pt), **DayOfWeekEdge_Worker** (4pt), **TimeOfDayEdge_Worker** (3pt) — all three read historical stats from Journal Monitor once it exists; until enough journal history accumulates, they return a neutral default score rather than zero.
Risk & Execution group: **RRPathClearance_Worker** (4pt), **NewsBlackout_Worker** (2pt), **SpreadSlippage_Worker** (2pt, distinct from the hard slippage reject gate in Setup Detection).
**ConfidenceScorer_Worker** — sums every active filter's score, rescales to 100 if any filter is toggled OFF (formula: `final = (sum of active scores / sum of active max-points) × 100`), and compares against the settings-defined minimum threshold (default 65) to output a pass/fail flag alongside the number.

**Check gate:** toggle each filter OFF one at a time and confirm the rescaling formula always returns a number out of 100 correctly; confirm the auto-disable rules for FundingRate_Worker and OrderBookImbalance_Worker correctly detect symbol type and feed availability; confirm the final score and its full breakdown are both retained (not just the total) for the Journal's filter-contribution analysis.

## 3. Tier 2 — Confidence_Monitor Assembly
Interface: `score_setup(setup_event) -> {total, breakdown, pass_fail}`.

**Check gate:** feed it 20 synthetic setups with known expected scores and confirm exact match.

## 4. Deliverable
Lock this file once both gates pass. Version → v0.5.0-alpha. Proceed to file 06.
