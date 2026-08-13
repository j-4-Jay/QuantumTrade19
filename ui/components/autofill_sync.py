"""Browser-autofill sync fix.

PATH: ui/components/autofill_sync.py  (NEW FILE)

Chrome/Edge autofill sets an input's value directly at the browser level, WITHOUT firing the
event React (and therefore Reflex's on_change) listens for - the field looks filled, but
AppState.login_username/login_password genuinely stay empty. This is a well-known Chromium
quirk with any React-based framework, with a standard fix: the CSS in global_css.py
(`input:-webkit-autofill { animation-name: qt19-autofill-detect; }`) makes the browser fire a
CSS animationstart event the instant its own autofill engine fills a field. We listen for
that here, then manually dispatch a real "input" event on the same element - which IS
something React's synthetic event system picks up, finally syncing the real value into state.
"""
from __future__ import annotations
import reflex as rx


def qt19_autofill_sync() -> rx.Component:
    return rx.script(
        """
        document.addEventListener('animationstart', function(e) {
            if (e.animationName === 'qt19-autofill-detect') {
                const el = e.target;
                setTimeout(function() {
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }, 0);
            }
        }, true);
        """
    )
