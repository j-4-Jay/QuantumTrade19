from __future__ import annotations
import reflex as rx

def qt19_password_field(placeholder, value, on_change, show_value, on_toggle_show):
    eye_style = {
        "background": "transparent",
        "box_shadow": "none",
        "cursor": "pointer",
        "color": "rgba(234,244,255,0.6)",
        "_hover": {"background": "transparent", "color": "#ffffff"},
        "_active": {"background": "transparent"},
        "_focus_visible": {"background": "transparent", "outline": "1px solid rgba(30,143,255,0.6)"},
    }
    return rx.input(
        rx.input.slot(
            rx.icon_button(
                rx.cond(show_value, rx.icon("eye-off", size=16), rx.icon("eye", size=16)),
                on_click=on_toggle_show, type="button", variant="ghost", size="1", style=eye_style,
            ),
            side="right",
        ),
        placeholder=placeholder, type=rx.cond(show_value, "text", "password"), value=value, on_change=on_change,
        border_radius="1rem", width="100%",
    )
