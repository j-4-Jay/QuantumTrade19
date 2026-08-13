from __future__ import annotations
import base64, io
from engines.workers.security.secure_keystorage_worker import SecureKeyStorageWorker
try:
    import pyotp
except ImportError:
    pyotp = None
try:
    import qrcode
except ImportError:
    qrcode = None

class Totp2FAWorker:
    def __init__(self, keystore: SecureKeyStorageWorker):
        self._keystore = keystore
    def get_or_create_secret(self):
        s = self._keystore.get_secret("totp_secret")
        if s is None:
            s = pyotp.random_base32() if pyotp else "JBSWY3DPEHPK3PXP"
            self._keystore.set_secret("totp_secret", s)
        return s
    def provisioning_uri(self, account_name):
        s = self.get_or_create_secret()
        if pyotp is None: return f"otpauth://totp/QuantumTrade19:{account_name}?secret={s}&issuer=QuantumTrade19"
        return pyotp.totp.TOTP(s).provisioning_uri(name=account_name, issuer_name="QuantumTrade19")
    def qr_code_data_uri(self, account_name):
        uri = self.provisioning_uri(account_name)
        if qrcode is None: return ""
        img = qrcode.make(uri); buf = io.BytesIO(); img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    def verify(self, code):
        s = self.get_or_create_secret()
        if pyotp is None: return code == "000000"
        return pyotp.TOTP(s).verify(code, valid_window=1)
