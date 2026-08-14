"""Shared glassmorphism style primitives.

PATH: ui/theme/glass.py  (REPLACE ENTIRE FILE)

CHANGE (Module 01 gap-closure item 5): added a uniform 0.9s cross-fade transition to every
style dict whose background/border/box-shadow/color values are driven by the --qt19-* CSS
custom properties set in page_shell.py's _theme_style_vars(). Custom properties themselves
can't be transitioned, but the consuming elements can - as long as they declare the
transition, which none of these previously did (only PAGE_BG_STYLE had a partial one, and
PILL_BUTTON_STYLE's existing transform transition is preserved alongside the new one).
"""
from __future__ import annotations


_THEME_CROSSFADE = "background 0.9s ease, border-color 0.9s ease, box-shadow 0.9s ease, color 0.9s ease"


GLASS_CARD_STYLE: dict = {
    "background": "var(--qt19-glass-bg)",
    "backdrop_filter": "blur(18px)",
    "border": "1px solid var(--qt19-glass-border)",
    "border_radius": "1.5rem",
    "box_shadow": "0 8px 32px rgba(0,0,0,0.18)",
    "padding": "1.25rem",
    "transition": _THEME_CROSSFADE,
}


GLASS_CARD_3XL_STYLE: dict = {**GLASS_CARD_STYLE, "border_radius": "1.75rem"}


PILL_BUTTON_STYLE: dict = {
    "border_radius": "9999px",
    "padding_x": "1.25rem",
    "padding_y": "0.55rem",
    "background": "var(--qt19-accent)",
    "color": "white",
    "box_shadow": "0 0 16px 2px var(--qt19-accent-glow)",
    "border": "none",
    "cursor": "pointer",
    "font_weight": "600",
    "transition": f"transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), {_THEME_CROSSFADE}",
    "_hover": {"transform": "scale(1.05)"},
}


GLOW_RING_STYLE: dict = {
    "border": "2px solid var(--qt19-accent)",
    "box_shadow": "0 0 12px 3px var(--qt19-accent-glow)",
    "border_radius": "9999px",
    "transition": _THEME_CROSSFADE,
}


PAGE_BG_STYLE: dict = {
    "background": "linear-gradient(160deg, var(--qt19-bg-from), var(--qt19-bg-to))",
    "min_height": "100vh",
    "color": "var(--qt19-text-primary)",
    "transition": _THEME_CROSSFADE,
    "cursor": "auto",
}


AUTH_BG_STYLE: dict = {
    "background": (
        "radial-gradient(circle at 30% 28%, rgba(30,143,255,0.22) 0%, transparent 38%),"
        "radial-gradient(circle at 70% 28%, rgba(147,51,234,0.16) 0%, transparent 34%),"
        "radial-gradient(circle at 50% 85%, rgba(30,143,255,0.10) 0%, transparent 42%),"
        "linear-gradient(160deg, #00060f 0%, #000208 100%)"
    ),
    "background_attachment": "fixed",
    "min_height": "100vh",
    "width": "100%",
    "color": "#EAF4FF",
    "display": "flex",
    "align_items": "center",
    "justify_content": "center",
    "cursor": "auto",
}



def heartbeat_pill_style(pulse_color) -> dict:
    """Return a pill-button *style dict* with a CSS custom property set for the heartbeat
    glow color. Pass this to `style=`; separately pass `class_name="qt19-heartbeat"` on the
    same button so the @keyframes qt19-heartbeat animation (defined once in global_css.py)
    picks up `--qt19-pulse-color` and animates it."""
    return {
        "border_radius": "9999px",
        "padding_x": "1.75rem",
        "padding_y": "0.65rem",
        "background": "rgba(20,20,25,0.85)",
        "border": "1px solid rgba(255,255,255,0.15)",
        "color": "white",
        "font_weight": "700",
        "cursor": "pointer",
        "--qt19-pulse-color": pulse_color,
    }