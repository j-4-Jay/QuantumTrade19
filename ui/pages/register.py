"""Registration Screen (first run only).

PATH: ui/pages/register.py  (REPLACE ENTIRE FILE)

Added keyboard-shortcut IDs (Enter = primary action, Esc = Back to Login).
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.components.branding import qt19_brand
from ui.components.cursor_glow import qt19_cursor_glow
from ui.components.border_chase import qt19_border_chase
from ui.components.password_field import qt19_password_field
from ui.theme.glass import GLASS_CARD_3XL_STYLE, PILL_BUTTON_STYLE, AUTH_BG_STYLE

_CARD_STYLE = {**GLASS_CARD_3XL_STYLE, "background": "rgba(5,10,20,0.55)", "border": "1px solid rgba(30,143,255,0.35)"}


def _form_stage() -> rx.Component:
    return rx.vstack(
        rx.input(placeholder="Choose a username", value=AppState.reg_username,
                  on_change=AppState.set_reg_username, border_radius="1rem", width="100%"),
        qt19_password_field("Password (min. 4 characters)", AppState.reg_password, AppState.set_reg_password,
                             AppState.show_reg_password, AppState.toggle_show_reg_password),
        qt19_password_field("Confirm password", AppState.reg_confirm_password, AppState.set_reg_confirm_password,
                             AppState.show_reg_confirm_password, AppState.toggle_show_reg_confirm_password),
        rx.hstack(
            rx.checkbox(checked=AppState.reg_enable_totp, on_change=AppState.toggle_reg_enable_totp),
            rx.text("Enable Google Authenticator (recommended)", font_size="0.8rem"),
            spacing="2", align_items="center", width="100%", justify_content="start",
        ),
        rx.text(
            "You can also connect Telegram/Discord alerts and manage 2FA later from "
            '"Manage Account Security" on the Login screen.',
            font_size="0.7rem", color="rgba(234,244,255,0.55)", text_align="center", width="100%",
        ),
        rx.cond(AppState.reg_error != "", rx.text(AppState.reg_error, color="#FF6B6B", font_size="0.8rem", text_align="center", width="100%")),
        rx.button("Create Account", id="qt19-primary-action", on_click=AppState.submit_registration, style=PILL_BUTTON_STYLE, width="100%"),
        rx.button("Back to Login", id="qt19-secondary-action", on_click=AppState.go_to_login, variant="ghost",
                   width="100%", font_size="0.75rem", color="rgba(234,244,255,0.6)"),
        spacing="3", width="100%", align_items="stretch",
    )


def _qr_stage() -> rx.Component:
    return rx.vstack(
        rx.text("Scan this QR code with Google Authenticator (or any TOTP app):",
                font_size="0.8rem", color="rgba(234,244,255,0.75)", text_align="center", width="100%"),
        rx.image(src=AppState.reg_qr_data_uri, width="200px", height="200px", border_radius="1rem"),
        rx.input(placeholder="Enter the 6-digit code", value=AppState.reg_totp_code,
                  on_change=AppState.set_reg_totp_code, border_radius="1rem", width="100%"),
        rx.cond(AppState.reg_error != "", rx.text(AppState.reg_error, color="#FF6B6B", font_size="0.8rem", text_align="center", width="100%")),
        rx.button("Confirm & Finish Setup", id="qt19-primary-action", on_click=AppState.confirm_totp_setup, style=PILL_BUTTON_STYLE, width="100%"),
        rx.button("Skip Authenticator Setup", on_click=AppState.skip_totp_setup, variant="ghost",
                   width="100%", font_size="0.75rem", color="rgba(234,244,255,0.6)"),
        rx.button("Back to Login", id="qt19-secondary-action", on_click=AppState.go_to_login, variant="ghost",
                   width="100%", font_size="0.75rem", color="rgba(234,244,255,0.6)"),
        spacing="3", width="100%", align_items="center",
    )


def register_screen() -> rx.Component:
    card = rx.vstack(
        qt19_brand("md"),
        rx.text("Create your QuantumTrade19 account", font_size="0.85rem", color="rgba(234,244,255,0.75)", text_align="center", width="100%"),
        rx.cond(AppState.reg_stage == "form", _form_stage(), _qr_stage()),
        spacing="4", width="380px", align_items="center", style=_CARD_STYLE,
    )
    return rx.box(
        qt19_cursor_glow(),
        rx.center(qt19_border_chase(card), height="100vh", width="100%"),
        style=AUTH_BG_STYLE, width="100%", height="100vh",
    )
