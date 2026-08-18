"""PATH: rxconfig.py  (REPLACE ENTIRE FILE)

FIX: the previous version tried to import SitemapPlugin from
`reflex_base.plugins.sitemap`, which is not a real, public import path in
Reflex. That import always failed, silently fell back to a plain config, and
the plugin was NEVER actually disabled. The correct, documented location is
`rx.plugins.SitemapPlugin` (see Reflex Plugins API reference). This version
uses that real path, with a defensive fallback kept only in case a future
Reflex version moves it again - it will not crash the app over a cosmetic
warning either way.
"""
import reflex as rx

try:
    config = rx.Config(app_name="quantumtrade19", disable_plugins=[rx.plugins.SitemapPlugin])
except AttributeError:
    config = rx.Config(app_name="quantumtrade19")
