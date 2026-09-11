# QuantumTrade19 - Master Roadmap & Spec Lock (Post File 04.1) - v2

STATUS: All sections below are DESIGN LOCKED via discussion. Only Track 1
has an active build spec so far (see companion file). Tracks 2-6 are
locked in full detail here so nothing is lost across future threads.

Save at: D:\QuantumTrade19\docs\specs\QuantumTrade19_Master_Roadmap_PostFile04_v1.md
(replaces v1 - same filename, new content, versioned here as v2 for tracking)
Updated: 08-09-2026 - added Track 6

---

## Build order (locked)

```
1. File 04 Core Correction        <- ACTIVE BUILD (see companion spec file) - awaiting final live re-validation
2. Visual bug fixes (Track 2)     <- next
3. File 02.2 Scanner v2 (Track 3) <- next
4. File 04.1b persistent callouts <- next
5. File 04.3 multi-window layout  <- anytime, fully independent
6. Historical Setup Backfill      <- NEW (added this thread), see Section below
```

---

## Track 2 - Visual bug fixes (chart rendering, NOT detection logic)

### 2.1 Cross-timeframe overlay leakage (bundled into Track 1's build - see companion spec Section 5)

### 2.2 Confirmed-setup zone overlay: edge-to-edge + z-order
```
Current: zone spans roughly candle1-center to candle3-center
Fix:     zone must span candle1's LEFT edge to candle3's RIGHT edge
         (widen the time range by half a candle-duration on each side)
Price range: unchanged - highest high to lowest low across all 3 candles
Z-order: zone must always render BEHIND the candle layer, never on top
```

### 2.3 Vertical marker lines occluding candle wicks
```
For any vertical marker line (period start/end, custom lines) that
visually crosses a candle at its current pixel position:
    - Invisible from (candle's High pixel - 30px) through
      (candle's Low pixel + 30px), fully exposing that candle plus
      breathing room.
    - Above/below that gap, the line renders exactly as it does today.
If a vertical line does NOT cross any candle at its current pixel
position, it stays fully continuous top-to-bottom, no gap.
Requires per-frame/per-redraw check of which candles the line's x-pixel
currently overlaps (accounting for candle body/wick width in pixels,
not just exact timestamp match).
```

### 2.4 Droplet dot placement bug (Prv. 4H Low example)
```
Observed: "Prv. 4H Low" line correctly at 78,133.00, but the droplet
dot rendered at 78,141.60 with a visible gap to the actual wick.
Hypothesis (unconfirmed, needs source inspection at build time):
timestamp/window misalignment in _precise_dot_point() (poi_chart_mixin.py)
between how the source period boundary was bucketed (UTC vs NY timezone
mode) and how the dot-placement scan defines its search window across
the currently-loaded chart-timeframe candles.
Fix requires inspecting poi_chart_mixin.py and poi_level_calculator_worker.py
current source directly - do not guess a fix without reading the live code.
```

---

## Track 3 - File 02.2 Multi-Symbol Opportunity Scanner v2 (supersedes v1 in these areas)

Everything in `File_02.2_OpportunityScanner_Spec_Lock_v1.md` remains valid
EXCEPT the items below, which are now locked as v2 changes:

```
v1 said: Top 10 displayed, auto-monitor top 3-5 automatically
v2 says: Top 20 listed in the DASHBOARD (not just a Trading Panel radar),
         where 20 is a DEFAULT, configurable in Settings later (not a
         hard cap).

v1 said: ranking = distance + momentum + volume
v2 says: ranking ALSO includes volatility and general trend strength,
         not just POI-proximity approach momentum. Exact weighting is a
         build-time decision, not blocking this lock.

NEW: per-symbol "Trade Allowed" toggle in the Dashboard.
    Default: OFF for every newly-listed symbol.
    Only symbols with Trade Allowed = ON get continuous File 04
    monitoring across ALL THREE timeframes (1m/5m/15m), independent of
    whatever chart/timeframe is currently open in the UI.

NEW: active-trade pinning rule.
    A symbol with an active trade (paper OR real) can NEVER vanish from
    the Dashboard table, regardless of current scanner rank.
    Sort order: active-trade symbols sorted A->Z, pinned at the TOP of
    the table; no-active-trade symbols sorted by scanner rank below them.
    Active-trade rows get distinct color treatment vs no-active-trade
    rows (exact palette TBD at build time).

NEW: separate "urgency" highlight.
    Among Trade-Allowed symbols specifically, the scanner keeps a
    SEPARATE ranking/highlight for "most urgent right now" - distinct
    from the raw top-20 discovery ranking (discovery = "what's
    interesting", urgency = "what needs eyes right now").
```

