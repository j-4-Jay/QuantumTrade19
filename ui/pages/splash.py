"""Splash Screen.

PATH: ui/pages/splash.py  (REPLACE ENTIRE FILE)

CHANGE: removed the static embedded <script> that started the bar animation - it only
reliably fired on the very first app load. The animation is now triggered from
AppState.run_splash_sequence via rx.call_script, which fires fresh on every single mount
(first load AND every subsequent logout->splash cycle).
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.components.branding import qt19_brand
from ui.components.cursor_glow import qt19_cursor_glow
from ui.theme.glass import AUTH_BG_STYLE, GLASS_CARD_3XL_STYLE
from config.settings import APP_TAGLINE, APP_VERSION

_CARD_STYLE = {**GLASS_CARD_3XL_STYLE, "background": "rgba(5,10,20,0.55)", "border": "1px solid rgba(30,143,255,0.35)"}


def splash_screen() -> rx.Component:
    return rx.box(
        qt19_cursor_glow(),
        rx.center(
            rx.vstack(
                qt19_brand("lg"),
                rx.text(
                    APP_TAGLINE, font_size="0.95rem", color="rgba(234,244,255,0.75)",
                    letter_spacing="0.04em", margin_top="0.75rem", text_align="center", width="100%",
                ),
                rx.text(
                    "INITIALIZING QUANTUM SYSTEMS...", font_size="0.7rem", letter_spacing="0.15em",
                    color="#8FCBFF", font_weight="600", margin_top="1.5rem", text_align="center", width="100%",
                ),
                rx.hstack(
                    rx.box(
                        rx.box(
                            id="qt19-splash-bar-fill",
                            style={
                                "height": "100%", "width": "100%", "border_radius": "9999px",
                                "background": "linear-gradient(90deg, #1E8FFF, #8FCBFF)",
                                "transform": "scaleX(0)", "transform_origin": "left",
                                "box_shadow": "0 0 16px 4px #8FCBFF, 0 0 4px 1px #1E8FFF",
                            },
                        ),
                        width="260px", height="8px", border_radius="9999px",
                        background="rgba(255,255,255,0.08)", overflow="hidden",
                    ),
                    rx.text("0%", id="qt19-splash-pct", font_size="0.85rem", font_weight="700",
                             color="#8FCBFF", min_width="2.5rem", text_align="left"),
                    spacing="3", align_items="center", justify_content="center", margin_top="0.75rem", width="100%",
                ),
                rx.text(APP_VERSION, font_size="0.65rem", color="rgba(234,244,255,0.4)",
                         margin_top="1rem", text_align="center", width="100%"),
                spacing="2", align_items="center", justify_content="center", width="100%",
            ),
            style=_CARD_STYLE, padding="2.5rem 3rem",
        ),
        style=AUTH_BG_STYLE, width="100%", height="100vh",
        on_mount=AppState.run_splash_sequence,
    )
