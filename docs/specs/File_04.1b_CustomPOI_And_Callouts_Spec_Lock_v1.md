# File 04.1b + Track 7 - Custom POI Levels + Persistent Callouts - SPEC LOCK v1

STATUS: DESIGN LOCKED this thread - build starts in the NEXT thread
Save at: D:\QuantumTrade19\docs\specs\File_04.1b_CustomPOI_And_Callouts_Spec_Lock_v1.md
Locked on: 08-09-2026

---

## Why these two are bundled into one next-thread build

User asked for both "first," and both are needed together to actually verify
setup detection visually: Custom POI Levels solve "waiting forever for a
real POI touch," and the "1/2/3" badges + confirmed callouts solve "I can't
see whether detection is working at all." Building them together in one
thread is reasonable since the user explicitly prioritized both; they are
still functionally independent (Custom POI does not require callouts to
work, and vice versa) and will be built/checked as two clearly separated
halves inside that thread.

---

## PART A - Track 7: Custom POI Levels (entirely new feature)

### A.1 Core rule (locked)
```
A Custom POI is a user-created price level that the 123Bull/123Bear
pipeline treats EXACTLY like any other POI (PDH/PDL/4H High/Low/etc.) for
detection purposes - same Touch/Sweep/Cross classification, same
role-agnostic Bull+Bear feed (per File 04 Core Correction), same Candle1/2/3
FSM chains.

CRITICAL DIFFERENCE: a Custom POI has NO historical requirement. It starts
being "active" for detection purposes at the EXACT moment the user confirms
its creation, and remains active forward, unlimited, until deleted. It is
never backdated and never needs historical candle data to exist.
```

### A.2 Quantity and entry points (locked)
```
Exactly 5 Custom POI slots (fixed number for this version - not
user-expandable yet).
Two equivalent entry points, both open the SAME popup:
    1. A new card in Settings -> Trading Defaults tab: "Custom POI Levels"
       (5 slots, same visual pattern as the existing "Custom Recurring
       Lines" card already in poi_engine_settings_card.py).
    2. A new button on the Trading Panel chart itself (exact placement -
       toolbar/right-click menu/floating button - is a build-time UI
       decision, propose the cleanest fit with the existing chart chrome).
```

### A.3 Popup fields (locked)
```
- Name (free text, shown on the chart line's label, same place POI names
  normally appear).
- Price (the level itself) - see A.4 for the smart input behavior.
- Line color (color picker, same pattern as existing POI color inputs).
- Line thickness (same slider pattern as poi_high_line_thickness /
  poi_low_line_thickness, 1-5px).
- Line transparency (same slider pattern as existing POI transparency
  controls, 0-100%).
```

### A.4 Smart price input (locked)
```
Default value on popup open: the symbol's CURRENT live market price
(read from whatever the Trading Panel is already displaying for that
symbol - trading_panel_current_close or equivalent live tick).
Input must support BOTH:
    - Direct numeric entry (type the exact price).
    - A slider that can move the price UP or DOWN smoothly from
      whatever value is currently in the box (a bidirectional
      "nudge" slider, not an absolute 0-100 slider) - e.g. centered at
      the current value, dragging right increases price, dragging left
      decreases it, with a sensible step size relative to the symbol's
      tick size (exact step-size formula is a build-time decision -
      propose something tick-size-aware so it feels natural at any
      price scale, e.g. BTC vs a cheap altcoin).
Typing a new number in the box must also re-center/update the slider so
they always stay in sync.
```

### A.5 Post-creation behavior (locked)
```
Once confirmed, the level becomes a full POI:
    - Appears in the same place/list where other active POIs are shown
      (Settings POI matrix / chart legend / wherever POIs are currently
      enumerated - exact UI location matches existing POI conventions,
      not a new separate list).
    - Renders on the chart as a horizontal line, using the chosen color/
      thickness/transparency.
    - Feeds Bull123FSMWorker AND Bear123FSMWorker identically to any
      other POI, starting from creation time forward (per A.1).
```

### A.6 Editing (locked)
```
Double-clicking the custom POI's line on the chart re-opens the SAME
popup, pre-filled with its current name/price/color/thickness/
transparency, for editing. This works REGARDLESS of whether the line is
currently locked (see A.7) - locking only affects drag-repositioning, not
the settings popup.
```

### A.7 Manual drag + lock (locked)
```
The user can drag the custom POI's line vertically on the chart to
reposition its price directly (in addition to typing/sliding in the
popup).
A small lock icon/button appears near the line's label. When locked:
    - Manual drag repositioning is disabled.
    - Double-click settings popup STILL opens and can still change the
      price via the popup's input/slider even while locked (A.6) - lock
      only blocks the direct chart-drag gesture, not the popup edit path.
```

