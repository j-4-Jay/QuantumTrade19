"""
FULL PATH: ui/components/deep_historical_data_card.py   <-- SAVE HERE, EXACT PATH

Settings card: numeric day-count input, with clear labels for the real
discovered ceiling and what is already downloaded, so the user can make
an informed choice.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE

_TIMEFRAME_OPTIONS = ["1m", "5m", "15m"]


def deep_historical_data_card() -> rx.Component:
    return rx.vstack(
        rx.text("Deep Historical Data", font_weight="700", font_size="1.1rem", color="var(--qt19-text-primary)"),
        rx.text(
            "Downloads extra candle history beyond the always-on 5-day baseline, "
            "purely to build a local archive for future ML/RL training. Never competes "
            "with live trading for API priority.",
            font_size="0.8rem", color="var(--qt19-text-muted)",
        ),

        rx.hstack(
            rx.text("Symbol:", font_size="0.85rem", color="var(--qt19-text-primary)"),
            rx.input(
                value=AppState.deep_history_symbol,
                on_change=AppState.set_deep_history_symbol,
                width="160px", border_radius="0.75rem",
            ),
            rx.text("Timeframe:", font_size="0.85rem", color="var(--qt19-text-primary)"),
            rx.select(
                _TIMEFRAME_OPTIONS,
                value=AppState.deep_history_timeframe,
                on_change=AppState.set_deep_history_timeframe,
                width="100px",
            ),
            spacing="3", align_items="center",
        ),

        rx.hstack(
            rx.vstack(
                rx.text("Real ceiling (actual max CoinDCX offers)", font_size="0.75rem", color="var(--qt19-text-muted)"),
                rx.text(AppState.deep_history_ceiling_days, font_weight="700", font_size="1rem", color="var(--qt19-accent)"),
                spacing="1", align_items="start",
            ),
            rx.vstack(
                rx.text("Already downloaded & saved", font_size="0.75rem", color="var(--qt19-text-muted)"),
                rx.text(f"{AppState.deep_history_covered_days} days", font_weight="700", font_size="1rem", color="var(--qt19-text-primary)"),
                spacing="1", align_items="start",
            ),
            rx.button(
                "Check Real Ceiling", on_click=AppState.check_deep_history_ceiling,
                size="2", variant="outline", border_radius="9999px",
            ),
            spacing="6", align_items="start", margin_top="0.5rem",
        ),

        rx.hstack(
            rx.text("Download this many extra days:", font_size="0.85rem", color="var(--qt19-text-primary)"),
            rx.input(
                placeholder="e.g. 365 (blank = download all, up to the real ceiling)",
                value=AppState.deep_history_target_days,
                on_change=AppState.set_deep_history_target_days,
                width="320px", border_radius="0.75rem", type="number",
            ),
            spacing="3", align_items="center", margin_top="0.5rem",
        ),

        rx.hstack(
            rx.button(
                rx.cond(AppState.deep_history_is_downloading, "Downloading...", "Start Download"),
                on_click=AppState.start_deep_history_download,
                disabled=AppState.deep_history_is_downloading,
                border_radius="9999px", style={"background": "var(--qt19-accent)", "color": "white"},
            ),
            rx.button(
                "Cancel", on_click=AppState.cancel_deep_history_download,
                disabled=~AppState.deep_history_is_downloading,
                variant="outline", border_radius="9999px",
            ),
            rx.button(
                "Delete Downloaded Data", on_click=AppState.delete_deep_history_data,
                variant="outline", color_scheme="red", border_radius="9999px",
            ),
            spacing="3", margin_top="0.75rem",
        ),

        rx.text(AppState.deep_history_status_message, font_size="0.78rem", color="var(--qt19-text-muted)", margin_top="0.3rem"),

        style=GLASS_CARD_STYLE, width="100%", spacing="3", padding="1.25rem",
    )
