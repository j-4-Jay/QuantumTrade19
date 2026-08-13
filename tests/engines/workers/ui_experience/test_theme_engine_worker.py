import tempfile
from pathlib import Path
from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker
from engines.workers.ui_experience.theme_engine_worker import ThemeEngineWorker

def test_cycle_all_six():
    with tempfile.TemporaryDirectory() as d:
        w = ThemeEngineWorker(SettingsPersistenceWorker(path=Path(d)/"settings.json"))
        seen = {w.get_active_key()}
        for _ in range(5): seen.add(w.cycle())
        assert len(seen) == 6
