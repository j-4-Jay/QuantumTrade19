"""Collapsible sidebar navigation card.

PATH: ui/components/sidebar.py  (REPLACE ENTIRE FILE)

FIX v0.4.55 - switched from class_name=HOVER_GLOW_CLASS (box-shadow based,
could be blocked by CSS specificity) to the new bulletproof
qt19_glow_card() wrapper (ui/components/glow_card.py) - a structurally
separate glow layer that cannot be blocked by anything on the card's own
style. See ui/theme/global_css.py's docstring for the full explanation.

FIX v0.4.49 (carried forward): sidebar only glows on mouse hover, no
tooltips on nav links, floating glass-card look with margin on all sides.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE
from ui.components.glow_card import qt19_glow_card


def _icon_for_tab(tab_name):
    return rx.match(tab_name, ("Dashboard", "layout-dashboard"), ("Trading Panel", "candlestick-chart"),
        ("Journal & Reports", "book-text"), ("Alerts", "bell"), ("Settings", "settings"), "circle")


def _tab_button(tab_name):
    is_active = AppState.active_tab == tab_name
    label = rx.cond(AppState.sidebar_collapsed, rx.fragment(), rx.text(tab_name, font_size="0.85rem", font_weight="600"))
    return rx.button(
        rx.hstack(rx.icon(_icon_for_tab(tab_name), size=18), label, spacing="3"),
        on_click=AppState.set_active_tab(tab_name),
        width="100%",
        justify_content=rx.cond(AppState.sidebar_collapsed, "center", "start"),
        style=rx.cond(
            is_active,
            {"background": "var(--qt19-accent)", "color": "white", "box_shadow": "0 0 16px 2px var(--qt19-accent-glow)", "border_radius": "9999px"},
            {"background": "transparent", "color": "var(--qt19-text-muted)", "border_radius": "9999px"},
        ),
    )


def _collapse_toggle_button() -> rx.Component:
    """Real, visible control for AppState.toggle_sidebar_collapsed()."""
    return rx.button(
        rx.icon(
            rx.cond(AppState.sidebar_collapsed, "chevron-right", "chevron-left"),
            size=18,
        ),
        on_click=AppState.toggle_sidebar_collapsed,
        width="100%",
        justify_content="center",
        variant="ghost",
        style={
            "background": "transparent",
            "color": "var(--qt19-text-muted)",
            "border_radius": "9999px",
            "border": "1px solid var(--qt19-glass-border)",
        },
    )


def qt19_sidebar():
    return qt19_glow_card(
        rx.vstack(
            rx.foreach(AppState.sidebar_tabs, _tab_button),
            rx.spacer(),
            _collapse_toggle_button(),
            height="100%",
            padding="1rem",
            spacing="2",
        ),
        card_style={
            **GLASS_CARD_STYLE,
            "width": rx.cond(AppState.sidebar_collapsed, "64px", "230px"),
            "min_width": rx.cond(AppState.sidebar_collapsed, "64px", "230px"),
            "transition": "width 0.28s cubic-bezier(0.22,1,0.36,1), min-width 0.28s cubic-bezier(0.22,1,0.36,1)",
        },
        height="calc(100% - 1.5rem)",
        margin="0.75rem 0 0.75rem 0.75rem",
    )
