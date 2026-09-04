"""PATH: rxconfig.py  (REPLACE ENTIRE FILE)

TARGET PATH: D:\QuantumTrade19\rxconfig.py

FIX v0.4.9c: Reflex's own REFLEX_HOT_RELOAD_EXCLUDE_PATHS always splits its
value on a literal colon (":"), confirmed directly in Reflex's source
(packages/reflex-base/src/reflex_base/environment.py: "Separated by a
colon."). On Windows, any ABSOLUTE path such as "D:\QuantumTrade19\data"
already contains a colon (the drive letter), so Reflex's own parser splits
it into "D" and "\QuantumTrade19\data", corrupting the path into garbage
like "D:\QuantumTrade19\D" - which is exactly what crashed on both previous
attempts (using ":" and ";" as MY join separator made no difference, because
Reflex re-splits on ":" internally regardless).

Fix: use RELATIVE folder names only (no colon possible) - "data", "logs",
".web", "tracker_files" - and force os.chdir() to this file's own directory
first, so Reflex's Path.absolute() resolution always lands on the correct
D:\QuantumTrade19\<folder> path regardless of the working directory the app
was launched from.

Still keeps the v0.4.7 SitemapPlugin fix: rx.plugins.SitemapPlugin is the
correct, documented path (reflex_base.plugins.sitemap does not exist), with a
defensive fallback kept only in case a future Reflex version moves it again -
it will not crash the app over a cosmetic warning either way.
"""
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(_PROJECT_ROOT)

_EXCLUDED_RELATIVE_NAMES = ["data", "logs", ".web", "tracker_files"]

for _name in _EXCLUDED_RELATIVE_NAMES:
    (_PROJECT_ROOT / _name).mkdir(parents=True, exist_ok=True)

# Reflex splits this value on ":" internally - relative names never contain
# a colon, so they survive that split intact even on Windows.
os.environ["REFLEX_HOT_RELOAD_EXCLUDE_PATHS"] = ":".join(_EXCLUDED_RELATIVE_NAMES)

import reflex as rx

try:
    config = rx.Config(app_name="quantumtrade19", disable_plugins=[rx.plugins.SitemapPlugin])
except AttributeError:
    config = rx.Config(app_name="quantumtrade19")
