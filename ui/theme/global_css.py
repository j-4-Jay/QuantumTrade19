"""Global CSS keyframes + forced cursor override + autofill detection.

PATH: ui/theme/global_css.py  (REPLACE ENTIRE FILE)

FIX v0.4.55 - completely rebuilt the hover-glow technique after TWO
targeted CSS specificity fixes (!important, style unification) produced
zero visible change. Rather than keep fighting box-shadow precedence
rules on the card element itself, this uses a structurally different,
bulletproof technique: a SEPARATE glow layer element, positioned behind
and slightly larger than the card, that only changes OPACITY on hover.
Since this glow layer is not the same DOM element as the card and never
touches box-shadow at all, there is no possible CSS specificity conflict
with any inline style the card itself has - the glow can never be blocked
by anything on the card, structurally guaranteed regardless of the card's
own background/border/box-shadow/overflow.

New classes:
  .qt19-glow-wrap   - put on the OUTER wrapper (position: relative)
  .qt19-glow-layer  - the actual glow element, a child of the wrapper,
                      absolutely positioned slightly larger than the
                      wrapper, blurred, transparent at rest, becomes
                      visible only via opacity on :hover of the wrapper
  .qt19-glow-content - put on the actual card/content box (the translucent
                      glass card itself), sits ABOVE the glow layer via
                      z-index so the card's own background naturally
                      masks the center of the glow, leaving only a soft
                      ring visible around the edges - the correct "glow
                      bleeding out from behind a glass card" look.

See ui/components/glow_card.py for the ready-made component that wires
these three classes together correctly - use qt19_glow_card(...) instead
of manually combining GLASS_CARD_STYLE + HOVER_GLOW_CLASS from now on.

CHANGE (v0.4.51-v0.4.52, superseded): the [data-radius="full"] exclusion
and !important box-shadow attempts are no longer needed for the glow
specifically (kept below only because [data-radius="full"] may still
protect something else unrelated I cannot see from this file), since the
new glow layer never has box-shadow or the "full" radius data attribute.
"""
from __future__ import annotations
import reflex as rx


