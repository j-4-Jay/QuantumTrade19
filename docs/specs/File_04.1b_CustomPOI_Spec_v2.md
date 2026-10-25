# File 04.1b v2 - Independent POI Lines - SPEC v2 (DRAFT for Jay's approval)

STATUS: Read by Jay and approved as perfect on 25-10-2026, with the decisions in section 14. No code yet. Task FT-C.1. Decision I (Jay, 24-10-2026).
Save at: D:\QuantumTrade19\docs\specs\File_04.1b_CustomPOI_Spec_v2.md
Replaces: Part A of File_04.1b_CustomPOI_And_Callouts_Spec_Lock_v1.md (that file stays unchanged).
Part B of the old file (1/2/3 badges and callouts) moves to stage FT-H (setup callouts), built after this stage.

## 1. Purpose
Jay can place a horizontal POI line at any price on the chart, so setups, alerts, paper trades and trailing can be tested without waiting for a real POI.

## 2. What changes from the old Part A
Old: 5 slots, a Settings card, a popup with a price slider, double-click edit, lock icon.
New: no slots, no popup, no Settings card. Everything is on the chart by right-click and drag.
Old rules kept: the line feeds the same pipeline as real POIs; it starts at creation and is never backdated; deleting it does not remove setups it already helped confirm.
Old rules dropped: the 5-slot limit (now 10), the Settings card, the popup, the lock icon, double-click edit.

## 3. Name and numbering
- Public name: Independent POI. Label on the right of the line: Ind. POI <#>.
- The number is automatic: the lowest free number from 1 to 10 for that symbol.
- Deleting a line does not renumber the others. A freed number can be reused by the next new line.

## 4. Add and delete (right-click)
- Right-click on empty chart: the existing menu gets one new item, Add Independent POI. The price is the price at the click.
- Right-click on or near an existing Ind. POI line (a few pixels): the menu shows Delete Independent POI <#>, the style items (section 6) and the live switch (section 8).
- The existing menu order (Jay-locked FT-0.7) stays as it is. The new items are added in a separate group, and nothing existing is moved. Changing ui/components/trading_panel_context_menu.py needs Jay's U + ENTER.
- At 10 lines on a symbol, Add is shown greyed out with the note: limit of 10 reached.
- Delete asks no question (a test line is cheap) and takes effect at once: the line stops feeding the pipeline from that moment.

## 5. Drag
- The line can be dragged up or down to any price.
- The price snaps to the symbol's tick size.
- Moving a line counts as a new level from the moment you drop it. Touch state is cleared and detection starts from the drop time forward. It is never backdated.
- While dragging, the price is shown next to the label.

## 6. Style (per line, in the right-click menu)
- Colour.
- Thickness: 1 to 5 px (same range as the existing POI line thickness).
- Transparency: 0 to 100 percent.
- Line style: solid, dashed, dotted.
- Defaults: one default style, shown clearly different from real POIs so a test line is never mistaken for a real one.

## 7. Scope and saving
- A line belongs to one symbol. It shows on the 1m, 5m and 15m charts of that symbol. It is one line, not three.
- Maximum 10 lines per symbol.
- Lines are saved per symbol and come back after an app restart until Jay deletes them.
- Storage (decided 25-10-2026): config/independent_pois.json, tracked in git so Home and Office get the same lines. It holds prices and styles only. The Allow live use switch is always loaded as OFF. Not stored in data/settings.json.
- Each line stores: id, number, symbol, price, creation time, colour, thickness, transparency, line style, live switch (default off).
- The id is unique and never reused. The number can be reused. Ghost Mode (stage FT-G) is tied to the id, not to the number.

