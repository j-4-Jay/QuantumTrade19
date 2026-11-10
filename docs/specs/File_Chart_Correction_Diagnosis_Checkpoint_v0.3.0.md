# FT-H.37 diagnosis-only checkpoint v0.3.0 - 10-11-2026 04:54 IST

## Authority and scope
After two failed functional candidates (774 and 783), the AI stopped and asked Jay. Jay selected A at 04:54 IST: record both failures, then diagnose the running reset/loader path without another functional repair. This document supplements v0.1.0/v0.2.0; it is not a third candidate or feature acceptance. Existing code remains in place. No rollback, new functional change, lock or push authorized. No File 02 change or new unlock authorized. Preserve all stashes, POI copies, logs and backups.

## Verified evidence
774 applied with backup Debug/Backups/batch_20261110_034534. After test-runner adjustment 776 used installed Bun, measured 14 focused passed and 513 passed/23 skipped overall. 774 FAILED live chart check for 03:58/03:59 IST ETH 1m candles.
780 diagnostic-only helper update applied with backup Debug/Backups/batch_20261110_041447. Browser snapshots show ready and live guard true, patches delivered, reset counter increasing, but chart values remain provisional. No proof of a File 02 fault. Large forming-volume boundary values were also observed; separate uninvestigated issue.
Installed sources read: react-klinecharts 1.0.1 and KLineCharts 10.0.2. Wrapper static-data effect can replace manual onReady loader. 783 changed QT19 child to stable dataLoader prop; no dependencies edited. 783 applied with backup Debug/Backups/batch_20261110_042510. Actual test results: 21 focused passed in 2.82s; full suite 520 passed and 23 skipped in 53.00s. These tests did not establish actual browser acceptance.
783 FAILED live check again: recorder started 04:38:01 IST for openings 04:38/04:39/04:40. All three DB/exchange candles match at +10/+30/+55s. Screenshot with Source DB and CoinDCX matches 5/5 still shows chart differences:
- 04:38: chart close 2130.7 volume 341.784; DB/exchange close 2130.69 volume 357.192.
- 04:39: chart low 2130.05 close 2130.17775862 volume 523.234; DB/exchange low/close 2129.9 volume 545.205.
- 04:40: chart volume 499.71; DB/exchange volume 518.791.
An extra 04:41 screenshot shows chart volume 502.509 versus DB/exchange 522.026; recorder covers only first three candles. Do not count four recorder samples. No output confirming tracker request 784 has been supplied; do not claim it applied. Latest confirmed tracker before this checkpoint is v0.17.29 from request 777.

## Diagnosis plan (not implemented by this request)
Inspect installed KLineCharts resetData/setDataLoader behaviour and current QT19 loader/reset hooks. Trace actual init getBars invocation, the dataRef values supplied to callback, post-reset chart values, and later overwrites. Recheck whether loader identity matches supplied stable object in running build. Separate missed load, stale ref, asynchronous reset behaviour, stale compiled build and later overwrite using measurements. No third speculative repair. New instrumentation, if needed, must be clearly labelled diagnostic only and avoid orders, database writes or automatic scrolling; no broad dependency scan or edits. Preserve view and current forming candle. No more candle recordings needed until diagnostic evidence justifies another test.

## Gates and remaining work
FT-H.37 stays IN_PROGRESS/PENDING. No acceptance or lock. Update tracker after successful checkpoint output. Any later functional repair requires a new explicit decision from Jay; diagnosis approval is not that approval. Dispatch remains 9 seconds; busy-session/5m/15m settlement and setup input safety are not certified. Temporary diagnostics require deliberate removal and retest before eventual lock. No tracker trimming approved.
