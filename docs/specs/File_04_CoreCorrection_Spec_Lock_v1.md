# File 04 Core Correction - SPEC LOCK v1
## Role-Agnostic Direction Detection + Strict Candle Reuse Toggle

STATUS: DESIGN LOCKED - reopens File 04 (previously locked at v0.4.0-alpha)
Save at: D:\QuantumTrade19\docs\specs\File_04_CoreCorrection_Spec_Lock_v1.md
Locked on: 08-09-2026

---

## 1. Why File 04 is being reopened

Live chart observation on B-BTC_USDT 1m showed 123Bull setups confirming
repeatedly while 123Bear setups almost never fired, even near candle
sequences that visually looked like valid Green-Red-Red patterns. Root
cause found: `POIInteractionDetectorWorker` currently assigns
`search_direction` based on the POI's role:

```
role == "support"    -> search_direction = SetupDirection.BULL (only)
role == "resistance" -> search_direction = SetupDirection.BEAR (only)
```

This was an implementation assumption made while wiring File 04, NOT a
requirement of `123Bull_Setup_Master_Prompt.md` / `123Bear_Setup_Master_Prompt.md`.
The user has explicitly rejected this gating: support/resistance role is
POI metadata for a POSSIBLE FUTURE different setup type, and must have
ZERO influence on 123Bull/123Bear detection eligibility.

## 2. Corrected rule (locked)

```
Every closed candle's interaction with EVERY active POI - regardless of
that POI's role (support/resistance) or type (PDH/PDL/4H High/4H Low) -
feeds BOTH the Bull123FSMWorker AND the Bear123FSMWorker for that
(symbol, timeframe, poi_id).

Role-based direction gating is REMOVED entirely from the 123Bull/123Bear
pipeline.
```

Concretely, in `engines/workers/setup/poi_interaction_detector_worker.py`,
`_classify_interaction`'s caller (`detect()`) currently builds ONE
`Interaction` per POI with a single `search_direction`. This must change
to either:
  (a) emit `search_direction=""` (both) and let the Tier-2 assembly feed
      the SAME interaction dict to both `bull_interactions` and
      `bear_interactions`, or
  (b) emit two logical interactions (or one interaction consumed by both
      dicts) so `SetupDetectionMonitor.on_candle_closed()`'s existing
      split:
      ```python
      bull_interactions = {i.poi_id: i for i in interactions if i.search_direction == SetupDirection.BULL}
      bear_interactions = {i.poi_id: i for i in interactions if i.search_direction == SetupDirection.BEAR}
      ```
      populates BOTH dicts for the SAME poi_id whenever a touch occurs.

Exact implementation choice is a build-time decision, not a design
constraint - either approach preserves the existing, already-correct
per-poi_id parallel-pipeline behavior (Section 4 below).

Scenario-B retest / double-cross-flip logic (Section 5 of the master
prompts) is UNCHANGED - it still reads `POIStateRecord.state` and
`INVERSE_FVG` role directly from File 03, exactly as before. Only the
BASE role->direction restriction is removed.

## 3. New Settings toggle: Strict Candle Reuse Lock

```
Setting name:    Strict Candle Reuse Lock
Setting default: OFF
```

| State | Behavior |
|---|---|
| ON | Current locked behavior, unchanged: once a candle is part of a CONFIRMED setup, it can never be used as Candle1/2/3 in any other setup on that (symbol, timeframe), ever again. |
| OFF (default) | Every candle that interacts with a POI runs the full Candle1/2/3 detection test, regardless of whether it or its neighbors already belong to a previously confirmed setup. |

Implementation touchpoint: `_Base123FSMWorker._step_waiting_c3()` in
`engines/workers/setup/_fsm_base.py` currently does:
```python
if self._lock_registry.any_locked([c1, c2, candle]):
    confirmed = False
```
unconditionally. This must become conditional on the new setting - when
the setting is OFF, this check must be skipped entirely (treat
`any_locked(...)` as always False), while `CandleLockRegistry.lock_all()`
can still be called on every confirmation (harmless bookkeeping) so that
flipping the toggle ON later starts enforcing from that point forward
without needing a restart.

The setting must be read live (not baked in at construction), consistent
with every other Settings toggle already used elsewhere in the app
(e.g. `poi_display_enabled` / `poi_strategy_enabled` patterns).

## 4. What is explicitly NOT changing (already correct, verified from source)

```
- Per-(symbol, timeframe, poi_id) parallel pipelines: ALREADY correct.
  A single candle touching multiple POIs already runs multiple
  independent FSM chains today - confirmed directly from
  SetupDetectionMonitor.on_candle_closed()'s existing loop over
  touched_poi_ids | active_poi_ids. No change needed here.
- Candle1/Candle2/Candle3 color rules, confirmation extreme tests,
  recycle-on-fail logic in _fsm_base.py: UNCHANGED, already validated
  against real historical data at the original v0.4.0-alpha lock.
- MTF cascade worker: UNCHANGED.
- Engulfing / FVG confirmation confidence-input workers: UNCHANGED.
```

## 5. Companion fix bundled into this same build pass (visualization safety, not FSM logic)

While diagnosing a "detection with no visible POI" report, the most
likely explanation was NOT a Display/Strategy misconfiguration (user
confirmed both were ON for the 4 active POI types) but a possible
cross-timeframe overlay leakage: `market_data_monitor.py`'s candle-close
subscriber already forwards EVERY closed candle on EVERY timeframe
(1m/5m/15m) to `SetupDetectionMonitor.on_candle_closed()`, regardless of
which timeframe is visually selected on the Trading Panel. The
visualization mixin (`setup_visualization_mixin.py`) may be showing a
stale or wrong-timeframe overlay if it does not refresh IMMEDIATELY on a
symbol/timeframe switch (it currently only refreshes on its ~3s poll
tick).

Locked defensive fix (bundled with this same build, regardless of
whether this was the exact root cause):
```
1. Overlays/dots must be strictly filtered to the EXACT currently
   selected (symbol, timeframe) pair - never show a setup computed for
   a different timeframe than the one currently rendered.
2. Switching trading_panel_symbol or trading_panel_chart_tf must trigger
   an IMMEDIATE refresh_setup_visualization() call, not wait for the
   next background poll tick.
```

## 6. Check gate for this reopening (required before re-lock)

```
1. Automated suite: existing 25/25 (or current count) File 04 tests must
   still pass with the role-agnostic change (existing tests may need
   updates if any hard-coded a role->direction assumption).
2. New automated test: one POI touch must be shown to start BOTH a Bull
   pending chain AND a Bear pending chain simultaneously, for the SAME
   poi_id.
3. New automated test: Strict Candle Reuse Lock OFF allows a candle
   already used in a confirmed setup to be reused in a new pipeline;
   Strict Candle Reuse Lock ON preserves the original no-reuse behavior.
4. Real live-chart re-validation: user re-observes B-BTC_USDT 1m (or any
   live symbol) and confirms 123Bear setups now form under the same
   conditions that previously only produced 123Bull setups.
5. Visualization check: user switches symbol/timeframe on the Trading
   Panel and confirms no stale/wrong-timeframe setup marker ever appears.
```

## 7. Explicit non-goals for this pass

```
- Does NOT touch the Scanner (File 02.2), the persistent setup store /
  3D callouts (File 04.1b), or the multi-window workspace (File 04.3).
- Does NOT change Candle1/2/3 color rules or confirmation math.
- Does NOT change MTF cascade behavior.
- Does NOT touch Dashboard/Journal/Alerts pages.
