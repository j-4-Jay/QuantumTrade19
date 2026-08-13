"""Global CSS keyframes + forced cursor override + autofill detection.

PATH: ui/theme/global_css.py  (REPLACE ENTIRE FILE)

CHANGE: all 10 transition durations slowed from ~0.5s-0.6s to ~0.9s-1.0s, per request, so
they register clearly to the eye instead of feeling instantaneous.
"""
from __future__ import annotations
import reflex as rx

_CSS = """
* { cursor: auto !important; }
button, a, [role="button"], input[type="checkbox"], input[type="radio"] { cursor: pointer !important; }

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
"""


def qt19_global_css() -> rx.Component:
    """Render the single shared <style> block. Include this exactly once, at the app root."""
    return rx.html(f"<style>{_CSS}</style>")
