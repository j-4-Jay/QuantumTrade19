# File 04.1c - Setup Callouts Spec v2 - Addendum 1 (approved by Jay, 31-10-2026)

Adds to docs/specs/File_04.1c_Callouts_Spec_v2.md (the visual design there stays LOCKED). These items are approved by Jay; the full-journey pictures for mini and big views are shown for the final lock.

## 1. Content changes
- The heading shows the STATE name instead of 123Bull or 123Bear: Running, SL Hit, Win, B.E. The timeframe follows with a dot, then the POI short name with a dot. The direction is shown by the border colour and the icon.
- Zone POIs carry the source timeframe prefix, for example 4H FVG. Month uses 1Mo and minute uses 1m so they never look alike.
- Row of three: QTY, RISK and PROFIT. RISK is the flat amount per setup (Rs 1000 now). PROFIT is Live RRR times the risk amount: positive green, negative red, zero plain.

## 2. POI short names (chart labels already in the software)
Lines: P1m H, P1m L, P5m H, P5m L, P15m H, P15m L, P1H H, P1H L, P4H H, P4H L, PDH, PDL, PWH, PWL, PMH, PML.
Zones: R-Flip, S-Flip, FVG, iFVG, OB (with the source timeframe prefix). Independent POI: IND.

## 3. Mini and big views
- The mini view is the default at creation: row 1 the straight Confidence badge; row 2 the stage name and the POI name. Pointer, drag, snap, placement and the colour journey are the same as the big view.
- Click on the stage name expands to the big view. The badge slides to its tilted place and the name slides to the heading place. After a short delay the other info dissolves in, one by one in a shuffled order.
- Click anywhere else (not the badge) reverses it: the info dissolves out in shuffled order, then the badge and the name slide back to the mini places.
- Extras: a ring around the badge that fills to the score; the score counts up once on expand; one light sweep across the glass. They run once per click; nothing runs while idle; Reduced motion switches them off.

## 4. Score badge popup
- A click on the badge opens a popup. For now it shows the text Score Table Coming Soon. Later it lists every factor of the Confidence Score with its own score. No Close or Save button; it closes on a click outside. The badge click does not expand or collapse the callout.

## 5. One setup with many POIs (VERY IMPORTANT)
- When one setup is linked to more than one POI, then after the Candle 3 confirmation each POI opens its own trade and shows its own callout.
- Open points to settle before code: flat risk per setup or per POI trade; where the callouts of one setup sit so they do not cover each other.

## 6. Right-click menu
- Under Hide Candles: a Callouts item with a flyout: a switch for each stage (Running, SL Hit, Win, B.E.) and an All ON or OFF switch. The Callouts item shows a small tag when any stage is switched off.
- Change Mode becomes a flyout of switches, one ON at a time, with a reset button: Auto match App Theme.

## 7. Speed rules
- Each callout is its own layer and moves by transform, not by left and top. Redraw only when a shown value changes. Measured 31-10-2026 (software-only test): 40 big callouts by left and top 324 ms per frame; own layer plus transform 23 ms; 40 mini callouts 17 ms.
