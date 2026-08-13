from __future__ import annotations
from engines.workers.ui_experience.animation_choreographer_worker import AnimationChoreographerWorker

class PageTransitionWorker:
    def __init__(self, choreographer: AnimationChoreographerWorker):
        self._choreographer = choreographer
