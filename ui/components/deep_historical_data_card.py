"""
FULL PATH: ui/components/deep_historical_data_card.py  (REPLACE ENTIRE FILE)

FIX v0.4.40 - "confirm dialog renders BEHIND the Gold card" (a real CSS
stacking-context bug, not a z-index number problem): the confirm dialog
was a plain rx.box with position="fixed" and z_index="9999". That normally
puts it on top of everything - EXCEPT when an ancestor element establishes
its own new CSS stacking context (which glassmorphism cards typically do,
via backdrop-filter/transform in GLASS_CARD_STYLE). Once that happens, a
descendant's position:fixed + z-index is only compared against siblings
INSIDE that same stacking context - it can no longer out-rank a sibling
card that sits in a later, separate stacking context on the page, no
matter how high its z-index number is.

Fixed by converting _confirm_dialog into a real, CONTROLLED
rx.alert_dialog.root(open=..., on_open_change=...) - exactly like the
already-correct Delete confirmation dialog on this same page. Radix's
alert_dialog renders its content in a React portal attached directly to
<body>, completely outside any card's stacking context, so it always
renders above everything regardless of what any ancestor card's CSS does.
No trigger button is needed since it's a controlled dialog - it opens
automatically from AppState.handle_duration_keydown() setting
confirm_open=True (see deep_history_card_mixin.py), exactly as before.

CHANGE v0.4.17 (unchanged): Enter key inside the duration input starts the
download directly; Delete requires an explicit confirm dialog.

CHANGE v0.4.16 (unchanged): all hover-card color values remain hardcoded -
Radix portals do not inherit CSS custom properties scoped elsewhere in the
DOM.
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE


_STATE_FILL_COLOR = {
    "downloading": "#1E8FFF",
    "queued": "#6B7280",
    "paused": "#FF8C00",
    "complete": "#16C784",
    "broker_ceiling": "#16C784",
    "incomplete": "#16C784",
    "error": "#EA3943",
    "idle": "#16C784",
}


_CARD_BG = "#0E1712"
_CARD_BORDER = "rgba(120, 200, 150, 0.35)"
_TEXT_PRIMARY = "#E8F5EC"
_TEXT_MUTED = "#93A9A0"
_GREEN = "#16C784"
_BLUE = "#1E8FFF"
_RED = "#EA3943"



def _gap_marker(gap: dict) -> rx.Component:
    return rx.box(
        position="absolute",
        left=f"{gap['left_pct']}%",
        width=f"{gap['width_pct']}%",
        top="0",
        height="100%",
        background=_RED,
        opacity="0.9",
    )



def _gap_line(label: str) -> rx.Component:
    return rx.text(label, font_size="0.72rem", color=_TEXT_PRIMARY, padding_y="0.1rem")



def _hover_card_content(item: dict, symbol: str) -> rx.Component:
    return rx.vstack(
        rx.text(f"{symbol} - {item['tf']}", font_weight="800", font_size="0.85rem", color=_TEXT_PRIMARY),
        rx.divider(),
        rx.text("PRESENT DATA", font_size="0.65rem", font_weight="700", color=_GREEN, letter_spacing="0.05em"),
        rx.text(item["present_range_label"], font_size="0.75rem", color=_TEXT_PRIMARY),
        rx.text(f"Total: {item['db_label']}", font_size="0.72rem", color=_TEXT_MUTED),
        rx.divider(),
        rx.text("BROKER CEILING", font_size="0.65rem", font_weight="700", color=_BLUE, letter_spacing="0.05em"),
        rx.text(item["broker_label"], font_size="0.75rem", color=_TEXT_PRIMARY),
        rx.divider(),
        rx.text("GAP DATA", font_size="0.65rem", font_weight="700", color=_RED, letter_spacing="0.05em"),
        rx.cond(
            item["has_gap"],
            rx.vstack(
                rx.foreach(item["gap_labels"], _gap_line),
                spacing="0", width="100%",
            ),
            rx.text("No gaps detected", font_size="0.72rem", color=_TEXT_MUTED),
        ),
        rx.cond(
            item["is_busy"],
            rx.box(
                rx.divider(),
                rx.hstack(
                    rx.spinner(size="1"),
                    rx.text(item["eta_label"], font_size="0.72rem", font_weight="700", color=_BLUE),
                    spacing="2", align_items="center",
                ),
                width="100%",
            ),
        ),
        spacing="1",
        width="260px",
        max_height="240px",
        overflow_y="auto",
        padding="0.75rem",
        align_items="stretch",
        background=_CARD_BG,
    )



def _mini_bar(item: dict, symbol: str) -> rx.Component:
    fill_color = rx.match(
        item["state"],
        ("downloading", _STATE_FILL_COLOR["downloading"]),
        ("queued", _STATE_FILL_COLOR["queued"]),
        ("paused", _STATE_FILL_COLOR["paused"]),
        ("error", _STATE_FILL_COLOR["error"]),
        _STATE_FILL_COLOR["idle"],
    )
    bar = rx.box(
        rx.box(
            width=f"{item['green_pct']}%",
            height="100%",
            background=fill_color,
            transition="width 0.6s ease, background 0.3s ease",
        ),
        rx.foreach(item["gaps"], _gap_marker),
        rx.cond(
            item["broker_probed"],
            rx.box(
                position="absolute", right="0", top="0", height="100%", width="2px",
                background="rgba(255,255,255,0.75)",
            ),
        ),
        position="relative",
        width="100%",
        height="14px",
        background="rgba(120,140,170,0.16)",
        border_radius="4px",
        overflow="hidden",
    )
    return rx.hover_card.root(
        rx.hover_card.trigger(
            rx.vstack(
                rx.hstack(
                    rx.text(item["tf"], font_size="0.65rem", font_weight="700", color="var(--qt19-text-muted)"),
                    rx.cond(
                        item["has_gap"],
                        rx.box(width="6px", height="6px", border_radius="9999px", background="#EA3943"),
                    ),
                    spacing="1", align_items="center",
                ),
                bar,
                rx.text(item["db_label"], font_size="0.6rem", color="var(--qt19-text-muted)"),
                rx.cond(
                    item["is_busy"],
                    rx.hstack(
                        rx.spinner(size="1"),
                        rx.text(item["eta_label"], font_size="0.58rem", color="var(--qt19-accent)", font_weight="700"),
                        spacing="1", align_items="center",
                    ),
                ),
                spacing="1",
                width="100%",
                align_items="stretch",
            ),
        ),
        rx.hover_card.content(
            _hover_card_content(item, symbol),
            style={
                "background": _CARD_BG,
                "border": f"1px solid {_CARD_BORDER}",
                "border-radius": "0.7rem",
                "box-shadow": "0 10px 30px rgba(0,0,0,0.5)",
            },
        ),
    )



def _duration_control(row: dict) -> rx.Component:
    return rx.hstack(
        rx.input(
            value=row["duration_value"],
            on_change=lambda v: AppState.set_card_duration_value(row["symbol"], v),
            on_key_down=lambda key: AppState.handle_duration_keydown(row["symbol"], key),
            width="60px",
            size="1",
        ),
        rx.select(
            ["Days", "Months", "Years"],
            value=row["duration_unit"],
            on_change=lambda v: AppState.set_card_duration_unit(row["symbol"], v),
            size="1",
            width="90px",
        ),
        rx.text("(press Enter)", font_size="0.62rem", color="var(--qt19-text-muted)"),
        spacing="1", align_items="center",
    )



def _confirm_dialog(row: dict) -> rx.Component:
    """Real, controlled, portaled dialog - fixes v0.4.40's stacking-context
    bug. Opens automatically when row["confirm_open"] is True (set by
    AppState.handle_duration_keydown) - no visible trigger button needed."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Confirm Download Duration"),
            rx.alert_dialog.description(
                row["confirm_message"],
                white_space="pre-wrap",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", size="2", variant="outline",
                              on_click=AppState.cancel_download_confirm(row["symbol"])),
                ),
                rx.alert_dialog.action(
                    rx.button("Proceed Anyway", size="2", variant="solid",
                              on_click=AppState.confirm_download_proceed(row["symbol"])),
                ),
                spacing="3", justify="end", margin_top="0.75rem", width="100%",
            ),
            style={"background": _CARD_BG, "border": f"1px solid {_CARD_BORDER}", "color": _TEXT_PRIMARY},
        ),
        open=row["confirm_open"],
        on_open_change=lambda is_open: AppState.cancel_download_confirm(row["symbol"]),
    )



