from __future__ import annotations
import reflex as rx
from config.settings import APP_SUBHEADING, LOGO_IMAGE_PATH

def qt19_brand(size="md"):
    dims = {"sm": ("32px","1rem"), "md": ("48px","1.35rem"), "lg": ("80px","2rem")}
    logo_px, word_px = dims.get(size, dims["md"])
    return rx.hstack(
        rx.image(src=LOGO_IMAGE_PATH, width=logo_px, height=logo_px,
                  style={"filter":"drop-shadow(0 0 10px var(--qt19-accent-glow, #8FCBFF))"}, alt="QuantumTrade19 logo"),
        rx.vstack(
            rx.hstack(
                rx.text("QuantumTrade", font_weight="800", font_size=word_px, color="inherit"),
                rx.text("19", font_weight="800", font_size=word_px, color="var(--qt19-accent, #1E8FFF)",
                         style={"text_shadow":"0 0 10px var(--qt19-accent-glow, #8FCBFF)"}),
                spacing="0"),
            rx.text(APP_SUBHEADING, font_size="0.7rem", opacity="0.75"),
            spacing="0", align_items="start"),
        spacing="3", align_items="center")
