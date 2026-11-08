# QT19 Candle Info Popup - Spec v0.1.0 (FT-H.39)
Requested by Jay 08-11-2026. Design approved in chat 08-11-2026. Status: NOT BUILT.

## 1. Gesture
1. Press and hold the left mouse button on a candle, or anywhere in that candle's vertical column inside the chart, for 2 seconds without moving (more than about 3 pixels cancels).
2. After about 0.3 s a thin progress ring shows around the pointer.
3. At 2 s the popup opens near the pointer, at least 2 bars to the right of the candle. Near the right edge it moves left so it stays inside the chart.
4. Clicking outside never closes a popup. Only its own X button closes it.
5. Maximum 10 popups. The 11th hold shows a short notice and opens nothing.
6. Position is fixed on screen (does not follow scroll or zoom). The candle time is shown in the popup.
7. All popups close when the symbol changes. They stay when the timeframe changes.

## 2. Content
- Title: symbol, timeframe, status badge.
- Candle time (open time): New York and IST, format DD-MM-YYYY HH:MM:SS AM/PM, both from the same timestamp.
- Rows: Open, High, Low, Close, Volume.
- Source tag: DB for a closed candle, Live for the forming candle (the database has no row until it closes).
- Chart check: each row compares the database value with the candle drawn on the chart. If they differ, that row shows both values with the chart value highlighted.
- Compare with CoinDCX: one fetch of that candle. A row that differs shows the CoinDCX value and the difference.
- Buttons: Refresh, Auto refresh toggle (default OFF), Copy (values as text), Compare with CoinDCX, X.
- Status badge: Forming; Closed, syncing (within 15 s of the close, with a countdown); Settled.
- A value that changes on refresh flashes briefly.

## 3. Refresh rules
- Values stay as at creation until a refresh. Nothing updates by itself.
- Refresh: one read now.
- Auto refresh ON: one read per second until 15 s after that candle's close, then it stops and the badge shows Settled. If the candle is already older than 15 s, it does nothing.
- Each popup refreshes on its own.
- Evidence for 15 s: ETH 1m calibration 08-11-2026, 20 candles, database equal to CoinDCX within 5 to 10 s.

## 4. Look and motion
- Window background is a gradient from the candle colour: green tones rising, red tones falling, grey flat (open equals close).
- Appear: window fades in, content follows after 0.75 s. Close: content fades first, then the window.
- Reduced motion ON: no animation.
- Left side: a fixed-width dotted handle to drag. Resize: content re-arranges and stays readable; there is a minimum size.
- Opacity and transform animations only. No blur filter.

## 5. Resource rule (must be measured)
- No timer, poll or listener runs while no popup is open.
- Idle with popups open and Auto OFF: zero work.
- Auto ON: at most 15 reads per popup, then none.
- Compare with CoinDCX: one request per click, one at a time, with a short cooldown.
- Test target: report idle CPU and frame time in the headless browser before Jay tests.

## 6. Build plan (small requests, app stopped)
1. New file ui/components/candle_info_popup_js.py with the whole popup in browser code; tested in the headless browser.
2. A small hook in ui/components/kline_chart.py (needs Jay's unlock): start the hold detection, pass candle data and the symbol.
3. New state file for two server actions: read one candle from data/historical_candles.db (read-only), and fetch one candle from CoinDCX with a short timeout.
4. Tests, then Jay's checks, then lock.

## 7. Jay's verification checklist (to run in the software)
1. Hold 2 s on a closed candle without moving. Expect the ring, then the popup 2 bars to the right. Pass or fail.
2. Move the mouse 10 pixels while holding. Expect no popup. Pass or fail.
3. Click outside the popup. Expect it stays. Pass or fail.
4. Press X. Expect content fades, then the window. Pass or fail.
5. Open 10 popups, hold an 11th. Expect a notice, no 11th. Pass or fail.
6. Press Refresh on a closed candle. Expect values as in the database. Pass or fail.
7. Turn Auto ON on a just-closed candle. Expect values to settle within 15 s and the badge to say Settled. Pass or fail.
8. Hold on the forming candle. Expect the Live tag and no error. Pass or fail.
9. Press Compare with CoinDCX. Expect equal values or the differing rows shown. Pass or fail.
10. Change the symbol. Expect all popups to close. Change the timeframe. Expect them to stay. Pass or fail.
11. Drag by the dotted handle and resize. Expect smooth movement and readable content. Pass or fail.
12. Turn Reduced motion ON. Expect no animation. Pass or fail.
13. Leave the chart with popups open and Auto OFF for 5 minutes. Expect no growth in CPU. Pass or fail.