All v1 sections NOT mentioned above remain unchanged and still locked:
POI scope (PDH/PDL/P4H High/P4H Low only, no zones), liquidity filter
(absolute floor AND bottom-20% relative exclusion, BOTH required),
distance/priority bands, approach-momentum calculation (60s window, 5s
samples, +1 tick/min minimum), tie-breaker (PDH/PDL beats P4H on ties),
events list, zero Telegram/Discord in this module, local SQLite only.

---

## Track 4 - File 04.1b: Persistent Setup Store + 3D Callouts

(Full detail from prior thread discussion, captured here since no
standalone file was created for it yet.)

### Locked UID format
```
<Symbol>_<DDMMYYYY NY date>_<Timeframe>_<per-symbol-per-day counter>
Example: B-BTC_USDT_07092026_5m_03
Counter scope: per symbol, per New York calendar day (NOT per timeframe -
a symbol's 1m and 5m confirmations on the same day share one counter).
Short chart-display form may omit the symbol prefix if space-constrained.
```

### Locked confidence placeholder
```
Confidence: File 05 pending
(never a fake/guessed score)
```

### Locked callout anchors
```
123Bull callout tail tip = Candle 3 LOW
123Bear callout tail tip = Candle 3 HIGH
Anchor price is FIXED forever once set; only the callout BOX can be
dragged by the user - its tail stretches/pivots to keep touching the
fixed anchor.
```

### Locked visual behavior - detection phase (temporary, CSS/SVG pseudo-3D only, zero WebGL cost)
```
- Small shaded "1"/"2"/"3" badges appear ONLY while their role is
  currently active in a pipeline (per (symbol, timeframe, poi_id,
  direction) - multiple independent badges can stack on ONE candle if
  multiple POI pipelines are simultaneously active there).
- Badges vanish immediately on confirm, fail, abort, or recycle - no
  exceptions, no "Failed" popup/label/history marker of any kind.
- No permanent record of failed/recycled attempts in the chart UI.
```

### Locked visual behavior - confirmed setup (permanent, until future lifecycle states exist)
```
- One small persistent callout, shaped per the user's reference image:
  thick colored raised rim, light/white inner face, folded upper-right
  detail, speech-bubble tail.
- Bull raised-border color: lime green.
- Bear raised-border color: crimson.
- Text: black, pillow-embossed effect, slight tilt.
- Compact by default; enlarges smoothly on hover; full detail (UID +
  confidence) shown on hover.
- Position is user-draggable; PERSISTED per symbol+timeframe+setup UID
  as an anchor-relative offset (never raw screen pixels - must survive
  resize/zoom/theme/restart).
```

### Locked placement rule (applies to ALL info objects app-wide, not just this module)
```
1. Never render inside or overlapping any candle's body or wick.
2. Prefer the nearest empty space near the candle it refers to.
3. If crowded, offset outward until clear, staying as close as possible.
4. The reference anchor point stays fixed; only the label/box moves.
```

### Locked persistence (local SQLite only, zero cost)
```
Subscribes via SetupDetectionMonitor's EXISTING subscribe(callback) bus
(File 04's own docstring already anticipates this consumer) - does NOT
touch File 04 internals.
New worker: SetupStoreWorker (same pattern as CandleStoreWorker).
Stores per confirmed setup: UID, symbol, timeframe, NY confirmation date,
daily per-symbol counter, direction, C1/C2/C3 timestamps+OHLC, fixed
anchor price, poi_id, current lifecycle state (initially "confirmed"),
FUTURE lifecycle fields ready-but-unused (sl_hit, breakeven_hit, tp1_hit,
tp2_hit, tp3_hit, trailing_active, closed), callout drag-offset, created/
updated timestamps.
Chart re-reads persisted setups whenever the displayed-day window changes,
so increasing "Display Last X Days" brings old confirmed callouts back
automatically once their Candle3 is in the visible range.
```

### Explicit deferred TODO (do not build now)
```
Visual lifecycle changes for SL hit / breakeven hit / TP1-3 collected /
trailing active / trade closed - WAIT until File 10 Risk Math Monitor and
later execution/auto-trailing modules supply authoritative events. Never
guess SL/BE/TP status from chart candles alone.
```

---

## Track 5 - File 04.3: Multi-Window Chart Workspace (new, standalone UI feature)

