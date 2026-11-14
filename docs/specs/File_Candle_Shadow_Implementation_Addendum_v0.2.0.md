# QT19 Candle Shadow Implementation Addendum v0.2.0
Thread009 | 12-11-2026 04:04 IST | BUILD, NOT ACCEPTED OR LOCKED
Supersedes only Shadow implementation details in File_Candle_Stream_Toggle_Design_v0.1.0.md. Stream mode, its proposed timing/quiet-period rules and a production toggle are NOT implemented or approved. Jay approved Shadow-first03:41 and small market_data_monitor.py hooks plus new worker/log/tests04:02. No other existing code path unlocked.

## Implemented scope, pending application and local evaluation
- New candle_shadow_worker.py, shadow_evidence_log.py, two offline test files, Start_Candle_Shadow and Evaluate_Candle_Shadow BAT launchers.
- Existing market_data_monitor.py: opt-in startup after existing initialization, stop, subscription lifecycle, observation of current close, subscriber-delivery attempt and incoming reconciliation values. No change to decision callbacks, persistence, dispatch delay, chart, setup rules or locks.
- Default OFF. New launcher's process-scoped QT19_CANDLE_SHADOW=1 is inherited by existing clean PowerShell launcher; setlocal restores caller environment. No settings file edits. Worker is also disabled automatically during pytest. No new orders, credentials or REST requests.
- Separate transport and bounded nonblocking queue4096. Current feed callbacks copy only public numeric candle fields into observation queue; no log I/O or network wait in those callbacks. Overflow count invalidates completeness, never silently counted as success.
- Network observer supervises a separate socket, retry1..30seconds on connection loss/10s without candle events; emit/parser/log errors may stop observation with an error log rather than affect the current feed. No unconditional data-continuity assertion. Channel heartbeat is not per-symbol completeness.
- Stop requests worker exit and waits at most2seconds; if transport connect is still blocked, report stop_pending. Reader/transport teardown can finish later. Do NOT claim instant shutdown. Existing transport timeout semantics remain unchanged. Restart does not start a second observer while the old one is alive.

## Evidence
Debug/CandleShadow/shadow_<UTC>_<unique>.jsonl; new exclusive file each observer instance. No automatic deletion, overwriting or database writes. Max20MB new file; existing shadow files count against100MB directory allowance checked at open; reached cap disables observation, never deletes history. Quota is per-process accounting, not a filesystem-wide reservation against concurrent processes. One QT19 server only. Free space/quota failure stops observer and logs error. Current feed continues.
- stream_update: symbol,timeframe,exact aligned open_time,numeric OHLCV, exchange Ets and local receipt timestamp.
- current_close/current_delivery/reconcile_observation: detached values and stream snapshot then known, exact match flags. current_delivery means attempted fan-out, NOT proof every subscriber succeeded. reconcile_observation means returned REST/reconciliation values, NOT guaranteed exchange-final or successful database save.
- scheduled_snapshot at +1/+3/+10s: requested/actual capture times, lateness, queue loss, capture_on_schedule flag. Flag only means capture timing criteria, NOT data correctness, finality, decision readiness or full interval coverage. A queue backlog or updates received after requested offset are flagged; do not present late snapshots as at-offset evidence.
- Connection epochs, losses, session starts/stops, clock discontinuities. Old cache discarded at reconnection. Cache holds30minutes, max2048 keys; no input replay. 15m current-path observations may be logged but no stream15m derivation is supplied in this milestone.
- local_minus_Ets is a timestamp difference combining clock skew, network and exchange timestamp semantics. It is NOT a measured clock offset and is not used to correct data or schedule trading.
- No raw credentials, settings or arbitrary payload dumps. Futures product/pair/channel/interval, finite OHLCV and aligned timestamps validated.

## Measurement limitations and earlier result correction
Probe825/828 summary is promising:20ETH1m and4ETH5m match later REST at+1s. Last observed update is not guaranteed final; partial first/last intervals, later changes outside recording, clock mismatch and connection gaps must be checked before making an SLA claim. Earlier claim of a measured six-times speedup or exact0.29s correction is unsupported: runs differed and timestamp differences are not clock calibration. Trade-built comparisons are inconclusive for architecture selection: initial partial capture/deduplication/completeness were not established. Do not drop an alternative on those counts alone. No universal3s guarantee, busy-session pass, chart correctness pass or Jay acceptance.

## Evaluation sequence
1 BUILD: apply request; app stopped; U+ENTER only named monitor path. Stop if any validation, backup or anchor fails.
2 EVALUATE: Evaluate_Candle_Shadow.bat runs only offline Shadow/helper tests and existing probe tests. New tests have no sockets or database construction. Full project suite still PENDING until existing persistence tests' isolation is verified; do not assume suite is database-free.
3 REBUILD/REEVALUATE on failure; two failed repairs of same defect require stop and Jay decision.
4 JAY TESTS after offline pass and explicit go-ahead: normal launcher off; then app fully stopped and Shadow launcher; current chart/feed/countdown/popup unaffected, evidence appears, one observer per server, subscription changes/stop/restart; observe enough actual closes, inspect bounded evidence for drops/disconnects/correctness. Do not request database changes, intentional production network outage or live orders.
5 JAY CONFIRMS / LOCK: only explicit Jay result and authorization. None supplied yet. No staging, tag, commit or push in this build.

## Records
FT-H.37 remains IN_PROGRESS/PENDING, failed774/783 chart acceptance and retained diagnostics remain valid. Earlier CSV/tracker discrepancy is unresolved; live local row is code-independent task-status evidence, not proof all office work was pushed. Reconcile without overwriting older evidence. Standalone probe825 applied4/4;828 applied2/2; latest probe-focused13passed0.38s. New sandbox checks21passed0.04s include synthetic monitor-hook harness, NOT actual local regression or network proof.
