"""Settings tab - App-Shell placeholder page, with Transition Effects + Tab Switch Animation.

PATH: ui/pages/settings.py  (REPLACE ENTIRE FILE)

CHANGE: added a second, independent card - "Tab Switch Animation" - controlling the
Dashboard <-> Trading Panel <-> Journal & Reports <-> Alerts <-> Settings tab-change effect,
separate from the Login->Dashboard screen-entrance pool above it. Reuses the same
AppState.transition_effect_options catalog and single/sequential/shuffle mode pattern, just
bound to the tab_transition_* state instead of transition_*.
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


def _tab_effect_checkbox(opt: dict[str, str]) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.tab_transition_effects_enabled.contains(opt["key"]),
            on_change=lambda checked: AppState.toggle_tab_transition_effect(opt["key"], checked),
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


def _tab_transition_section() -> rx.Component:
    return rx.vstack(
        rx.heading("Tab Switch Animation", size="4"),
        rx.text("Controls the effect used when switching between Dashboard, Trading Panel, "
                "Journal & Reports, Alerts, and Settings.",
                font_size="0.8rem", color="var(--qt19-text-muted)"),
        rx.hstack(
            rx.text("Mode:", font_size="0.82rem", font_weight="600"),
            rx.select(
                ["single", "sequential", "shuffle"],
                value=AppState.tab_transition_mode,
                on_change=AppState.set_tab_transition_mode,
                width="180px",
            ),
            spacing="3", align_items="center",
        ),
        rx.grid(
            rx.foreach(AppState.transition_effect_options, _tab_effect_checkbox),
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
                "land module-by-module; the Transition Effects sections below are wired now.",
                color="var(--qt19-text-muted)", font_size="0.85rem",
            ),
            style=GLASS_CARD_3XL_STYLE, width="100%", margin_top="1rem",
        ),
        _transition_effects_section(),
        _tab_transition_section(),
        width="100%", spacing="3",
    )