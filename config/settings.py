"""Module 01 - UI/UX & App Shell. Global static config.

PATH: config/settings.py  (REPLACE ENTIRE FILE)

CHANGE (v0.3.7): added Lime Green Day/Night as a 4th theme hue (8 total
themes now). Existing Yellow/Saffron/Blue themes are untouched.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

APP_NAME: str = "QuantumTrade19"
APP_SUBHEADING: str = "by Jayprakash Pattnaik"
APP_TAGLINE: str = "Precision. Quantum. Profits."
APP_VERSION: str = "v0.1.0-alpha"
SIDEBAR_TABS: list[str] = ["Dashboard", "Trading Panel", "Journal & Reports", "Alerts", "Settings"]
SPLASH_DURATION_SECONDS: float = 5.0
SPLASH_HOLD_SECONDS: float = 2.0

ThemeHue = Literal["yellow", "saffron", "blue", "lime"]
ThemeMode = Literal["day", "night"]


@dataclass(frozen=True)
class ThemeDefinition:
    hue: ThemeHue
    mode: ThemeMode
    accent: str
    accent_glow: str
    bg_from: str
    bg_to: str
    glass_bg: str
    glass_border: str
    text_primary: str
    text_muted: str


THEMES: dict[str, ThemeDefinition] = {
    "yellow-day": ThemeDefinition("yellow", "day", "#F5C518", "#FFE68A", "#FFF9E5", "#FDEFC0", "rgba(255,255,255,0.55)", "rgba(245,197,24,0.45)", "#2B2400", "#6B5E00"),
    "yellow-night": ThemeDefinition("yellow", "night", "#F5C518", "#FFE68A", "#141200", "#232000", "rgba(20,18,0,0.55)", "rgba(245,197,24,0.35)", "#FFF4CC", "#C9B65B"),
    "saffron-day": ThemeDefinition("saffron", "day", "#FF7A18", "#FFB067", "#FFF1E5", "#FFE0C2", "rgba(255,255,255,0.55)", "rgba(255,122,24,0.45)", "#361A00", "#8A4E12"),
    "saffron-night": ThemeDefinition("saffron", "night", "#FF7A18", "#FFB067", "#1A0D00", "#2B1500", "rgba(26,13,0,0.55)", "rgba(255,122,24,0.35)", "#FFE3C6", "#D69A64"),
    "blue-day": ThemeDefinition("blue", "day", "#1E8FFF", "#8FCBFF", "#E9F4FF", "#CFE7FF", "rgba(255,255,255,0.55)", "rgba(30,143,255,0.45)", "#00203B", "#2E5D85"),
    "blue-night": ThemeDefinition("blue", "night", "#1E8FFF", "#8FCBFF", "#00060F", "#001A33", "rgba(0,6,15,0.55)", "rgba(30,143,255,0.35)", "#D6ECFF", "#6FA6D9"),
    "lime-day": ThemeDefinition("lime", "day", "#65D22C", "#B6F29A", "#F2FCE9", "#DEF5C4", "rgba(255,255,255,0.55)", "rgba(101,210,44,0.45)", "#173500", "#3F6B1A"),
    "lime-night": ThemeDefinition("lime", "night", "#65D22C", "#B6F29A", "#0A1300", "#132400", "rgba(10,19,0,0.55)", "rgba(101,210,44,0.35)", "#E8FBD8", "#96C878"),
}
DEFAULT_THEME_KEY: str = "blue-night"
THEME_ORDER: list[str] = [
    "yellow-day", "yellow-night",
    "saffron-day", "saffron-night",
    "blue-day", "blue-night",
    "lime-day", "lime-night",
]
THEME_LABELS: dict[str, str] = {
    "yellow-day": "Yellow \u00b7 Day", "yellow-night": "Yellow \u00b7 Night",
    "saffron-day": "Saffron \u00b7 Day", "saffron-night": "Saffron \u00b7 Night",
    "blue-day": "Blue \u00b7 Day", "blue-night": "Blue \u00b7 Night",
    "lime-day": "Lime Green \u00b7 Day", "lime-night": "Lime Green \u00b7 Night",
}

LIVE_GLOW_COLOR: str = "#EF4444"
LIVE_GLOW_SHADOW: str = "rgba(239,68,68,0.55)"
LOGO_IMAGE_PATH: str = "/branding/logo.png"
FAVICON_NOTE: str = "Place favicon.ico directly in assets/favicon.ico (NOT assets/branding/)."
MIN_PASSWORD_LENGTH: int = 4

CURSOR_DEFAULT_IMAGE_PATH: str = "/branding/cursor_default.png"
CURSOR_ACTIVE_IMAGE_PATH: str = "/branding/cursor_active.png"

TRANSITION_EFFECTS: dict[str, str] = {
    "dissolve": "Dissolve",
    "zoom-in": "Zoom In",
    "zoom-out": "Zoom Out",
    "slide-up": "Page Slide Up",
    "slide-down": "Page Slide Down",
    "slide-left": "Page Slide Left",
    "slide-right": "Page Slide Right",
    "flip-x": "Page Flip (Horizontal)",
    "flip-y": "Page Flip (Vertical)",
    "blur-in": "Blur In",
}
