"""Global Enter/Escape keyboard shortcuts.

PATH: ui/components/keyboard_shortcuts.py  (NEW FILE)

Rather than wiring a Reflex event handler into every single form, each screen just marks its
one primary action button with id="qt19-primary-action" and its one back/cancel button with
id="qt19-secondary-action" (only one screen is ever mounted at a time, so there's never an ID
collision). This one global listener then does plain `.click()` on whichever is present -
Enter submits, Escape backs out/cancels. The Logout dialog uses its own distinct IDs so it
takes priority over whatever screen it's floating on top of.
"""
from __future__ import annotations
import reflex as rx


def qt19_keyboard_shortcuts() -> rx.Component:
    return rx.script(
        """
        document.addEventListener('keydown', function(e) {
            const tag = (e.target.tagName || '').toLowerCase();
            const dialogOpen = document.getElementById('qt19-logout-dialog');

            if (e.key === 'Enter') {
                if (tag === 'textarea') return;
                if (dialogOpen) {
                    const primary = document.getElementById('qt19-logout-primary');
                    if (primary) { e.preventDefault(); primary.click(); }
                    return;
                }
                const primary = document.getElementById('qt19-primary-action');
                if (primary && !primary.disabled) { e.preventDefault(); primary.click(); }
            } else if (e.key === 'Escape') {
                if (dialogOpen) {
                    const cancelBtn = document.getElementById('qt19-logout-cancel');
                    if (cancelBtn) { e.preventDefault(); cancelBtn.click(); }
                    return;
                }
                const secondary = document.getElementById('qt19-secondary-action');
                if (secondary) { e.preventDefault(); secondary.click(); }
            }
        });
        """
    )
