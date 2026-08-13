from __future__ import annotations
import reflex as rx

def qt19_password_field(placeholder, value, on_change, show_value, on_toggle_show):
    return rx.box(
        rx.input(placeholder=placeholder, type=rx.cond(show_value, "text", "password"), value=value, on_change=on_change,
                  border_radius="1rem", width="100%", padding_right="2.5rem"),
        rx.icon_button(rx.icon(rx.cond(show_value, "eye-off", "eye"), size=16), on_click=on_toggle_show, variant="ghost", size="1",
                        style={"position":"absolute","right":"0.4rem","top":"50%","transform":"translateY(-50%)"}),
        position="relative", width="100%",
    )
