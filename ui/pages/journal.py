"""Journal & Reports tab - App-Shell placeholder page.

PATH: ui/pages/journal.py  (REPLACE ENTIRE FILE)

CHANGE (v0.3.7): removed the repeated "Journal & Reports" heading (sidebar
already shows the active page). Added the soft hover-glow class to the
main card.
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
    )
