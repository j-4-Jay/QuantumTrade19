"""File 03.1 POIMonitor settings and zone-source control integration checks."""
from __future__ import annotations

from pathlib import Path

from engines.monitors.poi_monitor import POIMonitor
from engines.workers.poi.poi_settings import POISettingsStore
from engines.workers.poi.poi_types import POIType
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from tests.workers.poi.poi_test_helpers import FakeMarketDataMonitor, FakeSymbolRegistry, candle

SYMBOLS = ("B-BTC_USDT", "B-ETH_USDT")


def _monitor(tmp_path: Path) -> POIMonitor:
    mdm = FakeMarketDataMonitor()
    for tf in ("1m", "5m", "15m", "1H", "4H", "1D", "1W", "1M"):
        mdm.set_series(tf, [
            candle(100, 102, 98, 101),
            candle(101, 105, 95, 100),
            candle(100, 103, 99, 102),
        ])
        mdm.set_live(tf, candle(100, 103, 99, 102))
    store = POISettingsStore(SettingsPersistenceWorker(tmp_path / "settings.json"))
    return POIMonitor(mdm, FakeSymbolRegistry(SYMBOLS), settings_store=store)


def test_display_and_strategy_controls_are_independent_and_persist(tmp_path: Path) -> None:
    monitor = _monitor(tmp_path)
    monitor.set_poi_display_enabled(POIType.PDH, False)
    assert monitor.get_poi_settings()["display_enabled"][POIType.PDH] is False
    assert monitor.get_poi_settings()["strategy_enabled"][POIType.PDH] is True
    monitor.set_poi_strategy_enabled(POIType.PDH, False)
    assert monitor.get_poi_settings()["display_enabled"][POIType.PDH] is False
    assert monitor.get_poi_settings()["strategy_enabled"][POIType.PDH] is False
    restored = POISettingsStore(SettingsPersistenceWorker(tmp_path / "settings.json")).get()
    assert restored.display_enabled[POIType.PDH] is False
    assert restored.strategy_enabled[POIType.PDH] is False


def test_zone_source_tf_setting_fans_out_and_persists(tmp_path: Path) -> None:
    monitor = _monitor(tmp_path)
    monitor.set_zone_source_tf_enabled("5m", True)
    assert monitor.get_poi_settings()["zone_source_tf_enabled"]["5m"] is True
    for symbol in SYMBOLS:
        assert monitor._level_workers[symbol].zone_source_tf_enabled["5m"] is True
        assert monitor._fvg_workers[symbol].zone_source_tf_enabled["5m"] is True
        assert monitor._ob_workers[symbol].zone_source_tf_enabled["5m"] is True
        assert monitor._inv_workers[symbol].zone_source_tf_enabled["5m"] is True
    restored = POISettingsStore(SettingsPersistenceWorker(tmp_path / "settings.json")).get()
    assert restored.zone_source_tf_enabled["5m"] is True


def test_legacy_type_toggle_maps_to_strategy_control(tmp_path: Path) -> None:
    monitor = _monitor(tmp_path)
    monitor.set_poi_type_enabled(POIType.FVG, True)
    assert monitor.get_poi_settings()["strategy_enabled"][POIType.FVG] is True
    assert all(monitor._fvg_workers[symbol].strategy_enabled[POIType.FVG] for symbol in SYMBOLS)
