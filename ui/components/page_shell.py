"""Shared page-shell component.

PATH: ui/components/page_shell.py  (REPLACE ENTIRE FILE)

CHANGE (v0.3.7): restructured so the topbar spans the FULL width of the
screen (top row), with the sidebar + content area as a row underneath it,
instead of sidebar + (topbar+content) side by side. This is what makes the
header full-width and the sidebar correspondingly shorter. The content box
automatically fills whatever width the (now-collapsible) sidebar frees up -
no extra logic needed, since the sidebar's own width transition (see
ui/components/sidebar.py) combined with this row's flex="1" content box
handles the expand/collapse resize automatically.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.components.sidebar import qt19_sidebar
from ui.components.topbar import qt19_topbar
from ui.components.cursor_glow import qt19_cursor_glow
from ui.components.logout_dialog import qt19_logout_dialog
from ui.theme.glass import PAGE_BG_STYLE


def _theme_style_vars() -> dict:
    return {
        "--qt19-accent": AppState.theme_vars["accent"], "--qt19-accent-glow": AppState.theme_vars["accent_glow"],
        "--qt19-bg-from": AppState.theme_vars["bg_from"], "--qt19-bg-to": AppState.theme_vars["bg_to"],
        "--qt19-glass-bg": AppState.theme_vars["glass_bg"], "--qt19-glass-border": AppState.theme_vars["glass_border"],
        "--qt19-text-primary": AppState.theme_vars["text_primary"], "--qt19-text-muted": AppState.theme_vars["text_muted"],
    }


def qt19_page_shell(content: rx.Component, show_nav: bool = True) -> rx.Component:
    body = rx.vstack(
        rx.cond(show_nav, qt19_topbar(), rx.fragment()),
        rx.hstack(
            rx.cond(show_nav, qt19_sidebar(), rx.fragment()),
            rx.box(content, width="100%", padding="1.5rem", flex="1", overflow_y="auto"),
            width="100%", height="100%", spacing="0", align_items="stretch",
        ),
        width="100%", height="100vh", spacing="0", style=PAGE_BG_STYLE,
    )
    return rx.box(qt19_cursor_glow(), body, qt19_logout_dialog(), style=_theme_style_vars(), height="100vh", width="100%")
