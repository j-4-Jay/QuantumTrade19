"""PATH: tests/monitors/test_setup_buffer_view.py  (NEW FILE)

FT-H.3 Step B tests for engines/workers/setup/setup_buffer_view.py (temporary settings.json only).
"""
from types import SimpleNamespace

from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from engines.workers.setup.setup_buffer_settings import SetupBufferSettings
from engines.workers.setup.setup_buffer_view import buffer_rows


def make(tmp_path):
    return SetupBufferSettings(SettingsPersistenceWorker(tmp_path / "settings.json"))


def test_one_row_per_symbol_with_the_default(tmp_path):
    rows = buffer_rows(make(tmp_path), ["B-BTC_USDT", "B-ETH_USDT"])
    assert rows == [
        {"symbol": "B-BTC_USDT", "ticks": "7", "custom": "no"},
        {"symbol": "B-ETH_USDT", "ticks": "7", "custom": "no"},
    ]


def test_override_is_marked_and_shows_its_value(tmp_path):
    s = make(tmp_path)
    s.set_buffer_ticks("B-ETH_USDT", 2.5)
    rows = buffer_rows(s, ["B-BTC_USDT", "B-ETH_USDT"])
    assert rows[1] == {"symbol": "B-ETH_USDT", "ticks": "2.5", "custom": "yes"}
    assert rows[0]["custom"] == "no"


def test_default_change_shows_in_rows_without_override(tmp_path):
    s = make(tmp_path)
    s.set_default_ticks(10)
    assert buffer_rows(s, ["B-BTC_USDT"])[0]["ticks"] == "10"


def test_symbols_can_be_text_objects_or_dicts(tmp_path):
    rows = buffer_rows(make(tmp_path), ["A", SimpleNamespace(symbol="B"), {"symbol": "C"}])
    assert [r["symbol"] for r in rows] == ["A", "B", "C"]


def test_duplicates_blanks_and_junk_are_dropped(tmp_path):
    rows = buffer_rows(make(tmp_path), ["A", "A", " ", "", None, SimpleNamespace()])
    assert [r["symbol"] for r in rows] == ["A"]


def test_saved_override_of_a_symbol_not_in_the_list_is_appended_sorted(tmp_path):
    s = make(tmp_path)
    s.set_buffer_ticks("Z-OLD", 3)
    s.set_buffer_ticks("A-OLD", 4)
    rows = buffer_rows(s, ["B-BTC_USDT"])
    assert [r["symbol"] for r in rows] == ["B-BTC_USDT", "A-OLD", "Z-OLD"]
    assert rows[1]["custom"] == "yes"


def test_empty_or_missing_symbol_list(tmp_path):
    s = make(tmp_path)
    assert buffer_rows(s, []) == []
    assert buffer_rows(s, None) == []
