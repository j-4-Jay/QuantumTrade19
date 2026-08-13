"""Settings tab - App-Shell placeholder page, now with a real Transition Effects section.

PATH: ui/pages/settings.py  (REPLACE ENTIRE FILE)

Lets you pick which of the 10 Login->Dashboard animations are active, and whether to always
use a single one, cycle through them in order, or pick one at random each time.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_3XL_STYLE, PILL_BUTTON_STYLE


def _effect_checkbox(opt: dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.transition_effects_enabled.contains(opt["key"]),
            on_change=lambda checked: AppState.toggle_transition_effect(opt["key"], checked),
        ),
        rx.text(opt["label"], font_size="0.82rem"),
        spacing="2", align_items="center", width="100%",
    )


def _transition_effects_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Login \u2192 Dashboard Transition", size="4"),
        rx.text("Pick which entrance animations are allowed, and how they're chosen each time you log in.",
                font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.hstack(
            rx.text("Mode:", font_size="0.82rem", font_weight="600"),
            rx.select(
                ["single", "sequential", "shuffle"],
                value=AppState.transition_mode,
                on_change=AppState.set_transition_mode,
                width="180px",
            ),
            spacing="3", align_items="center",
        ),
        rx.grid(
            rx.foreach(AppState.transition_effect_options, _effect_checkbox),
            columns="2", spacing="2", width="100%", margin_top="0.5rem",
        ),
        spacing="3", width="100%",
        style={**GLASS_CARD_3XL_STYLE, "margin_top": "1rem"},
    )


def settings_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Settings", size="6"),
        rx.box(
            rx.text(
                "Full settings cards (POI, Security, Sound, Theme, Deep Historical Data, etc.) "
                "land module-by-module; the Transition Effects section below is wired now.",
                color="var(--qt19-text-muted)", font_size="0.85rem",
            ),
            style=GLASS_CARD_3XL_STYLE, width="100%", margin_top="1rem",
        ),
        _transition_effects_section(),
        width="100%", spacing="3",
    )
