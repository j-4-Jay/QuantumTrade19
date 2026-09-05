"""Executable AppState mixin: POI Engine & Chart Visibility settings.

PATH: state/app_state_mixins/poi_settings_mixin.py  (REPLACE ENTIRE FILE)

FIX (Timezone Mode toggle) - added poi_timezone_mode ("UTC"/"NY", default
"NY", loaded from _engine.get_poi_settings()["timezone_mode"]) and
set_poi_timezone_mode() - persists via the engine (which now owns the
real timezone_mode setting inside POISettings) and refreshes the Trading
Panel chart overlays immediately so changed PDH/PDL/4H/Week/Month levels
show up right away.
"""
from __future__ import annotations

import asyncio
import reflex as rx

from state.app_state_mixins.shared import (
    _engine,
    POI_DEFAULT_STRATEGY_TYPES,
    POI_LINE_TF_LABELS,
    POI_LINE_TF_ORDER,
    POI_LINE_TYPE_MAP,
    POI_ZONE_TYPES,
)

_DEFAULT_TF_COLOR = {
    "1m": "#38BDF8", "5m": "#38BDF8", "15m": "#38BDF8",
    "1H": "#32CD32", "4H": "#FFFFFF",
    "1D": "#FFA500", "1W": "#FFFF00", "1M": "#DC143C",
}
_DEFAULT_CUSTOM_LINE_COLORS = ["#22C55E", "#F97316", "#38BDF8"]


def _default_custom_lines() -> list[dict]:
    return [
        {"enabled": False, "hour12": 8, "minute": 30, "meridiem": "AM", "color": _DEFAULT_CUSTOM_LINE_COLORS[i], "name": ""}
        for i in range(3)
    ]


