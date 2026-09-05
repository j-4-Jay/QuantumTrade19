"""Collapsible sidebar navigation card.

PATH: ui/components/sidebar.py  (REPLACE ENTIRE FILE)

FIX (collapsed icon alignment) - when collapsed, the tab button used to
render `rx.hstack(icon, label, spacing="3")` with `justify_content` set
only on the OUTER button - the inner hstack still hugged its own content
width and inherited Radix Button's default icon+text padding (asymmetric,
meant for the icon+label case), so the icon visually sat off-center
inside the collapsed square button. Fixed by rendering a completely
different, simpler tree when collapsed: `rx.center(icon, width="100%")`
with explicit zero padding and a fixed square height/width - guarantees
true centering regardless of any button default padding, and gives every
collapsed icon button the same premium, uniform square footprint.

FIX v0.4.55 (carried forward) - switched from class_name=HOVER_GLOW_CLASS
to the bulletproof qt19_glow_card() wrapper. Untouched by this patch.
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
    icon_el = rx.icon(_icon_for_tab(tab_name), size=18)
    expanded_content = rx.hstack(
        icon_el,
        rx.text(tab_name, font_size="0.85rem", font_weight="600"),
        spacing="3",
        align_items="center",
        width="100%",
    )
    collapsed_content = rx.center(icon_el, width="100%", height="100%")

    return rx.button(
        rx.cond(AppState.sidebar_collapsed, collapsed_content, expanded_content),
        on_click=AppState.set_active_tab(tab_name),
        width="100%",
        height="44px",
        padding=rx.cond(AppState.sidebar_collapsed, "0", "0.6rem 1rem"),
        style=rx.cond(
            is_active,
            {"background": "var(--qt19-accent)", "color": "white", "box_shadow": "0 0 16px 2px var(--qt19-accent-glow)", "border_radius": "9999px"},
            {"background": "transparent", "color": "var(--qt19-text-muted)", "border_radius": "9999px"},
        ),
    )


def _collapse_toggle_button() -> rx.Component:
    """Real, visible control for AppState.toggle_sidebar_collapsed()."""
    return rx.button(
        rx.center(
            rx.icon(
                rx.cond(AppState.sidebar_collapsed, "chevron-right", "chevron-left"),
                size=18,
            ),
            width="100%", height="100%",
        ),
        on_click=AppState.toggle_sidebar_collapsed,
        width="100%",
        height="44px",
        padding="0",
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
            align_items="center",
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
