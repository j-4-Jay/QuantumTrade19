"""Floating right sidebar of the Trading Panel (FT-U.3a).

PATH: ui/components/trading_right_sidebar.py  (NEW FILE)

A frosted-glass card that floats over the right side of the chart, so the
chart never changes size when it opens or closes. Four tabs in one row at
the top (Trade, POI, Setups, Alerts) and a collapse button. When closed,
only one round glowing handle stays on the right screen edge.
Tab contents are placeholders in this step.
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState
from ui.components.glow_card import qt19_glow_card
from ui.theme.glass import GLASS_CARD_STYLE, SQUARE_HANDLE_STYLE

_WIDTH = "360px"
_TABS = ["Trade", "Chart", "POI", "Setups", "Alerts"]
_PLACEHOLDERS = {
    "Trade": "Order ticket comes in step 3c.",
    "Chart": "Chart settings.",
    "POI": "POI controls.",
    "Setups": "Setup settings and stats.",
    "Alerts": "Alerts for this symbol come later.",
}


def _tab(name: str) -> rx.Component:
    active = AppState.right_panel_tab == name
    return rx.button(
        name,
        on_click=AppState.set_right_tab(name),
        class_name="qt19-nav-btn",
        flex="1",
        min_width="0",
        height="2.3rem",
        padding="0",
        style=rx.cond(
            active,
            {"background": "rgba(255,255,255,0.10)", "color": "white", "font_weight": "800", "font_size": "0.74rem",
             "border": "1px solid var(--qt19-accent)", "border_bottom": "1px solid transparent",
             "border_radius": "0.9rem 0.9rem 0 0", "box_shadow": "0 -4px 14px -2px var(--qt19-accent-glow)",
             "position": "relative", "z_index": "2", "margin_bottom": "-1px"},
            {"background": "rgba(255,255,255,0.03)", "color": "var(--qt19-text-muted)", "font_weight": "700",
             "font_size": "0.74rem", "border": "1px solid var(--qt19-glass-border)",
             "border_radius": "0.9rem 0.9rem 0 0"},
        ),
    )


def _collapse_button() -> rx.Component:
    return rx.button(
        rx.icon("chevrons-right", size=18),
        on_click=AppState.toggle_right_panel,
        title="Close trading sidebar",
        width="2.3rem",
        height="2.3rem",
        padding="0",
        flex_shrink="0",
        variant="ghost",
        style={**SQUARE_HANDLE_STYLE, "margin_bottom": "0.35rem"},
    )


def _placeholder(name: str) -> rx.Component:
    return rx.vstack(
        rx.text(name, font_size="1rem", font_weight="800"),
        rx.text(_PLACEHOLDERS[name], font_size="0.85rem", color="var(--qt19-text-muted)"),
        width="100%",
        align_items="start",
        spacing="2",
        padding="0.5rem 0.25rem",
    )


def _panel(contents: dict) -> rx.Component:
    body = rx.vstack(
        rx.hstack(
            *[_tab(name) for name in _TABS],
            _collapse_button(),
            width="100%",
            spacing="1",
            align_items="end",
            flex_shrink="0",
        ),
        rx.box(
            rx.match(
                AppState.right_panel_tab,
                *[(name, contents[name] if name in contents else _placeholder(name)) for name in _TABS],
                _placeholder("Trade"),
            ),
            width="100%",
            flex="1",
            min_height="0",
            overflow_y="auto",
            class_name="qt19-tab-dissolve",
            key=AppState.right_panel_tab,
            padding="0.9rem",
            border="1px solid var(--qt19-accent)",
            border_radius="0 0.9rem 0.9rem 0.9rem",
            background="rgba(255,255,255,0.04)",
            box_shadow="inset 0 0 18px rgba(0,0,0,0.18), 0 0 12px -2px var(--qt19-accent-glow)",
        ),
        width="100%",
        height="100%",
        spacing="0",
        align_items="stretch",
    )
    card = qt19_glow_card(
        body,
        card_style={
            **GLASS_CARD_STYLE,
            "width": _WIDTH,
            "min_width": _WIDTH,
            "height": "100%",
            "padding": "0.75rem",
            "background": "color-mix(in srgb, var(--qt19-glass-bg) 55%, transparent)",
            "backdrop_filter": "blur(26px) saturate(180%)",
            "box_shadow": "0 12px 40px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.16)",
        },
        margin="0 0 0 0.75rem",
        edge=True,
    )
    return rx.box(
        card,
        display="flex",
        align_items="stretch",
        flex_shrink="0",
        min_width="calc(360px + 0.75rem)",
    )


def _handle() -> rx.Component:
    return rx.box(
        rx.icon("chevrons-left", size=20),
        on_click=AppState.toggle_right_panel,
        title="Open trading sidebar",
        style={
            **SQUARE_HANDLE_STYLE,
            "position": "absolute",
            "top": "0.75rem",
            "right": "0.75rem",
            "width": "2.3rem",
            "height": "2.3rem",
            "display": "flex",
            "align_items": "center",
            "justify_content": "center",
            "z_index": "25",
        },
    )


def qt19_right_sidebar(contents: dict | None = None) -> rx.Component:
    return rx.box(
        _panel(contents or {}),
        class_name="qt19-right-wrap",
        display="flex",
        align_items="stretch",
        flex_shrink="0",
        width=rx.cond(AppState.right_panel_open, "calc(360px + 0.75rem)", "0px"),
        transition="width 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)",
    )


def qt19_right_handle() -> rx.Component:
    return rx.cond(AppState.right_panel_open, rx.fragment(), _handle())