def _delete_confirm_button(symbol: str) -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.button("Delete", size="1", variant="outline", color_scheme="red"),
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title(f"Delete all local data for {symbol}?"),
            rx.alert_dialog.description(
                "This permanently removes every downloaded 1m/5m/15m candle for this symbol "
                "from the local database. This cannot be undone. Other symbols are not affected."
            ),
            rx.hstack(
                rx.alert_dialog.cancel(rx.button("Cancel", variant="outline")),
                rx.alert_dialog.action(
                    rx.button("Delete Permanently", color_scheme="red",
                              on_click=AppState.delete_symbol_history(symbol)),
                ),
                spacing="3", justify="end", margin_top="0.75rem",
            ),
            style={"background": _CARD_BG, "border": f"1px solid {_CARD_BORDER}", "color": _TEXT_PRIMARY},
        ),
    )



def _combined_progress(row: dict) -> rx.Component:
    return rx.cond(
        row["combined_active"],
        rx.hstack(
            rx.spinner(size="1"),
            rx.progress(value=row["combined_percent"], max=100, width="100%", height="6px"),
            rx.text(f"{row['combined_percent']}%", font_size="0.65rem", color="var(--qt19-accent)", font_weight="700"),
            spacing="2", align_items="center", width="100%",
        ),
    )



