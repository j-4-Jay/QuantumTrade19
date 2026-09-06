"""Global CSS keyframes + forced cursor override + autofill detection.

PATH: ui/theme/global_css.py  (REPLACE ENTIRE FILE)

FIX (Day theme dropdown/menu text still invisible) - the previous fix
targeted the CONTAINER (`[role="menu"]`, `[data-radix-popper-content-wrapper] > *`)
but individual Radix menu/select ITEMS (`[role="menuitem"]`,
`[role="option"]`) get their own explicit color from Radix Themes'
internal color system, which has HIGHER specificity than an inherited
container color - the container fix alone was not enough. Added direct
rules for `[role="menuitem"]`, `[role="option"]`, `[role="menuitemradio"]`,
`[role="menuitemcheckbox"]` forcing the theme's own text color, on top of
the existing `[data-highlighted]` hover-fix (unchanged, still correct).
"""
from __future__ import annotations
import reflex as rx


_CSS = """
* { cursor: auto !important; }
button, a, [role="button"], input[type="checkbox"], input[type="radio"] { cursor: pointer !important; }


html, body {
  height: 100% !important;
  overflow: hidden !important;
  overflow-x: hidden !important;
}


/* ---- Modern, near-invisible scrollbars everywhere ---- */
* {
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.22) transparent;
}
*::-webkit-scrollbar { width: 6px; height: 6px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.22);
  border-radius: 9999px;
  transition: background 0.2s ease;
}
*::-webkit-scrollbar-thumb:hover { background: rgba(148, 163, 184, 0.5); }
*::-webkit-scrollbar-corner { background: transparent; }


/* ---- Theme-matched inputs, selects, dropdown popovers, menus ---- */
input, textarea, select {
  background: var(--qt19-glass-bg) !important;
  border-color: var(--qt19-glass-border) !important;
  color: var(--qt19-text-primary) !important;
}
input::placeholder, textarea::placeholder { color: var(--qt19-text-muted) !important; opacity: 1; }
input[type="color"] { border: none !important; }

[data-radix-popper-content-wrapper] > *,
[role="listbox"],
[role="menu"] {
  background: var(--qt19-glass-bg) !important;
  border: 1px solid var(--qt19-glass-border) !important;
  color: var(--qt19-text-primary) !important;
  backdrop-filter: blur(18px);
}

/* Individual items have their OWN explicit Radix color (higher
   specificity than the container's inherited color) - must be forced
   directly, not just on the container. */
[role="menuitem"],
[role="menuitemradio"],
[role="menuitemcheckbox"],
[role="option"] {
  color: var(--qt19-text-primary) !important;
}
[role="menuitem"] *,
[role="menuitemradio"] *,
[role="menuitemcheckbox"] *,
[role="option"] * {
  color: inherit !important;
}

/* Every Radix Select/Menu/DropdownMenu item uses [data-highlighted] on
   hover/keyboard-focus, in every Radix Themes version - this is the
   single rule that fixes "invisible on hover" in both Day and Night. */
[data-highlighted] {
  background: var(--qt19-accent) !important;
  color: white !important;
}
[data-highlighted] * {
  color: white !important;
}


/* ---- Droplet wave dots at each POI's High/Low formation point ---- */
.qt19-poi-dot {
  position: absolute;
  width: 9px;
  height: 9px;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 2;
  display: none;
}
.qt19-poi-dot-core {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: radial-gradient(
    circle at 32% 26%,
    rgba(255, 255, 255, 0.95) 0%,
    var(--qt19-dot-color) 42%,
    rgba(0, 0, 0, 0.4) 100%
  );
  box-shadow:
    0 0 4px 1px var(--qt19-dot-color),
    inset 0 0 2px rgba(255, 255, 255, 0.75),
    inset 0 -1px 2px rgba(0, 0, 0, 0.4);
  z-index: 2;
}
.qt19-poi-dot-ring {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--qt19-dot-color) 0%, transparent 72%);
  filter: blur(0.6px);
  opacity: 0.5;
  animation: qt19-droplet-ping 2.8s cubic-bezier(0.22, 0.61, 0.36, 1) infinite;
  will-change: transform, opacity;
  z-index: 1;
}
@keyframes qt19-droplet-ping {
  0%   { transform: scale(1);   opacity: 0.5; }
  55%  { opacity: 0.24; }
  100% { transform: scale(5.2); opacity: 0; }
}


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


/* ---- v0.4.55 bulletproof glow - separate layer, never fights box-shadow ---- */
.qt19-glow-wrap { position: relative !important; }
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
.qt19-glow-wrap:hover .qt19-glow-layer { opacity: 0.7; }
.qt19-glow-content { position: relative !important; z-index: 1 !important; }


@keyframes qt19-sidebar-collapse { from { width: 230px; } to { width: 64px; } }
@keyframes qt19-sidebar-expand { from { width: 64px; } to { width: 230px; } }
.qt19-sidebar-collapsing { animation: qt19-sidebar-collapse 0.28s cubic-bezier(0.22,1,0.36,1) both; }
.qt19-sidebar-expanding { animation: qt19-sidebar-expand 0.28s cubic-bezier(0.22,1,0.36,1) both; }
"""


def qt19_global_css() -> rx.Component:
    """Render the single shared style block. Include this exactly once,
    at the app root."""
    return rx.html(f"<style>{_CSS}</style>")
