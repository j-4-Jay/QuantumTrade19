"""Logout confirmation dialog.

PATH: ui/components/logout_dialog.py  (REPLACE ENTIRE FILE)

Added distinct IDs (qt19-logout-dialog / qt19-logout-primary / qt19-logout-cancel) so the
global keyboard shortcut listener gives this modal priority over whatever screen sits behind
it. Enter defaults to the SAFEST action (Keep Trades Running & Logout, or plain Logout) -
the destructive "Close All Trades" choice is deliberately left mouse-only.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import PILL_BUTTON_STYLE


def _trade_choice_body() -> rx.Component:
    return rx.vstack(
        rx.icon("triangle-alert", size=28, color="#F5A524"),
        rx.text("You have open trades.", font_weight="700", font_size="0.95rem"),
        rx.text("Close all open trades before logging out, or keep them running in the background?",
                font_size="0.8rem", color="var(--qt19-text-muted, #9FB3C8)", text_align="center"),
        rx.button("Close All Trades & Logout", on_click=AppState.confirm_logout_close_trades, style=PILL_BUTTON_STYLE, width="100%"),
        rx.button("Keep Trades Running & Logout", id="qt19-logout-primary", on_click=AppState.confirm_logout_keep_trades,
                   variant="outline", width="100%", border_radius="9999px"),
        rx.button("Cancel", id="qt19-logout-cancel", on_click=AppState.close_logout_dialog, variant="ghost", width="100%"),
        spacing="3", align_items="center",
    )


def _simple_confirm_body() -> rx.Component:
    return rx.vstack(
        rx.icon("log-out", size=28, color="var(--qt19-accent, #1E8FFF)"),
        rx.text("Logout of QuantumTrade19?", font_weight="700", font_size="0.95rem"),
        rx.text("This will safely end your session and return to Login.", font_size="0.8rem", color="var(--qt19-text-muted, #9FB3C8)", text_align="center"),
        rx.button("Logout", id="qt19-logout-primary", on_click=AppState.confirm_logout_no_trades, style=PILL_BUTTON_STYLE, width="100%"),
        rx.button("Cancel", id="qt19-logout-cancel", on_click=AppState.close_logout_dialog, variant="ghost", width="100%"),
        spacing="3", align_items="center",
    )


def qt19_logout_dialog() -> rx.Component:
    return rx.cond(
        AppState.show_logout_dialog,
        rx.box(
            rx.center(
                rx.box(
                    rx.cond(AppState.logout_stage == "trade_choice", _trade_choice_body(), _simple_confirm_body()),
                    style={"background": "rgba(10,15,25,0.92)", "border": "1px solid rgba(30,143,255,0.35)", "border_radius": "1.75rem",
                           "padding": "1.75rem", "backdrop_filter": "blur(18px)", "box_shadow": "0 8px 40px rgba(0,0,0,0.5)"},
                    width="360px",
                ),
                height="100vh", width="100%",
            ),
            id="qt19-logout-dialog",
            position="fixed", top="0", left="0", width="100%", height="100%",
            background="rgba(0,0,0,0.55)", z_index="600",
        ),
    )
