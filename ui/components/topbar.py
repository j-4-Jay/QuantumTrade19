from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.components.branding import qt19_brand
from config.settings import LIVE_GLOW_COLOR, LIVE_GLOW_SHADOW

_STATUS_COLORS = {
    "connected": "#32CD32",     # lime green
    "degraded": "#FF8C00",      # orange
    "down": "#DC143C",          # crimson
    "connecting": "#6B7280",    # neutral gray while first health check is pending
}
_STATUS_LABELS = {
    "connected": "Connected",
    "degraded": "Degraded",
    "down": "Disconnected",
    "connecting": "Connecting",
}
_PILL_WIDTH = "128px"
_PILL_HEIGHT = "30px"


def _theme_menu():
    return rx.menu.root(
        rx.menu.trigger(rx.icon_button(rx.icon("palette"), variant="ghost", border_radius="9999px")),
        rx.menu.content(rx.foreach(AppState.theme_options, lambda opt: rx.menu.item(opt["label"], on_click=AppState.set_theme(opt["key"])))),
    )


def _paper_live_button():
    return rx.button(
        rx.text(rx.cond(AppState.paper_mode, "PAPER", "LIVE"), font_weight="700", font_size="0.75rem"),
        on_click=AppState.toggle_paper_live, width="72px", justify_content="center", border_radius="9999px",
        style=rx.cond(
            AppState.paper_mode,
            {"background": "var(--qt19-accent)", "color": "white", "box_shadow": "0 0 10px 2px var(--qt19-accent-glow)"},
            {"background": LIVE_GLOW_COLOR, "color": "white", "box_shadow": f"0 0 12px 3px {LIVE_GLOW_SHADOW}"},
        ),
    )


def _sound_button():
    return rx.tooltip(
        rx.icon_button(rx.icon(rx.cond(AppState.sound_muted, "volume-x", "volume-2")), on_click=AppState.toggle_sound, variant="ghost", border_radius="9999px"),
        content=rx.cond(AppState.sound_muted, "Unmute UI sounds", "Mute UI sounds"),
    )


def _ws_status_pill():
    """Fixed-size pill so it never resizes between states. Filled with the
    status color and glowing with the same color, per state:
    Connected = lime green, Degraded = orange, Disconnected = crimson,
    Connecting = neutral gray (transient, before first health check)."""
    fill_color = rx.match(
        AppState.ws_status,
        ("connected", _STATUS_COLORS["connected"]),
        ("degraded", _STATUS_COLORS["degraded"]),
        ("down", _STATUS_COLORS["down"]),
        _STATUS_COLORS["connecting"],
    )
    label = rx.match(
        AppState.ws_status,
        ("connected", _STATUS_LABELS["connected"]),
        ("degraded", _STATUS_LABELS["degraded"]),
        ("down", _STATUS_LABELS["down"]),
        _STATUS_LABELS["connecting"],
    )
    return rx.box(
        rx.text(label, font_size="0.72rem", font_weight="700", color="white", white_space="nowrap"),
        width=_PILL_WIDTH, height=_PILL_HEIGHT,
        display="flex", align_items="center", justify_content="center",
        border_radius="9999px",
        background=fill_color,
        box_shadow=f"0 0 10px 3px {fill_color}",
        transition="background 0.3s ease, box-shadow 0.3s ease",
    )


def qt19_topbar():
    return rx.hstack(
        qt19_brand("sm"), rx.spacer(),
        _ws_status_pill(),
        _paper_live_button(), _theme_menu(), _sound_button(),
        rx.tooltip(rx.icon_button(rx.icon("lock"), on_click=AppState.lock_app, variant="ghost", border_radius="9999px"), content="Lock QuantumTrade19"),
        rx.tooltip(rx.icon_button(rx.icon("log-out"), on_click=AppState.open_logout_dialog, variant="ghost", border_radius="9999px"), content="Logout"),
        width="100%", padding="0.75rem 1.25rem",
        style={"background": "var(--qt19-glass-bg)", "backdrop_filter": "blur(18px)", "border_bottom": "1px solid var(--qt19-glass-border)"},
        align_items="center",
    )
