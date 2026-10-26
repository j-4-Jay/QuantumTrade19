"""Executable AppState mixin: Independent POI lines on the Trading Panel chart.

PATH: state/app_state_mixins/independent_poi_mixin.py (NEW FILE)
STAGE: FT-C, task FT-C.3. SPEC: docs/specs/File_04.1b_CustomPOI_Spec_v2.md

What it does:
- keeps one IndependentPOIStore (engines/workers/poi/independent_poi_worker.py)
  and connects it to the POI monitor, so the lines run through the same POI
  pipeline as real POIs;
- exposes the lines of the current symbol as chart items (kind "ind_line");
- open_chart_menu(x, y) opens the existing Trading Panel menu and reads, in the
  browser, the price at the click and the nearest Independent line (within 8 px);
- add / delete / move actions.

Saving to disk, styling, the PAPER badge and the Home/Office sync come in
FT-C.4, FT-C.5 and FT-C.7.
"""
from __future__ import annotations

import json
import logging

import reflex as rx

from engines.workers.poi.independent_poi_worker import (
    MAX_LINES_PER_SYMBOL, IndependentPOIStore, build_chart_items,
)
from engines.workers.poi.independent_poi_persistence import default_path, load_lines, save_lines
from state.app_state_mixins.shared import _engine, TRADING_PANEL_CHART_ID

_STORE = None
_SYNCED = False
logger = logging.getLogger("independent_poi_mixin")
_CLICK_TOLERANCE_PX = 8

_FIT_MENU_JS = """(function() {
    var tries = 0;
    function fit() {
        var el = document.getElementById('qt19-chart-menu');
        if (!el) { if (tries++ < 20) setTimeout(fit, 25); return; }
        function place() {
            var r = el.getBoundingClientRect();
            var m = 8, left = r.left, top = r.top;
            if (r.right > window.innerWidth - m) left = Math.max(m, window.innerWidth - r.width - m);
            if (r.bottom > window.innerHeight - m) top = Math.max(m, window.innerHeight - r.height - m);
            if (left !== r.left) el.style.left = left + 'px';
            if (top !== r.top) el.style.top = top + 'px';
        }
        place();
        if (window.ResizeObserver && !el.__qt19RO) {
            el.__qt19RO = new ResizeObserver(place);
            el.__qt19RO.observe(el);
        }
    }
    fit();
})()"""


def _push_to_monitor(symbol: str, pois: list) -> None:
    """Hand the lines to the POI monitor. Runs only when the user adds, moves or
    deletes a line, so reading the lines never starts the engine early."""
    _engine.ensure_poi_monitor_started()
    if _engine.poi_monitor is not None:
        _engine.poi_monitor.set_independent_pois(symbol, pois)


def _on_store_change(symbol: str, pois: list) -> None:
    """Called after every add, move, delete or style change: save to disk, then tell the monitor."""
    try:
        save_lines(default_path(), _STORE.all_lines())
    except Exception:  # noqa: BLE001
        logger.exception("Independent POI lines could not be saved")
    _push_to_monitor(symbol, pois)


def _get_store() -> IndependentPOIStore:
    global _STORE
    if _STORE is None:
        _STORE = IndependentPOIStore(on_change=_on_store_change)
        try:
            _STORE.restore(load_lines(default_path()))
        except Exception:  # noqa: BLE001
            logger.exception("Independent POI lines could not be loaded")
    return _STORE


def _sync_restored_once() -> None:
    """When the POI monitor exists, hand it the lines loaded from disk (once)."""
    global _SYNCED
    if _SYNCED or _STORE is None or _engine.poi_monitor is None:
        return
    _SYNCED = True
    for symbol in _STORE.symbols():
        _engine.poi_monitor.set_independent_pois(symbol, _STORE.pois(symbol))


def _tick_size(symbol: str) -> float:
    try:
        return float(_engine.market_data.symbol_registry.get_tick_size(symbol))
    except Exception:
        return 0.0


def _find_item(items: list, uid: str) -> dict:
    for item in items:
        if item.get("uid") == uid:
            return item
    return {}


