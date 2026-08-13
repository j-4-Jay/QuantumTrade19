"""PATH: rxconfig.py  (REPLACE ENTIRE FILE)

FIX: silences the repeated "SitemapPlugin ... not explicitly added" warning by explicitly
disabling it, exactly as the warning itself suggested. Import is defensive - if your installed
Reflex version moved the plugin's module path, this falls back to the plain config instead of
crashing the app over a cosmetic warning.
"""
import reflex as rx

try:
    from reflex_base.plugins.sitemap import SitemapPlugin
    config = rx.Config(app_name="quantumtrade19", disable_plugins=[SitemapPlugin])
except ImportError:
    config = rx.Config(app_name="quantumtrade19")
