from __future__ import annotations
import reflex as rx
from ui.theme.glass import GLASS_CARD_3XL_STYLE

def trading_panel_page():
    return rx.vstack(rx.heading("Trading Panel", size="6"),
        rx.box(rx.text("Chart + POI/FVG overlay, risk sidebar, and status bar land in later modules.", color="var(--qt19-text-muted)", font_size="0.85rem"), style=GLASS_CARD_3XL_STYLE, width="100%", margin_top="1rem"),
        width="100%", spacing="3")
