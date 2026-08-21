"""
PATH: tests/engines/masters/test_master_app_engine_health_states.py (NEW FILE)

Covers the two get_market_data_health() branches that were previously
unverified: 'down' (no symbol reporting OK or DEGRADED) and 'connecting'
(no health data collected yet). The 'connected' and 'degraded' branches
already have coverage elsewhere (OK -> DEGRADED -> OK transition test).

These tests only rely on the *shape* of MarketDataMonitor.get_health()'s
return value (a dict of symbol -> status string) and on MasterAppEngine's
own aggregation rules, reproduced here from the source for reference:

    if not health: return "connecting"
    if values == {"OK"}: return "connected"
    if "OK" in values or "DEGRADED" in values: return "degraded"
    return "down"

We deliberately don't assert on the exact per-symbol status string
MarketDataMonitor uses to mean "unhealthy" (e.g. "DOWN"/"STALE"/etc) since
that wasn't confirmed against MarketDataMonitor's own source - we only
assert that *any* status other than "OK"/"DEGRADED" collapses to "down",
which is the actual contract get_market_data_health() implements.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from engines.masters.master_app_engine import MasterAppEngine


@pytest.fixture
def engine() -> MasterAppEngine:
    """force_memory=True keeps SecurityMonitor off disk. MarketDataMonitor
    is constructed but never started (ensure_market_data_started() is
    lazy), so no real network/socket activity happens here - matches the
    existing pattern used by the OK->DEGRADED->OK transition test."""
    return MasterAppEngine(force_memory=True)


def test_health_is_connecting_before_any_health_check_completes(engine: MasterAppEngine) -> None:
    """No symbols have reported yet -> get_health() returns an empty dict."""
    engine.market_data.get_health = MagicMock(return_value={})

    assert engine.get_market_data_health() == "connecting"


def test_health_is_down_when_no_symbol_is_ok_or_degraded(engine: MasterAppEngine) -> None:
    """Every subscribed symbol is unhealthy (neither OK nor DEGRADED) ->
    the topbar pill must collapse to 'down', not 'degraded' or 'connecting'."""
    engine.market_data.get_health = MagicMock(
        return_value={"B-BTC_USDT": "STALE", "B-ETH_USDT": "STALE"}
    )

    assert engine.get_market_data_health() == "down"


def test_health_is_down_even_with_mixed_unhealthy_statuses(engine: MasterAppEngine) -> None:
    """Guards against a regression where 'down' only triggers on a single
    specific status string instead of "anything that isn't OK/DEGRADED"."""
    engine.market_data.get_health = MagicMock(
        return_value={"B-BTC_USDT": "STALE", "B-ETH_USDT": "TIMEOUT"}
    )

    assert engine.get_market_data_health() == "down"


def test_health_is_not_connecting_once_any_symbol_has_reported(engine: MasterAppEngine) -> None:
    """Regression guard: an empty-*looking* but non-empty dict (e.g. a
    symbol with a falsy/None status) must NOT be treated the same as the
    true 'no health data yet' case - only `not health` (empty dict) maps
    to 'connecting'."""
    engine.market_data.get_health = MagicMock(return_value={"B-BTC_USDT": "STALE"})

    assert engine.get_market_data_health() != "connecting"
    assert engine.get_market_data_health() == "down"
