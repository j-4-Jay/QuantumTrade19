"""Global-mount Trading Panel chart right-click menu.

PATH: ui/components/trading_panel_context_menu.py  (REPLACE ENTIRE FILE)

FIX (Change Mode submenu didn't open) - the previous version used an
absolutely-positioned flyout (`left: 100%`) nested inside the menu's own
box. That's fragile inside a custom `position: fixed` menu with no
guaranteed overflow/stacking context, and evidently never became visible.
Replaced with a simple INLINE EXPANSION instead: clicking "Change Mode"
reveals the option list directly below it, in normal block flow, inside
the exact same menu box - no absolute positioning, no z-index, no
overflow/clipping possible. Guaranteed to render since it's the same
technique every other menu item already uses successfully.

FIX (hover text invisible in Day theme, carried forward + reinforced) -
`color="inherit"` on every label text, matching the global CSS fix in
ui/theme/global_css.py.
"""
from __future__ import annotations


import reflex as rx


from state.app_state import AppState


def _menu_item(label, on_click) -> rx.Component:
    return rx.box(
        rx.text(label, font_size="0.82rem", font_weight="500", color="inherit"),
        on_click=[on_click, AppState.close_trading_panel_menu],
        padding="0.5rem 0.9rem",
        border_radius="0.6rem",
        cursor="pointer",
        width="100%",
        color="inherit",
        _hover={"background": "var(--qt19-accent)", "color": "white"},
    )


def _menu_divider() -> rx.Component:
    return rx.divider(margin_y="0.2rem")


def _bg_mode_option(opt: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.cond(
                opt["swatch"] != "",
                rx.box(width="14px", height="14px", border_radius="9999px", background=opt["swatch"], border="1px solid rgba(255,255,255,0.25)", flex_shrink="0"),
                rx.icon("sparkles", size=14, flex_shrink="0"),
            ),
            rx.text(opt["label"], font_size="0.8rem", font_weight="500", color="inherit"),
            spacing="2", align_items="center", width="100%",
        ),
        on_click=[AppState.set_trading_panel_bg_mode(opt["key"]), AppState.close_trading_panel_menu],
        padding="0.45rem 0.8rem",
        border_radius="0.6rem",
        cursor="pointer",
        width="100%",
        color="inherit",
        _hover={"background": "var(--qt19-accent)", "color": "white"},
    )


def _change_mode_row() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("Change Mode", font_size="0.82rem", font_weight="500", color="inherit"),
            rx.spacer(),
            rx.icon(
                rx.cond(AppState.trading_panel_bg_submenu_open, "chevron-down", "chevron-right"),
                size=14,
            ),
            width="100%", align_items="center",
        ),
        on_click=AppState.toggle_trading_panel_bg_submenu,
        padding="0.5rem 0.9rem",
        border_radius="0.6rem",
        cursor="pointer",
        width="100%",
        color="inherit",
        _hover={"background": "var(--qt19-accent)", "color": "white"},
    )


def _change_mode_options() -> rx.Component:
    """Inline-expanding list, directly below the Change Mode row, in
    normal document flow - no absolute positioning, so it can never fail
    to render due to overflow/z-index/clipping."""
    return rx.cond(
        AppState.trading_panel_bg_submenu_open,
        rx.box(
            rx.foreach(AppState.trading_panel_bg_mode_options, _bg_mode_option),
            padding_left="0.5rem",
            margin_top="0.15rem",
            max_height="260px",
            overflow_y="auto",
            width="100%",
        ),
    )


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
                _change_mode_row(),
                _change_mode_options(),
                _menu_divider(),
                _menu_item(
                    rx.cond(AppState.trading_panel_follow_live, "Follow Live: Turn OFF", "Follow Live: Turn ON"),
                    AppState.toggle_trading_panel_follow_live,
                ),
                _menu_item("Go to Live", AppState.go_live_trading_panel),
                position="fixed",
                z_index="999",
                min_width="200px",
                max_height="80vh",
                overflow_y="auto",
                padding="0.4rem",
                style=AppState.trading_panel_menu_style,
            ),
        ),
    )
