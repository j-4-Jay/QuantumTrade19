# File 04 - Touch Rule REVISION 5 (123Bull and 123Bear) - Spec Lock v1

Status: PENDING Jay's live check. Rule confirmed by Jay on 05-11-2026. Supersedes the touch condition in Section 6 of 123Bull_Setup_Master_Prompt.md and 123Bear_Setup_Master_Prompt.md and REVISION 4 of engines/workers/setup/_fsm_base.py.

## The rule (Bull = Red, Green, Green. Bear = Green, Red, Red. Same rule, mirrored)

1. Three consecutive closed candles, same timeframe, separate search for each POI.
2. POI condition: Candle 1 and/or Candle 2 must touch (touch, sweep or cross) the POI. Either one, or both. Candle 3 does not need to touch.
3. A candle that touches the POI and has a different colour from the candle before it is Candle 2; the candle before it is Candle 1 (Candle 1 does not need to touch).
4. A touching candle with the same colour as the candle before it starts a new attempt as Candle 1.
5. A Candle 1 that touched the POI: the very next candle is tested as Candle 2 even if it does not touch. Different colour = Candle 2. Same colour = the attempt ends (a same-colour candle that touches starts a new attempt as Candle 1).
6. Candle 3 has the same colour as Candle 2 and closes beyond Candle 2's extreme (Bull: above its high. Bear: below its low). Only the close counts.
7. If Candle 3 fails, Candle 2 is recycled as the new Candle 1. If that candle touched the POI itself, rule 5 applies to the next candle. If it did not touch, the next candle must touch (no silent drift).
8. After a doji (no colour) the recycled candle is kept as Candle 1 only if it touched.
9. Confirmed candles are locked as before (Strict Candle Reuse Lock setting unchanged).

## Example (XAU 1m, 05-11-2026)

Big green candle crosses the 4H High POI (4077.16): Candle 1. Small red candle touches it (low 4077.14): Candle 2. Next candle green: fails as Candle 3. Red candle recycled as Candle 1 (it touched). Next green = Candle 2 (no touch needed). Next green closes above its high: 123Bull confirmed.

## Code and tests

Code: engines/workers/setup/_fsm_base.py (one shared change for Bull and Bear). Tests: tests/test_setup_touch_rule_rev5.py. Two older tests that described the REVISION 4 behaviour were renamed to _superseded_by_rev5_... in tests/test_setup_detection_monitor.py.
