# FT-U Gate Checklist v1 - Trading Panel layout (for Jay)
Date: 29-10-2026. Run each item in the app. Write PASS or FAIL for every number and paste the list to the AI.
Before you start: full restart of the app, close old tabs on localhost:3000, hard refresh (Ctrl+Shift+R).

## A. Left sidebar
1. Dashboard, Journal, Alerts, Settings: the sidebar shows full, icons and collapsed. Expected: each state works, the round handle is at the top of the sidebar.
2. Click the handle in full state. Expected: icons state. Click again: the sidebar slides out, one glowing handle stays at the top-left.
3. Click the handle when collapsed. Expected: the sidebar slides in, the handle goes away.
4. Collapsed on the Dashboard. Expected: the KPI cards start to the right of the handle on the same top line.
5. Hover the sidebar card. Expected: a light runs around the card edge only, no blob in the centre.
6. Trading Panel, sidebar open. Expected: the sidebar floats over the chart; the chart does not move or redraw when the sidebar changes.

## B. Right sidebar
7. Trading Panel: the right sidebar shows five tabs in one row (Trade, Chart, POI, Setups, Alerts), the active tab glows and joins the content box.
8. Click each tab. Expected: the content fades in. Trade shows the price pills; Chart shows Display Last; POI shows four buttons; Setups shows Detect setups and Setup Stats.
9. Collapse the right sidebar. Expected: the card slides out, the chart widens smoothly, a round handle shows at the top-right of the chart.
10. Open it again. Expected: the card slides in, the chart narrows smoothly, the price axis stays visible.
11. The top and bottom of the right sidebar line up with the left sidebar and the chart card. No clipped borders.

## C. Bottom card
12. The trade details card is under the chart. Expected: it has a header, column titles and a placeholder text.
13. Drag the divider above the card. Expected: the height follows the mouse, minimum about 120px, maximum 60% of the window; the cursor is a two-way arrow.
14. Double-click the divider. Expected: the height returns to 220px. Press F5: the height is kept.
15. Click the collapse arrow in the card. Expected: the card drops, the chart grows down, a handle shows at the bottom-right of the chart.
16. Click the handle. Expected: the card rises again with its saved height.

## D. Mini bar and chart
17. The mini bar (symbol and time frames) is at the top centre of the chart. Change symbol and time frame: the chart follows.
18. Drag the mini bar by its dot grip. Expected: it moves inside the chart only; press F5, it stays.
19. No header rows are above the chart. The chart, left sidebar and right sidebar share the same top line.

## E. Motion and Reduced motion
20. Settings > Appearance > Reduced Motion is OFF by default. Expected: all effects above are visible.
21. Switch Reduced motion ON. Expected: panels open and close at once, tabs switch without effect, the edge light stands still.
22. Switch it OFF. Expected: the effects come back.

## F. Other pages
23. Dashboard, Journal and Reports, Alerts, Settings: no layout problem, no errors.
24. Log out and in again: the sidebar and panel states are as expected.
