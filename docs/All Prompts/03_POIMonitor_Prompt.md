# File 03 — POI Monitor Engine (Master Build Prompt)
**Depends on:** File 02 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is the "map maker" — it draws the important price lines and zones (POIs) on every symbol's chart, using only the higher timeframes (never the 1m/5m/15m trading timeframes), and keeps track of how close price currently is to each one.

## 2. Tier 1 — Workers

1. **POI_Level_Calculator_Worker** — computes, per symbol, per enabled POI type: 1-Month High/Low, 1-Week High/Low, Previous Day High/Low, 4-Hour High/Low, Resistance Flip, Support Flip. Reads candles only from Market_Data_Monitor's HTF candle series (1H/4H/Daily/Weekly/Monthly), never the trading timeframes.
2. **FVG_Detector_Worker** — scans HTF candles for a 3-candle gap pattern (a Fair Value Gap) and records it as a price-range POI with a start/end price and the candle index it formed on.
3. **OrderBlock_Detector_Worker** — detects the last opposite-colored candle before a strong impulsive move and records it as a price-range POI.
4. **InverseFVG_Detector_Worker** — detects an FVG that price has fully closed through and flips its role (was resistance, now support, or vice versa), per the rules locked in the 123Bull/123Bear master prompts.
5. **POI_State_Tracker_Worker** — for every active POI, continuously computes: current distance in ticks, state tag (Approaching/Hit/Crossed/Retesting), and last-touch timestamp. This is exactly what feeds the Dashboard table's Distance/State/Last-Touch columns.

**Check gate:** verify every POI type toggle in Settings actually turns its calculation on/off live; verify PDH/PDL and 4H H/L (the two default-ON types) compute correctly against a known historical example; verify state tags transition correctly as a simulated price path approaches, touches, crosses, and retests a level.

## 3. Tier 2 — POI_Monitor Assembly
Interface: `get_active_pois(symbol)`, `get_poi_state(symbol, poi_id)`, `set_poi_type_enabled(type, bool)`.

**Check gate:** confirm multiple POIs on the same symbol track fully independently (moving one never affects another's state).

## 4. Deliverable
Lock this file once both gates pass. Version → v0.3.0-alpha. Proceed to file 04.
