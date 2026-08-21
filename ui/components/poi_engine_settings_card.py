"""File 03.1 Scope E - POI Engine & Chart Visibility Settings card.

PATH: ui/components/poi_engine_settings_card.py (REPLACE ENTIRE FILE)

CHANGE: added a small "Applying..." status badge bound to
AppState.poi_backend_busy, so it's visible that the checkbox itself responds
instantly while the real backend recompute (genuine network I/O) finishes
in the background - not a freeze.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_3XL_STYLE


def _poi_line_row(row: dict) -> rx.Component:
    return rx.hstack(
        rx.text(row["label"], font_size="0.82rem", font_weight="600", width="90px"),
        rx.vstack(
            rx.text("High", font_size="0.7rem", color="var(--qt19-text-muted)"),
            rx.hstack(
                rx.checkbox(
                    checked=row["high_display"],
                    on_change=lambda checked: AppState.toggle_poi_display(row["high_type"], checked),
                ),
                rx.text("Display", font_size="0.72rem"),
                rx.checkbox(
                    checked=row["high_strategy"],
                    on_change=lambda checked: AppState.toggle_poi_strategy(row["high_type"], checked),
                ),
                rx.text("Strategy", font_size="0.72rem"),
                spacing="2",
            ),
            spacing="1", align_items="start",
        ),
        rx.vstack(
            rx.text("Low", font_size="0.7rem", color="var(--qt19-text-muted)"),
            rx.hstack(
                rx.checkbox(
                    checked=row["low_display"],
                    on_change=lambda checked: AppState.toggle_poi_display(row["low_type"], checked),
                ),
                rx.text("Display", font_size="0.72rem"),
                rx.checkbox(
                    checked=row["low_strategy"],
                    on_change=lambda checked: AppState.toggle_poi_strategy(row["low_type"], checked),
                ),
                rx.text("Strategy", font_size="0.72rem"),
                spacing="2",
            ),
            spacing="1", align_items="start",
        ),
        spacing="4", width="100%", padding_y="0.3rem",
        border_bottom="1px solid var(--qt19-glass-border)",
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


def _poi_lines_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Previous High/Low Lines", size="3"),
        rx.text("One row per source timeframe. Display controls what appears on the chart; "
                "Strategy controls eligibility for setup detection.",
                font_size="0.78rem", color="var(--qt19-text-muted)"),
        rx.vstack(rx.foreach(AppState.poi_line_rows, _poi_line_row), spacing="1", width="100%", margin_top="0.5rem"),
        spacing="2", width="100%",
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
