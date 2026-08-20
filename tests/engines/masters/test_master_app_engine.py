"""
PATH: tests/engines/masters/test_master_app_engine.py (REPLACE ENTIRE FILE)

FIX (ISSUE-008): these tests assumed a recovery-code-at-registration flow
(`acknowledge_recovery_and_enter_shell()`, a recovery code returned from
finish_registration_without_totp()) that does not exist anywhere in the real
MasterAppEngine and is not documented in the locked
Module01_GapClosure_FINAL_LOCKED_Summary.md. The real, working,
already-locked flow transitions straight to SHELL on successful
registration, and uses the channel-based (TOTP/Telegram/Discord) forgot-
password flow that is already wired into the live UI. Rewritten to match
that real flow. No production file changed.
"""
from engines.masters.master_app_engine import MasterAppEngine, ShellScreen


def test_register_flow():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash()
    assert e.screen == ShellScreen.REGISTER
    e.register_credentials("trader1", "S3cret!")
    ok = e.finish_registration_without_totp("trader1", "S3cret!")
    assert ok is True
    assert e.screen == ShellScreen.SHELL


def test_lock_unlock():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash()
    e.register_credentials("trader1", "S3cret!")
    e.finish_registration_without_totp("trader1", "S3cret!")
    e.lock()
    assert e.screen == ShellScreen.LOCKED
    assert e.unlock("S3cret!") is True
    assert e.screen == ShellScreen.SHELL


def test_logout_to_splash():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash()
    e.register_credentials("trader1", "S3cret!")
    e.finish_registration_without_totp("trader1", "S3cret!")
    assert e.logout(True) == ShellScreen.SPLASH


def test_forgot_password_end_to_end():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash()
    e.register_credentials("trader1", "OldPass1")
    e.finish_registration_without_totp("trader1", "OldPass1")

    e.begin_forgot_password()
    assert e.screen == ShellScreen.FORGOT_PASSWORD
    # Fresh registration with no TOTP/Telegram/Discord configured -> no
    # recovery method exists yet, so the real flow routes straight to the
    # unverified reset path.
    assert e.has_any_recovery_method() is False

    ok = e.reset_password_unverified("NewPass2")
    assert ok is True
    assert e.screen == ShellScreen.LOGIN
    assert e.attempt_login("trader1", "NewPass2") is True