def _probe_js(x: int, y: int, lines: list) -> str:
    return f"""(function() {{
        var out = {{price: 0, uid: "", number: 0}};
        var chart = window.QT19_CHARTS && window.QT19_CHARTS['{TRADING_PANEL_CHART_ID}'];
        if (!chart) return out;
        var el = (typeof chart.getDom === 'function' ? chart.getDom() : null) || document.getElementById('{TRADING_PANEL_CHART_ID}');
        if (!el) return out;
        var r = el.getBoundingClientRect();
        var px = {{x: {int(x)} - r.left, y: {int(y)} - r.top}};
        try {{
            var p = chart.convertFromPixel(px, {{paneId: 'candle_pane'}});
            if (p && typeof p.value === 'number') out.price = p.value;
        }} catch (e) {{}}
        var lines = {json.dumps(lines)};
        var best = {_CLICK_TOLERANCE_PX};
        lines.forEach(function(l) {{
            try {{
                var q = chart.convertToPixel({{value: l.price}}, {{paneId: 'candle_pane'}});
                if (q && typeof q.y === 'number') {{
                    var d = Math.abs(q.y - px.y);
                    if (d <= best) {{ best = d; out.uid = l.uid; out.number = l.number; }}
                }}
            }} catch (e) {{}}
        }});
        return out;
    }})()"""


