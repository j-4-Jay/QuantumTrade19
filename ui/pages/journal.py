from __future__ import annotations
import reflex as rx
from ui.theme.glass import GLASS_CARD_3XL_STYLE

def journal_page():
    return rx.vstack(rx.heading("Journal & Reports", size="6"),
        rx.box(rx.text("Equity curve, filter-contribution table, and Auto-Learning panel land in the Journal Monitor module.", color="var(--qt19-text-muted)", font_size="0.85rem"), style=GLASS_CARD_3XL_STYLE, width="100%", margin_top="1rem"),
        width="100%", spacing="3")
