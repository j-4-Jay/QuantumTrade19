from __future__ import annotations
SPRING_TRANSITION = {"type": "spring", "stiffness": 220, "damping": 22, "mass": 0.9}

class AnimationChoreographerWorker:
    def default(self): return dict(SPRING_TRANSITION)
