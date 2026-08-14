"""Animation_Choreographer_Worker - reusable motion presets for the whole app.

PATH: engines/workers/ui_experience/animation_choreographer_worker.py  (REPLACE ENTIRE FILE)

CHANGE (Module 01 gap-closure item 7): added the canonical list of transition effect names
and the CSS class mapping. This is now the single source of truth for which effects exist -
must stay in sync with the qt19-transition-* classes defined in ui/theme/global_css.py.
Previously this list was only implicitly defined via string literals scattered across
config/settings.py, settings_persistence_worker.py defaults, and app_state.py.
"""
from __future__ import annotations
SPRING_TRANSITION = {"type": "spring", "stiffness": 220, "damping": 22, "mass": 0.9}
ERROR_SHAKE_CLASS = "qt19-shake"

TRANSITION_EFFECT_NAMES: list[str] = [
    "dissolve", "zoom-in", "zoom-out", "slide-up", "slide-down",
    "slide-left", "slide-right", "flip-x", "flip-y", "blur-in",
]


class AnimationChoreographerWorker:
    def default(self):
        return dict(SPRING_TRANSITION)

    def error_preset(self) -> str:
        return ERROR_SHAKE_CLASS

    def all_transition_effects(self) -> list[str]:
        """Canonical list of every screen-transition effect this app supports."""
        return list(TRANSITION_EFFECT_NAMES)

    def css_class_for(self, effect: str) -> str:
        return f"qt19-transition-{effect}"