"""Reusable "glass card with bulletproof hover glow" wrapper component.

PATH: ui/components/glow_card.py  (NEW FILE)

FIX v0.4.55 - see ui/theme/global_css.py's docstring for the full
explanation of why the glow needed a structurally different technique.
This component wires the three new CSS classes together correctly so you
never have to remember the pattern by hand:

    qt19_glow_card(
        *children,
        card_style=GLASS_CARD_STYLE,   # or GLASS_CARD_3XL_STYLE, or a dict
        **extra_props_for_the_wrapper, # e.g. width="100%", flex="1", etc.
    )

Produces:
    <outer wrapper class="qt19-glow-wrap" position=relative>
        <glow layer class="qt19-glow-layer">            (invisible at rest)
        <actual card class="qt19-glow-content" style=card_style>
            {children}
        </actual card>
    </outer wrapper>

The glow layer is a completely separate element from the card - it can
never be blocked by anything on the card's own style (background, border,
box-shadow, overflow) because it isn't part of that element's box at all.
"""
from __future__ import annotations

import reflex as rx


def qt19_glow_card(*children, card_style: dict, **wrapper_props) -> rx.Component:
    return rx.box(
        rx.box(class_name="qt19-glow-layer"),
        rx.box(*children, style=card_style, class_name="qt19-glow-content"),
        class_name="qt19-glow-wrap",
        **wrapper_props,
    )
