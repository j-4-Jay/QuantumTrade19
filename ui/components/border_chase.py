"""A single small glow dot, with a fading comet tail, continuously traveling the exact
rounded-rectangle border of a card - colored to whatever theme is currently active.

PATH: ui/components/border_chase.py  (REPLACE ENTIRE FILE)

REDESIGN: the previous version used a rotated conic-gradient mask, which rendered as an
ill-fitting rotating wedge, not a comet - wrong technique entirely. This version uses CSS
Motion Path (`offset-path` + `offset-distance`): a small circular dot is anchored to the
card's own rounded-rectangle outline as its literal travel path, then several fainter/smaller
"echo" copies of that same dot are stacked behind it using negative `animation-delay` on the
identical animation - which is the standard, lightweight way to produce a trailing comet tail
in pure CSS (no JS, GPU-only, negligible cost). Slow (14s/lap) and small (7px head dot) per
"very subtle" and "a little long" tail.
"""
from __future__ import annotations
import reflex as rx

_LAP_SECONDS = 14.0
_TAIL_DOT_COUNT = 7  # 1 bright head + 6 fading echoes = "a little long" tail


def _comet_dot(radius: str, index: int) -> rx.Component:
    """One dot in the comet chain. index 0 = the bright head; higher = further back/fainter."""
    delay = -(_LAP_SECONDS * index / (_TAIL_DOT_COUNT * 4))  # tight stagger so the tail reads as continuous
    size = max(2.5, 7 - index * 0.7)
    opacity = max(0.05, 1 - index * 0.16)
    blur = max(3, 8 - index)
    return rx.box(
        style={
            "position": "absolute", "top": "0", "left": "0",
            "width": f"{size}px", "height": f"{size}px",
            "border_radius": "9999px",
            "background": "var(--qt19-accent, #1E8FFF)",
            "box_shadow": f"0 0 {blur}px 1px var(--qt19-accent-glow, #8FCBFF)",
            "opacity": f"{opacity:.2f}",
            "offset_path": f"inset(0px round {radius})",
            "offset_distance": "0%",
            "animation": f"qt19-border-chase-move {_LAP_SECONDS}s linear infinite",
            "animation_delay": f"{delay:.2f}s",
            "pointer_events": "none",
            "z_index": "2",
        },
    )


def qt19_border_chase(child: rx.Component, radius: str = "1.75rem") -> rx.Component:
    """Wrap `child` (a card) with the comet-dot chasing its exact border shape."""
    dots = [_comet_dot(radius, i) for i in range(_TAIL_DOT_COUNT)]
    return rx.box(*dots, child, position="relative")
