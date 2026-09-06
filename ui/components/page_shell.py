"""Shared page-shell component.

PATH: ui/components/page_shell.py  (REPLACE ENTIRE FILE)

FIX (shared background / seamless glow blend) - the sidebar's own outer
margin ("0.75rem 0 0.75rem 0.75rem") and the content box's own padding
("1.5rem" on all sides) used to stack independently, producing a slightly
asymmetric double-gap between the sidebar's right edge and the first
content card's left edge - visually reading as two disconnected floating
panels instead of one continuous surface. Content box's LEFT padding is
now reduced to match the sidebar's own margin unit exactly (0.75rem),
so there is exactly ONE consistent gap between them; top/right/bottom
padding are unchanged. Both panels already render on the exact same
PAGE_BG_STYLE gradient (this vstack's own `style=`) - the gap width was
the only real inconsistency, not the background itself.

CHANGE (v0.3.7, unchanged) - topbar spans the full width; sidebar renders
below it as a row with the content area.
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
            rx.box(
                content,
                width="100%",
                padding_top="1.5rem",
                padding_right="1.5rem",
                padding_bottom="1.5rem",
                padding_left="0.75rem",
                flex="1",
                overflow_y="auto",
            ),
            width="100%", height="100%", spacing="0", align_items="stretch",
        ),
        width="100%", height="100vh", spacing="0", style=PAGE_BG_STYLE,
    )
    return rx.box(qt19_cursor_glow(), body, qt19_logout_dialog(), style=_theme_style_vars(), height="100vh", width="100%")
