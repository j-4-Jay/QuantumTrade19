"""
FULL PATH: tests/state/test_candle_rows_merge.py
FT-H.34: corrected closed candles reach the chart candle list.
"""
from state.app_state_mixins.candle_rows_merge import merge_rows_by_timestamp


def _row(ts, o=1.0, h=2.0, l=0.5, c=1.5, v=10.0):
    return {"timestamp": ts, "open": o, "high": h, "low": l, "close": c, "volume": v}


def test_corrected_volume_replaces_the_old_row():
    existing = [_row(1), _row(2), _row(3)]
    out = merge_rows_by_timestamp(existing, [_row(2, v=14.0)])
    assert [r["volume"] for r in out] == [10.0, 14.0, 10.0]
    assert existing[1]["volume"] == 10.0


def test_returns_none_when_nothing_changed():
    existing = [_row(1), _row(2)]
    assert merge_rows_by_timestamp(existing, [_row(1), _row(2)]) is None


def test_newer_candles_are_appended_in_order():
    out = merge_rows_by_timestamp([_row(1), _row(2)], [_row(3), _row(4)])
    assert [r["timestamp"] for r in out] == [1, 2, 3, 4]


def test_missing_old_candle_inside_history_is_not_inserted():
    out = merge_rows_by_timestamp([_row(1), _row(3)], [_row(2)])
    assert out is None


def test_empty_inputs_return_none():
    assert merge_rows_by_timestamp([], [_row(1)]) is None
    assert merge_rows_by_timestamp([_row(1)], []) is None
