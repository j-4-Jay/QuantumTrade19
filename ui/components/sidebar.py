"""Collapsible sidebar navigation card.

PATH: ui/components/sidebar.py  (REPLACE ENTIRE FILE)

CHANGE (v0.3.7): sidebar is now collapsible. When collapsed, it shrinks to
a narrow icon-only rail (64px) and the content area (see
ui/components/page_shell.py) automatically expands to fill the freed space.
Collapsed/expanded state is persisted (AppState.sidebar_collapsed, saved via
SettingsPersistenceWorker in core_shell_mixin.py's toggle handler) so it is
remembered across app restarts. This sidebar now renders BELOW the
full-width topbar, which is what makes it shorter than before.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState


def _icon_for_tab(tab_name):
    return rx.match(tab_name, ("Dashboard", "layout-dashboard"), ("Trading Panel", "candlestick-chart"),
        ("Journal & Reports", "book-text"), ("Alerts", "bell"), ("Settings", "settings"), "circle")


def _tab_button(tab_name):
    is_active = AppState.active_tab == tab_name
    label = rx.cond(AppState.sidebar_collapsed, rx.fragment(), rx.text(tab_name, font_size="0.85rem", font_weight="600"))
    return rx.tooltip(
        rx.button(
            rx.hstack(rx.icon(_icon_for_tab(tab_name), size=18), label, spacing="3"),
            on_click=AppState.set_active_tab(tab_name),
            width="100%",
            justify_content=rx.cond(AppState.sidebar_collapsed, "center", "start"),
            style=rx.cond(
                is_active,
                {"background": "var(--qt19-accent)", "color": "white", "box_shadow": "0 0 16px 2px var(--qt19-accent-glow)", "border_radius": "9999px"},
                {"background": "transparent", "color": "var(--qt19-text-muted)", "border_radius": "9999px"},
            ),
        ),
        content=tab_name,
    )


def qt19_sidebar():
    return rx.vstack(
        rx.foreach(AppState.sidebar_tabs, _tab_button),
        rx.spacer(),
        height="100%",
        padding="1rem",
        spacing="2",
        style={
            "background": "var(--qt19-glass-bg)",
            "backdrop_filter": "blur(18px)",
            "border_right": "1px solid var(--qt19-glass-border)",
            "width": rx.cond(AppState.sidebar_collapsed, "64px", "230px"),
            "min_width": rx.cond(AppState.sidebar_collapsed, "64px", "230px"),
            "transition": "width 0.28s cubic-bezier(0.22,1,0.36,1), min-width 0.28s cubic-bezier(0.22,1,0.36,1)",
            "overflow": "hidden",
        },
    )
