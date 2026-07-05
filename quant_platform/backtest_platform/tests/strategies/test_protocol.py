"""strategies.protocol — the strategy contract + registry (ADR-027).

Proves the extensibility claim: a brand-new strategy plugs in by implementing
``StrategyRunner`` and registering a name — no edits to engine/research/CLI
dispatch. Also covers the registry's guard rails (duplicate / unknown name).
"""
from __future__ import annotations

import pandas as pd
import pytest

from backtest_platform.strategies import protocol
from backtest_platform.strategies.protocol import (
    StrategyRun,
    StrategyRunner,
    get_strategy,
    list_strategies,
    register_strategy,
)


@pytest.fixture
def clean_registry():
    """Snapshot + restore the global registry so a test's fakes don't leak."""
    before = dict(protocol._REGISTRY)
    yield
    protocol._REGISTRY.clear()
    protocol._REGISTRY.update(before)


def test_strategy_run_defaults_are_empty():
    run = StrategyRun({"trades": 0})
    assert run.metrics == {"trades": 0}
    assert run.returns.empty
    assert run.trades == []


def test_register_and_resolve_a_new_strategy(clean_registry):
    from pydantic import BaseModel as _BM
    from typing import ClassVar as _CV

    @register_strategy("fake_v0")
    class FakeRunner:
        config_model: _CV[type[_BM]] = _BM
        title: _CV[str] = "Fake v0"
        gate: _CV = ()  # declares a (here empty) validation gate — part of the contract
        def run(self, symbols, start, end, config, loader):
            return StrategyRun({"trades": len(symbols)}, pd.Series([0.01, 0.02]))

    assert "fake_v0" in list_strategies()
    runner = get_strategy("fake_v0")
    # the registry hands back an *instance*, structurally a StrategyRunner
    assert isinstance(runner, StrategyRunner)
    out = runner.run(["A", "B"], "2024-01-01", "2024-02-01", None, lambda sid: pd.DataFrame())
    assert out.metrics == {"trades": 2}
    assert len(out.returns) == 2


def test_duplicate_registration_is_rejected(clean_registry):
    @register_strategy("dup")
    class A:
        def run(self, *a):  # pragma: no cover - never called
            ...

    with pytest.raises(ValueError, match="already registered"):

        @register_strategy("dup")
        class B:
            def run(self, *a):  # pragma: no cover - never called
                ...


def test_unknown_strategy_raises_with_available_names():
    with pytest.raises(ValueError, match="unknown strategy"):
        get_strategy("does_not_exist")


def test_builtin_strategies_are_registered():
    # importing the runners module (via research) registers the built-ins
    import backtest_platform.research.runners  # noqa: F401

    assert {"four_layer", "momentum", "inst_flow"}.issubset(set(list_strategies()))
