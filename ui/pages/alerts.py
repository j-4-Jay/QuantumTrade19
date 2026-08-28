"""Alerts tab - App-Shell placeholder page.

PATH: ui/pages/alerts.py  (REPLACE ENTIRE FILE)

CHANGE (v0.3.7): removed the repeated "Alerts" heading (sidebar already
shows the active page). Added the soft hover-glow class to the main card.
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
    )
