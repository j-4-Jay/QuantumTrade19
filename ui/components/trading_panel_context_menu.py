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


def _ind_poi_add_item() -> rx.Component:
    return rx.cond(
        AppState.ind_poi_can_add,
        _menu_item("Add Independent POI", AppState.add_independent_poi),
        rx.box(
            rx.text("Add Independent POI (limit of 10 reached)", font_size="0.82rem", font_weight="500", color="inherit"),
            padding="0.5rem 0.9rem",
            opacity="0.45",
            width="100%",
            cursor="not-allowed",
        ),
    )


def _ind_poi_delete_item() -> rx.Component:
    return rx.cond(
        AppState.ind_poi_target_uid != "",
        _menu_item(AppState.ind_poi_delete_label, AppState.delete_independent_poi),
    )


_IND_POI_SWATCHES = [
    "#F59E0B", "#EF4444", "#22C55E", "#3B82F6", "#A855F7",
    "#EC4899", "#14B8A6", "#FFFFFF", "#FACC15", "#94A3B8",
]


def _ind_poi_style_item() -> rx.Component:
    return rx.cond(
        AppState.ind_poi_target_uid != "",
        _menu_item("Independent POI Style", AppState.open_ind_poi_style_popup),
    )


def _ind_poi_swatch(color: str) -> rx.Component:
    return rx.box(
        width="22px",
        height="22px",
        border_radius="6px",
        background=color,
        border="1px solid rgba(255,255,255,0.35)",
        cursor="pointer",
        flex_shrink="0",
        on_click=AppState.set_ind_poi_style_color(color),
    )


def _ind_poi_line_style_button(label: str, key: str) -> rx.Component:
    return rx.button(
        label,
        size="1",
        variant=rx.cond(AppState.ind_poi_style_line_style == key, "solid", "soft"),
        on_click=AppState.set_ind_poi_style_line_style(key),
    )


def _ind_poi_style_popup() -> rx.Component:
    return rx.cond(
        AppState.ind_poi_style_popup_open,
        rx.fragment(
            rx.box(
                position="fixed",
                top="0", left="0", right="0", bottom="0",
                z_index="999",
                background="rgba(0,0,0,0.25)",
                on_click=AppState.close_ind_poi_style_popup,
                on_context_menu=[rx.prevent_default, AppState.close_ind_poi_style_popup],
            ),
            rx.box(
                rx.text(AppState.ind_poi_style_title, font_size="0.95rem", font_weight="700", color="inherit"),
                rx.text("Colour", font_size="0.75rem", opacity="0.7", color="inherit"),
                rx.hstack(
                    *[_ind_poi_swatch(color) for color in _IND_POI_SWATCHES],
                    rx.el.input(
                        type="color",
                        value=AppState.ind_poi_style_color,
                        on_change=AppState.set_ind_poi_style_color,
                        style={"width": "34px", "height": "26px", "padding": "0", "border": "none", "background": "transparent", "cursor": "pointer"},
                    ),
                    spacing="2",
                    wrap="wrap",
                    align_items="center",
                ),
                rx.text(AppState.ind_poi_style_width_text, font_size="0.8rem", color="inherit"),
                rx.el.input(
                    type="range", min="1", max="5", step="1",
                    value=AppState.ind_poi_style_width,
                    on_change=AppState.set_ind_poi_style_width,
                    style={"width": "100%"},
                ),
                rx.text(AppState.ind_poi_style_opacity_text, font_size="0.8rem", color="inherit"),
                rx.el.input(
                    type="range", min="0", max="100", step="5",
                    value=AppState.ind_poi_style_opacity,
                    on_change=AppState.set_ind_poi_style_opacity,
                    style={"width": "100%"},
                ),
                rx.text("Line style", font_size="0.75rem", opacity="0.7", color="inherit"),
                rx.hstack(
                    _ind_poi_line_style_button("Solid", "solid"),
                    _ind_poi_line_style_button("Dashed", "dashed"),
                    _ind_poi_line_style_button("Dotted", "dotted"),
                    spacing="2",
                ),
                rx.divider(),
                rx.hstack(
                    rx.switch(checked=AppState.ind_poi_style_allow_live, on_change=AppState.set_ind_poi_allow_live),
                    rx.text("Allow live use of this line", font_size="0.82rem", color="inherit"),
                    spacing="2",
                    align_items="center",
                ),
                rx.text("Paper only unless this is ON. It is never saved: it is OFF after every restart.", font_size="0.72rem", opacity="0.7", color="inherit"),
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1000",
                min_width="300px",
                max_width="90vw",
                max_height="80vh",
                overflow_y="auto",
                padding="0.9rem",
                display="flex",
                flex_direction="column",
                gap="0.6rem",
                style=AppState.ind_poi_popup_style,
            ),
        ),
    )


