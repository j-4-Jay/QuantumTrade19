"""Reflex State - thin UI binding layer over the Master App Engine (no business logic here).

PATH: state/app_state.py (REPLACE ENTIRE FILE)

Composes executable mixins from state/app_state_mixins/.

FIX (Timezone Mode toggle) - added poi_timezone_mode: str = "NY" - drives
the new UTC/NY toggle for PDH/PDL/4H/Week/Month POI calculation
boundaries (see poi_level_calculator_worker.py). Default "NY" per
explicit request.
"""
from __future__ import annotations

import reflex as rx

from config.settings import DEFAULT_THEME_KEY
from state.app_state_mixins.shared import SHELL_STATE_CLASS
from state.app_state_mixins.core_shell_mixin import CoreShellMixin
from state.app_state_mixins.auth_security_mixin import AuthSecurityMixin
from state.app_state_mixins.market_dashboard_mixin import MarketDashboardMixin
from state.app_state_mixins.poi_settings_mixin import PoiSettingsMixin
from state.app_state_mixins.trading_panel_mixin import TradingPanelMixin
from state.app_state_mixins.deep_history_card_mixin import DeepHistoryCardMixin
from state.app_state_mixins.poi_chart_mixin import PoiChartMixin

TRADING_PANEL_TF_OPTIONS = ["1m", "5m", "15m"]
TRADING_PANEL_DAY_PRESETS = ["1", "3", "5", "7", "14", "30", "90"]

