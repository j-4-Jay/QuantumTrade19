from __future__ import annotations
import reflex as rx
from ui.theme.glass import GLASS_CARD_3XL_STYLE

def alerts_page():
    return rx.vstack(rx.heading("Alerts", size="6"),
        rx.box(rx.text("Live fired-alert feed lands in the Alert Monitor module; this is the App-Shell placeholder.", color="var(--qt19-text-muted)", font_size="0.85rem"), style=GLASS_CARD_3XL_STYLE, width="100%", margin_top="1rem"),
        width="100%", spacing="3")