## 8. Safety (hard rules)
- Paper-only by default. Every Ind. POI line shows a visible PAPER badge.
- Each line has its own Allow live use switch. It is off by default and is not saved as on without Jay's action on that line.
- The per-symbol Trade Allowed switch still applies on top of it.
- In this stage nothing can place an order. The paper account comes at Step 3 and auto trade at Step 7. Until then the live switch is stored only.
- No broker credentials and no live trading are touched by this feature (rule 4.6).
- A line that is not switched live can only feed alerts, paper trades and tests, never a real order.

## 9. Pipeline (same as real POIs)
- The line joins the active POI list that File 03 returns to File 04, in the same shape as a real POI, with a flag marking it as independent.
- Touch, Sweep and Cross classification is the same as for real POIs.
- The Bull and Bear feed is role-agnostic, as in the File 04 core correction. Candle 1, 2 and 3 chains are the same.
- Detection starts at the creation time (or drop time after a drag) and runs forward only.
- A behaviour fix in the real POI pipeline applies to Ind. POI lines automatically, because there is no separate code path for detection.
- File 04 core logic is not changed.

## 10. Files likely touched (read live code first, small ranges)
- New: engines/workers/poi/independent_poi_worker.py (state, cap, numbering, saving).
- engines/monitors/poi_monitor.py (LOCKED, File 03): include the independent lines in the active POI list. Needs U + ENTER.
- engines/workers/poi/poi_types.py: independent flag. Check if locked.
- state/app_state_mixins/poi_chart_mixin.py and a new mixin or part for line state.
- ui/components/kline_chart.py, ui/components/trading_panel_chart.py: drawing, label, drag, snap.
- ui/components/trading_panel_context_menu.py (Jay-locked FT-0.7): the new items. Needs U + ENTER.
- Each locked file is named to Jay first, one by one, before any change.

## 11. Tests (named before the build)
1. Add at a price creates a line with number 1; a second gets number 2.
2. The 11th line on one symbol is refused.
3. Delete frees the number and the next add reuses it; other numbers are unchanged.
4. Drag snaps to the tick size (check on a high-price and a low-price symbol).
5. The line appears on 1m, 5m and 15m of its symbol and not on other symbols.
6. After a simulated restart the lines come back with the same style and price.
7. A candle touching the line starts Bull and Bear checks like a real POI.
8. No candle before the creation time is ever tested against the line.
9. The live switch is off by default and a new line shows the PAPER badge.
10. The existing File 04 tests still pass (169/169 or more in total).

## 12. Check list for Jay in the software (FT-C.6 gate)
Each item: action, expected result, pass or fail.
1. Right-click empty chart, Add Independent POI. Expect a line at the click price, label Ind. POI 1 on the right, PAPER badge.
2. Add more lines. Expect numbers 2, 3 and so on.
3. Drag a line. Expect it to follow the mouse and land on a tick price.
4. Change colour, thickness, transparency and line style. Expect the line to change at once.
5. Switch between 1m, 5m and 15m. Expect the same lines on each.
6. Switch to another symbol. Expect none of these lines there.
7. Restart the app. Expect the lines back with the same price and style.
8. Place a line at the current price and wait for a candle to touch it. Expect Bull and Bear checks to start like a real POI.
9. Right-click a line, Delete Independent POI. Expect it to vanish and its number to be free.
10. Add 10 lines. Expect Add greyed out for the 11th.
Status stays PENDING until every item passes and Jay confirms.

## 13. Risks
- Menu file is Jay-locked: a careless change could break the FT-0.7 menu. Mitigation: add only, test the old order after.
- A test line near a real POI could be confused with it. Mitigation: different default style and the label.
- A stray line used live. Mitigation: section 8.
- Many lines slow the chart. Mitigation: the cap of 10 per symbol.
- Drag on a busy chart could clash with chart panning. Mitigation: drag only when the pointer is on the line.

## 14. Open points for Jay
- A. Decided: stored in config/independent_pois.json and synced through git (see section 7).
- B. Decided: moving a line restarts detection from the open of the current live candle, never backdated.
- C. Decided: a freed number is reused by the next new line. Ghost Mode does not carry over to the reused number.
