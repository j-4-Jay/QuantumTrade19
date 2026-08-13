"""Custom cursor - REMOVED per request. This is now a no-op.

PATH: ui/components/cursor_glow.py  (REPLACE ENTIRE FILE)

Kept the same function name/signature (qt19_cursor_glow) so every page that already calls it
(splash, login, register, forgot_password, manage_security, app_lock, page_shell) needs zero
changes - it now simply renders nothing, restoring the plain default Windows/OS cursor
everywhere (combined with the `cursor: "none"` removal in ui/theme/glass.py).
"""
from __future__ import annotations
import reflex as rx


def qt19_cursor_glow() -> rx.Component:
    """No-op - custom cursor feature removed. Returns an empty fragment."""
    return rx.fragment()
