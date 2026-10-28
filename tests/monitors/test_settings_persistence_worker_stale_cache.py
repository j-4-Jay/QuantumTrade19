"""Tests: two settings workers on one file must not undo each other (thread 004).

PATH: tests/monitors/test_settings_persistence_worker_stale_cache.py  (NEW FILE)
"""
import json
import tempfile
import unittest
from pathlib import Path

from engines.workers.security.settings_persistence_worker import SettingsPersistenceWorker


class StaleCacheTests(unittest.TestCase):
    def test_second_worker_does_not_undo_first_workers_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            first = SettingsPersistenceWorker(path=path)
            second = SettingsPersistenceWorker(path=path)
            first.save({"poi_engine_settings": {"flag": False}})
            second.load()
            first.save({"poi_engine_settings": {"flag": True}})
            second.save({"active_tab": "Settings"})
            on_disk = json.loads(path.read_text())
            self.assertTrue(on_disk["poi_engine_settings"]["flag"])
            self.assertEqual(on_disk["active_tab"], "Settings")

    def test_save_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            SettingsPersistenceWorker(path=path).save({"a": 1})
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["settings.json"])

    def test_memory_mode_never_touches_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            worker = SettingsPersistenceWorker(path=path, force_memory=True)
            worker.save({"a": 1})
            self.assertFalse(path.exists())
            self.assertEqual(worker.load()["a"], 1)

    def test_broken_file_is_not_wiped_by_a_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            worker = SettingsPersistenceWorker(path=path)
            worker.save({"keep": "yes"})
            path.write_text("{ broken")
            worker.save({"other": 2})
            on_disk = json.loads(path.read_text())
            self.assertEqual(on_disk["keep"], "yes")
            self.assertEqual(on_disk["other"], 2)


if __name__ == "__main__":
    unittest.main()

