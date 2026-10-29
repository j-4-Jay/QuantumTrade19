"""Bottom trade-details card of the Trading Panel (FT-U.4.2).

PATH: ui/components/trading_bottom_panel.py  (NEW FILE)

A frosted-glass card under the chart row. It squeezes the chart height (it does
not float). Its height is read from the CSS variable --qt19-bottom-h (default
220px, 120px to 60% of the window); a divider above it is dragged to resize
and double-clicked to reset. When closed it takes no space and only one round
glowing handle stays at the bottom centre of the chart.
The table is a placeholder until paper trades exist.
"""
from __future__ import annotations

import reflex as rx

from state.app_state import AppState
from ui.components.glow_card import qt19_glow_card
from ui.theme.glass import GLASS_CARD_STYLE, SQUARE_HANDLE_STYLE

_BOTTOM_JS = """(function(){
  if(window.__qt19Bottom){window.__qt19Bottom.restore();return;}
  var K='qt19_bottom_h',root=document.documentElement,drag=null,DEF=220;
  function maxH(){return Math.floor(window.innerHeight*0.6);}
  function setH(h){h=Math.max(120,Math.min(maxH(),h));root.style.setProperty('--qt19-bottom-h',h+'px');return h;}
  function curH(){var v=parseFloat(root.style.getPropertyValue('--qt19-bottom-h'));return isNaN(v)?DEF:v;}
  function restore(){var v=parseFloat(localStorage.getItem(K));if(!isNaN(v))setH(v);}
  document.addEventListener('pointerdown',function(e){
    var d=e.target.closest?e.target.closest('#qt19-bottom-divider'):null;if(!d)return;
    drag={y0:e.clientY,h0:curH()};root.classList.add('qt19-dragging');
    try{d.setPointerCapture(e.pointerId);}catch(x){}
    e.preventDefault();
  },true);
  document.addEventListener('pointermove',function(e){
    if(!drag)return;setH(drag.h0-(e.clientY-drag.y0));
  },true);
  function end(){if(!drag)return;drag=null;root.classList.remove('qt19-dragging');localStorage.setItem(K,String(curH()));}
  document.addEventListener('pointerup',end,true);
  document.addEventListener('pointercancel',end,true);
  document.addEventListener('dblclick',function(e){
    var d=e.target.closest?e.target.closest('#qt19-bottom-divider'):null;if(!d)return;
    setH(DEF);localStorage.setItem(K,String(DEF));
  },true);
  window.addEventListener('resize',function(){setH(curH());});
  window.__qt19Bottom={restore:restore};
  restore();
})();"""

_COLUMNS = ["Symbol", "Side", "Entry", "SL", "RRR", "P/L (INR)", "Status"]


def _collapse_button() -> rx.Component:
    return rx.box(
        rx.icon("chevrons-down", size=18),
        on_click=AppState.toggle_bottom_panel,
        title="Close trade details",
        style={
            **SQUARE_HANDLE_STYLE,
            "width": "2.3rem",
            "height": "2.3rem",
            "display": "flex",
            "align_items": "center",
            "justify_content": "center",
            "flex_shrink": "0",
        },
    )


def _header_cell(name: str) -> rx.Component:
    return rx.text(
        name,
        flex="1",
        font_size="0.78rem",
        font_weight="800",
        color="var(--qt19-text-muted)",
    )


def _divider() -> rx.Component:
    return rx.box(
        rx.box(
            width="56px",
            height="4px",
            border_radius="9999px",
            background="var(--qt19-accent)",
            opacity="0.7",
        ),
        id="qt19-bottom-divider",
        on_mount=rx.call_script(_BOTTOM_JS),
        title="Drag to resize. Double-click to reset.",
        style={
            "height": "10px",
            "width": "100%",
            "display": "flex",
            "align_items": "center",
            "justify_content": "center",
            "cursor": "ns-resize",
            "touch_action": "none",
            "flex_shrink": "0",
        },
    )


def _card() -> rx.Component:
    body = rx.vstack(
        rx.hstack(
            rx.text("Trade details", font_size="1rem", font_weight="800"),
            rx.spacer(),
            _collapse_button(),
            width="100%",
            align_items="center",
            flex_shrink="0",
        ),
        rx.box(
            rx.vstack(
                rx.hstack(
                    *[_header_cell(name) for name in _COLUMNS],
                    width="100%",
                    padding_bottom="0.4rem",
                    border_bottom="1px solid var(--qt19-glass-border)",
                    flex_shrink="0",
                ),
                rx.text(
                    "No trades yet. Paper trades will appear here.",
                    font_size="0.85rem",
                    color="var(--qt19-text-muted)",
                ),
                width="100%",
                spacing="3",
                align_items="stretch",
            ),
            width="100%",
            flex="1",
            min_height="0",
            overflow_y="auto",
        ),
        width="100%",
        height="100%",
        spacing="3",
        align_items="stretch",
    )
    return qt19_glow_card(
        body,
        card_style={
            **GLASS_CARD_STYLE,
            "width": "100%",
            "height": "var(--qt19-bottom-h, 220px)",
            "padding": "0.75rem 1rem",
            "background": "color-mix(in srgb, var(--qt19-glass-bg) 55%, transparent)",
            "backdrop_filter": "blur(26px) saturate(180%)",
            "box_shadow": "0 12px 40px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.16)",
        },
        margin="0",
        width="100%",
        edge=True,
    )


def qt19_bottom_panel() -> rx.Component:
    return rx.box(
        rx.vstack(_divider(), _card(), width="100%", spacing="0", flex_shrink="0", padding_top="0.75rem"),
        class_name="qt19-bottom-wrap",
        width="100%",
        flex_shrink="0",
        height=rx.cond(AppState.bottom_panel_open, "calc(var(--qt19-bottom-h, 220px) + 10px + 0.75rem)", "0px"),
        transition="height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)",
    )


def qt19_bottom_handle() -> rx.Component:
    return rx.cond(
        AppState.bottom_panel_open,
        rx.fragment(),
        rx.box(
            rx.icon("chevrons-up", size=18),
            on_click=AppState.toggle_bottom_panel,
            title="Open trade details",
            style={
                **SQUARE_HANDLE_STYLE,
                "position": "absolute",
                "bottom": "0.75rem",
                "right": "0.75rem",
                "width": "2.3rem",
                "height": "2.3rem",
                "display": "flex",
                "align_items": "center",
                "justify_content": "center",
                "z_index": "25",
            },
        ),
    )
