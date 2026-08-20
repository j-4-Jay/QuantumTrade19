"""
PATH: tests/engines/monitors/test_security_monitor.py (REPLACE ENTIRE FILE)

FIX (ISSUE-009): two of the four tests here called `skip_totp_enrollment()`,
which does not exist. In the real SecurityMonitor, "skipping" TOTP during
registration is simply the absence of ever calling begin_totp_enrollment()/
confirm_totp_enrollment() - is_totp_enabled() already defaults to False, so
there is nothing to explicitly call. The same tests also assumed a
`m.recovery.generate_recovery_code()` / single-argument
`verify_identity_for_reset(code)` recovery-code system that does not exist -
see ISSUE-008's reasoning (no blueprint/locked-summary backing, and a
complete working channel-based forgot-password flow already exists and is
live). Rewritten both broken tests to match the real, working flow.

test_totp_flow and test_blank_username_is_first_run were already passing
against the real code and are unchanged.
"""
from engines.monitors.security_monitor import SecurityMonitor


def _code(m):
    try:
        import pyotp
        return pyotp.TOTP(m.totp.get_or_create_secret()).now()
    except ImportError:
        return "000000"


def test_first_run_then_login():
    m = SecurityMonitor(force_memory=True)
    assert m.is_first_run() is True
    assert m.register_credentials("trader1", "S3cret!") is True
    assert m.login("trader1", "S3cret!") is True


def test_totp_flow():
    m = SecurityMonitor(force_memory=True)
    m.register_credentials("trader1", "S3cret!")
    m.begin_totp_enrollment("trader1")
    code = _code(m)
    assert m.confirm_totp_enrollment(code) is True
    assert m.login("trader1", "S3cret!") is False
    assert m.login("trader1", "S3cret!", code) is True


def test_blank_username_is_first_run():
    m = SecurityMonitor(force_memory=True)
    m.keystore.set_secret("auth_username", "")
    assert m.is_first_run() is True


def test_forgot_password_via_recovery():
    m = SecurityMonitor(force_memory=True)
    m.register_credentials("trader1", "OldPass1")
    # No TOTP/Telegram/Discord configured yet -> no recovery method exists,
    # matching the real, locked has_any_recovery_method() behavior.
    assert m.has_any_recovery_method() is False
    ok = m.reset_password("trader1", "NewPass2")
    assert ok is True
    assert m.login("trader1", "NewPass2") is True
    assert m.login("trader1", "OldPass1") is False
