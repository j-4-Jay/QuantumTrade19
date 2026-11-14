"""Offline monitor hook contract tests; no monitor construction or database writes."""
import ast
import logging
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "engines/monitors/market_data_monitor.py"


def hook_monitor():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MarketDataMonitor")
    funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ("_start_candle_shadow", "_shadow_call")]
    assert len(funcs) == 2
    shell = ast.ClassDef(name="Hooks", bases=[], keywords=[], body=funcs, decorator_list=[])
    mod = ast.fix_missing_locations(ast.Module(body=[shell], type_ignores=[]))
    scope = {"logger": logging.getLogger("test_shadow")}
    exec(compile(mod, str(SOURCE), "exec"), scope)
    obj = scope["Hooks"]()
    obj._lock = threading.RLock()
    obj._subscribed = {"B-ETH_USDT"}
    return obj


def test_default_off(monkeypatch):
    monkeypatch.delenv("QT19_CANDLE_SHADOW", raising=False)
    obj = hook_monitor(); obj._start_candle_shadow()
    assert "_candle_shadow" not in obj.__dict__


def test_pytest_guard_even_when_opted_in(monkeypatch):
    monkeypatch.setenv("QT19_CANDLE_SHADOW", "1")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test")
    obj = hook_monitor(); obj._start_candle_shadow()
    assert "_candle_shadow" not in obj.__dict__


def test_start_once_and_membership_snapshot(monkeypatch):
    import engines.workers.market_data.candle_shadow_worker as module
    fake = SimpleNamespace(thread=SimpleNamespace(is_alive=lambda: True), start=Mock())
    ctor = Mock(return_value=fake)
    monkeypatch.setattr(module, "CandleShadowWorker", ctor)
    monkeypatch.setenv("QT19_CANDLE_SHADOW", "1")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    obj = hook_monitor(); obj._start_candle_shadow(); obj._start_candle_shadow()
    ctor.assert_called_once(); fake.start.assert_called_once_with(["B-ETH_USDT"])


def test_hook_exception_isolated():
    obj = hook_monitor()
    obj._candle_shadow = SimpleNamespace(observe=Mock(side_effect=RuntimeError("test")))
    obj._shadow_call("observe", "current_close", object())
    obj._candle_shadow.observe.assert_called_once()


def test_named_lifecycle_hooks_present():
    src = SOURCE.read_text(encoding="utf-8")
    for text in ('self._start_candle_shadow()', 'self._shadow_call("stop")',
                 'self._shadow_call("subscribe", symbol)', 'self._shadow_call("unsubscribe", symbol)',
                 '"current_close", candle', '"current_delivery", candle', '"reconcile_observation", observed_candle'):
        assert text in src
