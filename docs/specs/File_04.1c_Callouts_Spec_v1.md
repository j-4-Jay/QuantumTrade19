# File 04.1c - Setup Callouts Spec v1 (APPROVED by Jay, 27-10-2026)

Status: APPROVED by Jay on 27-10-2026 (his answers to Q1 to Q5 are in section 14). Code starts only after the FT-H build plan is agreed with Jay.
Date: 27-10-2026. Thread 004. Stage FT-H (Step 0.6), task FT-H.1.
Replaces: Part B of docs/specs/File_04.1b_CustomPOI_And_Callouts_Spec_Lock_v1.md (M04e). The old file stays unchanged.
Sources used: Status CSV rows FT-H to FT-H.10 (Jay, 26-10-2026); Master Roadmap PostFile04 v2, Track 4; key rules of the continuation prompt. Where they differ, Jay's newer decisions win and the difference is listed in section 14.

## 1. Purpose
One callout for every confirmed 123Bull and 123Bear setup. It shows what the setup is, how the trade stands now, and how big the trade would be. Ghost POI (FT-G) will later use the callouts as clickable badges, so each callout exposes a click hook.

## 2. Names and colours (fixed, from the CSV)
- Names: 123Bull and 123Bear.
- Border: 123Bull #0E9464, 123Bear #990000.
- Inside colour shows the trade state, a gradient from Profit #06402B to SL Hit #36404A.
- Break Even #FFCE1B exists in the design but stays inactive until trailing SL exists.
- Text is very prominent.

## 3. Shape, tail and placement
- One smooth vector shape: body, tail and medium border drawn together with the gradient. No images.
- The tail tip is fixed at Candle 3: Low for 123Bull, High for 123Bear, plus a gap of 3 ticks (Jay, 27-10-2026). The anchor price never changes.
- The callout box sits outside the block and never covers a candle body or wick.
- Placement rule (app-wide): prefer the nearest empty space; if crowded, move outward until clear while staying close; the anchor stays fixed and only the box moves.
- The current block formation and dots are not changed (FT-H.6).

## 4. Drag
- The user drags the box; the tip stays fixed.
- The tail base slides along the border and round the corners.
- It runs in the browser. The position is saved when the box is dropped.
- The saved position is an offset relative to the anchor, never raw screen pixels, so it survives resize, zoom, theme change and restart.

## 5. What the callout shows (six rows, accepted by Jay for now; can be updated later)
1. Title: 123Bull or 123Bear, with the timeframe.
2. Entry and SL, with the risk in ticks.
3. Quantity and risk amount in INR.
4. Live RRR.
5. Peak RRR.
6. Confidence: greyed with a dash until File 05 exists (placeholder text: Confidence: File 05 pending; never a guessed score).
The UID is shown on hover only.

## 6. Colour behaviour
- While the price runs from entry towards SL, the inside colour fades from Profit to SL Hit.
- After 1.5R is reached the inside colour is solid Profit.
- Text updates at most about 4 times a second and dims when the feed is stale.

## 7. Outcome rules (read-only tracker, FT-H.2)
- Entry = Candle 3 close.
- SL = lowest (Bull) or highest (Bear) OHLC of Candle 1 to 3, minus or plus the buffer.
- Risk is stored in ticks.
- SL Hit = a wick touch before 1.5R.
- Reaching 1.5R is a win. The trade closes when the price returns to the 1.5R price, and the peak RRR is recorded.
- Not hit and not closed = Open.
- The tracker stores the first touch time of each RRR level (steps of 0.5R), the SL time and the deepest adverse dip.
- It only reads. It never sends an alert and never places an order.

## 8. Settings and money
- SL buffer: default 7 ticks, adjustable per symbol by Jay.
- Currency is always INR. Flat risk Rs 1000 per setup, set in the Trading Panel.
- Quantity = risk amount divided by the entry-to-SL distance, rounded down to the lot step. Below the minimum lot it is shown in grey.

## 9. Saving
- A new worker, SetupStoreWorker (local SQLite, same pattern as CandleStoreWorker), subscribes through the existing SetupDetectionMonitor subscribe(callback) bus. It does not touch File 04 internals.
- UID format: Symbol_DDMMYYYY (New York date)_Timeframe_counter, for example B-BTC_USDT_07092026_5m_03. The counter is per symbol per New York day, not per timeframe.
- Stored per confirmed setup: UID, symbol, timeframe, NY date, counter, direction, Candle 1 to 3 times and OHLC, fixed anchor price, poi_id, outcome fields from section 7, box offset, created and updated times.
- The chart reads the saved setups again when the Display Last X Days window changes, so old callouts come back when their Candle 3 is in view.
- After a restart the callouts come back with their outcome and position (a gate check).

## 10. Recalculate setups button
- On the Setup Stats card and the report screen.
- Pressed twice to confirm (no popup).
- Runs in the background in chunks. The old results stay until the new run finishes.
- Needed when the trailing SL plan arrives.

## 11. Speed
- Redraw only when a shown value changes.
- No images, no heavy effects.

## 12. Not in this stage
- Break Even and trailing SL visuals (wait for the trailing plan).
- TP1 to TP3 collected and trade-closed visuals driven by orders (wait for Risk Math and Execution).
- Ghost POI, reports and alerts (FT-G, FT-R, Step 1).

## 13. Gate (FT-H.10, Jay checks in the software)
Colours, tail movement, drag, live RRR, quantity, and recovery after restart. The existing File 04 tests (29) and 4c. Test_And_Check.bat must still pass. A task is LOCKED only after Jay confirms.

## 14. Differences and Jay's answers (27-10-2026)
Q1. DECIDED: no new 1/2/3 badges and no Bull/Bear tick labels in this stage. The current block and dots stay.
Q2. DECIDED: the six rows in section 5 are accepted for now. They will be updated later if required.
Q3. DECIDED: the fixed border colours and the Profit to SL Hit gradient replace the old white face and the embossed text.
Q4. DECIDED: the outcome rules in section 7 use the candles (read-only), even though the old roadmap said not to guess from candles.
Q5. DECIDED: the tail gap is 3 ticks.