class PoiSettingsMixin(rx.State, mixin=True):
    def load_poi_settings(self) -> None:
        settings = _engine.get_poi_settings()
        self.poi_display_enabled = settings.get("display_enabled", {})
        self.poi_strategy_enabled = settings.get("strategy_enabled", {})
        self.poi_zone_source_tf_enabled = settings.get("zone_source_tf_enabled", {})
        self.poi_timezone_mode = settings.get("timezone_mode", "NY")

        visual = _engine.security.persistence.load().get("poi_visual_settings", {})
        self.poi_show_labels = visual.get("show_labels", True)
        self.poi_show_tooltips = visual.get("show_tooltips", True)
        self.poi_line_transparency = visual.get("line_transparency", 100)
        self.poi_zone_opacity = visual.get("zone_opacity", 30)
        self.poi_show_source_tf_badge = visual.get("show_source_tf_badge", True)
        self.poi_show_logical_id = visual.get("show_logical_id", False)
        self.poi_reduced_motion = visual.get("reduced_motion", False)
        self.poi_vertical_line_style = visual.get("vertical_line_style", "dashed")
        self.poi_vertical_line_opacity = visual.get("vertical_line_opacity", 100)

        tf_settings = _engine.security.persistence.load().get("poi_tf_settings", {})
        self.poi_tf_color = tf_settings.get("color", dict(_DEFAULT_TF_COLOR))
        self.poi_tf_vertical_enabled = tf_settings.get(
            "vertical_enabled",
            {tf: (tf in ("1D", "4H", "1W", "1M")) for tf in POI_LINE_TF_ORDER},
        )
        self.poi_tf_display_enabled = {
            tf: self.poi_display_enabled.get(POI_LINE_TYPE_MAP[tf][0], False)
            for tf in POI_LINE_TF_ORDER
        }
        self.poi_tf_strategy_enabled = {
            tf: self.poi_strategy_enabled.get(POI_LINE_TYPE_MAP[tf][0], False)
            for tf in POI_LINE_TF_ORDER
        }

        custom = _engine.security.persistence.load().get("poi_custom_lines_v2")
        if custom and len(custom) == 3 and "hour12" in custom[0]:
            self.poi_custom_lines = custom
        else:
            self.poi_custom_lines = _default_custom_lines()

        self.poi_settings_loaded = True
        if self.active_tab == "Trading Panel":
            self.refresh_poi_chart_overlays()

    @rx.event(background=True)
    async def set_poi_timezone_mode(self, mode: str | list[str]):
        resolved = mode[0] if isinstance(mode, list) else mode
        async with self:
            self.poi_timezone_mode = resolved
            self.poi_backend_busy = True
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()
        try:
            await asyncio.to_thread(_engine.set_poi_timezone_mode, resolved)
        finally:
            async with self:
                self.poi_backend_busy = False
                if self.active_tab == "Trading Panel":
                    self.refresh_poi_chart_overlays()

    @rx.event(background=True)
    async def toggle_poi_display(self, poi_type: str, checked: bool):
        async with self:
            self.poi_display_enabled = {**self.poi_display_enabled, poi_type: checked}
            self.poi_backend_busy = True
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()
        try:
            await asyncio.to_thread(_engine.set_poi_display_enabled, poi_type, checked)
        finally:
            async with self:
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def toggle_poi_strategy(self, poi_type: str, checked: bool):
        async with self:
            self.poi_strategy_enabled = {**self.poi_strategy_enabled, poi_type: checked}
            self.poi_backend_busy = True
        try:
            await asyncio.to_thread(_engine.set_poi_strategy_enabled, poi_type, checked)
        finally:
            async with self:
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def toggle_poi_zone_source_tf(self, timeframe: str, checked: bool):
        async with self:
            self.poi_zone_source_tf_enabled = {**self.poi_zone_source_tf_enabled, timeframe: checked}
            self.poi_backend_busy = True
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()
        try:
            await asyncio.to_thread(_engine.set_poi_zone_source_tf_enabled, timeframe, checked)
        finally:
            async with self:
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def toggle_poi_tf_display(self, tf: str, checked: bool):
        high_type, low_type = POI_LINE_TYPE_MAP[tf]
        async with self:
            self.poi_tf_display_enabled = {**self.poi_tf_display_enabled, tf: checked}
            self.poi_display_enabled = {**self.poi_display_enabled, high_type: checked, low_type: checked}
            self.poi_backend_busy = True
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()

        def _apply():
            _engine.set_poi_display_enabled(high_type, checked)
            _engine.set_poi_display_enabled(low_type, checked)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def toggle_poi_tf_strategy(self, tf: str, checked: bool):
        high_type, low_type = POI_LINE_TYPE_MAP[tf]
        async with self:
            self.poi_tf_strategy_enabled = {**self.poi_tf_strategy_enabled, tf: checked}
            self.poi_strategy_enabled = {**self.poi_strategy_enabled, high_type: checked, low_type: checked}
            self.poi_backend_busy = True

        def _apply():
            _engine.set_poi_strategy_enabled(high_type, checked)
            _engine.set_poi_strategy_enabled(low_type, checked)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    def _save_poi_tf_settings(self) -> None:
        _engine.security.persistence.save({
            "poi_tf_settings": {
                "color": dict(self.poi_tf_color),
                "vertical_enabled": dict(self.poi_tf_vertical_enabled),
            }
        })
        if self.active_tab == "Trading Panel":
            self.refresh_poi_chart_overlays()

    def set_poi_tf_color(self, tf: str, color: str) -> None:
        self.poi_tf_color = {**self.poi_tf_color, tf: color}
        self._save_poi_tf_settings()

    def toggle_poi_tf_vertical(self, tf: str, checked: bool) -> None:
        self.poi_tf_vertical_enabled = {**self.poi_tf_vertical_enabled, tf: checked}
        self._save_poi_tf_settings()

    def _save_custom_lines(self) -> None:
        _engine.security.persistence.save({"poi_custom_lines_v2": self.poi_custom_lines})
        if self.active_tab == "Trading Panel":
            self.refresh_poi_chart_overlays()

    def toggle_custom_line_enabled(self, index: int, checked: bool) -> None:
        lines = [dict(x) for x in self.poi_custom_lines]
        lines[index]["enabled"] = checked
        self.poi_custom_lines = lines
        self._save_custom_lines()

    def set_custom_line_hour(self, index: int, value: str) -> None:
        lines = [dict(x) for x in self.poi_custom_lines]
        try:
            lines[index]["hour12"] = max(1, min(12, int(value)))
        except ValueError:
            return
        self.poi_custom_lines = lines
        self._save_custom_lines()

    def set_custom_line_minute(self, index: int, value: str) -> None:
        lines = [dict(x) for x in self.poi_custom_lines]
        try:
            lines[index]["minute"] = max(0, min(59, int(value)))
        except ValueError:
            return
        self.poi_custom_lines = lines
        self._save_custom_lines()

    def set_custom_line_meridiem(self, index: int, value: str | list[str]) -> None:
        resolved = value[0] if isinstance(value, list) else value
        lines = [dict(x) for x in self.poi_custom_lines]
        lines[index]["meridiem"] = resolved
        self.poi_custom_lines = lines
        self._save_custom_lines()

    def set_custom_line_color(self, index: int, value: str) -> None:
        lines = [dict(x) for x in self.poi_custom_lines]
        lines[index]["color"] = value
        self.poi_custom_lines = lines
        self._save_custom_lines()

    def set_custom_line_name(self, index: int, value: str) -> None:
        lines = [dict(x) for x in self.poi_custom_lines]
        lines[index]["name"] = value
        self.poi_custom_lines = lines
        self._save_custom_lines()

    def _save_poi_visual_settings(self) -> None:
        _engine.security.persistence.save({
            "poi_visual_settings": {
                "show_labels": self.poi_show_labels,
                "show_tooltips": self.poi_show_tooltips,
                "line_transparency": self.poi_line_transparency,
                "zone_opacity": self.poi_zone_opacity,
                "show_source_tf_badge": self.poi_show_source_tf_badge,
                "show_logical_id": self.poi_show_logical_id,
                "reduced_motion": self.poi_reduced_motion,
                "vertical_line_style": self.poi_vertical_line_style,
                "vertical_line_opacity": self.poi_vertical_line_opacity,
            }
        })
        if self.active_tab == "Trading Panel":
            self.refresh_poi_chart_overlays()

    def toggle_poi_show_labels(self, checked: bool) -> None:
        self.poi_show_labels = checked
        self._save_poi_visual_settings()

    def toggle_poi_show_tooltips(self, checked: bool) -> None:
        self.poi_show_tooltips = checked
        self._save_poi_visual_settings()

    def toggle_poi_show_source_tf_badge(self, checked: bool) -> None:
        self.poi_show_source_tf_badge = checked
        self._save_poi_visual_settings()

    def toggle_poi_show_logical_id(self, checked: bool) -> None:
        self.poi_show_logical_id = checked
        self._save_poi_visual_settings()

    def toggle_poi_reduced_motion(self, checked: bool) -> None:
        self.poi_reduced_motion = checked
        self._save_poi_visual_settings()

    def set_poi_line_transparency(self, value: list[float]) -> None:
        self.poi_line_transparency = int(value[0])
        self._save_poi_visual_settings()

    def set_poi_zone_opacity(self, value: list[float]) -> None:
        self.poi_zone_opacity = int(value[0])
        self._save_poi_visual_settings()

    def set_poi_vertical_line_style(self, value: str | list[str]) -> None:
        resolved = value[0] if isinstance(value, list) else value
        self.poi_vertical_line_style = resolved
        self._save_poi_visual_settings()

    def set_poi_vertical_line_opacity(self, value: list[float]) -> None:
        self.poi_vertical_line_opacity = int(value[0])
        self._save_poi_visual_settings()

    @rx.event(background=True)
    async def poi_show_all(self):
        async with self:
            poi_types = list(self.poi_display_enabled.keys())
            self.poi_display_enabled = {t: True for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_display_enabled(t, True)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def poi_hide_all(self):
        async with self:
            poi_types = list(self.poi_display_enabled.keys())
            self.poi_display_enabled = {t: False for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_display_enabled(t, False)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def poi_enable_default_strategy(self):
        async with self:
            poi_types = list(self.poi_strategy_enabled.keys())
            self.poi_strategy_enabled = {t: (t in POI_DEFAULT_STRATEGY_TYPES) for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_strategy_enabled(t, t in POI_DEFAULT_STRATEGY_TYPES)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def poi_disable_all_strategy(self):
        async with self:
            poi_types = list(self.poi_strategy_enabled.keys())
            self.poi_strategy_enabled = {t: False for t in poi_types}
            self.poi_backend_busy = True

        def _apply():
            for t in poi_types:
                _engine.set_poi_strategy_enabled(t, False)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.load_poi_settings()
                self.poi_backend_busy = False

    def poi_reset_chart_filters(self) -> None:
        pass

    @rx.var
    def poi_tf_card_rows(self) -> list[dict]:
        return [{
            "tf": tf,
            "label": POI_LINE_TF_LABELS[tf],
            "display": self.poi_tf_display_enabled.get(tf, False),
            "strategy": self.poi_tf_strategy_enabled.get(tf, False),
            "color": self.poi_tf_color.get(tf, _DEFAULT_TF_COLOR.get(tf, "#38BDF8")),
            "vertical_enabled": self.poi_tf_vertical_enabled.get(tf, False),
        } for tf in POI_LINE_TF_ORDER]

    @rx.var
    def poi_zone_type_rows(self) -> list[dict]:
        return [{
            "type": t, "label": label,
            "display": self.poi_display_enabled.get(t, False),
            "strategy": self.poi_strategy_enabled.get(t, False),
        } for t, label in POI_ZONE_TYPES]

    @rx.var
    def poi_zone_source_tf_rows(self) -> list[dict]:
        return [{"tf": tf, "enabled": self.poi_zone_source_tf_enabled.get(tf, False)} for tf in POI_LINE_TF_ORDER]
