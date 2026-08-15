"""Dashboard tab - shell scaffold per locked mockup: pinned cards + main table + footer.

PATH: ui/pages/dashboard.py (REPLACE ENTIRE FILE)

FIX: clicking the favorite star no longer opens the Symbol Detail popup.
Uses rx.stop_propagation so the star's click event never bubbles up to
the row's on_click handler -- clicking anywhere else in the row still
opens the popup as before.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE

_PINNED = ["Gold", "ETHUSD", "BTCUSD"]
_COLUMNS = ["Fav", "Trade Allowed", "Instrument", "Trend", "Liquidity TF", "Interaction", "Risk", "Bias", "Confidence Score"]


def _pinned_card(name: str) -> rx.Component:
    return rx.vstack(
        rx.text(name, font_weight="700", font_size="1rem", color="var(--qt19-text-primary)"),
        rx.text(
            AppState.pinned_prices.get(name, "--"),
            font_size="1.1rem", font_weight="600", color="var(--qt19-text-primary)",
        ),
        style=GLASS_CARD_STYLE, min_width="180px",
        on_click=lambda: AppState.open_detail_popup(name), cursor="pointer",
    )


def _header_cell(label: str) -> rx.Component:
    return rx.table.column_header_cell(label, color="var(--qt19-text-primary)", font_weight="700")


def _favorite_star(row: dict) -> rx.Component:
    return rx.box(
        rx.icon(
            "star",
            fill=rx.cond(row["is_favorite"], "#FFD700", "none"),
            color=rx.cond(row["is_favorite"], "#FFD700", "var(--qt19-text-muted)"),
            size=18,
        ),
        cursor="pointer",
        on_click=[AppState.toggle_favorite(row["symbol"]), rx.stop_propagation],
    )


def _symbol_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(_favorite_star(row)),
        rx.table.cell("--", color="var(--qt19-text-primary)"),
        rx.table.cell(row["symbol"], color="var(--qt19-text-primary)", font_weight="600"),
        rx.table.cell("--", color="var(--qt19-text-primary)"),
        rx.table.cell("--", color="var(--qt19-text-primary)"),
        rx.table.cell("--", color="var(--qt19-text-primary)"),
        rx.table.cell("--", color="var(--qt19-text-primary)"),
        rx.table.cell("--", color="var(--qt19-text-primary)"),
        rx.table.cell("--", color="var(--qt19-text-primary)"),
        on_click=lambda: AppState.open_detail_popup(row["symbol"]),
        cursor="pointer",
    )


def dashboard_page() -> rx.Component:
    return rx.vstack(
        rx.hstack(*[_pinned_card(n) for n in _PINNED], spacing="4"),
        rx.box(
            rx.table.root(
                rx.table.header(rx.table.row(*[_header_cell(c) for c in _COLUMNS])),
                rx.table.body(rx.foreach(AppState.symbol_rows, _symbol_row)),
                width="100%",
            ),
            style=GLASS_CARD_STYLE, width="100%", margin_top="1.25rem",
        ),
        rx.hstack(
            rx.input(placeholder="Search symbol...", border_radius="1rem", width="240px"),
            rx.spacer(),
            rx.text("Live date/time --:--:--", font_size="0.75rem", color="var(--qt19-text-muted)"),
            width="100%", margin_top="1rem",
        ),
        width="100%", spacing="4",
    )