def _symbol_card(row: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(row["symbol"], font_weight="700", font_size="0.95rem", color="var(--qt19-text-primary)"),
                rx.spacer(),
                _duration_control(row),
                rx.button("Cancel", size="1", variant="outline",
                          on_click=AppState.cancel_symbol_downloads(row["symbol"])),
                _delete_confirm_button(row["symbol"]),
                width="100%",
                align_items="center",
                spacing="2",
                wrap="wrap",
            ),
            _combined_progress(row),
            rx.hstack(
                rx.foreach(row["tfs"], lambda item: _mini_bar(item, row["symbol"])),
                width="100%",
                spacing="3",
                align_items="stretch",
            ),
            _confirm_dialog(row),
            spacing="3",
            width="100%",
        ),
        style=GLASS_CARD_STYLE,
        width="100%",
        padding="0.9rem 1.1rem",
    )



def deep_historical_data_card() -> rx.Component:
    return rx.vstack(
        rx.text("Deep Historical Data", font_weight="700", font_size="1.1rem", color="var(--qt19-text-primary)"),
        rx.text(
            "Type a duration and press Enter to download 1m/5m/15m together for that symbol only "
            "- other symbols are never affected. If your entry is smaller than data already "
            "present, you'll get a clear confirmation first (nothing is ever deleted by entering a "
            "smaller number). Bars show % of the broker ceiling present locally (white tick = "
            "ceiling reference, refreshed automatically every 30 minutes). Gaps heal automatically "
            "in the background - a spinner and ETA appear whenever a timeframe is active. Hover a "
            "bar for a full scrollable breakdown. Delete requires explicit confirmation.",
            font_size="0.78rem", color="var(--qt19-text-muted)",
        ),
        rx.grid(
            rx.foreach(AppState.deep_history_symbol_cards, _symbol_card),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="3",
            width="100%",
            margin_top="0.5rem",
        ),
        style=GLASS_CARD_STYLE, width="100%", spacing="3", padding="1.25rem",
    )
