from engines.masters.master_app_engine import MasterAppEngine, ShellScreen

def test_register_flow():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash(); assert e.screen == ShellScreen.REGISTER
    e.register_credentials("trader1", "S3cret!")
    code = e.finish_registration_without_totp("trader1", "S3cret!")
    assert code and "-" in code
    assert e.screen == ShellScreen.REGISTER
    assert e.acknowledge_recovery_and_enter_shell() == ShellScreen.SHELL

def test_lock_unlock():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash(); e.register_credentials("trader1", "S3cret!")
    e.finish_registration_without_totp("trader1", "S3cret!"); e.acknowledge_recovery_and_enter_shell()
    e.lock(); assert e.screen == ShellScreen.LOCKED
    assert e.unlock("S3cret!") is True; assert e.screen == ShellScreen.SHELL

def test_logout_to_splash():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash(); e.register_credentials("trader1", "S3cret!")
    e.finish_registration_without_totp("trader1", "S3cret!"); e.acknowledge_recovery_and_enter_shell()
    assert e.logout(True) == ShellScreen.SPLASH

def test_forgot_password_end_to_end():
    e = MasterAppEngine(force_memory=True)
    e.finish_splash(); e.register_credentials("trader1", "OldPass1")
    code = e.finish_registration_without_totp("trader1", "OldPass1")
    e.acknowledge_recovery_and_enter_shell()
    e.begin_forgot_password()
    assert e.verify_identity_for_reset(code) is True
    assert e.reset_password("NewPass2") is True
    assert e.screen == ShellScreen.LOGIN
    assert e.attempt_login("trader1", "NewPass2") is True
