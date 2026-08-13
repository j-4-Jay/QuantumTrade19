from engines.monitors.security_monitor import SecurityMonitor

def _code(m):
    try:
        import pyotp; return pyotp.TOTP(m.totp.get_or_create_secret()).now()
    except ImportError: return "000000"

def test_first_run_then_login():
    m = SecurityMonitor(force_memory=True)
    assert m.is_first_run() is True
    assert m.register_credentials("trader1", "S3cret!") is True
    m.skip_totp_enrollment()
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
    m.skip_totp_enrollment()
    code = m.recovery.generate_recovery_code()
    assert m.verify_identity_for_reset(code) is True
    assert m.reset_password("trader1", "NewPass2") is True
    assert m.login("trader1", "NewPass2") is True
    assert m.login("trader1", "OldPass1") is False