### A.8 Deletion
```
A delete option must exist somewhere reachable from the popup or the
settings card (exact placement is a build-time decision) - a Custom POI
that's no longer wanted must be removable, immediately stopping it from
feeding the FSM pipelines from that point forward. Deleting does NOT
retroactively remove any setups it already helped confirm.
```

### A.9 Persistence
```
All 5 slots' name/price/color/thickness/transparency/locked-state persist
across app restarts, same generic _engine.security.persistence pattern
used everywhere else in Settings.
```

### A.10 Files likely touched (confirm/adjust at build time once sources are read)
```
- New: engines/workers/poi/custom_poi_worker.py (or similar) - owns the 5
  slots' state + exposes them alongside get_active_pois() output so
  SetupDetectionMonitor sees them identically to real POIs.
- state/app_state_mixins/poi_settings_mixin.py or a new dedicated mixin -
  popup state, slot CRUD, persistence.
- ui/components/poi_engine_settings_card.py - new "Custom POI Levels" card.
- ui/components/ (new) custom_poi_popup.py or similar - the popup itself.
- ui/components/kline_chart.py / trading_panel_chart.py - drag-to-
  reposition gesture handling, double-click-to-edit handling, lock icon
  rendering.
- engines/monitors/poi_monitor.py - must include custom POIs in whatever
  it returns from get_active_pois(symbol) (read-only from File 04's POV).
Files needed at build time (not yet fetched): poi_monitor.py, poi_types.py,
poi_chart_mixin.py, kline_chart.py, trading_panel_chart.py.
```

---

## PART B - Track 4: "1/2/3" in-progress badges + persistent confirmed callouts

Full detail already locked in `QuantumTrade19_Master_Roadmap_PostFile04_v1.md`
Track 4 section (UID format, confidence placeholder, callout anchors,
detection-phase badge behavior, confirmed-callout visual spec, placement
rule, SQLite persistence via new SetupStoreWorker). That section is the
authoritative spec for Part B - repeated here only as a pointer, not
duplicated, to avoid drift between two copies.

### B.1 Immediate purpose this thread adds to Track 4's existing spec
```
The user's stated goal for wanting this now specifically: SEE the "1"/"2"/
"3" badges appear/disappear live on the chart as candles get tested by the
FSM, and see a permanent callout appear the moment a setup CONFIRMS - this
is the direct visual proof that detection is running correctly, badge-by-
badge, complementing (not replacing) the existing candle-highlight+icon
overlay that setup_visualization_helper.py already produces.
```

### B.2 Files likely touched (confirm/adjust at build time)
```
- New: engines/workers/setup/setup_store_worker.py (SQLite persistence).
- engines/monitors/setup_detection_monitor.py - subscribe SetupStoreWorker
  via the EXISTING subscribe(callback) bus (no internal changes needed
  per Track 4's original design).
- _fsm_base.py / bull123_fsm_worker.py / bear123_fsm_worker.py - MAY need
  a way to expose "which candle currently holds role 1/2/3 in an ACTIVE
  pending chain" for the badge renderer - exact mechanism (new getter vs
  reusing get_pending()) is a build-time decision once these files are
  re-examined together with the badge UI requirement.
- setup_visualization_helper.py / setup_visualization_mixin.py - badge +
  callout dot/overlay shapes, on top of the existing confirmed/pending
  shapes (additive, not replacing).
- ui/components/kline_chart.py or trading_panel_chart.py - badge stacking
  rendering, callout box rendering (raised rim, drag-persist, hover
  expand), per Track 4's exact visual spec.
Files needed at build time (not yet fetched): kline_chart.py,
trading_panel_chart.py, poi_chart_mixin.py (for consistent drag/placement
conventions already used for POI droplets).
```

---

## Check gate for this next build (draft - refine at build time)
```
1. Automated tests: existing File 04 suite (29/29) must still pass
   unchanged - Custom POI and callouts are additive, must not touch FSM
   core logic.
2. New test: a Custom POI created with a price equal to the current live
   price starts feeding Bull+Bear FSM chains immediately (same as any
   other POI touch test).
3. New test: SetupStoreWorker persists a confirmed setup and reloads it
   correctly after a simulated restart.
4. User re-validates live: creates a Custom POI near the current price,
   watches a natural candle sequence trigger 1/2/3 badges, and watches a
   confirmed callout appear on completion.
5. User re-validates: double-click edit, drag reposition, lock/unlock,
   and delete all work as specified for a Custom POI.
```
