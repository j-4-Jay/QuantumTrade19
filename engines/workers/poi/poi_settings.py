"""Persistent File 03.1 POI display, strategy, and zone-source settings.

PATH: engines/workers/poi/poi_settings.py (REPLACE ENTIRE FILE)

FIX (Timezone Mode toggle) - added timezone_mode: str = "NY" ("UTC" or
"NY") - persisted alongside the existing display/strategy/zone-source
settings. Default is "NY" per explicit request; existing installs with
no saved value also default to "NY" going forward (not "UTC") - if you
want existing users to keep seeing UTC-cut levels until they explicitly
opt in, tell me and I'll flip this one default line.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker

from .poi_types import (
    DEFAULT_DISPLAY_ENABLED,
    DEFAULT_STRATEGY_ENABLED,
    DEFAULT_ZONE_SOURCE_TF_ENABLED,
    POIType,
    ZONE_SOURCE_TFS,
)


SETTINGS_KEY = "poi_engine_settings"


@dataclass
class POISettings:
    """Independent POI rendering, strategy, and zone-source controls."""

    display_enabled: Dict[str, bool] = field(
        default_factory=lambda: dict(DEFAULT_DISPLAY_ENABLED)
    )
    strategy_enabled: Dict[str, bool] = field(
        default_factory=lambda: dict(DEFAULT_STRATEGY_ENABLED)
    )
    zone_source_tf_enabled: Dict[str, bool] = field(
        default_factory=lambda: dict(DEFAULT_ZONE_SOURCE_TF_ENABLED)
    )
    timezone_mode: str = "NY"

    @classmethod
    def from_dict(cls, value: Dict[str, Any] | None) -> "POISettings":
        value = value or {}
        display = dict(DEFAULT_DISPLAY_ENABLED)
        strategy = dict(DEFAULT_STRATEGY_ENABLED)
        zone_tfs = dict(DEFAULT_ZONE_SOURCE_TF_ENABLED)

        display.update(
            {
                key: bool(enabled)
                for key, enabled in value.get("display_enabled", {}).items()
                if key in POIType._value2member_map_
            }
        )
        strategy.update(
            {
                key: bool(enabled)
                for key, enabled in value.get("strategy_enabled", {}).items()
                if key in POIType._value2member_map_
            }
        )
        zone_tfs.update(
            {
                tf: bool(enabled)
                for tf, enabled in value.get("zone_source_tf_enabled", {}).items()
                if tf in ZONE_SOURCE_TFS
            }
        )
        timezone_mode = value.get("timezone_mode", "NY")
        if timezone_mode not in ("UTC", "NY"):
            timezone_mode = "NY"
        return cls(
            display_enabled=display,
            strategy_enabled=strategy,
            zone_source_tf_enabled=zone_tfs,
            timezone_mode=timezone_mode,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display_enabled": dict(self.display_enabled),
            "strategy_enabled": dict(self.strategy_enabled),
            "zone_source_tf_enabled": dict(self.zone_source_tf_enabled),
            "timezone_mode": self.timezone_mode,
        }


class POISettingsStore:
    """SettingsPersistenceWorker adapter for the File 03.1 POI setting group."""

    def __init__(
        self,
        persistence: SettingsPersistenceWorker | None = None,
    ) -> None:
        self._persistence = persistence or SettingsPersistenceWorker()
        self._settings = POISettings.from_dict(
            self._persistence.load().get(SETTINGS_KEY)
        )

    def get(self) -> POISettings:
        return self._settings

    def save(self) -> None:
        self._persistence.save({SETTINGS_KEY: self._settings.to_dict()})

    def set_display_enabled(self, poi_type: str, enabled: bool) -> None:
        self._require_poi_type(poi_type)
        self._settings.display_enabled[poi_type] = bool(enabled)
        self.save()

    def set_strategy_enabled(self, poi_type: str, enabled: bool) -> None:
        self._require_poi_type(poi_type)
        self._settings.strategy_enabled[poi_type] = bool(enabled)
        self.save()

    def set_zone_source_tf_enabled(self, timeframe: str, enabled: bool) -> None:
        if timeframe not in ZONE_SOURCE_TFS:
            raise ValueError(f"Unsupported zone source timeframe: {timeframe}")
        self._settings.zone_source_tf_enabled[timeframe] = bool(enabled)
        self.save()

    def set_timezone_mode(self, mode: str) -> None:
        self._settings.timezone_mode = mode if mode in ("UTC", "NY") else "NY"
        self.save()

    @staticmethod
    def _require_poi_type(poi_type: str) -> None:
        if poi_type not in POIType._value2member_map_:
            raise ValueError(f"Unknown POI type: {poi_type}")
