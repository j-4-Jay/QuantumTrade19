from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_3XL_STYLE

def symbol_detail_popup():
    return rx.cond(AppState.detail_popup_open,
        rx.box(rx.center(rx.box(rx.vstack(
            rx.hstack(rx.heading(AppState.detail_popup_symbol, size="5"), rx.spacer(),
                       rx.icon_button(rx.icon("x"), on_click=AppState.close_detail_popup, variant="ghost"), width="100%"),
            rx.divider(),
            rx.text("1. Decision View", font_weight="700", font_size="0.8rem"),
            rx.text("2. Confidence Score radial gauge + breakdown", font_size="0.75rem", color="var(--qt19-text-muted)"),
            rx.text("3. Directional Bias banner", font_size="0.75rem", color="var(--qt19-text-muted)"),
            rx.text("4. Trade-TF vs HTF-POI mini bars (15m/5m/1m)", font_size="0.75rem", color="var(--qt19-text-muted)"),
            rx.text("5. POI Levels ladder + mini structure chart", font_size="0.75rem", color="var(--qt19-text-muted)"),
            rx.text("6. Market Structure / Momentum / Volatility-Volume gauges", font_size="0.75rem", color="var(--qt19-text-muted)"),
            spacing="3", align_items="start"), style=GLASS_CARD_3XL_STYLE, width="520px"), height="100vh", width="100%"),
        on_click=AppState.close_detail_popup, position="fixed", top="0", left="0", width="100%", height="100%",
        background="rgba(0,0,0,0.35)", style={"backdrop_filter":"blur(6px)"}, z_index="500"))
