# QT19 Trading Panel Layout Spec v1 (FT-U.1) - DRAFT for Jay's approval
Thread 005, 28-10-2026. Stage FT-U sits right after FT-H (Jay, 28-10-2026). No code until Jay approves this spec and the pictures.

## 1. Panels
| Panel | Where | Sizes | States | Scope |
|---|---|---|---|---|
| Left sidebar | left edge | full 230px, icons 72px, collapsed 0px (handle only) | 3 (full, icons, collapsed) | whole software (page_shell) |
| Right sidebar | right of chart, ends above the bottom card | open 360px, closed 0px | 2 | Trading Panel only |
| Bottom card | full window width, extreme left to extreme right, under both sidebars | open 220px default, drag-resizable, closed 0px | 2 | Trading Panel only |
| Chart | middle | fills what is left | - | squeezed when panels open, widened when closed |

## 2. Rules
1. A collapsed right or bottom card is NOT drawn and takes NO space (width/height 0, display none after the animation).
2. Collapsed state shows only a small glowing round handle on the screen edge. It floats over the chart edge and takes no layout space.
3. Handles are always visible, 36px round, cyan glow, chevron icon.
4. Gap between all cards: 0.5rem (today it is far larger). Inner card padding stays generous (1rem).
5. Left bar cycles full -> icons -> collapsed -> full. Right and bottom: open <-> closed. Collapsed left = 0px, no line, no space; only its handle.
6. States are saved in settings (left already saved as sidebar_stage; new keys right_panel_open, bottom_panel_open).
7. Right sidebar tabs: Trade, POI, Setups, Alerts. Order ticket card under the tabs. Existing extra cards move into these tabs.
8. Bottom card: trade details table (open trade, entry, SL, RRR, P/L in INR).

## 3. Look and motion (CSS only)
- Dark navy glass cards, cyan glow border, rounded corners, gradient and shine on active items.
- Open/close: width/height transition 420ms, spring curve cubic-bezier(0.34, 1.56, 0.64, 1); chart resizes with it.
- Handle hover: glow grows, slight scale 1.08.
- The Reduced motion setting switches all of this off (no transitions).

## 3b. Jay's changes of 28-10-2026 (wireframe v2)
9. Left sidebar collapsed state = a single round handle on the left edge, like the right sidebar. No bar, no space.
10. Right sidebar open: the four tabs sit at the very top of the card, in one tidy row, with the active tab glowing. The order ticket card starts right under them.
11. Bottom card spans the full window width, from the extreme left to the extreme right edge. The left sidebar and the right sidebar both end above it (Jay, 28-10-2026, replaces the earlier wording). On other pages the left sidebar keeps its full height.
12. Bottom card height is resizable by dragging the divider between chart and bottom card. Limits: 120px to 60% of the window height. Default 220px. Double-click on the divider resets it. Height is saved in settings.
13. All three handles are draggable along their own edge only: left and right handles move up and down, the bottom handle moves left and right. A click (less than 5px movement) opens or closes the card. A drag moves the handle and does not toggle.
14. Handle positions are saved in settings and kept inside the window. Settings gets a Reset handle positions button.
15. Page_shell gets an optional bottom slot; only the Trading Panel fills it.
16. Motion (Jay, 28-10-2026): the same spring transition runs on the left sidebar width, the right sidebar, the bottom card and the chart resize, and tab switch animations are active for all tabs in the whole software. Reduced motion switches all of them off.

## 4. Known defect to investigate (FT-U.2)
Left sidebar collapsing is defective today. Read of sidebar.py: the line stage still keeps a 14px wide card with 0.75rem margin and a 280px tall box, so it eats space. Fixed by rule 9. Where cycle_sidebar_stage lives is still to be found (SEARCH).

## 5. Pictures
Wireframe states A-D: QT19_TradingPanel_Layout_States_Wireframe_v1.png.

## 6. Approval
Jay approves: spec [ ]  pictures [ ]
