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
