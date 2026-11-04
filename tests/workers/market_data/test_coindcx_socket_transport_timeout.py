"""
FULL PATH: tests/workers/market_data/test_coindcx_socket_transport_timeout.py
FT-H.35: the live feed connect has a short timeout and falls back if the library refuses the setting.
"""
import engines.workers.market_data.coindcx_socket_transport as mod


class FakeWS:
    def __init__(self):
        self.sent = []
        self._first = True

    def recv(self):
        if self._first:
            self._first = False
            return ("0{}", None)
        raise RuntimeError("closed")

    def close(self):
        pass

    def __getattr__(self, name):
        def _record(*args, **kwargs):
            self.sent.append((name, args))
        return _record


class FakeSession:
    calls = []
    reject_timeout = False

    def __init__(self, impersonate=None):
        pass

    def ws_connect(self, url, **kwargs):
        FakeSession.calls.append(dict(kwargs))
        if FakeSession.reject_timeout and "timeout" in kwargs:
            raise TypeError("unexpected keyword argument timeout")
        return FakeWS()

    def close(self):
        pass


def _transport(monkeypatch, reject):
    FakeSession.calls = []
    FakeSession.reject_timeout = reject
    monkeypatch.setattr(mod, "Session", FakeSession)
    return mod.CoinDCXSocketTransport()


def test_connect_passes_a_short_timeout(monkeypatch):
    t = _transport(monkeypatch, reject=False)
    t.connect("wss://stream.coindcx.com")
    try:
        assert FakeSession.calls[0]["timeout"] == mod._CONNECT_TIMEOUT_S
        assert mod._CONNECT_TIMEOUT_S <= 15
    finally:
        t.disconnect()


def test_connect_falls_back_when_library_refuses_timeout(monkeypatch):
    t = _transport(monkeypatch, reject=True)
    t.connect("wss://stream.coindcx.com")
    try:
        assert len(FakeSession.calls) == 2
        assert "timeout" in FakeSession.calls[0]
        assert "timeout" not in FakeSession.calls[1]
    finally:
        t.disconnect()