```
Preset layouts:
    1. Two windows top + one window bottom
    2. One window top + two windows bottom
    3. Three windows stacked vertically
    4. Three windows stacked horizontally
    5. Various two-window split combinations (vertical/horizontal split)
    6. Single window (today's current behavior - stays default)

Rules:
    - Each window is a FULLY INDEPENDENT Trading Panel instance: own
      symbol, timeframe, POI settings, drawings, setup markers - no
      shared state between panes.
    - Dividers between windows are draggable/resizable even while a
      preset is active - presets set the STARTING layout, not a locked one.
    - One button/menu to pick a preset.
    - Ideally each pane remembers its own symbol/TF when switching
      between presets, rather than resetting on layout change.
```

No dependency on POI/FSM/scanner logic - buildable independently, any time.

---

## Track 6 - Historical Setup Backfill (POI-aware rescan) - NEW, added 08-09-2026

### Why this is its own track, not part of File 04 Core Correction
```
File 04 (as originally built and as corrected in Track 1) only ever reacts
to NEW candles closing live, going forward from whenever the app process
started. It has never scanned backward over candles that already existed
before the monitor was instantiated. The user wants to verify the
role-agnostic fix (Track 1) by seeing confirmed setups appear retroactively
across the candles ALREADY visible/loaded on the chart, up to the current
live candle.

This requires POI values AS THEY EXISTED AT EACH HISTORICAL POINT IN TIME
(PDH/PDL change daily, 4H High/Low change every 4 hours) - NOT today's
current POIs. `POIMonitor.get_active_pois(symbol)` (the only read interface
SetupDetectionMonitor currently has) only ever returns TODAY's current
POIs. There is no existing method anywhere in File 03 to ask "what were
the PDH/PDL/4H levels as of 3 days ago at 2pm?" - reconstructing that is a
File 03 (POI Monitor) concern, not a File 04 concern, and touches files
File 04 Core Correction was explicitly scoped to leave alone.
```

### User's proposed approach (locked, correct, becomes the design)
```
1. FIRST calculate and store POI levels across the full requested lookback
   window (the same "Detect setups from last N days" value already used
   by setup_detect_lookback_days_map in setup_visualization_mixin.py),
   day-by-day (for PDH/PDL/daily-role POIs) and 4H-window-by-4H-window
   (for 4H High/Low POIs), respecting whatever Display/Strategy POI types
   and Timezone Mode are currently active in Settings.
2. THEN replay the already-loaded historical candles, oldest to newest,
   through the exact same Bull123FSMWorker/Bear123FSMWorker chains,
   feeding each candle the POI set that was actually active AT THAT
   CANDLE'S OWN TIMESTAMP (not today's POIs).
3. Confirmed setups from the replay populate the chart exactly like a
   live confirmation would (same overlay/dot builder, same event
   emission), so the whole existing visualization pipeline needs zero
   changes - only the REPLAY SOURCE of candles+POIs is new.
```

### What building this actually requires (scope estimate for the dedicated thread)
```
- File 03 (POI Monitor) gains a historical POI reconstruction path -
  likely a new method such as get_pois_as_of(symbol, timestamp) or a
  batch get_pois_for_range(symbol, start_ts, end_ts) that runs the
  existing PDH/PDL/4H-High/4H-Low/FVG/Inverse-FVG/Order-Block calculator
  workers (poi_level_calculator_worker.py, fvg_detector_worker.py, etc.)
  against historical candle windows instead of "now".
- SetupDetectionMonitor (File 04) gains a one-time backfill entrypoint,
  e.g. rescan_range(symbol, tf, candles) that feeds candles through
  on_candle_closed()-equivalent logic using the reconstructed
  per-timestamp POI sets instead of poi_monitor.get_active_pois().
- MTF cascade timing (MTFCascadeWorker uses wall-clock time.time() for
  timeout/proximity checks) needs a replay-safe time source, or cascade
  behavior must be explicitly skipped/approximated during backfill - to
  be decided at build time once MTFCascadeWorker's exact timing
  dependency is inspected.
- UI needs a trigger (button, or automatic on chart load) and likely a
  progress indicator, since replaying many days of candles is not
  instant.
- Files needed at build time (not yet fetched): poi_monitor.py,
  poi_level_calculator_worker.py, poi_state_tracker_worker.py, and any
  other File 03 worker that currently reads "today" instead of an
  arbitrary historical window.
```

### Explicit non-goals for Track 6 (until stated otherwise)
```
- Does NOT change the live, forward-going detection behavior at all -
  backfill is a one-time/on-demand replay, additive only.
- Does NOT persist backfilled setups differently from live ones - same
  ConfirmedSetup shape, same in-memory store (Track 4's persistent store
  is still a separate, later concern).
- Does NOT retroactively change confidence scoring (File 05, not built
  yet) - backfilled setups get the same "Confidence: File 05 pending"
  placeholder as live ones.
```