class AppState(
    CoreShellMixin,
    AuthSecurityMixin,
    MarketDashboardMixin,
    PoiSettingsMixin,
    TradingPanelMixin,
    DeepHistoryCardMixin,
    PoiChartMixin,
    rx.State,
):
    screen: str = SHELL_STATE_CLASS.SPLASH.value
    active_tab: str = "Dashboard"
    settings_active_subtab: str = "appearance"
    theme_key: str = DEFAULT_THEME_KEY
    paper_mode: bool = True
    is_locked: bool = False
    sound_muted: bool = False
    sidebar_collapsed: bool = False

    totp_required: bool = False

    reg_username: str = ""
    reg_password: str = ""
    reg_confirm_password: str = ""
    reg_enable_totp: bool = False
    reg_error: str = ""
    reg_stage: str = "form"
    reg_qr_data_uri: str = ""
    reg_totp_code: str = ""
    show_reg_password: bool = False
    show_reg_confirm_password: bool = False

    login_username: str = ""
    login_password: str = ""
    login_totp: str = ""
    login_error: str = ""
    show_login_password: bool = False
    show_lock_password: bool = False
    login_credentials_match: bool = False
    login_error_seq: int = 0
    login_remember_device: bool = False

    manage_username: str = ""
    manage_password: str = ""
    manage_error: str = ""
    manage_stage: str = "verify"
    manage_totp_qr: str = ""
    manage_totp_code: str = ""
    show_manage_password: bool = False
    tg_bot_token: str = ""
    tg_chat_id: str = ""
    tg_enabled: bool = False
    tg_configured: bool = False
    tg_message: str = ""
    dc_webhook_url: str = ""
    dc_enabled: bool = False
    dc_configured: bool = False
    dc_message: str = ""

    forgot_stage: str = "choose"
    forgot_selected_method: str = ""
    forgot_code: str = ""
    forgot_otp_sent: bool = False
    forgot_verified: bool = False
    forgot_new_password: str = ""
    forgot_confirm_password: str = ""
    forgot_error: str = ""
    show_forgot_new_password: bool = False
    show_forgot_confirm_password: bool = False
    forgot_available_methods: list[str] = []
    forgot_has_any_method: bool = False

    show_logout_dialog: bool = False
    logout_stage: str = "confirm"

    detail_popup_open: bool = False
    detail_popup_symbol: str = ""
    ws_status: str = "connected"
    pinned_prices: dict[str, str] = {}
    symbol_rows: list[dict] = []
    deep_history_symbol: str = "B-BTC_USDT"
    deep_history_timeframe: str = "1m"
    deep_history_target_days: str = ""
    deep_history_ceiling_days: str = "Not checked yet"
    deep_history_covered_days: str = "0"
    deep_history_is_downloading: bool = False
    deep_history_status_message: str = ""

    # --- Deep Historical Data Settings card (per-symbol) ---
    _card_duration_value: dict[str, str] = {}
    _card_duration_unit: dict[str, str] = {}
    _card_confirm_open: dict[str, bool] = {}
    _card_confirm_message: dict[str, str] = {}
    _card_pending_requested_days: dict[str, int] = {}
    _deep_history_cards_poll_running: bool = False
    _deep_history_cards_poll_tick: int = 0

    poi_settings_loaded: bool = False
    poi_display_enabled: dict[str, bool] = {}
    poi_strategy_enabled: dict[str, bool] = {}
    poi_zone_source_tf_enabled: dict[str, bool] = {}
    poi_timezone_mode: str = "NY"
    poi_show_labels: bool = True
    poi_show_tooltips: bool = True
    poi_line_transparency: int = 100
    poi_zone_opacity: int = 30
    poi_show_source_tf_badge: bool = True
    poi_show_logical_id: bool = False
    poi_reduced_motion: bool = False
    poi_backend_busy: bool = False

    # --- Combined per-TF POI state ---
    poi_tf_display_enabled: dict[str, bool] = {}
    poi_tf_strategy_enabled: dict[str, bool] = {}
    poi_tf_color: dict[str, str] = {}
    poi_tf_vertical_enabled: dict[str, bool] = {}
    poi_custom_lines: list[dict] = [
        {"enabled": False, "hour12": 8, "minute": 30, "meridiem": "AM", "color": "#22C55E", "name": ""},
        {"enabled": False, "hour12": 8, "minute": 30, "meridiem": "AM", "color": "#F97316", "name": ""},
        {"enabled": False, "hour12": 8, "minute": 30, "meridiem": "AM", "color": "#38BDF8", "name": ""},
    ]

    # --- POI vertical start/end markers ---
    poi_vertical_line_style: str = "dashed"
    poi_vertical_line_opacity: int = 100

    # --- POI chart overlays ---
    poi_chart_overlays: list[dict] = []
    poi_chart_overlays_version: int = 0
    _poi_chart_poll_running: bool = False

    # --- Chart crosshair settings ---
    trading_panel_crosshair_enabled: bool = True
    trading_panel_crosshair_color: str = "#758696"
    trading_panel_crosshair_opacity: int = 100
    trading_panel_crosshair_style: str = "dashed"
    trading_panel_crosshair_thickness: int = 1

    transition_effects_enabled: list[str] = ["dissolve", "zoom-in", "slide-up", "flip-x", "blur-in"]
    transition_mode: str = "shuffle"
    transition_active_effect: str = "dissolve"
    _transition_sequence_index: int = 0

    tab_transition_effects_enabled: list[str] = ["slide-left"]
    tab_transition_mode: str = "single"
    tab_transition_active_effect: str = "slide-left"
    _tab_transition_sequence_index: int = 0

    _splash_task_running: bool = False
    _ws_poll_running: bool = False
    _price_poll_running: bool = False
    _deep_history_poll_running: bool = False
    _poi_monitor_starting: bool = False

    # --- Trading Panel chart state (react-klinecharts) ---
    trading_panel_symbol: str = "B-BTC_USDT"
    trading_panel_chart_tf: str = "5m"
    trading_panel_display_days_input: str = "5"
    trading_panel_display_days_draft: str = "5"
    trading_panel_chart_theme: str = "night"
    trading_panel_grid_enabled: bool = False
    trading_panel_candles: list[dict] = []
    trading_panel_data_version: int = 0
    trading_panel_current_open: str = "--"
    trading_panel_current_high: str = "--"
    trading_panel_current_low: str = "--"
    trading_panel_current_close: str = "--"
    trading_panel_local_days: str = "0"
    trading_panel_broker_days: str = "Not checked yet"
    trading_panel_notice: str = ""
    trading_panel_follow_live: bool = False

    trading_panel_tf_progress: dict[str, dict] = {}

    trading_panel_safe_mode_active: bool = False
    trading_panel_safe_mode_message: str = ""

    trading_panel_poll_running: bool = False
    trading_panel_last_candle_ts: float = 0.0

    # --- Custom right-click chart menu (v0.3.8) ---
    trading_panel_menu_open: bool = False
    trading_panel_menu_x: int = 0
    trading_panel_menu_y: int = 0
