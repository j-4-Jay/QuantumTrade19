"""Alerts tab - App-Shell placeholder page.

PATH: ui/pages/alerts.py  (REPLACE ENTIRE FILE)

FIX (in-card scrolling, not page-level) - card now takes the full page
height and scrolls its OWN content internally (overflow_y="auto") if it
ever grows taller than the page - matches the new non-scrolling canvas
wrapper in quantumtrade19.py.

CHANGE (v0.3.7, unchanged) - no repeated heading; soft hover-glow class.
"""
from __future__ import annotations
import reflex as rx
from ui.theme.glass import GLASS_CARD_3XL_STYLE, HOVER_GLOW_CLASS



def alerts_page():
    return rx.box(
        rx.text(
            "Live fired-alert feed lands in the Alert Monitor module; this is the App-Shell placeholder.",
            color="var(--qt19-text-muted)",
            font_size="0.85rem",
        ),
        style=GLASS_CARD_3XL_STYLE,
        class_name=HOVER_GLOW_CLASS,
        width="100%",
        height="100%",
        overflow_y="auto",
        overflow_x="hidden",
    )
