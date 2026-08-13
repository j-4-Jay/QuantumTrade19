from __future__ import annotations
import reflex as rx
from state.app_state import AppState

def _icon_for_tab(tab_name):
    return rx.match(tab_name, ("Dashboard","layout-dashboard"), ("Trading Panel","candlestick-chart"),
        ("Journal & Reports","book-text"), ("Alerts","bell"), ("Settings","settings"), "circle")

def _tab_button(tab_name):
    is_active = AppState.active_tab == tab_name
    return rx.button(
        rx.hstack(rx.icon(_icon_for_tab(tab_name), size=18), rx.text(tab_name, font_size="0.85rem", font_weight="600"), spacing="3"),
        on_click=AppState.set_active_tab(tab_name), width="100%", justify_content="start",
        style=rx.cond(is_active,
            {"background":"var(--qt19-accent)","color":"white","box_shadow":"0 0 16px 2px var(--qt19-accent-glow)","border_radius":"9999px"},
            {"background":"transparent","color":"var(--qt19-text-muted)","border_radius":"9999px"}))

def qt19_sidebar():
    return rx.vstack(rx.foreach(AppState.sidebar_tabs, _tab_button), rx.spacer(),
        height="100%", padding="1rem", spacing="2",
        style={"background":"var(--qt19-glass-bg)","backdrop_filter":"blur(18px)","border_right":"1px solid var(--qt19-glass-border)","width":"230px","min_width":"230px"})
