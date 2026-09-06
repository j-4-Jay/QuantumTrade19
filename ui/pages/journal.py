"""Journal & Reports tab - App-Shell placeholder page.

PATH: ui/pages/journal.py  (REPLACE ENTIRE FILE)

FIX (in-card scrolling, not page-level) - card now takes the full page
height and scrolls its OWN content internally (overflow_y="auto") if it
ever grows taller than the page - matches the new non-scrolling canvas
wrapper in quantumtrade19.py.

CHANGE (v0.3.7, unchanged) - no repeated heading; soft hover-glow class.
"""
from __future__ import annotations
import reflex as rx
from ui.theme.glass import GLASS_CARD_3XL_STYLE, HOVER_GLOW_CLASS



def journal_page():
    return rx.box(
        rx.text(
            "Equity curve, filter-contribution table, and Auto-Learning panel land in the Journal Monitor module.",
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
