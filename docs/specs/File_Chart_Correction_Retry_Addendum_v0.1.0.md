# FT-H.37 event-driven correction retry v0.1.0 - 10-11-2026

## Evidence and limits
Home report for ETH 1m candles opening 03:16, 03:17 and 03:18 IST shows DB/exchange OHLCV agreement at +10/+30/+55 seconds, differences at +1 second. Popup refreshed at 03:26:43 for the 03:17 candle showed DB/exchange close 2126.28 and volume 1479.888 versus chart close 2126.50094574 and volume 1463.413, exactly its +1-second provisional values. Browser page refresh removed the discrepancy. No reset-only recovery was verified. This proves one stale chart sample, not a root-cause attribution or dispatch safety.

## Approved scope
Jay approved reopening ui/components/kline_chart.py for scoped FT-H.37 repair at 03:41 IST on 10-11-2026. New helper ui/components/chart_correction_js.py and focused tests extend the chart; no countdown, popup, market-data, database or dispatch-delay changes. This is a Blueprint extension. It does not supersede FT-H.26 v0.4.0 reset gap or FT-H.36 scrolled-view stability.

## Implementation
Keep the existing strict at-live guard and its 3px remembered-offset comparison. Retain pending corrected rows while away; retry on scroll/zoom/visible-range actions and existing live callbacks, coalesced into one animation frame only when rows are pending. Explicit scrollToRealTime calls rebase the remembered offset to the reported current offset and schedule retry; this does not itself initiate scrolling or change countdown reservation. No new polling timer. Merge matching timestamps into the current browser data list so a newer forming candle is preserved; no insertion of historical or future rows. Keep unapplied rows if loader is not ready or reset throws. Context changes discard old-symbol/timeframe pending work. Destroy removes owned subscriptions/frame/wrapper/registry entry. Existing resetData path remains; no direct in-place chart internal mutation.

## Evaluation and risks
Thirteen isolated Node mock scenarios passed before delivery, covering live merge/forming preservation; held/retry via scroll and live tick; explicit return offset rebasing; coalescing/latest row; no-op; loader readiness; context isolation; reset exception; teardown; invalid rows; missing timestamps; and idle scheduling. Integration source assertion and full local suite have not run. Mock API behaviour does not prove actual KLineCharts rendering, animation offset timing, Reflex lifecycle or correction delivery. Original gate may still reject some genuinely live views; this revision does not claim otherwise. A dropped server patch or lack of exchange correction notification is not repaired by queue retry.
Risks: reset flicker, view jump or live update regression; additional resets when held corrections become eligible. No database writes, orders, credentials or live trading. No new perpetual timer or idle animation loop.

## Jay software acceptance (pending)
1. Three newly closed ETH 1m candles: at +30 seconds Refresh and Compare in popup show DB/exchange match with no chart differences, without browser reload or timeframe switch. Record exact candle opening times.
2. At live: forming candle continues and new candle appears without vanish/flicker for three closes.
3. Scroll back about 20 bars: view remains fixed through a close, corrections held, no jump to live.
4. Slight pan with newest candle visible: no forced snap. Explicit reset/go-live then retained corrections catch up without a new exchange correction being required; refreshed popup shows no chart differences.
5. Zoom/resize/symbol/timeframe changes: no old-symbol patch, freeze or wrong data; returned live chart receives corrections.
6. Countdown reset retains three-full-bar border gap and axis clearance where space permits; ordinary panning overlap and flips/Reduced Motion unchanged; popup/locator/callouts unchanged.
Run focused tests and full suite; stop on failures, rebuild and re-evaluate. FT-H.37 remains IN_PROGRESS/PENDING until all required coverage passes and Jay explicitly confirms lock. 5m/15m/busy-session settlement and dispatch hold decisions remain separate open requirements, not certified by this repair.
