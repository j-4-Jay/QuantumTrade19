# File 04.1c - Setup Callouts Spec v2 (VISUAL DESIGN LOCKED by Jay, 31-10-2026)

Status: the visual design in sections 2 to 6 is LOCKED by Jay on 31-10-2026 (thread 006). Sections 7 to 9 are approved intent; their details are agreed step by step before code.
Replaces: the visual parts of docs/specs/File_04.1c_Callouts_Spec_v1.md (sections 2, 3 and 5). Rules for outcomes (v1 section 7 and 7b) are unchanged.
Reference pictures: QT19_Callout_Journey_123Bull_v8.png and QT19_Callout_Journey_123Bear_v8.png (seven states each). They are the source of truth for the look.

## 1. Purpose
One callout per confirmed 123Bull or 123Bear setup. It shows the setup, the trade state and the Confidence Score at a glance, on a dark chart, with the text always easy to read.

## 2. Border and LED glow (never change in the life of a setup)
- 123Bull: border #0E9464, LED glow #1FE0A0, direction icon pointing up.
- 123Bear: border #990000, LED glow #FF3B3B, direction icon pointing down.
- The glow is a soft strip around the outside of the border only (never inside the card), not pulsing.
- The border colour is the main symbol of the setup and never changes through the journey.

## 3. Body colour by state (dark glass with a top highlight band)
- Creation and running: #4188FF, deepened toward navy at the bottom, white text. This is the creation default.
- Journey toward SL: the body goes from #4188FF to #FF6200 through violet, pink and coral (OKLCH mix). Text stays white (contrast about 4.2 or better).
- SL Hit: bright #FF6200 with dark text.
- Closed Win: mint #9FE2BF with dark text.
- Break Even hit: #FFCE1B with dark text.
- Toward profit the body stays the single running colour; it becomes mint only when the win closes. The fade is for the SL journey only.
- The text colour is chosen by contrast; there is no half-way text colour.

## 4. Inner cards
- ENTRY, SL and TICKS cards: inside colour always #0D142C, in every state.
- Card edges and labels: ENTRY #35D0FF, SL #FF5A5F, TICKS #FFC83D. Values are white and bold.

## 5. Confidence Score sticker
- Round scalloped sticker on the top-right corner, tilted 11 degrees, shiny (gloss streak and sparkle), white rim, soft shadow, with the text CONFIDENCE SCORE curved along the top.
- Colour by state: creation and journey gold (#FFC83D family, dark text); SL Hit #2B343C; Closed Win #0A3A29; Break Even #EC267D. The three darker stickers use white text.
- The score is a whole number from 1 to 100, font size 22 (the same as the heading). Until File 05 exists it shows a dash and the small word FILE 05. A score is never guessed.

## 6. Layout (base size x = 320 by 187)
- Row 1: direction icon, name (123Bull or 123Bear) and the timeframe.
- Row 2: ENTRY, SL and TICKS cards.
- Row 3: Qty and Risk (INR).
- Row 4: Live RRR and Peak RRR.
- Last line: the UID.
- No empty band at the top. The sticker overhangs the top-right corner by about 37 px.

## 7. Pointer, drag and resize (approved intent)
- The pointer tip snaps to the centre of the setup block: the top side when the callout sits above the block, the bottom side when it sits below. This replaces the old rule (Candle 3 Low or High plus 3 ticks).
- Dragging the callout past the block centre swaps the side automatically. The tail stretches with the position.
- Default size is x/2. The four corners resize proportionally from x/4 (smallest) to x (largest); text and framework scale together.
- Position and size are saved per setup when dropped. The first version saves in the browser (no server load). A database copy can follow.

## 8. Setup detection state 1 to 2 to 3 (approved intent)
- While a setup forms, the three candles get the numbers 1, 2 and 3: lime green for 123Bull and orange-red for 123Bear.
- The letters stay readable in normal chart mode and scale with the candle size when the chart is zoomed.
- A short formation animation runs only when a number appears. No always-running loop. The first priority is zero extra load, then look and feel.
- This replaces the old blue pending label. The old Bull and Bear check-mark labels are already removed.

## 9. Performance rules
- Draw again only when a shown value changes. No timers for animation. Honour the Reduced motion setting.
- Colours are computed in the browser from the state, with no images.

## 10. Open items
- Whether the journey colour fades linearly or with a slow start is not decided; version one uses a linear fade.
- Break Even needs the trailing SL (later); the design is ready.
