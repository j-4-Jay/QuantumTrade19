"""Collapsible sidebar navigation card.

PATH: ui/components/sidebar.py  (REPLACE ENTIRE FILE)

FIX (line-stage: icon instead of a decorative line) - removed the
colored decorative bar entirely. The collapsed-to-a-line stage now shows
ONE single icon button filling the whole card top-to-bottom - the entire
card IS the handle, clearly clickable, no separate thin visual element
pretending to be a "line" anymore.
"""
from __future__ import annotations
import reflex as rx
from state.app_state import AppState
from ui.theme.glass import GLASS_CARD_STYLE, SQUARE_HANDLE_STYLE
from ui.components.glow_card import qt19_glow_card

_ICON_SIZE = 27
_ICON_COL_WIDTH = "32px"
_FULL_WIDTH = "230px"
_ICONS_WIDTH = "72px"
_LINE_WIDTH = "14px"
_HANDLE_HEIGHT = "52px"
_OUTER_PADDING = "0.85rem"
_LINE_HEIGHT_TOTAL = "280px"
_LEFT_HANDLE_JS = """(function(){
  if(window.__qt19LeftHandle){window.__qt19LeftHandle.restore();return;}
  var KEY='qt19_left_handle_top',root=document.documentElement,drag=null,moved=false,suppress=false;
  function clamp(y){return Math.max(70,Math.min(window.innerHeight-24,y));}
  function setTop(y){root.style.setProperty('--qt19-left-handle-top',clamp(y)+'px');}
  function curTop(){return parseFloat(root.style.getPropertyValue('--qt19-left-handle-top'));}
  function restore(){var v=parseFloat(localStorage.getItem(KEY));if(!isNaN(v))setTop(v);}
  document.addEventListener('pointerdown',function(e){
    var h=e.target.closest?e.target.closest('#qt19-left-handle'):null;if(!h)return;
    var r=h.getBoundingClientRect();drag={y0:e.clientY,top0:r.top+r.height/2};moved=false;
    try{h.setPointerCapture(e.pointerId);}catch(x){}
  },true);
  document.addEventListener('pointermove',function(e){
    if(!drag)return;var dy=e.clientY-drag.y0;
    if(!moved&&Math.abs(dy)<5)return;moved=true;setTop(drag.top0+dy);
  },true);
  function end(){
    if(!drag)return;
    if(moved){suppress=true;setTimeout(function(){suppress=false;},60);var v=curTop();if(!isNaN(v))localStorage.setItem(KEY,String(v));}
    drag=null;
  }
  document.addEventListener('pointerup',end,true);
  document.addEventListener('pointercancel',end,true);
  document.addEventListener('click',function(e){
    if(suppress&&e.target.closest&&e.target.closest('#qt19-left-handle')){e.stopPropagation();e.preventDefault();}
  },true);
  window.addEventListener('resize',function(){var v=curTop();if(!isNaN(v))setTop(v);});
  window.__qt19LeftHandle={restore:restore};
  restore();
})();"""


def _icon_for_tab(tab_name):
    return rx.match(tab_name, ("Dashboard", "layout-dashboard"), ("Trading Panel", "candlestick-chart"),
        ("Journal & Reports", "book-text"), ("Alerts", "bell"), ("Settings", "settings"), "circle")


def _tab_button(tab_name):
    is_active = AppState.active_tab == tab_name
    icon_el = rx.icon(_icon_for_tab(tab_name), size=_ICON_SIZE)

    full_content = rx.hstack(
        rx.box(icon_el, width=_ICON_COL_WIDTH, display="flex", align_items="center", justify_content="center", flex_shrink="0"),
        rx.text(tab_name, font_size="0.95rem", font_weight="700", text_align="left", style={"text_shadow": "0 1px 8px rgba(0,0,0,0.55)"}),
        spacing="2",
        align_items="center",
        width="100%",
        justify_content="start",
    )
    icons_content = rx.center(icon_el, width="100%", height="100%")

    return rx.button(
        rx.cond(AppState.sidebar_stage == "full", full_content, icons_content),
        on_click=AppState.set_active_tab(tab_name),
        class_name="qt19-nav-btn",
        width="100%",
        height=_HANDLE_HEIGHT,
        padding=rx.cond(AppState.sidebar_stage == "full", "0 0.75rem", "0"),
        style=rx.cond(
            is_active,
            {"background": "var(--qt19-accent)", "color": "white", "box_shadow": "0 0 16px 2px var(--qt19-accent-glow)", "border_radius": "0.9rem"},
            {"background": "rgba(255,255,255,0.05)", "color": "var(--qt19-text-primary)", "border_radius": "0.9rem"},
        ),
    )


