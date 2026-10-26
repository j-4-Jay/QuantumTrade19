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

import reflex as rx

from engines.workers.poi.independent_poi_worker import (
    MAX_LINES_PER_SYMBOL, IndependentPOIStore, build_chart_items,
)
from state.app_state_mixins.shared import _engine, TRADING_PANEL_CHART_ID

_STORE = None
_CLICK_TOLERANCE_PX = 8


def _get_store() -> IndependentPOIStore:
    global _STORE
    if _STORE is None:
        _engine.ensure_poi_monitor_started()
        _STORE = IndependentPOIStore(on_change=_engine.poi_monitor.set_independent_pois)
    return _STORE


def _tick_size(symbol: str) -> float:
    try:
        return float(_engine.market_data.symbol_registry.get_tick_size(symbol))
    except Exception:
        return 0.0


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

    @rx.var
    def ind_poi_overlays(self) -> list[dict]:
        _ = self.ind_poi_revision
        return build_chart_items(_get_store().lines(self.trading_panel_symbol))

    @rx.var
    def ind_poi_overlays_version(self) -> int:
        return self.ind_poi_revision

    @rx.var
    def ind_poi_count(self) -> int:
        return len(self.ind_poi_overlays)

    @rx.var
    def ind_poi_can_add(self) -> bool:
        return len(self.ind_poi_overlays) < MAX_LINES_PER_SYMBOL

    def open_chart_menu(self, x: int, y: int):
        self.open_trading_panel_menu(x, y)
        self.ind_poi_click_price = 0.0
        self.ind_poi_target_uid = ""
        self.ind_poi_target_number = 0
        lines = [{"uid": i["uid"], "number": i["number"], "price": i["price"]} for i in self.ind_poi_overlays]
        return rx.call_script(_probe_js(x, y, lines), callback=type(self).set_ind_poi_probe)

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
