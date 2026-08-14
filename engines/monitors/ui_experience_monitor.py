"""UI Experience Monitor - groups the 5 UI Experience Workers behind one interface upward.

PATH: engines/monitors/ui_experience_monitor.py  (REPLACE ENTIRE FILE)

CHANGE (Module 01 gap-closure item 6): added play_sound(event_name) passthrough so callers
go through the Monitor interface instead of reaching into self.sound directly.
"""
from __future__ import annotations
from engines.workers.ui_experience.theme_engine_worker import ThemeEngineWorker
from engines.workers.ui_experience.sound_engine_worker import SoundEngineWorker
from engines.workers.ui_experience.cursor_glow_worker import CursorGlowWorker
from engines.workers.ui_experience.animation_choreographer_worker import AnimationChoreographerWorker
from engines.workers.ui_experience.page_transition_worker import PageTransitionWorker
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker


class UIExperienceMonitor:
    def __init__(self, persistence=None):
        self.persistence = persistence or SettingsPersistenceWorker()
        self.theme = ThemeEngineWorker(self.persistence)
        self.sound = SoundEngineWorker(self.persistence)
        self.cursor = CursorGlowWorker()
        self.choreographer = AnimationChoreographerWorker()
        self.transitions = PageTransitionWorker(self.choreographer)

    def play_sound(self, event_name: str) -> str | None:
        return self.sound.play(event_name)