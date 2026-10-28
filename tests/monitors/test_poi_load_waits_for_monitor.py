"""Test: load_poi_settings waits for the POI monitor instead of loading an empty answer (thread 004).

PATH: tests/monitors/test_poi_load_waits_for_monitor.py  (NEW FILE)
"""
import unittest
from types import SimpleNamespace
from unittest import mock

from state.app_state_mixins import poi_settings_mixin


def _fake_state():
    return SimpleNamespace(
        poi_settings_loaded=False,
        active_tab="Settings",
        poi_display_enabled={},
        poi_strategy_enabled={},
        poi_zone_source_tf_enabled={},
        poi_timezone_mode="NY",
    )


class LoadWaitsForMonitorTests(unittest.TestCase):
    def test_empty_engine_answer_does_not_mark_loaded(self):
        state = _fake_state()
        engine = mock.MagicMock()
        engine.get_poi_settings.return_value = {}
        with mock.patch.object(poi_settings_mixin, "_engine", engine):
            poi_settings_mixin.PoiSettingsMixin.load_poi_settings(state)
        self.assertFalse(state.poi_settings_loaded)
        self.assertEqual(state.poi_display_enabled, {})

    def test_second_call_loads_when_monitor_is_ready(self):
        state = _fake_state()
        engine = mock.MagicMock()
        engine.security.persistence.load.return_value = {}
        with mock.patch.object(poi_settings_mixin, "_engine", engine):
            engine.get_poi_settings.return_value = {}
            poi_settings_mixin.PoiSettingsMixin.load_poi_settings(state)
            engine.get_poi_settings.return_value = {
                "display_enabled": {"1W_HIGH": True},
                "strategy_enabled": {"1W_HIGH": True},
                "zone_source_tf_enabled": {},
                "timezone_mode": "NY",
            }
            poi_settings_mixin.PoiSettingsMixin.load_poi_settings(state)
        self.assertTrue(state.poi_settings_loaded)
        self.assertTrue(state.poi_display_enabled["1W_HIGH"])


if __name__ == "__main__":
    unittest.main()

