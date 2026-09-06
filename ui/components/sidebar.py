"""Collapsible sidebar navigation card.

PATH: ui/components/sidebar.py  (REPLACE ENTIRE FILE)

FIX (line-stage: icon instead of a decorative line) - removed the
colored decorative bar entirely. The collapsed-to-a-line stage now shows
ONE single icon button filling the whole card top-to-bottom - the entire
card IS the handle, clearly clickable, no separate thin visual element
pretending to be a "line" anymore.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE
from ui.components.glow_card import qt19_glow_card

_ICON_SIZE = 27
_ICON_COL_WIDTH = "32px"
_FULL_WIDTH = "230px"
_ICONS_WIDTH = "72px"
_LINE_WIDTH = "14px"
_HANDLE_HEIGHT = "52px"
_OUTER_PADDING = "0.85rem"
_LINE_HEIGHT_TOTAL = "280px"


def _icon_for_tab(tab_name):
    return rx.match(tab_name, ("Dashboard", "layout-dashboard"), ("Trading Panel", "candlestick-chart"),
        ("Journal & Reports", "book-text"), ("Alerts", "bell"), ("Settings", "settings"), "circle")


def _tab_button(tab_name):
    is_active = AppState.active_tab == tab_name
    icon_el = rx.icon(_icon_for_tab(tab_name), size=_ICON_SIZE)

    full_content = rx.hstack(
        rx.box(icon_el, width=_ICON_COL_WIDTH, display="flex", align_items="center", justify_content="center", flex_shrink="0"),
        rx.text(tab_name, font_size="0.85rem", font_weight="600", text_align="left"),
        spacing="2",
        align_items="center",
        width="100%",
        justify_content="start",
    )
    icons_content = rx.center(icon_el, width="100%", height="100%")

    return rx.button(
        rx.cond(AppState.sidebar_stage == "full", full_content, icons_content),
        on_click=AppState.set_active_tab(tab_name),
        width="100%",
        height=_HANDLE_HEIGHT,
        padding=rx.cond(AppState.sidebar_stage == "full", "0 0.75rem", "0"),
        style=rx.cond(
            is_active,
            {"background": "var(--qt19-accent)", "color": "white", "box_shadow": "0 0 16px 2px var(--qt19-accent-glow)", "border_radius": "0.9rem"},
            {"background": "rgba(255,255,255,0.03)", "color": "var(--qt19-text-muted)", "border_radius": "0.9rem"},
        ),
    )


def _stage_handle_icon() -> rx.Component:
    return rx.match(
        AppState.sidebar_stage,
        ("full", rx.icon("chevrons-left", size=16)),
        ("icons", rx.icon("minus", size=16)),
        rx.icon("chevrons-right", size=16),
    )


def _stage_handle_button(height: str) -> rx.Component:
    return rx.button(
        rx.center(_stage_handle_icon(), width="100%", height="100%"),
        on_click=AppState.cycle_sidebar_stage,
        width="100%",
        height=height,
        padding="0",
        flex_shrink="0",
        variant="ghost",
        style={
            "background": "transparent",
            "color": "var(--qt19-text-muted)",
            "border_radius": "0.9rem",
            "border": "1px solid var(--qt19-glass-border)",
        },
    )


def _full_or_icons_body() -> rx.Component:
    return rx.vstack(
        rx.foreach(AppState.sidebar_tabs, _tab_button),
        _stage_handle_button(_HANDLE_HEIGHT),
        width="100%",
        padding=_OUTER_PADDING,
        spacing="2",
        align_items="center",
    )


def _line_body() -> rx.Component:
    """No decorative bar anymore - the entire card is one big icon
    button, clearly clickable, filling the full collapsed-line height."""
    return rx.box(
        _stage_handle_button("100%"),
        width="100%",
        height=_LINE_HEIGHT_TOTAL,
        padding=_OUTER_PADDING,
    )


def qt19_sidebar():
    width = rx.match(
        AppState.sidebar_stage,
        ("full", _FULL_WIDTH),
        ("icons", _ICONS_WIDTH),
        _LINE_WIDTH,
    )
    body = rx.cond(AppState.sidebar_stage == "line", _line_body(), _full_or_icons_body())
    return qt19_glow_card(
        body,
        card_style={
            **GLASS_CARD_STYLE,
            "width": width,
            "min_width": width,
            "padding": "0",
        },
        margin="0.75rem",
    )
