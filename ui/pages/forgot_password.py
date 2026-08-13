"""Forgot Password Screen.

PATH: ui/pages/forgot_password.py  (REPLACE ENTIRE FILE)

ADDED: a real "Cancel" button on the reset stage (previously the only way out was completing
the reset) - fully aborts back to Login via the same cancel_forgot_password handler used
elsewhere. Card now has the traveling border-light effect + keyboard-shortcut IDs.
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


def _method_button(method: str) -> rx.Component:
    return rx.button(
        rx.hstack(rx.icon(rx.match(method, ("totp", "shield-check"), ("telegram", "send"), ("discord", "message-circle"), "key"), size=18),
                   rx.text(rx.match(method, ("totp", "Google Authenticator"), ("telegram", "Telegram"), ("discord", "Discord"), method)),
                   spacing="2"),
        on_click=lambda: AppState.select_forgot_method(method),
        variant="outline", width="100%", border_radius="1rem", justify_content="start",
    )


def _choose_stage() -> rx.Component:
    return rx.vstack(
        rx.text("Verify your identity using one of your active methods:", font_size="0.8rem",
                color="rgba(234,244,255,0.75)", text_align="center", width="100%"),
        rx.foreach(AppState.forgot_available_methods, _method_button),
        rx.cond(AppState.forgot_error != "", rx.text(AppState.forgot_error, color="#FF6B6B", font_size="0.8rem", width="100%", text_align="center")),
        rx.button("Back to Login", id="qt19-secondary-action", on_click=AppState.cancel_forgot_password, variant="ghost",
                   width="100%", font_size="0.75rem", color="rgba(234,244,255,0.6)"),
        spacing="3", width="100%",
    )


def _enter_code_stage() -> rx.Component:
    return rx.vstack(
        rx.cond(
            AppState.forgot_selected_method == "totp",
            rx.text("Enter the current code from your authenticator app.", font_size="0.8rem",
                    color="rgba(234,244,255,0.75)", text_align="center", width="100%"),
            rx.vstack(
                rx.text(rx.cond(AppState.forgot_otp_sent, "A code was sent. Enter it below.", "Sending code..."),
                        font_size="0.8rem", color="rgba(234,244,255,0.75)", text_align="center", width="100%"),
                rx.button("Resend code", on_click=AppState.resend_forgot_otp, variant="ghost",
                           font_size="0.7rem", color="rgba(234,244,255,0.55)"),
                spacing="1", align_items="center", width="100%",
            ),
        ),
        rx.input(placeholder="Enter code", value=AppState.forgot_code, on_change=AppState.set_forgot_code,
                  border_radius="1rem", width="100%"),
        rx.cond(AppState.forgot_error != "", rx.text(AppState.forgot_error, color="#FF6B6B", font_size="0.8rem", width="100%", text_align="center")),
        rx.button("Verify", id="qt19-primary-action", on_click=AppState.verify_forgot_identity, style=PILL_BUTTON_STYLE, width="100%"),
        rx.button("Back to Login", id="qt19-secondary-action", on_click=AppState.cancel_forgot_password, variant="ghost",
                   width="100%", font_size="0.75rem", color="rgba(234,244,255,0.6)"),
        spacing="3", width="100%", align_items="center",
    )


def _reset_stage() -> rx.Component:
    return rx.vstack(
        rx.cond(
            AppState.forgot_has_any_method,
            rx.text("Identity verified. Choose a new password.", font_size="0.8rem", color="rgba(234,244,255,0.75)", width="100%"),
            rx.text("No recovery method is configured yet, so you can reset your password directly - "
                    "no code or old password required.", font_size="0.78rem", color="#F5A524", text_align="center", width="100%"),
        ),
        qt19_password_field("New password (min. 4 characters)", AppState.forgot_new_password, AppState.set_forgot_new_password,
                             AppState.show_forgot_new_password, AppState.toggle_show_forgot_new_password),
        qt19_password_field("Confirm new password", AppState.forgot_confirm_password, AppState.set_forgot_confirm_password,
                             AppState.show_forgot_confirm_password, AppState.toggle_show_forgot_confirm_password),
        rx.cond(AppState.forgot_error != "", rx.text(AppState.forgot_error, color="#FF6B6B", font_size="0.8rem", width="100%", text_align="center")),
        rx.button("Set New Password", id="qt19-primary-action", on_click=AppState.submit_new_password, style=PILL_BUTTON_STYLE, width="100%"),
        rx.button("Cancel", id="qt19-secondary-action", on_click=AppState.cancel_forgot_password, variant="ghost",
                   width="100%", font_size="0.75rem", color="rgba(234,244,255,0.6)"),
        spacing="3", width="100%",
    )


def forgot_password_screen() -> rx.Component:
    card = rx.vstack(
        qt19_brand("md"),
        rx.text("Reset your password", font_size="0.9rem", font_weight="700"),
        rx.cond(AppState.forgot_stage == "choose", _choose_stage(),
                rx.cond(AppState.forgot_stage == "enter_code", _enter_code_stage(), _reset_stage())),
        spacing="4", width="360px", align_items="stretch", style=_CARD_STYLE,
    )
    return rx.box(
        qt19_cursor_glow(),
        rx.center(qt19_border_chase(card), height="100vh", width="100%"),
        style=AUTH_BG_STYLE, width="100%", height="100vh",
    )
