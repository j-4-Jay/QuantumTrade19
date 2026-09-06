"""File 03.1 Scope E - POI Engine & Chart Visibility Settings cards.

PATH: ui/components/poi_engine_settings_card.py (REPLACE ENTIRE FILE)

FIX (r2 - disabled= prop needs a Var-safe expression) - `~row["display"]`
is not guaranteed to compile as boolean negation on a dict-indexed Var in
every Reflex version; replaced with the always-safe
`rx.cond(row["display"], False, True)` pattern for the disabled= prop on
every merged sub-control.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_3XL_STYLE


def _color_input(value: str, on_change) -> rx.Component:
    return rx.input(
        type="color", value=value, on_change=on_change,
        width="36px", height="28px", padding="0", border="none", cursor="pointer",
    )


def _card_header(title: str, on_reset) -> rx.Component:
    return rx.hstack(
        rx.heading(title, size="4"),
        rx.spacer(),
        rx.button("Reset", on_click=on_reset, size="1", variant="soft"),
        width="100%", align_items="center",
    )


def poi_timezone_card() -> rx.Component:
    return rx.vstack(
        _card_header("Timezone Mode", AppState.reset_poi_timezone_default),
        rx.text(
            "Controls which clock PDH/PDL and 4H lines cut their \u201cprevious period\u201d "
            "boundary on. 1m/5m/15m/1H lines and all zones are unaffected.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.segmented_control.root(
            rx.segmented_control.item("New York (auto DST)", value="NY"),
            rx.segmented_control.item("UTC", value="UTC"),
            value=AppState.poi_timezone_mode,
            on_change=AppState.set_poi_timezone_mode,
            size="2",
        ),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def _poi_tf_card(row: dict) -> rx.Component:
    """One card per timeframe - Display/Strategy/Color (always
    editable), plus the merged Duration Start/End marker, Droplet
    Display, Style, and Transparency controls - all four DISABLED until
    row["display"] is ON."""
    sub_disabled = rx.cond(row["display"], False, True)
    return rx.vstack(
        rx.hstack(
            rx.text(row["label"], font_size="0.85rem", font_weight="700"),
            rx.spacer(),
            _color_input(row["color"], lambda v: AppState.set_poi_tf_color(row["tf"], v)),
            width="100%", align_items="center",
        ),
        rx.hstack(
            rx.checkbox(checked=row["display"], on_change=lambda checked: AppState.toggle_poi_tf_display(row["tf"], checked)),
            rx.text("Display (High + Low)", font_size="0.72rem"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.hstack(
            rx.checkbox(checked=row["strategy"], on_change=lambda checked: AppState.toggle_poi_tf_strategy(row["tf"], checked)),
            rx.text("Strategy (High + Low)", font_size="0.72rem"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.divider(margin_y="0.1rem"),
        rx.hstack(
            rx.checkbox(
                checked=row["vertical_enabled"],
                disabled=sub_disabled,
                on_change=lambda checked: AppState.toggle_poi_tf_vertical(row["tf"], checked),
            ),
            rx.text("Duration Start/End Marker", font_size="0.7rem"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.hstack(
            rx.checkbox(
                checked=row["droplet_enabled"],
                disabled=sub_disabled,
                on_change=lambda checked: AppState.toggle_poi_tf_droplet(row["tf"], checked),
            ),
            rx.text("Droplet Display", font_size="0.7rem"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.hstack(
            rx.text("Style:", font_size="0.68rem", color="var(--qt19-text-muted)"),
            rx.segmented_control.root(
                rx.segmented_control.item("Dotted", value="dotted"),
                rx.segmented_control.item("Solid", value="solid"),
                value=row["vertical_style"],
                disabled=sub_disabled,
                on_change=lambda v: AppState.set_poi_tf_vertical_style(row["tf"], v),
                size="1",
            ),
            spacing="2", align_items="center", width="100%",
        ),
        rx.vstack(
            rx.text(f"Marker transparency: {row['vertical_opacity']}%", font_size="0.68rem", color="var(--qt19-text-muted)"),
            rx.slider(
                default_value=[row["vertical_opacity"]],
                disabled=sub_disabled,
                on_value_commit=lambda v: AppState.set_poi_tf_vertical_opacity(row["tf"], v),
                min=0, max=100, width="100%",
            ),
            spacing="1", width="100%",
        ),
        spacing="2", width="100%", padding="0.6rem 0.7rem",
        style={"background": "rgba(255,255,255,0.03)", "border": "1px solid var(--qt19-glass-border)", "border_radius": "0.65rem"},
    )


def poi_lines_card() -> rx.Component:
    return rx.vstack(
        _card_header("Previous High/Low Lines", AppState.reset_poi_lines_defaults),
        rx.text(
            "One card per timeframe. Display shows both High and Low together; Strategy makes "
            "both eligible for setup detection together - fully independent of Display. The "
            "Duration marker, Droplet, Style, and Transparency controls below only become "
            "editable once Display is turned ON.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.grid(
            rx.foreach(AppState.poi_tf_card_rows, _poi_tf_card),
            columns=rx.breakpoints(initial="1", sm="2", md="4"),
            spacing="3", width="100%", margin_top="0.5rem",
        ),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def poi_horizontal_style_card() -> rx.Component:
    return rx.vstack(
        _card_header("Horizontal POI Line Style", AppState.reset_poi_horizontal_style_defaults),
        rx.text(
            "One style + thickness for ALL High lines together, and a separate one for ALL Low "
            "lines together. Defaults: High = Solid 2px, Low = Solid 1px.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.grid(
            rx.vstack(
                rx.text("High Lines", font_size="0.82rem", font_weight="700"),
                rx.segmented_control.root(
                    rx.segmented_control.item("Dotted", value="dotted"),
                    rx.segmented_control.item("Solid", value="solid"),
                    value=AppState.poi_high_line_style, on_change=AppState.set_poi_high_line_style, size="1",
                ),
                rx.text(f"Thickness: {AppState.poi_high_line_thickness}px", font_size="0.76rem"),
                rx.slider(default_value=[AppState.poi_high_line_thickness], on_value_commit=AppState.set_poi_high_line_thickness, min=1, max=5, width="100%"),
                spacing="2", width="100%", padding="0.6rem 0.7rem",
                style={"background": "rgba(255,255,255,0.03)", "border": "1px solid var(--qt19-glass-border)", "border_radius": "0.65rem"},
            ),
            rx.vstack(
                rx.text("Low Lines", font_size="0.82rem", font_weight="700"),
                rx.segmented_control.root(
                    rx.segmented_control.item("Dotted", value="dotted"),
                    rx.segmented_control.item("Solid", value="solid"),
                    value=AppState.poi_low_line_style, on_change=AppState.set_poi_low_line_style, size="1",
                ),
                rx.text(f"Thickness: {AppState.poi_low_line_thickness}px", font_size="0.76rem"),
                rx.slider(default_value=[AppState.poi_low_line_thickness], on_value_commit=AppState.set_poi_low_line_thickness, min=1, max=5, width="100%"),
                spacing="2", width="100%", padding="0.6rem 0.7rem",
                style={"background": "rgba(255,255,255,0.03)", "border": "1px solid var(--qt19-glass-border)", "border_radius": "0.65rem"},
            ),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="3", width="100%", margin_top="0.5rem",
        ),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def _poi_zone_source_tf_checkbox(row: dict) -> rx.Component:
    return rx.hstack(
        rx.checkbox(checked=row["enabled"], on_change=lambda checked: AppState.toggle_poi_zone_source_tf(row["tf"], checked)),
        rx.text(row["tf"], font_size="0.78rem"),
        spacing="2", align_items="center",
    )


def poi_zone_matrix_card() -> rx.Component:
    return rx.vstack(
        _card_header("Zone Source-Timeframe Matrix", AppState.reset_poi_zone_matrix_defaults),
        rx.text(
            "Which timeframes Flip/FVG/Inverse FVG/Order Block zones are calculated from. "
            "Shared across all zone types. Always UTC-boundary based.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.grid(
            rx.foreach(AppState.poi_zone_source_tf_rows, _poi_zone_source_tf_checkbox),
            columns="4", spacing="2", width="100%", margin_top="0.5rem",
        ),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def _poi_zone_type_card(row: dict) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(row["label"], font_size="0.84rem", font_weight="700"),
            rx.spacer(),
            _color_input(row["color"], lambda v: AppState.set_poi_zone_color(row["type"], v)),
            width="100%", align_items="center",
        ),
        rx.hstack(
            rx.checkbox(checked=row["display"], on_change=lambda checked: AppState.toggle_poi_display(row["type"], checked)),
            rx.text("Display", font_size="0.72rem"),
            rx.checkbox(checked=row["strategy"], on_change=lambda checked: AppState.toggle_poi_strategy(row["type"], checked)),
            rx.text("Strategy", font_size="0.72rem"),
            spacing="2", align_items="center", width="100%", wrap="wrap",
        ),
        rx.hstack(
            rx.text("Show last:", font_size="0.72rem", color="var(--qt19-text-muted)"),
            rx.input(
                value=row["max_count"].to_string(),
                on_blur=lambda v: AppState.set_poi_zone_max_count(row["type"], v),
                width="56px", size="1", type_="number",
            ),
            rx.text("fresh zones", font_size="0.72rem", color="var(--qt19-text-muted)"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.vstack(
            rx.text(f"Transparency: {row['opacity']}%", font_size="0.7rem", color="var(--qt19-text-muted)"),
            rx.slider(
                default_value=[row["opacity"]],
                on_value_commit=lambda v: AppState.set_poi_zone_type_opacity(row["type"], v),
                min=0, max=100, width="100%",
            ),
            spacing="1", width="100%",
        ),
        spacing="2", width="100%", padding="0.6rem 0.7rem",
        style={"background": "rgba(255,255,255,0.03)", "border": "1px solid var(--qt19-glass-border)", "border_radius": "0.65rem"},
    )


def poi_zone_types_card() -> rx.Component:
    return rx.vstack(
        _card_header("Zone Types", AppState.reset_poi_zone_types_defaults),
        rx.text(
            "Only FRESH (not yet mitigated/touched) zones are ever shown. Each type has its own "
            "color, transparency, and a cap on how many of the most recent fresh zones to display "
            "(default 5) - keeps the chart readable no matter how many were historically detected.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.grid(
            rx.foreach(AppState.poi_zone_type_rows, _poi_zone_type_card),
            columns=rx.breakpoints(initial="1", sm="2", lg="3"),
            spacing="3", width="100%", margin_top="0.5rem",
        ),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def _custom_line_row(index: int) -> rx.Component:
    line = AppState.poi_custom_lines[index]
    return rx.vstack(
        rx.hstack(
            rx.checkbox(checked=line["enabled"], on_change=lambda checked: AppState.toggle_custom_line_enabled(index, checked)),
            rx.text(f"Custom Line {index + 1}", font_size="0.78rem", font_weight="600", width="110px"),
            _color_input(line["color"], lambda v: AppState.set_custom_line_color(index, v)),
            spacing="2", align_items="center", width="100%",
        ),
        rx.hstack(
            rx.input(value=line["hour12"].to_string(), on_blur=lambda v: AppState.set_custom_line_hour(index, v), placeholder="HH", width="54px", size="1", type_="number"),
            rx.text(":", font_size="0.9rem"),
            rx.input(value=line["minute"].to_string(), on_blur=lambda v: AppState.set_custom_line_minute(index, v), placeholder="MM", width="54px", size="1", type_="number"),
            rx.segmented_control.root(
                rx.segmented_control.item("AM", value="AM"),
                rx.segmented_control.item("PM", value="PM"),
                value=line["meridiem"], on_change=lambda v: AppState.set_custom_line_meridiem(index, v), size="1",
            ),
            rx.text("(New York time)", font_size="0.68rem", color="var(--qt19-text-muted)"),
            spacing="2", align_items="center", width="100%",
        ),
        rx.input(value=line["name"], on_blur=lambda v: AppState.set_custom_line_name(index, v), placeholder="Optional name shown on chart (else shows the time)", width="100%", size="1"),
        spacing="2", width="100%", padding="0.5rem 0.6rem",
        style={"background": "rgba(255,255,255,0.03)", "border": "1px solid var(--qt19-glass-border)", "border_radius": "0.6rem"},
    )


def poi_custom_lines_card() -> rx.Component:
    return rx.vstack(
        _card_header("Custom Recurring Lines", AppState.reset_poi_custom_lines_defaults),
        rx.text(
            "Up to 3 independent daily lines at a fixed time (America/New_York) - automatically "
            "reappear at the same time every day. Give one a Name to show that instead of the time.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.vstack(_custom_line_row(0), _custom_line_row(1), _custom_line_row(2), spacing="2", width="100%", margin_top="0.3rem"),
        spacing="2", width="100%", style=GLASS_CARD_3XL_STYLE,
    )


def poi_visual_controls_card() -> rx.Component:
    return rx.vstack(
        _card_header("Visual Controls", AppState.reset_poi_visual_controls_defaults),
        rx.hstack(rx.checkbox(checked=AppState.poi_show_labels, on_change=AppState.toggle_poi_show_labels), rx.text("POI labels", font_size="0.78rem"), spacing="2"),
        rx.hstack(rx.checkbox(checked=AppState.poi_show_tooltips, on_change=AppState.toggle_poi_show_tooltips), rx.text("POI tooltips", font_size="0.78rem"), spacing="2"),
        rx.hstack(rx.checkbox(checked=AppState.poi_show_source_tf_badge, on_change=AppState.toggle_poi_show_source_tf_badge), rx.text("Show source TF badge", font_size="0.78rem"), spacing="2"),
        rx.hstack(rx.checkbox(checked=AppState.poi_show_logical_id, on_change=AppState.toggle_poi_show_logical_id), rx.text("Show logical ID in tooltip", font_size="0.78rem"), spacing="2"),
        rx.hstack(rx.checkbox(checked=AppState.poi_reduced_motion, on_change=AppState.toggle_poi_reduced_motion), rx.text("Reduced motion", font_size="0.78rem"), spacing="2"),
        spacing="3", width="100%", style=GLASS_CARD_3XL_STYLE,
    )