_CSS = """
* { cursor: auto !important; }
button, a, [role="button"], input[type="checkbox"], input[type="radio"] { cursor: pointer !important; }


[data-radius="full"]:not(.qt19-hover-glow):not(.qt19-glow-wrap):not(.qt19-glow-content) { overflow: hidden !important; }


@keyframes qt19-autofill-detect { from {} to {} }
input:-webkit-autofill { animation-name: qt19-autofill-detect; animation-duration: 0.001s; }


:root {
  --qt19-pulse-blur-min: 2px;
  --qt19-pulse-blur-max: 6px;
  --qt19-pulse-spread-min: 0px;
  --qt19-pulse-spread-max: 1px;
}


@keyframes qt19-heartbeat {
  0%   { box-shadow: 0 0 var(--qt19-pulse-blur-min) var(--qt19-pulse-spread-min) var(--qt19-pulse-color, #DC143C); }
  10%  { box-shadow: 0 0 var(--qt19-pulse-blur-max) var(--qt19-pulse-spread-max) var(--qt19-pulse-color, #DC143C); }
  20%  { box-shadow: 0 0 var(--qt19-pulse-blur-min) var(--qt19-pulse-spread-min) var(--qt19-pulse-color, #DC143C); }
  30%  { box-shadow: 0 0 var(--qt19-pulse-blur-max) var(--qt19-pulse-spread-max) var(--qt19-pulse-color, #DC143C); }
  45%  { box-shadow: 0 0 var(--qt19-pulse-blur-min) var(--qt19-pulse-spread-min) var(--qt19-pulse-color, #DC143C); }
  100% { box-shadow: 0 0 var(--qt19-pulse-blur-min) var(--qt19-pulse-spread-min) var(--qt19-pulse-color, #DC143C); }
}
.qt19-heartbeat { animation: qt19-heartbeat 1.6s ease-in-out infinite; transition: background 0.35s ease; }


@keyframes qt19-shake {
  0%, 100% { transform: translateX(0); }
  15% { transform: translateX(-8px); }
  30% { transform: translateX(7px); }
  45% { transform: translateX(-6px); }
  60% { transform: translateX(5px); }
  75% { transform: translateX(-3px); }
  90% { transform: translateX(2px); }
}
.qt19-shake { animation: qt19-shake 0.4s ease; }


@keyframes qt19-tab-switch {
  from { opacity: 0; transform: translateX(12px); }
  to   { opacity: 1; transform: translateX(0); }
}
.qt19-tab-switch { animation: qt19-tab-switch 0.35s cubic-bezier(0.22,1,0.36,1) both; }


@keyframes qt19-border-chase-move {
  from { offset-distance: 0%; }
  to   { offset-distance: 100%; }
}


@keyframes qt19-anim-dissolve { from { opacity: 0; } to { opacity: 1; } }
@keyframes qt19-anim-zoom-in { from { opacity: 0; transform: scale(0.85); } to { opacity: 1; transform: scale(1); } }
@keyframes qt19-anim-zoom-out { from { opacity: 0; transform: scale(1.15); } to { opacity: 1; transform: scale(1); } }
@keyframes qt19-anim-slide-up { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: translateY(0); } }
@keyframes qt19-anim-slide-down { from { opacity: 0; transform: translateY(-40px); } to { opacity: 1; transform: translateY(0); } }
@keyframes qt19-anim-slide-left { from { opacity: 0; transform: translateX(60px); } to { opacity: 1; transform: translateX(0); } }
@keyframes qt19-anim-slide-right { from { opacity: 0; transform: translateX(-60px); } to { opacity: 1; transform: translateX(0); } }
@keyframes qt19-anim-flip-x { from { opacity: 0; transform: perspective(800px) rotateX(35deg); } to { opacity: 1; transform: perspective(800px) rotateX(0deg); } }
@keyframes qt19-anim-flip-y { from { opacity: 0; transform: perspective(800px) rotateY(35deg); } to { opacity: 1; transform: perspective(800px) rotateY(0deg); } }
@keyframes qt19-anim-blur-in { from { opacity: 0; filter: blur(10px); } to { opacity: 1; filter: blur(0); } }


.qt19-transition-dissolve { animation: qt19-anim-dissolve 1.0s ease both; }
.qt19-transition-zoom-in { animation: qt19-anim-zoom-in 0.9s cubic-bezier(0.34,1.56,0.64,1) both; }
.qt19-transition-zoom-out { animation: qt19-anim-zoom-out 0.9s cubic-bezier(0.34,1.56,0.64,1) both; }
.qt19-transition-slide-up { animation: qt19-anim-slide-up 0.9s cubic-bezier(0.22,1,0.36,1) both; }
.qt19-transition-slide-down { animation: qt19-anim-slide-down 0.9s cubic-bezier(0.22,1,0.36,1) both; }
.qt19-transition-slide-left { animation: qt19-anim-slide-left 0.9s cubic-bezier(0.22,1,0.36,1) both; }
.qt19-transition-slide-right { animation: qt19-anim-slide-right 0.9s cubic-bezier(0.22,1,0.36,1) both; }
.qt19-transition-flip-x { animation: qt19-anim-flip-x 1.0s ease both; }
.qt19-transition-flip-y { animation: qt19-anim-flip-y 1.0s ease both; }
.qt19-transition-blur-in { animation: qt19-anim-blur-in 1.0s ease both; }


/* ---- v0.4.55 bulletproof glow: separate layer, never fights box-shadow ---- */
.qt19-glow-wrap {
  position: relative !important;
}
.qt19-glow-layer {
  position: absolute !important;
  inset: -14px !important;
  border-radius: inherit;
  background: radial-gradient(circle, var(--qt19-accent-glow) 0%, transparent 68%);
  opacity: 0;
  filter: blur(18px);
  transition: opacity 0.35s ease;
  pointer-events: none !important;
  z-index: 0 !important;
}
.qt19-glow-wrap:hover .qt19-glow-layer {
  opacity: 0.7;
}
.qt19-glow-content {
  position: relative !important;
  z-index: 1 !important;
}


@keyframes qt19-sidebar-collapse {
  from { width: 230px; }
  to   { width: 64px; }
}
@keyframes qt19-sidebar-expand {
  from { width: 64px; }
  to   { width: 230px; }
}
.qt19-sidebar-collapsing { animation: qt19-sidebar-collapse 0.28s cubic-bezier(0.22,1,0.36,1) both; }
.qt19-sidebar-expanding { animation: qt19-sidebar-expand 0.28s cubic-bezier(0.22,1,0.36,1) both; }
"""


def qt19_global_css() -> rx.Component:
    """Render the single shared <style> block. Include this exactly once, at the app root."""
    return rx.html(f"<style>{_CSS}</style>")
