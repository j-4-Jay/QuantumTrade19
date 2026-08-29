"""
FULL PATH: ui/components/deep_historical_data_card.py  (REPLACE ENTIRE FILE)

CHANGE (v0.3.9): rebuilt as a pure VISUAL status monitor. Downloads can now
ONLY be started from the Trading Panel's Display Days box (per-symbol,
applies to 1m/5m/15m automatically). This card shows one real progress bar
per symbol per timeframe, color-coded by true state - queued, downloading,
paused, complete, or error - with only safety Cancel/Delete controls left,
no manual Start.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE

_STATE_COLORS = {
    "queued": "#6B7280",
    "downloading": "#1E8FFF",
    "paused": "#FF8C00",
    "complete": "#16C784",
    "error": "#EA3943",
    "idle": "#4B5563",
}
_STATE_LABELS = {
    "queued": "Queued",
    "downloading": "Downloading",
    "paused": "Paused",
    "complete": "Complete",
    "error": "Error",
    "idle": "Idle",
}


def _state_badge(row: dict) -> rx.Component:
    color = rx.match(
        row["state"],
        ("queued", _STATE_COLORS["queued"]),
        ("downloading", _STATE_COLORS["downloading"]),
        ("paused", _STATE_COLORS["paused"]),
        ("complete", _STATE_COLORS["complete"]),
        ("error", _STATE_COLORS["error"]),
        _STATE_COLORS["idle"],
    )
    label = rx.match(
        row["state"],
        ("queued", _STATE_LABELS["queued"]),
        ("downloading", _STATE_LABELS["downloading"]),
        ("paused", _STATE_LABELS["paused"]),
        ("complete", _STATE_LABELS["complete"]),
        ("error", _STATE_LABELS["error"]),
        _STATE_LABELS["idle"],
    )
    return rx.box(
        rx.text(label, font_size="0.68rem", font_weight="700", color="white", white_space="nowrap"),
        padding="0.15rem 0.6rem",
        border_radius="9999px",
        background=color,
        box_shadow=f"0 0 8px 1px {color}",
    )


def _progress_row(row: dict) -> rx.Component:
    bar_color = rx.match(
        row["state"],
        ("queued", _STATE_COLORS["queued"]),
        ("downloading", _STATE_COLORS["downloading"]),
        ("paused", _STATE_COLORS["paused"]),
        ("complete", _STATE_COLORS["complete"]),
        ("error", _STATE_COLORS["error"]),
        _STATE_COLORS["idle"],
    )
    return rx.vstack(
        rx.hstack(
            rx.text(row["symbol"], font_weight="700", font_size="0.85rem", color="var(--qt19-text-primary)"),
            rx.badge(row["tf"], variant="soft"),
            _state_badge(row),
            rx.spacer(),
            rx.text(
                f"{row['covered_label']} / {row['ceiling_label']}",
                font_size="0.75rem",
                color="var(--qt19-text-muted)",
            ),
            width="100%",
            align_items="center",
            spacing="2",
        ),
        rx.box(
            rx.box(
                width=f"{row['percent']}%",
                height="100%",
                background=bar_color,
                border_radius="9999px",
                transition="width 0.6s ease, background 0.3s ease",
            ),
            width="100%",
            height="10px",
            background="rgba(120,140,170,0.18)",
            border_radius="9999px",
            overflow="hidden",
        ),
        rx.cond(
            row["error"] != "",
            rx.text(row["error"], font_size="0.72rem", color="#EA3943", margin_top="0.1rem"),
        ),
        rx.hstack(
            rx.button(
                "Cancel",
                size="1",
                variant="outline",
                on_click=AppState.cancel_deep_history_for(row["symbol"], row["tf"]),
            ),
            rx.button(
                "Delete",
                size="1",
                variant="outline",
                color_scheme="red",
                on_click=AppState.delete_deep_history_for(row["symbol"], row["tf"]),
            ),
            spacing="2",
            margin_top="0.2rem",
        ),
        width="100%",
        spacing="1",
        padding="0.6rem 0",
        border_bottom="1px solid var(--qt19-glass-border)",
    )


def deep_historical_data_card() -> rx.Component:
    return rx.vstack(
        rx.text("Deep Historical Data", font_weight="700", font_size="1.1rem", color="var(--qt19-text-primary)"),
        rx.text(
            "Status monitor only - downloads are started from the Trading Panel's "
            "Display Last Days box (applies to 1m/5m/15m for that symbol automatically). "
            "Never competes with live trading for API priority.",
            font_size="0.8rem", color="var(--qt19-text-muted)",
        ),
        rx.vstack(
            rx.foreach(AppState.deep_history_status_rows, _progress_row),
            width="100%",
            spacing="1",
            margin_top="0.5rem",
        ),
        style=GLASS_CARD_STYLE, width="100%", spacing="3", padding="1.25rem",
    )
