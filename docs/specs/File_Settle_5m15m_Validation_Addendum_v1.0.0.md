# FT-H.37 bounded 5m/15m validation addendum v1.0.0

## Authority
Jay approved option 1 on 10-11-2026 06:21 IST and said proceed at 06:22. This authorizes a separate diagnostic helper, not a third functional chart repair, dispatch modification, feature acceptance or lock. Earlier failed candidates 774/783 and diagnosis checkpoints remain valid. Current scope remains IN_PROGRESS/PENDING.

## New files only
4c. Validate_Settle_5m15m.py and .bat; 4c. Evaluate_Settle_5m15m.bat; tests/test_settle_5m15m_observer.py. Existing helpers, loader, chart, File02, dispatch, credentials and databases are not modified. Reports only under Debug; never stage reports. Standard library tests use fabricated data and a temporary synthetic SQLite database, never the project database.

## Measurement contract
ETH only; three future UTC-epoch-aligned closes each of 5m and 15m, scheduled together. Target offsets 1/5/9/10/15/20/30/55 seconds. Maximum 48 public HTTP requests without retries. Each uses the futures candlesticks endpoint with resolution 5 and pcode f. 5m requires the exact timestamp; 15m requires all three exact native 5m timestamps and aggregates OHLCV. Missing or duplicate constituents are errors, not partial 15m matches. This is an exchange-derived reference, not a native 15m terminal comparison.

Read-only SQLite URI, exact symbol/timeframe/open-time queries. DB read before and after public request; match requires both to match all five reference values within absolute tolerance 1e-6. Public requests and SQLite reads are sequential, not atomic. Capture scheduled offset, request start/completion epoch and offsets, monotonic duration and errors. Starts over two seconds late skip network work; completions over two seconds late are inconclusive. No catch-up request burst, retries, background app hook, live order path or automatic refresh. A synchronous request may delay another observation; delays remain visible. Requests timeout at three seconds, but network and DNS behaviour can exceed a wall-clock expectation. Clock changes detected during observations are errors; use a stable computer clock.

## Interpretation and limits
CSV contains raw values and timing; JSON summary contains final status and matching suffix against the final observed reference. Suffix is observed convergence only, never exact settlement. All scheduled observations must be reviewed for errors, missing data, changes and lateness. A MATCH is not chart acceptance. No safe-delay recommendation or nine-second dispatch approval. Even a match before nine seconds cannot prove what the worker actually consumed. A +9 request completed later than nine seconds is not evidence of readiness at nine seconds. This single bounded sample is not busy-session or universal safety certification.

## Evaluation and Jay gate
Offline tests: boundaries and scheduling, strict constituent completeness/duplicates, finite values, timing and errors, late-skip no I/O, late completion, read-only synthetic DB and revised reference suffix. Sandbox: 12 tests passed; local project tests pending. Run evaluation launcher first and stop on failure. No predicted full-suite count is a measured result.

After local evaluation passes, Jay runs the observation launcher with the app already running normally. No concurrent recorder/calibrator. Up to about 46 minutes from start, possibly longer on network delays. Check: correct ETH/timeframes and report paths; per-observation status and actual completion offsets; six candle summaries; missing/error/late results reported without false matches; original chart/countdown/popup behaviour unchanged. Send final report summary and any errors. Do not repeat chart acceptance merely because this observer matches. No lock without Jay approval and remaining gates.

## Risks
Adds up to 48 public requests outside the app shared limiter; do not run other measurement helpers concurrently. Reports add small machine-local files to Debug. No original files replaced by this build; CSV/tracker reconciliation follows in the same work cycle. No push or cleanup authorized.
