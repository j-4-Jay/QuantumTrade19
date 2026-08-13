from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.components.branding import qt19_brand
from ui.components.cursor_glow import qt19_cursor_glow
from ui.components.password_field import qt19_password_field
from ui.theme.glass import GLASS_CARD_3XL_STYLE, PILL_BUTTON_STYLE, AUTH_BG_STYLE

_CARD = {**GLASS_CARD_3XL_STYLE, "background": "rgba(5,10,20,0.55)", "border": "1px solid rgba(30,143,255,0.35)"}

def app_lock_screen():
    return rx.box(
        qt19_cursor_glow(),
        rx.center(
            rx.vstack(
                rx.icon("lock", size=40, color="#1E8FFF"), qt19_brand("sm"),
                rx.text("Session locked. Background engines are still running.", font_size="0.8rem", color="rgba(234,244,255,0.75)"),
                qt19_password_field("Password", AppState.login_password, AppState.set_login_password, AppState.show_lock_password, AppState.toggle_show_lock_password),
                rx.cond(AppState.totp_required, rx.input(placeholder="Authenticator code", value=AppState.login_totp, on_change=AppState.set_login_totp, border_radius="1rem", width="100%")),
                rx.cond(AppState.login_error != "", rx.text(AppState.login_error, color="#FF6B6B", font_size="0.8rem")),
                rx.button("Unlock", on_click=AppState.unlock_app, style=PILL_BUTTON_STYLE, width="100%"),
                spacing="3", width="320px", align_items="stretch", style=_CARD),
            height="100vh", width="100%"),
        style=AUTH_BG_STYLE)
