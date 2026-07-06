"""Parametrized conformance tests — every registered strategy must satisfy the contract."""
import pytest
from quant_platform.services.research_validation import runners as _runners  # noqa: F401 — triggers registration
from quant_platform.services.research_validation.strategies.protocol import _REGISTRY, StrategyRun, list_strategies
from quant_platform.services.research_validation.strategies.conformance import (
    REQUIRED_METRIC_KEYS,
    check_strategy,
)


@pytest.mark.parametrize("name", list_strategies())
def test_strategy_conforms(name: str):
    report = check_strategy(name)
    assert report.ok, f"strategy {name!r} failed conformance:\n" + "\n".join(report.errors)


def test_conformance_catches_missing_metric():
    """check_strategy returns ok=False when a strategy omits a required metric key."""
    import pandas as pd
    from pydantic import BaseModel
    from typing import ClassVar

    from pydantic import BaseModel as _M

    class _EmptyConfig(_M):
        pass  # valid model, instantiable with no args

    class _BrokenRunner:
        config_model: ClassVar[type[_EmptyConfig]] = _EmptyConfig
        title: ClassVar[str] = "broken"

        def run(self, symbols, start, end, config, loader):
            return StrategyRun(metrics={}, returns=pd.Series(dtype=float), trades=[])

    _REGISTRY["__broken__"] = _BrokenRunner()
    try:
        report = check_strategy("__broken__")
        assert not report.ok
        assert any("cagr" in e for e in report.errors)
    finally:
        del _REGISTRY["__broken__"]


def test_required_metric_keys_are_complete():
    assert "cagr" in REQUIRED_METRIC_KEYS
    assert "sharpe" in REQUIRED_METRIC_KEYS
    assert "slippage_sharpe" in REQUIRED_METRIC_KEYS
    assert "maxdd" in REQUIRED_METRIC_KEYS
    assert "trades" in REQUIRED_METRIC_KEYS
    assert "bars" in REQUIRED_METRIC_KEYS
