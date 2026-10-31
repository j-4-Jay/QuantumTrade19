"""PATH: tests/monitors/test_callout_renderer_js.py  (NEW FILE)
FT-H.16 step 1 - simple structure checks for the callout browser code text."""
from ui.components.callout_renderer_js import CALLOUT_RENDERER_JS as JS


def test_main_functions_exist():
    for name in ("qt19BuildCallout", "qt19ShowScorePopup", "qt19ClosePopup", "qt19PopupOutside", "QT19_STATE_LOOK", "QT19_MINI", "QT19_BIG"):
        assert name in JS


def test_state_names_and_popup_text():
    for text in ("Running", "SL Hit", "Win", "B.E.", "Score Table Coming Soon", "CONFIDENCE SCORE"):
        assert text in JS


def test_no_python_quote_clash_and_braces_balanced():
    assert chr(34) * 3 not in JS
    assert JS.count("{") == JS.count("}")
    assert JS.count("(") == JS.count(")")
