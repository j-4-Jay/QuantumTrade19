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

def test_middle_click_close_is_supported():
    assert 'root.addEventListener("auxclick"' in CANDLE_INFO_POPUP_JS
    assert "e.button === 1" in CANDLE_INFO_POPUP_JS


def test_compact_resize_toggle_and_cursors():
    for text in ('grip.addEventListener("dblclick"', "p.nextCompact = !p.compact", "MIN_W = 280, MIN_H = 248", "qt19-cip-dragging", "qt19-cip-resizing"):
        assert text in CANDLE_INFO_POPUP_JS


def test_visibility_notice_uses_actions_not_extra_polling():
    assert "chart.subscribeAction(action, n.changed)" in CANDLE_INFO_POPUP_JS
    assert "n.chart.unsubscribeAction(action, n.changed)" in CANDLE_INFO_POPUP_JS
    assert "p.note.textContent === n.text" in CANDLE_INFO_POPUP_JS
    assert CANDLE_INFO_POPUP_JS.count("setInterval(") == 1


def test_db_errors_are_not_missing_rows_and_live_is_time_checked():
    assert 'if (payload.error) { p.note.textContent = "Database read failed;' in CANDLE_INFO_POPUP_JS
    assert "cur.isLast && Date.now() < p.ts + p.dur" in CANDLE_INFO_POPUP_JS


def test_comparison_runs_once_at_creation_and_button_reuses_it():
    assert "askDb(st, p);\n    askCompare(st, p);" in CANDLE_INFO_POPUP_JS
    assert 'bX.addEventListener("click", function () { askCompare(st, p); });' in CANDLE_INFO_POPUP_JS
    assert CANDLE_INFO_POPUP_JS.count('st.opts.request("compare",') == 1
    assert 'p.compareState === "pending") return;' in CANDLE_INFO_POPUP_JS


def test_comparison_badge_waits_for_both_complete_value_sets():
    for text in ('p.vals && p.cx && LABELS.every', 'Number.isFinite(Number(p.vals[k]))',
                 'CoinDCX: waiting for candle values', 'CoinDCX: matches (5/5)',
                 'CoinDCX: differs (', 'updateComparison(p);'):
        assert text in CANDLE_INFO_POPUP_JS


def test_compact_comparison_is_outside_hidden_footer():
    assert '[bR, bA, bC].forEach' in CANDLE_INFO_POPUP_JS
    assert 'compareBar.appendChild(compareBadge); compareBar.appendChild(bX);' in CANDLE_INFO_POPUP_JS
    assert '.qt19-cip.compact .qt19-cip-compare{display:flex}' in CANDLE_INFO_POPUP_JS
    assert 'p.compareState = "unavailable"' in CANDLE_INFO_POPUP_JS


def test_resize_hover_has_raised_hit_area_and_explicit_cursor():
    assert '.qt19-cip-g{position:absolute;z-index:20;' in CANDLE_INFO_POPUP_JS
    assert 'width:22px;height:22px;pointer-events:auto;cursor:nwse-resize!important' in CANDLE_INFO_POPUP_JS
    assert '.qt19-cip-g:hover{cursor:nwse-resize!important}' in CANDLE_INFO_POPUP_JS



