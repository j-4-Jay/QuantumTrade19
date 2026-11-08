"""FT-H.26 countdown structural checks; actual browser verification remains required."""
from pathlib import Path
from ui.components.chart_countdown_js import CHART_COUNTDOWN_JS


def test_countdown_matches_header_size_and_flip_duration():
    for text in ("font-size:1.3rem", "font-weight:800", ".4s cubic-bezier(.2,.9,.25,1)", "rotateX(90deg)"):
        assert text in CHART_COUNTDOWN_JS


def test_countdown_format_is_total_minutes_seconds_and_suffix():
    assert 'Math.floor(secs / 60)' in CHART_COUNTDOWN_JS
    assert 'secs % 60' in CHART_COUNTDOWN_JS
    assert '+ " s"' in CHART_COUNTDOWN_JS


def test_countdown_does_not_animate_position_or_poll_at_250ms():
    assert "transition:none" in CHART_COUNTDOWN_JS
    assert "setInterval(" not in CHART_COUNTDOWN_JS
    assert "1000 - (Date.now() % 1000) + 5" in CHART_COUNTDOWN_JS
    assert "if (!dead && !frame)" in CHART_COUNTDOWN_JS


def test_countdown_anchors_to_latest_close_and_cleans_up():
    for text in ("dataIndex:list.length - 1,value:last.close", "pixel.y - 4", "cancelAnimationFrame(frame)", "clearTimeout(timer)", "qt19-reduce-motion"):
        assert text in CHART_COUNTDOWN_JS


def test_countdown_uses_main_plot_not_full_host_for_axis_edge():
    for text in ('chart.getDom("candle_pane", "main")', 'plot.right - box.left', 'AXIS_GAP = 6', 'var width = el.offsetWidth'):
        assert text in CHART_COUNTDOWN_JS


def test_countdown_prioritizes_whole_capsule_visibility_over_candle_spacing():
    for text in ('var candleToBorder = 3.5 * bar', 'var minX = left + AXIS_GAP', 'var maxX = right - AXIS_GAP - width', 'Math.max(minX, Math.min(maxX, naturalX))'):
        assert text in CHART_COUNTDOWN_JS
    assert 'baseline' not in CHART_COUNTDOWN_JS
    assert 'x >= right || x + width <= left' not in CHART_COUNTDOWN_JS


def test_countdown_draws_above_candles_without_blocking_chart_input():
    assert 'el.style.zIndex = "40"' in CHART_COUNTDOWN_JS
    assert 'pointer-events:none' in CHART_COUNTDOWN_JS
    assert 'top + pixel.y - 4' in CHART_COUNTDOWN_JS


def test_reset_reserves_full_border_box_and_three_complete_bar_widths():
    for text in ('Math.ceil(candleToBorder + width + AXIS_GAP)', 'var width = el.offsetWidth',
                 'if (reservePending)', 'reservePending = false', 'chart.scrollToRealTime(0)',
                 'chart.__qt19LiveOff = chart.getOffsetRightDistance()'):
        assert text in CHART_COUNTDOWN_JS


def test_reset_handler_calls_countdown_hook_and_cleanup_removes_it():
    path = Path(__file__).resolve().parents[1] / "state/app_state_mixins/trading_panel_mixin.py"
    code = path.read_text(encoding="utf-8")
    assert "chart.__qt19CountdownReset();" in code
    assert "delete ownerChart.__qt19CountdownReset" in CHART_COUNTDOWN_JS



def test_countdown_fails_closed_without_valid_plot_bounds():
    assert '!box || !plot || plot.width <= 0' in CHART_COUNTDOWN_JS
    assert 'width + 2 * AXIS_GAP > plot.width' in CHART_COUNTDOWN_JS



def test_chart_countdown_is_not_driven_only_by_clock():
    path = Path(__file__).resolve().parents[1] / "ui/components/kline_chart.py"
    code = path.read_text(encoding="utf-8")
    for text in ("const result = callback(...args);", "qt19CountdownSchedule();", '"onPaneDrag"', "new ResizeObserver(qt19CountdownSchedule)", "countdownActionCleanupRef.current"):
        assert text in code
    assert "setInterval(qt19CountdownTick, 250)" not in code
