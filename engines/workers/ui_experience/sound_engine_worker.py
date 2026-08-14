"""Sound_Engine_Worker - tracks the master mute setting and resolves event names to audio
clip URLs. Actual playback happens client-side (this Worker is pure Python and has no
browser access); state/app_state.py triggers the browser Audio object via rx.call_script.

PATH: engines/workers/ui_experience/sound_engine_worker.py  (REPLACE ENTIRE FILE)

CHANGE (Module 01 gap-closure item 6): added play()/get_sound_url() - maps the 6 named UI
events to the placeholder .wav files under assets/sounds/ (served by Reflex at /sounds/*.wav).
Swap these filenames later for branded sound files without touching any calling code.
"""
from __future__ import annotations
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker


_SOUND_FILES: dict[str, str] = {
    "click": "/sounds/click.wav",
    "page-change": "/sounds/page_change.wav",
    "tab-slide": "/sounds/tab_slide.wav",
    "card-flip": "/sounds/card_flip.wav",
    "error": "/sounds/error.wav",
    "success": "/sounds/success.wav",
}


class SoundEngineWorker:
    def __init__(self, persistence: SettingsPersistenceWorker):
        self._persistence = persistence

    def is_master_on(self):
        return bool(self._persistence.load().get("sound_master_on", True))

    def set_master(self, on):
        self._persistence.save({"sound_master_on": on})

    def toggle_master(self):
        new = not self.is_master_on()
        self.set_master(new)
        return new

    def get_sound_url(self, event_name: str) -> str | None:
        """Returns the clip URL for a named event, or None if the name is unknown."""
        return _SOUND_FILES.get(event_name)

    def play(self, event_name: str) -> str | None:
        """Returns the clip URL to play if sound is enabled and the event name is known;
        returns None if muted or unknown (caller should skip playback silently)."""
        if not self.is_master_on():
            return None
        return self.get_sound_url(event_name)