def _stage_handle_icon() -> rx.Component:
    return rx.match(
        AppState.sidebar_stage,
        ("full", rx.icon("chevrons-left", size=16)),
        ("icons", rx.icon("chevrons-left", size=16)),
        rx.icon("chevrons-right", size=16),
    )


def _stage_handle_button(height: str) -> rx.Component:
    return rx.button(
        rx.center(_stage_handle_icon(), width="100%", height="100%"),
        on_click=AppState.cycle_sidebar_stage,
        width="100%",
        height=height,
        padding="0",
        flex_shrink="0",
        variant="ghost",
        style={
            "background": "transparent",
            "color": "var(--qt19-text-muted)",
            "border_radius": "0.9rem",
            "border": "1px solid var(--qt19-glass-border)",
        },
    )


def _square_handle() -> rx.Component:
    """Round-corner stage button at the top of the sidebar (same look as the right sidebar's)."""
    return rx.box(
        _stage_handle_icon(),
        on_click=AppState.cycle_sidebar_stage,
        title="Collapse sidebar",
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


def _full_or_icons_body() -> rx.Component:
    return rx.vstack(
        rx.box(_square_handle(), width="100%", display="flex", justify_content="flex-start", flex_shrink="0"),
        rx.foreach(AppState.sidebar_tabs, _tab_button),
        width="100%",
        padding=_OUTER_PADDING,
        spacing="2",
        align_items="center",
    )


def _collapsed_handle() -> rx.Component:
    """FT-U.2a: collapsed stage ("line" in settings) = no card, no space.
    Only one round glowing handle floats on the left screen edge."""
    return rx.box(
        rx.icon("chevrons-right", size=20),
        on_click=AppState.cycle_sidebar_stage,
        title="Open sidebar",
        style={
            **SQUARE_HANDLE_STYLE,
            "position": "absolute",
            "left": "1.6rem",
            "top": "1.6rem",
            "width": "2.3rem",
            "height": "2.3rem",
            "display": "flex",
            "align_items": "center",
            "justify_content": "center",
            "z_index": "60",
        },
    )


def qt19_sidebar():
    width = rx.match(
        AppState.sidebar_stage,
        ("full", _FULL_WIDTH),
        ("icons", _ICONS_WIDTH),
        _LINE_WIDTH,
    )
    body = _full_or_icons_body()
    card = qt19_glow_card(
        body,
        card_style={
            **GLASS_CARD_STYLE,
            "width": width,
            "min_width": width,
            "background": "color-mix(in srgb, var(--qt19-glass-bg) 55%, transparent)",
            "backdrop_filter": "blur(26px) saturate(180%)",
            "box_shadow": "0 12px 40px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.16)",
            "padding": "0",
        },
        margin="0.75rem",
        edge=True,
    )
    collapsed = AppState.sidebar_stage == "line"
    hidden_style = {
        "position": "absolute",
        "top": "0",
        "left": "0",
        "transform": "translateX(-130%)",
        "opacity": "0",
        "pointer_events": "none",
    }
    shown_style = {"position": "relative", "transform": "translateX(0)", "opacity": "1"}
    return rx.fragment(
        rx.box(
            card,
            style=rx.cond(collapsed, hidden_style, shown_style),
            transition="transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.35s ease",
        ),
        rx.cond(collapsed, _collapsed_handle(), rx.fragment()),
    )
