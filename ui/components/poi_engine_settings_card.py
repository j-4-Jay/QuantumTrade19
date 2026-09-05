"""File 03.1 Scope E - POI Engine & Chart Visibility Settings card.

PATH: ui/components/poi_engine_settings_card.py (REPLACE ENTIRE FILE)

CHANGE (v0.5.0-r11): custom recurring line rows now include a Name text
input (shown on the chart instead of the raw time when filled in) and a
12-hour hour/minute input pair plus an AM/PM segmented toggle, replacing
the old single 24-hour "HH:MM" text field.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_3XL_STYLE


def _color_input(value: str, on_change) -> rx.Component:
    return rx.input(
        type="color",
        value=value,
        on_change=on_change,
        width="36px",
        height="28px",
        padding="0",
        border="none",
        cursor="pointer",
    )


def _poi_tf_card(row: dict) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(row["label"], font_size="0.85rem", font_weight="700"),
            rx.spacer(),
            _color_input(row["color"], lambda v: AppState.set_poi_tf_color(row["tf"], v)),
            width="100%", align_items="center",
        ),
        rx.hstack(
            rx.checkbox(
                checked=row["display"],
                on_change=lambda checked: AppState.toggle_poi_tf_display(row["tf"], checked),
            ),
            rx.text("Display (High + Low)", font_size="0.72rem"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.hstack(
            rx.checkbox(
                checked=row["strategy"],
                on_change=lambda checked: AppState.toggle_poi_tf_strategy(row["tf"], checked),
            ),
            rx.text("Strategy (High + Low)", font_size="0.72rem"),
            spacing="2", align_items="center", width="100%",
        ),
        spacing="2", width="100%", padding="0.6rem 0.7rem",
        style={
            "background": "rgba(255,255,255,0.03)",
            "border": "1px solid var(--qt19-glass-border)",
            "border_radius": "0.65rem",
        },
    )


def _poi_lines_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Previous High/Low Lines", size="3"),
        rx.text(
            "One card per timeframe. Display shows both the High and Low line together; "
            "Strategy makes both eligible for setup detection together. Pick any color.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.grid(
            rx.foreach(AppState.poi_tf_card_rows, _poi_tf_card),
            columns=rx.breakpoints(initial="2", md="4"),
            spacing="3", width="100%", margin_top="0.5rem",
        ),
        spacing="2", width="100%",
    )


def _poi_zone_type_row(row: dict) -> rx.Component:
    return rx.hstack(
        rx.text(row["label"], font_size="0.82rem", font_weight="600", width="140px"),
        rx.checkbox(
            checked=row["display"],
            on_change=lambda checked: AppState.toggle_poi_display(row["type"], checked),
        ),
        rx.text("Display", font_size="0.75rem"),
        rx.checkbox(
            checked=row["strategy"],
            on_change=lambda checked: AppState.toggle_poi_strategy(row["type"], checked),
        ),
        rx.text("Use in Strategy", font_size="0.75rem"),
        spacing="3", width="100%", padding_y="0.3rem",
        border_bottom="1px solid var(--qt19-glass-border)",
    )


def _poi_zone_source_tf_checkbox(row: dict) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=row["enabled"],
            on_change=lambda checked: AppState.toggle_poi_zone_source_tf(row["tf"], checked),
        ),
        rx.text(row["tf"], font_size="0.78rem"),
        spacing="2", align_items="center",
    )


def _poi_zone_matrix_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Zone Source-Timeframe Matrix", size="3"),
        rx.text("Which timeframes Flip/FVG/Inverse FVG/Order Block zones are calculated from. "
                "Shared across all zone types.",
                font_size="0.78rem", color="var(--qt19-text-muted)"),
        rx.grid(
            rx.foreach(AppState.poi_zone_source_tf_rows, _poi_zone_source_tf_checkbox),
            columns="4", spacing="2", width="100%", margin_top="0.5rem",
        ),
        spacing="2", width="100%",
    )


def _poi_zone_types_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Zone Types", size="3"),
        rx.vstack(rx.foreach(AppState.poi_zone_type_rows, _poi_zone_type_row), spacing="1", width="100%", margin_top="0.5rem"),
        spacing="2", width="100%",
    )


def _tf_vertical_checkbox(row: dict) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=row["vertical_enabled"],
            on_change=lambda checked: AppState.toggle_poi_tf_vertical(row["tf"], checked),
        ),
        rx.text(row["label"], font_size="0.76rem"),
        spacing="2", align_items="center",
    )


def _custom_line_row(index: int) -> rx.Component:
    line = AppState.poi_custom_lines[index]
    return rx.vstack(
        rx.hstack(
            rx.checkbox(
                checked=line["enabled"],
                on_change=lambda checked: AppState.toggle_custom_line_enabled(index, checked),
            ),
            rx.text(f"Custom Line {index + 1}", font_size="0.78rem", font_weight="600", width="110px"),
            _color_input(line["color"], lambda v: AppState.set_custom_line_color(index, v)),
            spacing="2", align_items="center", width="100%",
        ),
        rx.hstack(
            rx.input(
                value=line["hour12"].to_string(),
                on_blur=lambda v: AppState.set_custom_line_hour(index, v),
                placeholder="HH",
                width="54px", size="1", type_="number",
            ),
            rx.text(":", font_size="0.9rem"),
            rx.input(
                value=line["minute"].to_string(),
                on_blur=lambda v: AppState.set_custom_line_minute(index, v),
                placeholder="MM",
                width="54px", size="1", type_="number",
            ),
            rx.segmented_control.root(
                rx.segmented_control.item("AM", value="AM"),
                rx.segmented_control.item("PM", value="PM"),
                value=line["meridiem"],
                on_change=lambda v: AppState.set_custom_line_meridiem(index, v),
                size="1",
            ),
            rx.text("(New York time)", font_size="0.68rem", color="var(--qt19-text-muted)"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.input(
            value=line["name"],
            on_blur=lambda v: AppState.set_custom_line_name(index, v),
            placeholder="Optional name shown on chart (else shows the time)",
            width="100%", size="1",
        ),
        spacing="2", width="100%", padding="0.5rem 0.6rem",
        style={
            "background": "rgba(255,255,255,0.03)",
            "border": "1px solid var(--qt19-glass-border)",
            "border_radius": "0.6rem",
        },
    )


def _poi_vertical_markers_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Previous-Period Start/End Markers", size="3"),
        rx.text(
            "Two vertical lines mark where each timeframe's previous period began and ended "
            "(e.g. the previous 4H candle's open/close time). Only shows when that "
            "timeframe's Display checkbox above is also ON. Same color as the horizontal "
            "line, 1px thick, recurring - they automatically shift forward as each period "
            "closes in real time.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.grid(
            rx.foreach(AppState.poi_tf_card_rows, _tf_vertical_checkbox),
            columns="4", spacing="2", width="100%", margin_top="0.5rem",
        ),
        rx.hstack(
            rx.text("Style:", font_size="0.78rem", font_weight="600"),
            rx.segmented_control.root(
                rx.segmented_control.item("Dashed", value="dashed"),
                rx.segmented_control.item("Solid", value="solid"),
                value=AppState.poi_vertical_line_style,
                on_change=AppState.set_poi_vertical_line_style,
                size="1",
            ),
            spacing="3", align_items="center", margin_top="0.75rem",
        ),
        rx.vstack(
            rx.text(f"Marker transparency: {AppState.poi_vertical_line_opacity}%", font_size="0.78rem"),
            rx.slider(
                default_value=[AppState.poi_vertical_line_opacity],
                on_value_commit=AppState.set_poi_vertical_line_opacity,
                min=0, max=100, width="100%",
            ),
            spacing="1", width="100%", margin_top="0.5rem",
        ),
        rx.divider(margin_y="0.5rem"),
        rx.text("Custom Recurring Lines", font_size="0.82rem", font_weight="700"),
        rx.text(
            "Up to 3 independent daily lines at a fixed time (America/New_York). They "
            "automatically reappear at the same time every day - nothing to reset manually. "
            "Give one a Name to show that instead of the time on the chart.",
            font_size="0.76rem", color="var(--qt19-text-muted)",
        ),
        rx.vstack(
            _custom_line_row(0), _custom_line_row(1), _custom_line_row(2),
            spacing="2", width="100%", margin_top="0.3rem",
        ),
        spacing="2", width="100%",
    )


def _poi_visual_controls_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Visual Controls", size="3"),
        rx.hstack(
            rx.checkbox(checked=AppState.poi_show_labels, on_change=AppState.toggle_poi_show_labels),
            rx.text("POI labels", font_size="0.78rem"),
            spacing="2",
        ),
        rx.hstack(
            rx.checkbox(checked=AppState.poi_show_tooltips, on_change=AppState.toggle_poi_show_tooltips),
            rx.text("POI tooltips", font_size="0.78rem"),
            spacing="2",
        ),
        rx.hstack(
            rx.checkbox(checked=AppState.poi_show_source_tf_badge, on_change=AppState.toggle_poi_show_source_tf_badge),
            rx.text("Show source TF badge", font_size="0.78rem"),
            spacing="2",
        ),
        rx.hstack(
            rx.checkbox(checked=AppState.poi_show_logical_id, on_change=AppState.toggle_poi_show_logical_id),
            rx.text("Show logical ID in tooltip", font_size="0.78rem"),
            spacing="2",
        ),
        rx.hstack(
            rx.checkbox(checked=AppState.poi_reduced_motion, on_change=AppState.toggle_poi_reduced_motion),
            rx.text("Reduced motion", font_size="0.78rem"),
            spacing="2",
        ),
        rx.vstack(
            rx.text(f"Line transparency: {AppState.poi_line_transparency}%", font_size="0.78rem"),
            rx.slider(
                default_value=[AppState.poi_line_transparency],
                on_value_commit=AppState.set_poi_line_transparency,
                min=0, max=100, width="100%",
            ),
            spacing="1", width="100%",
        ),
        rx.vstack(
            rx.text(f"Zone opacity: {AppState.poi_zone_opacity}%", font_size="0.78rem"),
            rx.slider(
                default_value=[AppState.poi_zone_opacity],
                on_value_commit=AppState.set_poi_zone_opacity,
                min=0, max=100, width="100%",
            ),
            spacing="1", width="100%",
        ),
        spacing="3", width="100%",
    )


def _poi_bulk_controls_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Bulk Controls", size="3"),
        rx.flex(
            rx.button("Show All POIs", on_click=AppState.poi_show_all, size="2", variant="soft"),
            rx.button("Hide All POIs", on_click=AppState.poi_hide_all, size="2", variant="soft"),
            rx.button("Enable Default Strategy POIs", on_click=AppState.poi_enable_default_strategy, size="2", variant="soft"),
            rx.button("Disable All Strategy POIs", on_click=AppState.poi_disable_all_strategy, size="2", variant="soft"),
            rx.button("Reset Chart POI Filters", on_click=AppState.poi_reset_chart_filters, size="2", variant="soft"),
            spacing="2", wrap="wrap",
        ),
        spacing="2", width="100%",
    )


def poi_engine_settings_card() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("POI Engine & Chart Visibility", size="4"),
            rx.cond(
                AppState.poi_backend_busy,
                rx.badge("Applying...", variant="soft", color_scheme="amber"),
            ),
            justify="between", width="100%", align_items="center",
        ),
        rx.text("Controls every POI type shown here independently of whether it's used for "
                "setup detection - Display and Strategy never affect each other. Toggles "
                "respond instantly; the backend recompute (real network calls) finishes a "
                "moment later in the background.",
                font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.cond(
            AppState.poi_settings_loaded,
            rx.vstack(
                _poi_lines_section(),
                rx.divider(),
                _poi_zone_matrix_section(),
                rx.divider(),
                _poi_zone_types_section(),
                rx.divider(),
                _poi_vertical_markers_section(),
                rx.divider(),
                _poi_visual_controls_section(),
                rx.divider(),
                _poi_bulk_controls_section(),
                spacing="4", width="100%", margin_top="0.5rem",
            ),
            rx.text("Loading POI settings...", font_size="0.8rem", color="var(--qt19-text-muted)", margin_top="0.5rem"),
        ),
        spacing="3", width="100%", style=GLASS_CARD_3XL_STYLE,
        on_mount=AppState.load_poi_settings,
    )
