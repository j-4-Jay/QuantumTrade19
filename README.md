<!-- tree-generator:start -->
```text
QuantumTrade19/
├── .continue/
│   └── mcpServers/
│       └── new-mcp-server.yaml
├── .vscode/
│   └── settings.json
├── assets/
│   ├── branding/
│   │   ├── cursor_active.png
│   │   ├── cursor_default.png
│   │   └── logo.png
│   ├── sounds/
│   │   ├── card_flip.wav
│   │   ├── click.wav
│   │   ├── error.wav
│   │   ├── page_change.wav
│   │   ├── success.wav
│   │   └── tab_slide.wav
│   └── background.jpg
├── config/
│   ├── __init__.py
│   ├── logging_config.py
│   └── settings.py
├── docs/
│   ├── All Prompts/
│   │   ├── 01_UIUX_DesignSystem_And_AppShell_Prompt.md
│   │   ├── 02_MarketDataMonitor_Prompt.md
│   │   ├── 03_POIMonitor_Prompt.md
│   │   ├── 03.1_Batch3_Continuation_Prompt.md
│   │   ├── 03.1_Pre-File-04 Enhancement Patch.md
│   │   ├── 04_SetupDetectionMonitor_Prompt.md
│   │   ├── 05_ConfidenceMonitor_Prompt.md
│   │   ├── 06_AlertMonitor_Prompt.md
│   │   ├── 07_JournalMonitor_Prompt.md
│   │   ├── 08_SystemHealthMonitor_Prompt.md
│   │   ├── 09_MasterAlertEngine_Prompt.md
│   │   ├── 10_RiskMathMonitor_Prompt.md
│   │   ├── 11_ExecutionMonitor_Prompt.md
│   │   ├── 12_MasterTradingEngine_Manual_Prompt.md
│   │   ├── 13_ExecutionMonitor_AutoUpgrade_Prompt.md
│   │   ├── 14_MasterTradingEngine_Auto_Prompt.md
│   │   ├── 15_LearningMonitor_Prompt.md
│   │   ├── 16_MasterLearningEngine_Prompt.md
│   │   ├── 17_IntelligenceMonitor_Prompt.md
│   │   ├── 18_MasterIntelligenceEngine_Prompt.md
│   │   └── 19_Packaging_Distribution_CrossPlatform_Prompt.md
│   ├── build_log/
│   │   ├── INDEX.md
│   │   ├── Module01_GapClosure_FINAL_LOCKED_Summary.md
│   │   ├── Module01_GapClosure_FINAL_LOCKED_Summary.pdf
│   │   ├── v0.2.0_MarketDataMonitor_Summary.md
│   │   ├── v0.2.1_MarketDataMonitor_ImportFix_Summary.md
│   │   ├── v0.3.0_POIMonitor_Summary.md
│   │   ├── v0.3.1_POIMatrix_Batch1_Batch2_Progress.md
│   │   ├── v0.3.1_POIMatrixAndControls_Summary.md
│   │   ├── v0.4.0-alpha_SetupDetectionMonitor_Summary.md
│   │   └── v0.5.0_POIChartOverlayWiring_Summary.md
│   ├── CURRENT_STATUS.md
│   ├── DECISIONS.md
│   ├── DELIVERABLES.md
│   ├── ENGINEERING_BIBLE.md
│   └── KNOWN_ISSUES.md
├── engines/
│   ├── event_bus/
│   │   ├── __init__.py
│   │   └── bus.py
│   ├── masters/
│   │   ├── __init__.py
│   │   ├── desktop.ini
│   │   └── master_app_engine.py
│   ├── monitors/
│   │   ├── __init__.py
│   │   ├── desktop.ini
│   │   ├── market_data_monitor.py
│   │   ├── poi_monitor.py
│   │   ├── security_monitor.py
│   │   ├── setup_detection_monitor.py
│   │   └── ui_experience_monitor.py
│   ├── workers/
│   │   ├── market_data/
│   │   │   ├── __init__.py
│   │   │   ├── broker_symbol_map.py
│   │   │   ├── candle_builder_worker.py
│   │   │   ├── candle_store_worker.py
│   │   │   ├── candle_store.py
│   │   │   ├── coindcx_socket_transport.py
│   │   │   ├── data_integrity_worker.py
│   │   │   ├── deep_history_downloader_worker.py
│   │   │   ├── gap_auto_heal_worker.py
│   │   │   ├── historical_data_loader_worker.py
│   │   │   ├── history_depth_prober_worker.py
│   │   │   ├── history_manifest_worker.py
│   │   │   ├── live_data_archiver_worker.py
│   │   │   ├── rate_limit_gate.py
│   │   │   ├── rest_poll_fallback_worker.py
│   │   │   ├── symbol_registry_worker.py
│   │   │   ├── tick_normalizer_worker.py
│   │   │   └── ws_feed_worker.py
│   │   ├── poi/
│   │   │   ├── __init__.py
│   │   │   ├── candle_access.py
│   │   │   ├── fvg_detector_worker.py
│   │   │   ├── htf_availability.py
│   │   │   ├── inverse_fvg_detector_worker.py
│   │   │   ├── orderblock_detector_worker.py
│   │   │   ├── poi_level_calculator_worker.py
│   │   │   ├── poi_settings.py
│   │   │   ├── poi_state_tracker_worker.py
│   │   │   └── poi_types.py
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── app_lock_worker.py
│   │   │   ├── auth_login_worker.py
│   │   │   ├── logout_worker.py
│   │   │   ├── otp_delivery_worker.py
│   │   │   ├── secure_credentials_loader.py
│   │   │   ├── secure_keystorage_worker.py
│   │   │   ├── settings_persistence_worker.py
│   │   │   └── totp_2fa_worker.py
│   │   ├── setup/
│   │   │   ├── _fsm_base.py
│   │   │   ├── bear123_fsm_worker.py
│   │   │   ├── bull123_fsm_worker.py
│   │   │   ├── candle_color_classifier_worker.py
│   │   │   ├── candle_lock_registry.py
│   │   │   ├── engulfing_detector_worker.py
│   │   │   ├── fvg_confirmation_detector_worker.py
│   │   │   ├── mtf_cascade_worker.py
│   │   │   ├── poi_interaction_detector_worker.py
│   │   │   └── setup_types.py
│   │   ├── ui_experience/
│   │   │   ├── __init__.py
│   │   │   ├── animation_choreographer_worker.py
│   │   │   ├── cursor_glow_worker.py
│   │   │   ├── page_transition_worker.py
│   │   │   ├── sound_engine_worker.py
│   │   │   └── theme_engine_worker.py
│   │   ├── __init__.py
│   │   └── desktop.ini
│   ├── __init__.py
│   └── desktop.ini
├── event_bus/
├── quantumtrade19/
│   ├── docs/
│   │   ├── build_log/
│   │   │   ├── v0.3.1_TradingPanel_KLineControls_Tracker.md
│   │   │   ├── v0.3.2_TradingPanel_KLineControls_Fix_Tracker.md
│   │   │   └── v0.3.3_AppState_LogicalSplit_Tracker.md
│   │   └── # react-klinecharts README.md
│   ├── __init__.py
│   └── quantumtrade19.py
├── reflex.lock/
│   ├── app_state.py
│   ├── bun.lock
│   └── package.json
├── state/
│   ├── app_state_mixins/
│   │   ├── auth_security_mixin.py
│   │   ├── core_shell_mixin.py
│   │   ├── deep_history_card_mixin.py
│   │   ├── market_dashboard_mixin.py
│   │   ├── poi_chart_mixin.py
│   │   ├── poi_settings_mixin.py
│   │   ├── shared.py
│   │   └── trading_panel_mixin.py
│   ├── app_state_parts/
│   │   ├── __init__.py
│   │   ├── 01_core_shell.py
│   │   ├── 02_auth_security.py
│   │   ├── 03_market_dashboard.py
│   │   ├── 04_poi_settings.py
│   │   └── 05_trading_panel.py
│   ├── backups/
│   │   ├── app_state_before_split_20260824_172335.py
│   │   └── app_state_before_v0.3.5_mixin_refactor_20260827_193453.py
│   ├── __init__.py
│   ├── 1_Split_AppState.ps1
│   ├── 2_Merge_AppState.ps1
│   ├── app_state_parts_manifest.json
│   ├── app_state.py
│   └── app_state.py.backup-20260817-232308
├── tests/
│   ├── engines/
│   │   ├── masters/
│   │   │   ├── __init__.py
│   │   │   ├── test_master_app_engine_health_states.py
│   │   │   └── test_master_app_engine.py
│   │   ├── monitors/
│   │   │   ├── __init__.py
│   │   │   └── test_security_monitor.py
│   │   ├── workers/
│   │   │   ├── security/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_app_lock_worker.py
│   │   │   │   ├── test_auth_login_worker.py
│   │   │   │   ├── test_logout_worker.py
│   │   │   │   └── test_totp_2fa_worker.py
│   │   │   ├── ui_experience/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_sound_engine_worker.py
│   │   │   │   └── test_theme_engine_worker.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── monitors/
│   │   ├── __init__.py
│   │   ├── test_poi_monitor_assembly.py
│   │   └── test_poi_monitor_file03_1_controls.py
│   ├── workers/
│   │   ├── market_data/
│   │   │   └── test_market_data_workers.py
│   │   ├── poi/
│   │   │   ├── __init__.py
│   │   │   ├── poi_test_helpers.py
│   │   │   ├── test_fvg_detector_worker.py
│   │   │   ├── test_inverse_fvg_detector_worker.py
│   │   │   ├── test_orderblock_detector_worker.py
│   │   │   ├── test_poi_matrix_settings.py
│   │   │   ├── test_poi_monitor_check_gates.py
│   │   │   └── test_zone_source_timeframe_matrix.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── test_market_data_monitor.py
│   └── test_setup_detection_monitor.py
├── tracker_files/
│   ├── thread_upload_bundles/
│   │   ├── ThreadUploadBundle_v1_20260903_034123.txt
│   │   ├── ThreadUploadBundle_v1_20260905_030701.txt
│   │   ├── ThreadUploadBundle_v1_20260906_143847.txt
│   │   ├── v0.3.3_thread_upload_bundle_20260825_093900.txt
│   │   ├── v0.3.4_thread_upload_bundle_20260825_094633.txt
│   │   ├── v0.4.8_thread_upload_bundle_20260830_173033.txt
│   │   └── v0.4.8_thread_upload_bundle_20260903_033126.txt
│   ├── v0.3.4_baseline_20260825_093616/
│   │   ├── state/
│   │   │   ├── app_state_parts/
│   │   │   │   ├── 01_core_shell.py
│   │   │   │   ├── 02_auth_security.py
│   │   │   │   ├── 03_market_dashboard.py
│   │   │   │   ├── 04_poi_settings.py
│   │   │   │   └── 05_trading_panel.py
│   │   │   ├── backups/
│   │   │   │   └── app_state_before_split_20260824_172335.py
│   │   │   └── app_state.py
│   │   ├── ui/
│   │   │   ├── components/
│   │   │   │   ├── kline_chart.py
│   │   │   │   └── trading_panel_chart.py
│   │   │   └── pages/
│   │   │       └── trading_panel.py
│   │   └── baseline_report.txt
│   ├── v0.3.3_AppState_LogicalSplit_Tracker.md
│   ├── v0.3.4_AppState_Refactor_Baseline_Checked_Tracker.md
│   ├── v0.3.7_shell_chart_workspace_source_bundle.txt
│   ├── v0.3.7_shell_extra_source_bundle.txt
│   ├── v0.3.9_deep_history_source_bundle.txt
│   ├── v0.3.9_market_data_monitor_bundle.txt
│   ├── v0.4.0_TradingPanel_Polish_Tracker.md
│   ├── v0.4.1_TradingPanel_Polish_Tracker.md
│   ├── v0.4.10_DeepHistoricalDataCard_FullControl_Tracker.md
│   ├── v0.4.14_GapAutoHealEngine_Tracker.md
│   ├── v0.4.15_AutoProbe_ETA_RichTooltip_Tracker.md
│   ├── v0.4.16_TooltipVisibility_ETAAnimation_Tracker.md
│   ├── v0.4.17_Diagnostic_EnterDownload_ConfirmDialogs_Tracker.md
│   ├── v0.4.18_CandleStorePerformanceFix_Tracker.md
│   ├── v0.4.19_InfiniteLoopFix_Tracker.md
│   ├── v0.4.20_ProbeTimeoutFix_Tracker.md
│   ├── v0.4.21_RealProgressWiring_Tracker.md
│   ├── v0.4.62_TradingPanelLiveChart_UIPolish_Tracker.md
│   ├── v0.4.8_TradingPanel_DataIntegrity_Tracker.md
│   ├── v0.4.9_HotReload_RestartLoop_Hotfix_Tracker.md
│   ├── v0.4.9d_DeepHistoricalDataCard_Redesign_Tracker.md
│   └── v0.5.0_POIChartOverlayWiring_Tracker.md
├── ui/
│   ├── components/
│   │   ├── __init__.py
│   │   ├── autofill_sync.py
│   │   ├── border_chase.py
│   │   ├── branding.py
│   │   ├── cursor_glow.py
│   │   ├── deep_historical_data_card.py
│   │   ├── glow_card.py
│   │   ├── keyboard_shortcuts.py
│   │   ├── kline_chart.py
│   │   ├── logout_dialog.py
│   │   ├── page_shell.py
│   │   ├── password_field.py
│   │   ├── poi_engine_settings_card.py
│   │   ├── sidebar.py
│   │   ├── symbol_detail_popup.py
│   │   ├── topbar.py
│   │   ├── trading_panel_chart.py
│   │   └── trading_panel_context_menu.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── alerts.py
│   │   ├── app_lock.py
│   │   ├── dashboard.py
│   │   ├── forgot_password.py
│   │   ├── journal.py
│   │   ├── login.py
│   │   ├── manage_security.py
│   │   ├── register.py
│   │   ├── settings.py
│   │   ├── splash.py
│   │   └── trading_panel.py
│   ├── sounds/
│   │   └── .gitkeep
│   ├── theme/
│   │   ├── __init__.py
│   │   ├── glass.py
│   │   └── global_css.py
│   └── __init__.py
├── .clinerules
├── .gitignore
├── 1. Start_QuantumTrade19.ps1
├── 2_Verify_v0.3.5_Refactor_And_Apply.ps1
├── 2. Stop_QuantumTrade19.ps1
├── 3. Install_New_Package.ps1
├── 4_Verify_v0.3.4_Refactor_Baseline.ps1
├── 4. Push_To_GitHub.ps1
├── 5. Pull_From_GitHub.ps1
├── 6_Create_Thread_Upload_Bundle.ps1
├── 7_Create_PathFile_Upload_Bundle.ps1
├── AGENTS.md
├── CHANGELOG.md
├── CLAUDE.md
├── Fix_QuantumTrade19_Console.ps1
├── fix_socketio_and_verify.ps1
├── install_coindcx_market_data_deps.ps1
├── Modelfile
├── project_tree.txt
├── pytest.ini
├── qt19_debug.log
├── QT19_File_03.1_Source_Pack_01.txt
├── README.md
├── Repair_QT19_Historical_Coverage_v0.4.8.ps1
├── requirements_before_encoding_fix.txt
├── requirements.txt
├── Reset_Registration.py
├── rxconfig.py
└── setup_project.bat
```
<!-- tree-generator:end -->
