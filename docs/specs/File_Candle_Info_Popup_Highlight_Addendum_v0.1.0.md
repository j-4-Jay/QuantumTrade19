# FT-H.39 candle locator addendum v0.1.0
Requested by Jay 08-11-2026. Extends File_Candle_Info_Popup_Spec_v0.1.0.md.

Click popup content to locate its original candle with a soft yellow glow, pulsing smoothly for 2 seconds. A repeated click restarts it; only one locator per chart. Buttons, dotted drag handle and resize grip retain their existing actions. Reduced motion uses a steady glow for 2 seconds. Use the original symbol, timeframe and exact timestamp; never substitute a neighbouring candle. If timeframe differs or the candle is not loaded/visible, show a note without moving the chart. Close/detach cancels the glow. No network/database calls. Animation runs only during the 2-second locator; no persistent new polling. Soft appearance uses box-shadow, not a blur filter.

Jay confirmed the original 13 checks on 08-11-2026; this addition remains PENDING and no lock is approved yet.

Verification: (1) click popup content: correct candle glows for 2 seconds; (2) click again: restarts, no duplicate glow; (3) buttons/drag/resize unchanged; (4) Reduced motion: steady glow then disappears; (5) different timeframe: note and no wrong candle; (6) offscreen/missing candle: note, no chart jump; (7) close/symbol switch/page exit during glow: no leftover; (8) after 2 seconds CPU returns to idle.

