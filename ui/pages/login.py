"""Login Screen (returning users).

PATH: ui/pages/login.py (REPLACE ENTIRE FILE)

CHANGE (Module 01 gap-closure item 10): added the "Remember this device" checkbox, wired to
AppState.login_remember_device / AppState.toggle_login_remember_device. Only shown when the
TOTP field is actually visible - remembering a device is meaningless if TOTP isn't the thing
being skipped.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.components.branding import qt19_brand
from ui.components.cursor_glow import qt19_cursor_glow
from ui.components.border_chase import qt19_border_chase
from ui.components.password_field import qt19_password_field
from ui.theme.glass import GLASS_CARD_3XL_STYLE, AUTH_BG_STYLE, heartbeat_pill_style
from config.settings import APP_TAGLINE

_CARD_STYLE = {**GLASS_CARD_3XL_STYLE, "background": "rgba(5,10,20,0.55)", "border": "1px solid rgba(30,143,255,0.35)"}


def login_screen() -> rx.Component:
    pulse_color = rx.cond(AppState.login_credentials_match, "rgba(57,255,136,0.7)", "rgba(220,20,60,0.7)")
    card = rx.vstack(
        qt19_brand("md"),
        rx.text(APP_TAGLINE, font_size="0.85rem", color="rgba(234,244,255,0.75)"),
        rx.vstack(
            rx.input(placeholder="Username", value=AppState.login_username,
                on_change=AppState.set_login_username, border_radius="1rem", width="100%"),
            qt19_password_field("Password", AppState.login_password, AppState.set_login_password,
                AppState.show_login_password, AppState.toggle_show_login_password),
            rx.cond(AppState.totp_required,
                rx.vstack(
                    rx.input(placeholder="Authenticator code", value=AppState.login_totp,
                        on_change=AppState.set_login_totp, border_radius="1rem", width="100%"),
                    rx.hstack(
                        rx.checkbox(checked=AppState.login_remember_device,
                            on_change=AppState.toggle_login_remember_device),
                        rx.text("Remember this device (skip 2FA for 60 days)",
                            font_size="0.72rem", color="rgba(234,244,255,0.65)"),
                        spacing="2", align_items="center", width="100%",
                    ),
                    spacing="2", width="100%",
                )),
            rx.hstack(
                rx.button("Manage Account Security", on_click=AppState.begin_manage_security, variant="ghost",
                    font_size="0.72rem", color="rgba(234,244,255,0.55)", padding="0"),
                rx.spacer(),
                rx.button("Forgot password?", on_click=AppState.begin_forgot_password, variant="ghost",
                    font_size="0.75rem", color="rgba(234,244,255,0.65)", padding="0"),
                width="100%",
            ),
            rx.button(
                "New here? Create an account", on_click=AppState.go_to_register, variant="ghost",
                font_size="0.72rem", color="rgba(234,244,255,0.55)", padding="0", width="100%",
            ),
            rx.cond(AppState.login_error != "", rx.text(AppState.login_error, color="#FF6B6B", font_size="0.8rem")),
            rx.button(
                "Submit", id="qt19-primary-action", on_click=AppState.submit_login,
                class_name="qt19-heartbeat", style=heartbeat_pill_style(pulse_color), width="100%",
            ),
            spacing="3", width="100%",
        ),
        spacing="4", width="340px", align_items="stretch", style=_CARD_STYLE,
    )

    return rx.box(
        qt19_cursor_glow(),
        rx.center(
            qt19_border_chase(
                rx.box(
                    card,
                    key=AppState.login_error_seq,
                    class_name=rx.cond(AppState.login_error != "", "qt19-shake", ""),
                )
            ),
            height="100vh", width="100%",
        ),
        style=AUTH_BG_STYLE, width="100%", height="100vh",
    )