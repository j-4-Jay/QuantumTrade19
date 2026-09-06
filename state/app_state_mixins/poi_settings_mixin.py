"""Executable AppState mixin: POI Engine & Chart Visibility settings.

PATH: state/app_state_mixins/poi_settings_mixin.py  (REPLACE ENTIRE FILE)

FIX (Bulk Controls redefined per explicit clarification) - renamed and
re-scoped from blanket "everything" operations to operations scoped to
whatever is CURRENTLY on the chart:

  poi_hide_extras() [was poi_hide_all] - captures every POI type
    currently Display=True (into _poi_hidden_by_extras) THEN turns
    Display off for exactly those - not a blanket "set everything
    False" (which would discard the memory of what was actually shown).

  poi_show_extras() [was poi_show_all] - restores Display=True ONLY for
    the types captured by the most recent poi_hide_extras() call, then
    clears that memory. Calling it without a prior Hide is a no-op.

  poi_enable_default_strategy() - Strategy now goes True for the UNION
    of the locked default set (PDH/PDL/4H_HIGH/4H_LOW) AND every POI
    type CURRENTLY Display=True (i.e. "already attached to the chart") -
    everything else resets to False.

  poi_disable_all_strategy() - now only iterates POI types CURRENTLY
    Display=True ("present on chart") and turns their Strategy off -
    types not currently shown are left untouched, not force-reset.
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
_DEFAULT_TF_DISPLAY = {tf: (tf in ("1D", "4H")) for tf in POI_LINE_TF_ORDER}
_DEFAULT_TF_VERTICAL_STYLE = {tf: "solid" for tf in POI_LINE_TF_ORDER}
_DEFAULT_TF_VERTICAL_OPACITY = {tf: 50 for tf in POI_LINE_TF_ORDER}
_DEFAULT_ZONE_SOURCE_TF = {"1m": True, "5m": False, "15m": True, "1H": False, "4H": False, "1D": False, "1W": False, "1M": False}

_ZONE_TYPE_KEYS = [t for t, _ in POI_ZONE_TYPES]
_DEFAULT_ZONE_COLOR = {
    "RESISTANCE_FLIP": "#EF4444",
    "SUPPORT_FLIP": "#22C55E",
    "FVG": "#3B82F6",
    "INVERSE_FVG": "#A855F7",
    "ORDER_BLOCK": "#F59E0B",
}
_DEFAULT_ZONE_MAX_COUNT = {t: 5 for t in _ZONE_TYPE_KEYS}
_DEFAULT_ZONE_OPACITY = {t: 30 for t in _ZONE_TYPE_KEYS}


def _default_custom_lines() -> list[dict]:
    return [
        {"enabled": False, "hour12": 8, "minute": 30, "meridiem": "AM", "color": _DEFAULT_CUSTOM_LINE_COLORS[i], "name": ""}
        for i in range(3)
    ]


class PoiSettingsMixin(rx.State, mixin=True):
    def load_poi_settings(self) -> None:
        if self.poi_settings_loaded:
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()
            return

        settings = _engine.get_poi_settings()
        self.poi_display_enabled = settings.get("display_enabled", {})
        self.poi_strategy_enabled = settings.get("strategy_enabled", {})
        self.poi_zone_source_tf_enabled = settings.get("zone_source_tf_enabled", {})
        self.poi_timezone_mode = settings.get("timezone_mode", "NY")

        visual = _engine.security.persistence.load().get("poi_visual_settings", {})
        self.poi_show_labels = visual.get("show_labels", True)
        self.poi_show_tooltips = visual.get("show_tooltips", True)
        self.poi_line_transparency = visual.get("line_transparency", 100)
        self.poi_show_source_tf_badge = visual.get("show_source_tf_badge", True)
        self.poi_show_logical_id = visual.get("show_logical_id", False)
        self.poi_reduced_motion = visual.get("reduced_motion", False)
        self.poi_high_line_style = visual.get("high_line_style", "solid")
        self.poi_high_line_thickness = visual.get("high_line_thickness", 2)
        self.poi_low_line_style = visual.get("low_line_style", "solid")
        self.poi_low_line_thickness = visual.get("low_line_thickness", 1)

        tf_settings = _engine.security.persistence.load().get("poi_tf_settings", {})
        self.poi_tf_color = tf_settings.get("color", dict(_DEFAULT_TF_COLOR))
        self.poi_tf_vertical_enabled = tf_settings.get("vertical_enabled", dict(_DEFAULT_TF_DISPLAY))
        self.poi_tf_droplet_enabled = tf_settings.get("droplet_enabled", dict(_DEFAULT_TF_DISPLAY))
        self.poi_tf_vertical_style = tf_settings.get("vertical_style", dict(_DEFAULT_TF_VERTICAL_STYLE))
        self.poi_tf_vertical_opacity = tf_settings.get("vertical_opacity", dict(_DEFAULT_TF_VERTICAL_OPACITY))
        self.poi_tf_display_enabled = {
            tf: self.poi_display_enabled.get(POI_LINE_TYPE_MAP[tf][0], False)
            for tf in POI_LINE_TF_ORDER
        }
        self.poi_tf_strategy_enabled = {
            tf: self.poi_strategy_enabled.get(POI_LINE_TYPE_MAP[tf][0], False)
            for tf in POI_LINE_TF_ORDER
        }

        zone_settings = _engine.security.persistence.load().get("poi_zone_settings", {})
        self.poi_zone_max_count = zone_settings.get("max_count", dict(_DEFAULT_ZONE_MAX_COUNT))
        self.poi_zone_color = zone_settings.get("color", dict(_DEFAULT_ZONE_COLOR))
        self.poi_zone_type_opacity = zone_settings.get("opacity", dict(_DEFAULT_ZONE_OPACITY))

        custom = _engine.security.persistence.load().get("poi_custom_lines_v2")
        if custom and len(custom) == 3 and "hour12" in custom[0]:
            self.poi_custom_lines = custom
        else:
            self.poi_custom_lines = _default_custom_lines()

        self._poi_hidden_by_extras = _engine.security.persistence.load().get("poi_hidden_by_extras", {})

        self.poi_settings_loaded = True
        if self.active_tab == "Trading Panel":
            self.refresh_poi_chart_overlays()

    def _sync_tf_dicts_from_flat(self) -> None:
        """Rebuilds poi_tf_display_enabled/poi_tf_strategy_enabled from
        the flat per-type dicts - call after any bulk mutation of
        poi_display_enabled/poi_strategy_enabled that isn't already
        going through the per-TF setters."""
        self.poi_tf_display_enabled = {
            tf: self.poi_display_enabled.get(POI_LINE_TYPE_MAP[tf][0], False)
            for tf in POI_LINE_TF_ORDER
        }
        self.poi_tf_strategy_enabled = {
            tf: self.poi_strategy_enabled.get(POI_LINE_TYPE_MAP[tf][0], False)
            for tf in POI_LINE_TF_ORDER
        }

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

    def reset_poi_timezone_default(self):
        return type(self).set_poi_timezone_mode("NY")

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
                "droplet_enabled": dict(self.poi_tf_droplet_enabled),
                "vertical_style": dict(self.poi_tf_vertical_style),
                "vertical_opacity": dict(self.poi_tf_vertical_opacity),
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

    def toggle_poi_tf_droplet(self, tf: str, checked: bool) -> None:
        self.poi_tf_droplet_enabled = {**self.poi_tf_droplet_enabled, tf: checked}
        self._save_poi_tf_settings()

    def set_poi_tf_vertical_style(self, tf: str, value: str | list[str]) -> None:
        resolved = value[0] if isinstance(value, list) else value
        self.poi_tf_vertical_style = {**self.poi_tf_vertical_style, tf: resolved}
        self._save_poi_tf_settings()

    def set_poi_tf_vertical_opacity(self, tf: str, value: list[float]) -> None:
        self.poi_tf_vertical_opacity = {**self.poi_tf_vertical_opacity, tf: int(value[0])}
        self._save_poi_tf_settings()

    @rx.event(background=True)
    async def reset_poi_lines_defaults(self):
        async with self:
            self.poi_tf_display_enabled = dict(_DEFAULT_TF_DISPLAY)
            self.poi_tf_strategy_enabled = dict(_DEFAULT_TF_DISPLAY)
            self.poi_tf_color = dict(_DEFAULT_TF_COLOR)
            self.poi_tf_vertical_enabled = dict(_DEFAULT_TF_DISPLAY)
            self.poi_tf_droplet_enabled = dict(_DEFAULT_TF_DISPLAY)
            self.poi_tf_vertical_style = dict(_DEFAULT_TF_VERTICAL_STYLE)
            self.poi_tf_vertical_opacity = dict(_DEFAULT_TF_VERTICAL_OPACITY)
            for tf in POI_LINE_TF_ORDER:
                high_type, low_type = POI_LINE_TYPE_MAP[tf]
                enabled = _DEFAULT_TF_DISPLAY[tf]
                self.poi_display_enabled = {**self.poi_display_enabled, high_type: enabled, low_type: enabled}
                self.poi_strategy_enabled = {**self.poi_strategy_enabled, high_type: enabled, low_type: enabled}
            self.poi_backend_busy = True
            self._save_poi_tf_settings()

        def _apply():
            for tf in POI_LINE_TF_ORDER:
                high_type, low_type = POI_LINE_TYPE_MAP[tf]
                enabled = _DEFAULT_TF_DISPLAY[tf]
                _engine.set_poi_display_enabled(high_type, enabled)
                _engine.set_poi_display_enabled(low_type, enabled)
                _engine.set_poi_strategy_enabled(high_type, enabled)
                _engine.set_poi_strategy_enabled(low_type, enabled)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    def reset_poi_horizontal_style_defaults(self) -> None:
        self.poi_high_line_style = "solid"
        self.poi_high_line_thickness = 2
        self.poi_low_line_style = "solid"
        self.poi_low_line_thickness = 1
        self._save_poi_visual_settings()

    @rx.event(background=True)
    async def reset_poi_zone_matrix_defaults(self):
        async with self:
            self.poi_zone_source_tf_enabled = dict(_DEFAULT_ZONE_SOURCE_TF)
            self.poi_backend_busy = True
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()

        def _apply():
            for tf, enabled in _DEFAULT_ZONE_SOURCE_TF.items():
                _engine.set_poi_zone_source_tf_enabled(tf, enabled)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    def _save_poi_zone_settings(self) -> None:
        _engine.security.persistence.save({
            "poi_zone_settings": {
                "max_count": dict(self.poi_zone_max_count),
                "color": dict(self.poi_zone_color),
                "opacity": dict(self.poi_zone_type_opacity),
            }
        })
        if self.active_tab == "Trading Panel":
            self.refresh_poi_chart_overlays()

    def set_poi_zone_max_count(self, zone_type: str, value: str) -> None:
        try:
            count = max(1, min(50, int(value)))
        except ValueError:
            return
        self.poi_zone_max_count = {**self.poi_zone_max_count, zone_type: count}
        self._save_poi_zone_settings()

    def set_poi_zone_color(self, zone_type: str, value: str) -> None:
        self.poi_zone_color = {**self.poi_zone_color, zone_type: value}
        self._save_poi_zone_settings()

    def set_poi_zone_type_opacity(self, zone_type: str, value: list[float]) -> None:
        self.poi_zone_type_opacity = {**self.poi_zone_type_opacity, zone_type: int(value[0])}
        self._save_poi_zone_settings()

    @rx.event(background=True)
    async def reset_poi_zone_types_defaults(self):
        async with self:
            zone_types = [t for t, _ in POI_ZONE_TYPES]
            self.poi_display_enabled = {**self.poi_display_enabled, **{t: False for t in zone_types}}
            self.poi_strategy_enabled = {**self.poi_strategy_enabled, **{t: False for t in zone_types}}
            self.poi_zone_max_count = dict(_DEFAULT_ZONE_MAX_COUNT)
            self.poi_zone_color = dict(_DEFAULT_ZONE_COLOR)
            self.poi_zone_type_opacity = dict(_DEFAULT_ZONE_OPACITY)
            self.poi_backend_busy = True
            self._save_poi_zone_settings()
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()

        def _apply():
            for t in zone_types:
                _engine.set_poi_display_enabled(t, False)
                _engine.set_poi_strategy_enabled(t, False)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    def reset_poi_custom_lines_defaults(self) -> None:
        self.poi_custom_lines = _default_custom_lines()
        self._save_custom_lines()

    def reset_poi_visual_controls_defaults(self) -> None:
        self.poi_show_labels = True
        self.poi_show_tooltips = True
        self.poi_show_source_tf_badge = True
        self.poi_show_logical_id = False
        self.poi_reduced_motion = False
        self._save_poi_visual_settings()

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
                "show_source_tf_badge": self.poi_show_source_tf_badge,
                "show_logical_id": self.poi_show_logical_id,
                "reduced_motion": self.poi_reduced_motion,
                "high_line_style": self.poi_high_line_style,
                "high_line_thickness": self.poi_high_line_thickness,
                "low_line_style": self.poi_low_line_style,
                "low_line_thickness": self.poi_low_line_thickness,
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

    def set_poi_high_line_style(self, value: str | list[str]) -> None:
        resolved = value[0] if isinstance(value, list) else value
        self.poi_high_line_style = resolved
        self._save_poi_visual_settings()

    def set_poi_high_line_thickness(self, value: list[float]) -> None:
        self.poi_high_line_thickness = int(value[0])
        self._save_poi_visual_settings()

    def set_poi_low_line_style(self, value: str | list[str]) -> None:
        resolved = value[0] if isinstance(value, list) else value
        self.poi_low_line_style = resolved
        self._save_poi_visual_settings()

    def set_poi_low_line_thickness(self, value: list[float]) -> None:
        self.poi_low_line_thickness = int(value[0])
        self._save_poi_visual_settings()

    # --- Bulk controls (renamed + re-scoped: operate on what is
    # CURRENTLY on the chart, not blanket-all) ---
    @rx.event(background=True)
    async def poi_hide_extras(self):
        """Hide Extras: remembers every POI type currently Display=True,
        then hides exactly those - not a blanket reset of every possible
        type. "Extras" means the objects currently shown on the chart
        beyond the candles/price line themselves."""
        async with self:
            currently_shown = {t: True for t, v in self.poi_display_enabled.items() if v}
            self._poi_hidden_by_extras = currently_shown
            self.poi_display_enabled = {**self.poi_display_enabled, **{t: False for t in currently_shown}}
            self._sync_tf_dicts_from_flat()
            self.poi_backend_busy = True
            _engine.security.persistence.save({"poi_hidden_by_extras": currently_shown})
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()

        def _apply():
            for t in currently_shown:
                _engine.set_poi_display_enabled(t, False)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def poi_show_extras(self):
        """Show Extras: restores Display=True ONLY for the POI types
        that the most recent Hide Extras click actually hid - a no-op if
        nothing was hidden."""
        async with self:
            to_restore = dict(self._poi_hidden_by_extras)
            if not to_restore:
                return
            self.poi_display_enabled = {**self.poi_display_enabled, **to_restore}
            self._sync_tf_dicts_from_flat()
            self._poi_hidden_by_extras = {}
            self.poi_backend_busy = True
            _engine.security.persistence.save({"poi_hidden_by_extras": {}})
            if self.active_tab == "Trading Panel":
                self.refresh_poi_chart_overlays()

        def _apply():
            for t in to_restore:
                _engine.set_poi_display_enabled(t, True)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def poi_enable_default_strategy(self):
        """Strategy = True for the union of the locked default set
        (PDH/PDL/4H_HIGH/4H_LOW) AND every POI type currently
        Display=True (already attached to the chart) - everything else
        resets to False."""
        async with self:
            currently_shown = {t for t, v in self.poi_display_enabled.items() if v}
            target = set(POI_DEFAULT_STRATEGY_TYPES) | currently_shown
            all_types = list(self.poi_strategy_enabled.keys())
            self.poi_strategy_enabled = {t: (t in target) for t in all_types}
            self._sync_tf_dicts_from_flat()
            self.poi_backend_busy = True

        def _apply():
            for t in all_types:
                _engine.set_poi_strategy_enabled(t, t in target)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
                self.poi_backend_busy = False

    @rx.event(background=True)
    async def poi_disable_all_strategy(self):
        """Strategy = False ONLY for POI types currently Display=True
        ("present on chart") - types not currently shown are left
        untouched."""
        async with self:
            currently_shown = [t for t, v in self.poi_display_enabled.items() if v]
            self.poi_strategy_enabled = {**self.poi_strategy_enabled, **{t: False for t in currently_shown}}
            self._sync_tf_dicts_from_flat()
            self.poi_backend_busy = True

        def _apply():
            for t in currently_shown:
                _engine.set_poi_strategy_enabled(t, False)
        try:
            await asyncio.to_thread(_apply)
        finally:
            async with self:
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
            "droplet_enabled": self.poi_tf_droplet_enabled.get(tf, False),
            "vertical_style": self.poi_tf_vertical_style.get(tf, "solid"),
            "vertical_opacity": self.poi_tf_vertical_opacity.get(tf, 50),
        } for tf in POI_LINE_TF_ORDER]

    @rx.var
    def poi_zone_type_rows(self) -> list[dict]:
        return [{
            "type": t, "label": label,
            "display": self.poi_display_enabled.get(t, False),
            "strategy": self.poi_strategy_enabled.get(t, False),
            "color": self.poi_zone_color.get(t, _DEFAULT_ZONE_COLOR.get(t, "#3B82F6")),
            "max_count": self.poi_zone_max_count.get(t, 5),
            "opacity": self.poi_zone_type_opacity.get(t, 30),
        } for t, label in POI_ZONE_TYPES]

    @rx.var
    def poi_zone_source_tf_rows(self) -> list[dict]:
        return [{"tf": tf, "enabled": self.poi_zone_source_tf_enabled.get(tf, False)} for tf in POI_LINE_TF_ORDER]
