import tempfile
from pathlib import Path
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from engines.workers.ui_experience.sound_engine_worker import SoundEngineWorker

def test_toggle():
    with tempfile.TemporaryDirectory() as d:
        w = SoundEngineWorker(SettingsPersistenceWorker(path=Path(d)/"settings.json"))
        was_on = w.is_master_on(); new = w.toggle_master()
        assert new != was_on
