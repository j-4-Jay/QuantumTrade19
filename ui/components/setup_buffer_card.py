"""Settings card: SL buffer per symbol (File 04.1c, FT-H.3 Step B).

PATH: ui/components/setup_buffer_card.py  (NEW FILE)

Default buffer in ticks, plus one row per symbol. An empty box or Reset gives the default again.
Values are saved the moment you leave the box (same as the other Settings cards).
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState
from ui.theme.glass import SETTINGS_CARD_STYLE as GLASS_CARD_3XL_STYLE


def _symbol_row(row) -> rx.Component:
    return rx.hstack(
        rx.text(row["symbol"], font_size="0.8rem", width="9rem"),
        rx.input(
            default_value=row["ticks"],
            key=row["key"],
            on_blur=lambda v: AppState.set_sl_buffer_symbol(row["symbol"], v),
            type_="number",
            width="5.5rem",
            size="1",
        ),
        rx.text("ticks", font_size="0.74rem", color="var(--qt19-text-muted)"),
        rx.cond(
            row["custom"] == "yes",
            rx.button(
                "Reset",
                on_click=lambda: AppState.reset_sl_buffer_symbol(row["symbol"]),
                size="1",
                variant="soft",
            ),
            rx.text("default", font_size="0.72rem", color="var(--qt19-text-muted)"),
        ),
        spacing="2",
        align_items="center",
        width="100%",
    )


def setup_buffer_card() -> rx.Component:
    return rx.vstack(
        rx.heading("SL Buffer (Setup Callouts)", size="4"),
        rx.text(
            "Ticks added below Candle 1-3 (123Bull) or above (123Bear) to get the SL. "
            "Leave a symbol box empty, or press Reset, to use the default.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.hstack(
            rx.text("Default for all symbols", font_size="0.8rem", width="9rem"),
            rx.input(
                default_value=AppState.sl_buffer_default_text,
                key=AppState.sl_buffer_default_key,
                on_blur=AppState.set_sl_buffer_default,
                type_="number",
                width="5.5rem",
                size="1",
            ),
            rx.text("ticks", font_size="0.74rem", color="var(--qt19-text-muted)"),
            spacing="2",
            align_items="center",
            width="100%",
        ),
        rx.cond(
            AppState.sl_buffer_rows.length() > 0,
            rx.vstack(
                rx.foreach(AppState.sl_buffer_rows, _symbol_row),
                spacing="2",
                width="100%",
            ),
            rx.text(
                "No symbols loaded yet.",
                font_size="0.74rem", color="var(--qt19-text-muted)",
            ),
        ),
        rx.cond(
            AppState.sl_buffer_message != "",
            rx.text(AppState.sl_buffer_message, font_size="0.74rem", color="var(--qt19-text-muted)"),
            rx.fragment(),
        ),
        spacing="3",
        width="100%",
        style=GLASS_CARD_3XL_STYLE,
        on_mount=AppState.load_sl_buffer_settings,
    )