def _ind_poi_open_delete_item() -> rx.Component:
    return rx.cond(
        AppState.ind_poi_count > 0,
        _menu_item("Delete Independent POI", AppState.open_ind_poi_delete_popup),
        rx.box(
            rx.text("Delete Independent POI", font_size="0.82rem", font_weight="500", color="inherit"),
            padding="0.5rem 0.9rem",
            opacity="0.45",
            width="100%",
            cursor="not-allowed",
        ),
    )


def _ind_poi_delete_row(row: dict) -> rx.Component:
    return rx.box(
        rx.checkbox(
            row["label"],
            checked=row["checked"],
            on_change=lambda _checked: AppState.toggle_ind_poi_selected(row["uid"]),
        ),
        width="100%",
        padding="0.3rem 0.2rem",
    )


def _ind_poi_delete_popup() -> rx.Component:
    return rx.cond(
        AppState.ind_poi_delete_popup_open,
        rx.fragment(
            rx.box(
                position="fixed",
                top="0", left="0", right="0", bottom="0",
                z_index="999",
                background="rgba(0,0,0,0.25)",
                on_click=AppState.close_ind_poi_delete_popup,
                on_context_menu=[rx.prevent_default, AppState.close_ind_poi_delete_popup],
            ),
            rx.box(
                rx.text("Delete Independent POI", font_size="0.95rem", font_weight="700", color="inherit"),
                rx.hstack(
                    rx.button("Select All", size="1", variant="soft", on_click=AppState.select_all_ind_poi),
                    rx.button("Select None", size="1", variant="soft", on_click=AppState.select_none_ind_poi),
                    spacing="2",
                ),
                rx.box(
                    rx.foreach(AppState.ind_poi_delete_rows, _ind_poi_delete_row),
                    max_height="40vh",
                    overflow_y="auto",
                    width="100%",
                ),
                rx.button(
                    "Delete",
                    color_scheme="red",
                    width="100%",
                    disabled=AppState.ind_poi_selected_count == 0,
                    on_click=AppState.delete_selected_ind_poi,
                ),
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1000",
                min_width="300px",
                max_width="90vw",
                max_height="80vh",
                overflow_y="auto",
                padding="0.9rem",
                display="flex",
                flex_direction="column",
                gap="0.6rem",
                style=AppState.ind_poi_popup_style,
            ),
        ),
    )


def trading_panel_context_menu() -> rx.Component:
    return rx.fragment(_trading_panel_menu_body(), _ind_poi_delete_popup(), _ind_poi_style_popup())


def _trading_panel_menu_body() -> rx.Component:
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
                _change_mode_row(),
                _change_mode_options(),
                _menu_divider(),
                _menu_item(
                    rx.cond(AppState.trading_panel_candles_visible, "Hide Candles", "Show Candles"),
                    AppState.toggle_trading_panel_candles,
                ),
                _menu_divider(),
                _menu_item("Reset View", AppState.reset_trading_panel_view),
                _menu_item("Go to Live", AppState.go_live_trading_panel),
                _menu_item(
                    rx.cond(AppState.trading_panel_follow_live, "Follow Live: Turn OFF", "Follow Live: Turn ON"),
                    AppState.toggle_trading_panel_follow_live,
                ),
                _menu_divider(),
                _ind_poi_add_item(),
                _ind_poi_open_delete_item(),
                _ind_poi_delete_item(),
                _ind_poi_style_item(),
                position="fixed",
                z_index="999",
                id="qt19-chart-menu",
                min_width="200px",
                max_height="80vh",
                overflow_y="auto",
                padding="0.4rem",
                style=AppState.trading_panel_menu_style,
            ),
        ),
    )