class IndependentPoiMixin(rx.State, mixin=True):
    ind_poi_revision: int = 0
    ind_poi_click_price: float = 0.0
    ind_poi_target_uid: str = ""
    ind_poi_target_number: int = 0
    ind_poi_delete_popup_open: bool = False
    ind_poi_delete_selected: list[str] = []
    ind_poi_style_popup_open: bool = False
    ind_poi_style_uid: str = ""

    @rx.var
    def ind_poi_overlays(self) -> list[dict]:
        _ = self.ind_poi_revision
        store = _get_store()
        _sync_restored_once()
        return build_chart_items(store.lines(self.trading_panel_symbol))

    @rx.var
    def ind_poi_overlays_version(self) -> int:
        return self.ind_poi_revision

    @rx.var
    def ind_poi_count(self) -> int:
        return len(self.ind_poi_overlays)

    @rx.var
    def ind_poi_can_add(self) -> bool:
        return len(self.ind_poi_overlays) < MAX_LINES_PER_SYMBOL

    @rx.var
    def chart_overlays_all(self) -> list[dict]:
        _sync_restored_once()
        return list(self.combined_chart_overlays) + list(self.ind_poi_overlays)

    @rx.var
    def chart_overlays_all_version(self) -> int:
        return self.combined_chart_overlays_version + self.ind_poi_overlays_version

    @rx.var
    def ind_poi_delete_label(self) -> str:
        return f"Delete Independent POI {self.ind_poi_target_number}"

    @rx.var
    def ind_poi_delete_rows(self) -> list[dict]:
        rows = []
        for item in self.ind_poi_overlays:
            price = f"{float(item['price']):,.8f}".rstrip("0").rstrip(".")
            rows.append({
                "uid": item["uid"],
                "label": f"{item['label']}   -   {price}",
                "checked": item["uid"] in self.ind_poi_delete_selected,
            })
        return rows

    @rx.var
    def ind_poi_selected_count(self) -> int:
        return len(self.ind_poi_delete_selected)

    @rx.var
    def ind_poi_popup_style(self) -> dict:
        day = self.trading_panel_chart_theme == "day"
        return {
            "background": "#f4f7fb" if day else "#141d29",
            "border": "1px solid " + ("rgba(20,30,50,0.18)" if day else "rgba(147,173,205,0.28)"),
            "borderRadius": "0.9rem",
            "color": "#152238" if day else "#dce8f7",
            "boxShadow": "0 12px 36px rgba(0,0,0,0.45)",
        }

    def open_ind_poi_delete_popup(self) -> None:
        self.ind_poi_delete_selected = []
        self.ind_poi_delete_popup_open = True

    def close_ind_poi_delete_popup(self) -> None:
        self.ind_poi_delete_popup_open = False

    def toggle_ind_poi_selected(self, uid: str) -> None:
        current = list(self.ind_poi_delete_selected)
        if uid in current:
            current.remove(uid)
        else:
            current.append(uid)
        self.ind_poi_delete_selected = current

    def select_all_ind_poi(self) -> None:
        self.ind_poi_delete_selected = [item["uid"] for item in self.ind_poi_overlays]

    def select_none_ind_poi(self) -> None:
        self.ind_poi_delete_selected = []

    def delete_selected_ind_poi(self) -> None:
        symbol = self.trading_panel_symbol
        store = _get_store()
        for uid in list(self.ind_poi_delete_selected):
            store.delete(symbol, uid)
        self.ind_poi_delete_selected = []
        self.ind_poi_delete_popup_open = False
        self.ind_poi_revision += 1

    @rx.var
    def ind_poi_style_title(self) -> str:
        return str(_find_item(self.ind_poi_overlays, self.ind_poi_style_uid).get("label", ""))

    @rx.var
    def ind_poi_style_color(self) -> str:
        return str(_find_item(self.ind_poi_overlays, self.ind_poi_style_uid).get("color", "#F59E0B"))

    @rx.var
    def ind_poi_style_width(self) -> int:
        return int(_find_item(self.ind_poi_overlays, self.ind_poi_style_uid).get("width", 2))

    @rx.var
    def ind_poi_style_opacity(self) -> int:
        return int(_find_item(self.ind_poi_overlays, self.ind_poi_style_uid).get("opacity", 100))

    @rx.var
    def ind_poi_style_line_style(self) -> str:
        return str(_find_item(self.ind_poi_overlays, self.ind_poi_style_uid).get("line_style", "dashed"))

    @rx.var
    def ind_poi_style_width_text(self) -> str:
        return f"Thickness: {self.ind_poi_style_width} px"

    @rx.var
    def ind_poi_style_opacity_text(self) -> str:
        return f"Transparency: {self.ind_poi_style_opacity} %"

    def open_ind_poi_style_popup(self) -> None:
        self.ind_poi_style_uid = self.ind_poi_target_uid
        self.ind_poi_style_popup_open = bool(self.ind_poi_style_uid)

    def close_ind_poi_style_popup(self) -> None:
        self.ind_poi_style_popup_open = False

    def _apply_ind_poi_style(self, **changes) -> None:
        if self.ind_poi_style_uid:
            _get_store().set_style(self.trading_panel_symbol, self.ind_poi_style_uid, **changes)
            self.ind_poi_revision += 1

    def set_ind_poi_style_color(self, value: str) -> None:
        self._apply_ind_poi_style(color=value)

    def set_ind_poi_style_width(self, value: str) -> None:
        self._apply_ind_poi_style(width=value)

    def set_ind_poi_style_opacity(self, value: str) -> None:
        self._apply_ind_poi_style(opacity=value)

    def set_ind_poi_style_line_style(self, value: str) -> None:
        self._apply_ind_poi_style(line_style=value)

    @rx.var
    def ind_poi_style_allow_live(self) -> bool:
        return bool(_find_item(self.ind_poi_overlays, self.ind_poi_style_uid).get("allow_live", False))

    def set_ind_poi_allow_live(self, value: bool) -> None:
        if self.ind_poi_style_uid:
            _get_store().set_allow_live(self.trading_panel_symbol, self.ind_poi_style_uid, bool(value))
            self.ind_poi_revision += 1

    def open_chart_menu(self, x: int, y: int):
        self.open_trading_panel_menu(x, y)
        self.ind_poi_click_price = 0.0
        self.ind_poi_target_uid = ""
        self.ind_poi_target_number = 0
        lines = [{"uid": i["uid"], "number": i["number"], "price": i["price"]} for i in self.ind_poi_overlays]
        return [
            rx.call_script(_FIT_MENU_JS),
            rx.call_script(_probe_js(x, y, lines), callback=type(self).set_ind_poi_probe),
        ]

    def set_ind_poi_probe(self, result: dict) -> None:
        result = result or {}
        self.ind_poi_click_price = float(result.get("price") or 0.0)
        self.ind_poi_target_uid = str(result.get("uid") or "")
        self.ind_poi_target_number = int(result.get("number") or 0)

    def add_independent_poi(self) -> None:
        price = self.ind_poi_click_price
        symbol = self.trading_panel_symbol
        if price > 0:
            _get_store().add(symbol, price, _tick_size(symbol))
        self.ind_poi_revision += 1

    def delete_independent_poi(self) -> None:
        if self.ind_poi_target_uid:
            _get_store().delete(self.trading_panel_symbol, self.ind_poi_target_uid)
            self.ind_poi_target_uid = ""
            self.ind_poi_target_number = 0
        self.ind_poi_revision += 1

    def move_independent_poi(self, uid: str, price: float) -> None:
        symbol = self.trading_panel_symbol
        _get_store().move(symbol, uid, float(price), _tick_size(symbol))
        self.ind_poi_revision += 1
