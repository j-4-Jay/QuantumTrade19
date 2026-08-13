"""Manage Account Security Screen.

PATH: ui/pages/manage_security.py  (REPLACE ENTIRE FILE - fully overwrite, don't merge)

This file only ever uses single tg_bot_token/tg_chat_id/dc_webhook_url fields on AppState -
there is no "tg_channels" list/foreach anywhere in this design. If your local copy referenced
AppState.tg_channels, it was not from this build; replace it completely with this version.
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
_SECTION_STYLE = {"border": "1px solid rgba(30,143,255,0.25)", "border_radius": "1rem", "padding": "1rem"}
_HELP_STYLE = {"font_size": "0.68rem", "color": "rgba(234,244,255,0.55)", "width": "100%", "line_height": "1.4"}


def _verify_stage() -> rx.Component:
    return rx.vstack(
        rx.text("Enter your username and password to manage account security.",
                font_size="0.8rem", color="rgba(234,244,255,0.75)", text_align="center", width="100%"),
        rx.input(placeholder="Username", value=AppState.manage_username, on_change=AppState.set_manage_username,
                  border_radius="1rem", width="100%"),
        qt19_password_field("Password", AppState.manage_password, AppState.set_manage_password,
                             AppState.show_manage_password, AppState.toggle_show_manage_password),
        rx.cond(AppState.manage_error != "", rx.text(AppState.manage_error, color="#FF6B6B", font_size="0.8rem", width="100%", text_align="center")),
        rx.button("Verify", id="qt19-primary-action", on_click=AppState.verify_manage_identity, style=PILL_BUTTON_STYLE, width="100%"),
        rx.button("Back to Login", id="qt19-secondary-action", on_click=AppState.finish_manage_security, variant="ghost",
                   width="100%", font_size="0.75rem", color="rgba(234,244,255,0.6)"),
        spacing="3", width="100%", align_items="center",
    )


def _totp_qr_stage() -> rx.Component:
    return rx.vstack(
        rx.text("Scan this QR code with Google Authenticator (or any TOTP app):",
                font_size="0.8rem", color="rgba(234,244,255,0.75)", text_align="center", width="100%"),
        rx.image(src=AppState.manage_totp_qr, width="200px", height="200px", border_radius="1rem"),
        rx.input(placeholder="Enter the 6-digit code", value=AppState.manage_totp_code,
                  on_change=AppState.set_manage_totp_code, border_radius="1rem", width="100%"),
        rx.cond(AppState.manage_error != "", rx.text(AppState.manage_error, color="#FF6B6B", font_size="0.8rem", width="100%", text_align="center")),
        rx.button("Confirm & Enable", id="qt19-primary-action", on_click=AppState.confirm_enable_totp, style=PILL_BUTTON_STYLE, width="100%"),
        spacing="3", width="100%", align_items="center",
    )


def _totp_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("shield-check", size=18, color="#22C55E"),
            rx.text("Google Authenticator", font_weight="700", font_size="0.85rem"),
            rx.spacer(),
            rx.badge(rx.cond(AppState.totp_required, "Enabled", "Disabled"),
                      color_scheme=rx.cond(AppState.totp_required, "green", "gray")),
            width="100%",
        ),
        rx.cond(
            AppState.totp_required,
            rx.button("Disable Google Authenticator", on_click=AppState.disable_totp, variant="outline",
                       width="100%", border_radius="1rem", color="#FF6B6B"),
            rx.button("Enable Google Authenticator", on_click=AppState.start_enable_totp, style=PILL_BUTTON_STYLE, width="100%"),
        ),
        spacing="2", width="100%", style=_SECTION_STYLE,
    )


def _telegram_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("send", size=18, color="#1E8FFF"),
            rx.text("Telegram Alerts & Recovery", font_weight="700", font_size="0.85rem"),
            rx.spacer(),
            rx.badge(rx.cond(AppState.tg_configured, "Configured", "Not configured"),
                      color_scheme=rx.cond(AppState.tg_configured, "green", "gray")),
            width="100%",
        ),
        rx.text("Setup: 1) Message your bot on Telegram first (search its username, tap Start, "
                "send any text) - bots can't message you until you message them first. "
                "2) Visit api.telegram.org/bot<TOKEN>/getUpdates in a browser after that to find "
                "your numeric chat_id in the response.", **_HELP_STYLE),
        rx.input(placeholder="Bot token (leave blank to keep existing)", value=AppState.tg_bot_token,
                  on_change=AppState.set_tg_bot_token, border_radius="1rem", width="100%"),
        rx.input(placeholder="Chat ID (leave blank to keep existing)", value=AppState.tg_chat_id,
                  on_change=AppState.set_tg_chat_id, border_radius="1rem", width="100%"),
        rx.hstack(rx.checkbox(checked=AppState.tg_enabled, on_change=AppState.toggle_tg_enabled),
                   rx.text("Enable Telegram channel", font_size="0.8rem"), spacing="2", align_items="center", width="100%"),
        rx.hstack(
            rx.button("Save", on_click=AppState.save_telegram, style={**PILL_BUTTON_STYLE, "width": "100%"}, flex="1"),
            rx.button("Send Test", on_click=AppState.test_telegram, variant="outline", border_radius="9999px", flex="1"),
            spacing="2", width="100%",
        ),
        rx.cond(AppState.tg_message != "", rx.text(AppState.tg_message, font_size="0.75rem", color="rgba(234,244,255,0.7)", width="100%")),
        spacing="2", width="100%", style=_SECTION_STYLE,
    )


def _discord_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("message-circle", size=18, color="#9333EA"),
            rx.text("Discord Alerts & Recovery", font_weight="700", font_size="0.85rem"),
            rx.spacer(),
            rx.badge(rx.cond(AppState.dc_configured, "Configured", "Not configured"),
                      color_scheme=rx.cond(AppState.dc_configured, "green", "gray")),
            width="100%",
        ),
        rx.text("Setup: Server Settings -> Integrations -> Webhooks -> New Webhook -> pick a "
                "channel -> Copy Webhook URL. A webhook only ever posts to that ONE channel.", **_HELP_STYLE),
        rx.input(placeholder="Webhook URL (leave blank to keep existing)", value=AppState.dc_webhook_url,
                  on_change=AppState.set_dc_webhook_url, border_radius="1rem", width="100%"),
        rx.hstack(rx.checkbox(checked=AppState.dc_enabled, on_change=AppState.toggle_dc_enabled),
                   rx.text("Enable Discord channel", font_size="0.8rem"), spacing="2", align_items="center", width="100%"),
        rx.hstack(
            rx.button("Save", on_click=AppState.save_discord, style={**PILL_BUTTON_STYLE, "width": "100%"}, flex="1"),
            rx.button("Send Test", on_click=AppState.test_discord, variant="outline", border_radius="9999px", flex="1"),
            spacing="2", width="100%",
        ),
        rx.cond(AppState.dc_message != "", rx.text(AppState.dc_message, font_size="0.75rem", color="rgba(234,244,255,0.7)", width="100%")),
        spacing="2", width="100%", style=_SECTION_STYLE,
    )


def _panel_stage() -> rx.Component:
    return rx.vstack(
        _totp_section(), _telegram_section(), _discord_section(),
        rx.button("Done", on_click=AppState.finish_manage_security, style=PILL_BUTTON_STYLE, width="100%"),
        spacing="3", width="100%",
    )


def manage_security_screen() -> rx.Component:
    card = rx.vstack(
        qt19_brand("md"),
        rx.text("Manage Account Security", font_size="0.9rem", font_weight="700"),
        rx.cond(AppState.manage_stage == "verify", _verify_stage(),
                rx.cond(AppState.manage_stage == "totp_qr", _totp_qr_stage(), _panel_stage())),
        spacing="4", width="440px", align_items="stretch", style=_CARD_STYLE,
    )
    return rx.box(
        qt19_cursor_glow(),
        rx.center(qt19_border_chase(card), height="100vh", width="100%"),
        style=AUTH_BG_STYLE, width="100%", height="100vh",
    )
