"""Page_Transition_Worker - decides which named CSS transition effect plays on each
screen-to-screen change.

PATH: engines/workers/ui_experience/page_transition_worker.py  (REPLACE ENTIRE FILE)

CHANGE (Module 01 gap-closure item 7): this was an empty stub - __init__ only, no methods.
Moved the single/sequential/shuffle selection logic here from state/app_state.py's
_pick_transition_effect(), which previously reimplemented this inline and never actually
called either this Worker or the Choreographer. The Choreographer supplies the effect names
and CSS class mapping; this Worker decides *which one* fires next, given the user's enabled
pool and chosen mode.
"""
from __future__ import annotations
import random
from engines.workers.ui_experience.animation_choreographer_worker import AnimationChoreographerWorker


class PageTransitionWorker:
    def __init__(self, choreographer: AnimationChoreographerWorker):
        self._choreographer = choreographer

    def pick(self, enabled_effects: list[str], mode: str, sequence_index: int) -> tuple[str, int]:
        """Returns (effect_name, next_sequence_index). `enabled_effects` should already be
        filtered to the user's Settings selection; falls back to 'dissolve' if the pool is
        empty. `sequence_index` is only advanced in 'sequential' mode - callers should
        persist and pass it back in on the next call."""
        pool = enabled_effects or ["dissolve"]
        if mode == "single":
            return pool[0], sequence_index
        if mode == "sequential":
            idx = sequence_index % len(pool)
            return pool[idx], idx + 1
        return random.choice(pool), sequence_index

    def css_class(self, effect: str) -> str:
        return self._choreographer.css_class_for(effect)