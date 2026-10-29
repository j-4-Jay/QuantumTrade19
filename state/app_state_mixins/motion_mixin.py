"""Executable AppState mixin: global Reduced motion switch (FT-U.5.3).

PATH: state/app_state_mixins/motion_mixin.py  (NEW FILE)

One switch for the whole software. Default OFF, so every effect shows.
When ON, the page shell adds the class qt19-reduce-motion, and the global
CSS turns off all animations and transitions under it.
"""
from __future__ import annotations

import reflex as rx

from state.app_state_mixins.shared import _engine


class MotionMixin(rx.State, mixin=True):
    motion_reduced: bool = False

    def set_motion_reduced(self, checked: bool) -> None:
        self.motion_reduced = bool(checked)
        _engine.security.persistence.save({"motion_reduced": bool(checked)})
