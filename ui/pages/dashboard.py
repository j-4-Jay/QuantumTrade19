"""Dashboard tab - shell scaffold per locked mockup: pinned cards + main table + footer.

PATH: ui/pages/dashboard.py  (REPLACE ENTIRE FILE)

FIX: the table's header/cell text now explicitly uses `var(--qt19-text-primary)` instead of
Radix's own default header color. Radix's table components carry their own internal color
tokens that aren't wired to our theme system, so on light Day themes (white-ish glass card)
the header text was staying a fixed shade that nearly disappeared against the background.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE

_PINNED = ["Gold", "ETHUSD", "BTCUSD"]
_COLUMNS = ["Trade Allowed", "Instrument", "Trend", "Liquidity TF", "Interaction", "Risk", "Bias", "Confidence Score"]


def _pinned_card(name: str) -> rx.Component:
    return rx.vstack(
        rx.text(name, font_weight="700", font_size="1rem", color="var(--qt19-text-primary)"),
        rx.text("-- awaiting Market Data Monitor --", font_size="0.7rem", color="var(--qt19-text-muted)"),
        style=GLASS_CARD_STYLE, min_width="180px",
        on_click=lambda: AppState.open_detail_popup(name), cursor="pointer",
    )


def _header_cell(label: str) -> rx.Component:
    return rx.table.column_header_cell(label, color="var(--qt19-text-primary)", font_weight="700")


def _body_cell() -> rx.Component:
    return rx.table.cell("--", color="var(--qt19-text-primary)")


def dashboard_page() -> rx.Component:
    return rx.vstack(
        rx.hstack(*[_pinned_card(n) for n in _PINNED], spacing="4"),
        rx.box(
            rx.table.root(
                rx.table.header(rx.table.row(*[_header_cell(c) for c in _COLUMNS])),
                rx.table.body(rx.table.row(*[_body_cell() for _ in _COLUMNS])),
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
