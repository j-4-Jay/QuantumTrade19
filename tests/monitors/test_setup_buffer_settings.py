"""PATH: tests/monitors/test_setup_buffer_settings.py  (NEW FILE)

FT-H.3 tests for engines/workers/setup/setup_buffer_settings.py. They use a temporary settings.json,
never the real data/settings.json.
"""
import json

import pytest

from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from engines.workers.setup.setup_buffer_settings import SetupBufferSettings


def make(tmp_path):
    return SetupBufferSettings(SettingsPersistenceWorker(tmp_path / "settings.json"))


def test_default_is_seven_ticks_for_any_symbol(tmp_path):
    s = make(tmp_path)
    assert s.get_default_ticks() == 7
    assert s.get_buffer_ticks("B-BTC_USDT") == 7
    assert s.has_override("B-BTC_USDT") is False


def test_symbol_override_does_not_change_other_symbols(tmp_path):
    s = make(tmp_path)
    assert s.set_buffer_ticks("B-BTC_USDT", 12) == 12
    assert s.get_buffer_ticks("B-BTC_USDT") == 12
    assert s.get_buffer_ticks("B-ETH_USDT") == 7
    assert s.has_override("B-BTC_USDT") is True


def test_values_are_saved_and_come_back_after_restart(tmp_path):
    s = make(tmp_path)
    s.set_buffer_ticks("B-BTC_USDT", 12)
    s.set_default_ticks(9)
    again = make(tmp_path)
    assert again.get_buffer_ticks("B-BTC_USDT") == 12
    assert again.get_buffer_ticks("B-XAU_USDT") == 9
    assert again.overrides() == {"B-BTC_USDT": 12}


def test_changing_the_default_does_not_touch_an_override(tmp_path):
    s = make(tmp_path)
    s.set_buffer_ticks("B-BTC_USDT", 12)
    s.set_default_ticks(3)
    assert s.get_buffer_ticks("B-BTC_USDT") == 12
    assert s.get_buffer_ticks("B-ETH_USDT") == 3


def test_reset_symbol_goes_back_to_the_default(tmp_path):
    s = make(tmp_path)
    s.set_buffer_ticks("B-BTC_USDT", 12)
    assert s.reset_symbol("B-BTC_USDT") is True
    assert s.get_buffer_ticks("B-BTC_USDT") == 7
    assert s.reset_symbol("B-BTC_USDT") is False
    assert s.overrides() == {}


def test_other_per_symbol_keys_are_kept(tmp_path):
    persistence = SettingsPersistenceWorker(tmp_path / "settings.json")
    persistence.set_per_symbol_setting("B-BTC_USDT", "leverage", 20)
    s = SetupBufferSettings(persistence)
    s.set_buffer_ticks("B-BTC_USDT", 5)
    assert persistence.get_per_symbol_setting("B-BTC_USDT", "leverage") == 20
    s.reset_symbol("B-BTC_USDT")
    assert persistence.get_per_symbol_setting("B-BTC_USDT", "leverage") == 20
    assert persistence.get_per_symbol_setting("B-BTC_USDT", "sl_buffer_ticks") is None


def test_empty_symbol_bucket_is_removed_on_reset(tmp_path):
    s = make(tmp_path)
    s.set_buffer_ticks("B-BTC_USDT", 5)
    s.reset_symbol("B-BTC_USDT")
    saved = json.loads((tmp_path / "settings.json").read_text())
    assert "B-BTC_USDT" not in saved["per_symbol_settings"]


@pytest.mark.parametrize("bad", [-1, "abc", "", None, True, float("nan"), float("inf"), 1001])
def test_bad_values_are_refused_and_nothing_is_saved(tmp_path, bad):
    s = make(tmp_path)
    with pytest.raises(ValueError):
        s.set_buffer_ticks("B-BTC_USDT", bad)
    with pytest.raises(ValueError):
        s.set_default_ticks(bad)
    assert s.get_buffer_ticks("B-BTC_USDT") == 7
    assert s.overrides() == {}


def test_text_numbers_from_a_screen_are_accepted(tmp_path):
    s = make(tmp_path)
    assert s.set_buffer_ticks("B-BTC_USDT", "10") == 10
    assert s.set_buffer_ticks("B-ETH_USDT", "2.5") == 2.5
    assert s.set_buffer_ticks("B-XAU_USDT", 0) == 0


def test_blank_symbol_is_refused(tmp_path):
    s = make(tmp_path)
    with pytest.raises(ValueError):
        s.set_buffer_ticks("  ", 5)


def test_damaged_saved_value_falls_back_to_the_default(tmp_path):
    persistence = SettingsPersistenceWorker(tmp_path / "settings.json")
    persistence.set_per_symbol_setting("B-BTC_USDT", "sl_buffer_ticks", "garbage")
    s = SetupBufferSettings(persistence)
    assert s.get_buffer_ticks("B-BTC_USDT") == 7
    assert s.overrides() == {}


def test_buffer_feeds_the_outcome_worker_sl(tmp_path):
    from types import SimpleNamespace
    from engines.workers.setup.setup_outcome_worker import SetupOutcomeWorker
    from engines.workers.setup.setup_types import ConfirmedSetup, SetupDirection

    def cd(n, o, h, l, c):
        return SimpleNamespace(symbol="B-BTC_USDT", timeframe="5m", open_time=n * 300000,
                               close_time=n * 300000 + 299999, open=o, high=h, low=l, close=c)

    setup = ConfirmedSetup(
        event_id="E", symbol="B-BTC_USDT", timeframe="5m", poi_id="P", direction=SetupDirection.BULL,
        c1=cd(1, 101, 102, 99, 100), c2=cd(2, 100, 101, 98, 99), c3=cd(3, 99, 101, 98.5, 100), confirmed_at=0.0,
    )
    s = make(tmp_path)
    s.set_buffer_ticks("B-BTC_USDT", 4)
    out = SetupOutcomeWorker().track(setup, tick_size=0.5, buffer_ticks=s.get_buffer_ticks("B-BTC_USDT"))
    assert out.sl == 96
