"""FT-H.39 candle info popup: checks on the browser code text (no browser needed)."""
from ui.components.candle_info_popup_js import CANDLE_INFO_POPUP_JS, candle_info_popup_script


def test_script_function_returns_the_constant():
    assert candle_info_popup_script() is CANDLE_INFO_POPUP_JS


def test_public_api_names_exist():
    for name in ("QT19CandlePopup", "attach", "detach", "closeAll", "receive"):
        assert name in CANDLE_INFO_POPUP_JS


def test_limits_match_the_spec():
    assert "MAX = 10" in CANDLE_INFO_POPUP_JS
    assert "SYNC_MS = 15000" in CANDLE_INFO_POPUP_JS
    assert "holdMs) || 2000" in CANDLE_INFO_POPUP_JS
    assert "appearMs : 750" in CANDLE_INFO_POPUP_JS


def test_braces_and_parentheses_balance():
    assert CANDLE_INFO_POPUP_JS.count("{") == CANDLE_INFO_POPUP_JS.count("}")
    assert CANDLE_INFO_POPUP_JS.count("(") == CANDLE_INFO_POPUP_JS.count(")")


def test_no_blur_filter_and_no_polling_loop():
    assert "backdrop-filter" not in CANDLE_INFO_POPUP_JS
    assert "setInterval(" in CANDLE_INFO_POPUP_JS
    assert CANDLE_INFO_POPUP_JS.count("setInterval(") == 1

def test_candle_locator_is_bounded_and_timestamp_matched():
    for text in ("function highlightCandle(st, p)", "indexOfTs(list, p.ts)", "elapsed >= 2000", "st.opts.getTf() !== p.tf", "cancelAnimationFrame(st.highlight.frame)"):
        assert text in CANDLE_INFO_POPUP_JS


def test_candle_locator_preserves_controls_and_reduced_motion():
    assert 'closest("button,.qt19-cip-h,.qt19-cip-g")' in CANDLE_INFO_POPUP_JS
    assert 'reduced(st) ? "0.85"' in CANDLE_INFO_POPUP_JS
    assert "pointer-events:none;z-index:49" in CANDLE_INFO_POPUP_JS

