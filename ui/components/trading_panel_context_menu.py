"""Global-mount Trading Panel chart right-click menu.

PATH: ui/components/trading_panel_context_menu.py  (NEW FILE)

CHANGE (v0.3.8.2 - fix menu offset): this menu must be mounted at the very
top level of the app (in quantumtrade19/quantumtrade19.py), NOT nested
inside ui/pages/trading_panel.py's component tree. Reason: the app's
screen-entrance transition wrapper applies a CSS `transform` (even a
resting `translateX(0)` counts, per the CSS spec) to an ancestor box, and
any `position: fixed` element inside a transformed ancestor is positioned
relative to THAT ancestor's box instead of the real browser viewport - this
was the exact cause of the menu opening at the wrong spot. Mounting it as a
sibling at the true root, outside every transformed wrapper, makes its
`position: fixed` left/top values match the real click coordinates exactly.
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState


def _menu_item(label, on_click) -> rx.Component:
    return rx.box(
        rx.text(label, font_size="0.82rem", font_weight="500"),
        on_click=[on_click, AppState.close_trading_panel_menu],
        padding="0.5rem 0.9rem",
        border_radius="0.6rem",
        cursor="pointer",
        width="100%",
        _hover={"background": "var(--qt19-accent)", "color": "white"},
    )


def _menu_divider() -> rx.Component:
    return rx.divider(margin_y="0.2rem")


def trading_panel_context_menu() -> rx.Component:
    return rx.cond(
        AppState.trading_panel_menu_open,
        rx.fragment(
            rx.box(
                position="fixed",
                top="0", left="0", right="0", bottom="0",
                z_index="998",
                on_click=AppState.close_trading_panel_menu,
                on_context_menu=[rx.prevent_default, AppState.close_trading_panel_menu],
            ),
            rx.box(
                _menu_item(
                    rx.cond(AppState.trading_panel_grid_enabled, "Hide Grid", "Show Grid"),
                    AppState.toggle_trading_panel_grid,
                ),
                _menu_divider(),
                _menu_item("Reset View", AppState.reset_trading_panel_view),
                _menu_divider(),
                _menu_item(
                    rx.cond(AppState.trading_panel_chart_theme == "night", "Day Mode", "Night Mode"),
                    AppState.set_trading_panel_chart_theme(
                        rx.cond(AppState.trading_panel_chart_theme == "night", "day", "night")
                    ),
                ),
                _menu_divider(),
                _menu_item(
                    rx.cond(AppState.trading_panel_follow_live, "Follow Live: Turn OFF", "Follow Live: Turn ON"),
                    AppState.toggle_trading_panel_follow_live,
                ),
                _menu_item("Go to Live", AppState.go_live_trading_panel),
                position="fixed",
                z_index="999",
                min_width="200px",
                padding="0.4rem",
                style=AppState.trading_panel_menu_style,
            ),
        ),
    )
