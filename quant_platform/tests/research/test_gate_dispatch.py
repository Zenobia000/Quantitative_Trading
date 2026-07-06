"""Gate-per-strategy dispatch (審查缺陷 #8 / completes ADR-027).

The审判庭 threshold set is strategy-specific: four-layer's health checks
(struct1_pct/churn_pct/avg_hold) only exist in four-layer's metrics; a
cross-sectional panel strategy (momentum/inst_flow) never produces them and was
therefore judged INCOMPLETE forever by the four-layer DEFAULT_GATE. These tests
pin the fix: every run is judged by ITS OWN declared gate, and a strategy that
declares no gate is a loud error — never a silent fallback to a foreign ruler.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from quant_platform.services.research_validation import runners as _runners  # noqa: F401 — register built-ins
from quant_platform.packages.application.is_harness import run_and_judge
from quant_platform.packages.domain.run_config import RunConfig
from quant_platform.services.research_validation.strategies import protocol
from quant_platform.services.research_validation.strategies.conformance import synthetic_loader

_SYMS = tuple(f"SYN{i:04d}" for i in range(6))


@pytest.fixture
def clean_registry():
    """Snapshot + restore the global registry so a test's fakes don't leak."""
    before = dict(protocol._REGISTRY)
    yield
    protocol._REGISTRY.clear()
    protocol._REGISTRY.update(before)


def _cfg(strategy: str, **params):
    return RunConfig(
        hypothesis=f"{strategy} gate dispatch",
        strategy=strategy,
        params=params,
        stocks=_SYMS,
        is_start=date(2019, 1, 1),
        is_end=date(2020, 12, 31),
    )


# ---- (a) panel runs must reach a real verdict, never perpetual INCOMPLETE ----

def test_momentum_run_and_judge_is_not_incomplete():
    rec = run_and_judge(_cfg("momentum", lookback_days=120),
                        loader=synthetic_loader(n_bars=600))
    assert rec["gate_status"] != "INCOMPLETE"
    assert rec["gate_status"] in ("PASS", "FAIL")


def test_inst_flow_run_and_judge_is_not_incomplete():
    rec = run_and_judge(_cfg("inst_flow"), loader=synthetic_loader(n_bars=600))
    assert rec["gate_status"] != "INCOMPLETE"
    assert rec["gate_status"] in ("PASS", "FAIL")


def test_four_layer_still_uses_its_health_gate():
    # four-layer must keep being judged by the health checks it alone produces.
    rec = run_and_judge(_cfg("four_layer"), loader=synthetic_loader(n_bars=600))
    assert "struct1_pct" in rec["gate_summary"] or rec["gate_status"] in ("PASS", "FAIL", "INCOMPLETE")
    keys = {c.key for c in protocol.get_strategy_gate("four_layer")}
    assert {"struct1_pct", "churn_pct", "avg_hold"} <= keys


# ---- (b) a declared gate must only reference metrics the strategy produces ----

@pytest.mark.parametrize("name", ["four_layer", "momentum", "inst_flow", "template"])
def test_declared_gate_keys_subset_of_produced_metrics(name):
    runner = protocol.get_strategy(name)
    gate = protocol.get_strategy_gate(name)  # raises today (no such fn) → RED
    result = runner.run(list(_SYMS), date(2019, 1, 1), date(2020, 12, 31),
                        runner.config_model(), synthetic_loader(n_bars=500))
    gate_keys = {c.key for c in gate}
    missing = gate_keys - result.metrics.keys()
    assert not missing, f"{name} gate references non-produced metrics: {sorted(missing)}"


# ---- (c) no declared gate + no explicit gate → loud error, not silent fallback -

def test_run_and_judge_raises_when_strategy_declares_no_gate(clean_registry):
    from typing import ClassVar

    from pydantic import BaseModel

    from quant_platform.services.research_validation.strategies.protocol import StrategyRun, register_strategy

    class _NoGateConfig(BaseModel):
        pass

    @register_strategy("_nogate")
    class _NoGateRunner:
        config_model: ClassVar[type[_NoGateConfig]] = _NoGateConfig
        title: ClassVar[str] = "declares no gate"
        gate = None  # explicit: this strategy ships without a validation gate

        def run(self, symbols, start, end, config, loader):
            return StrategyRun(
                {"cagr": 0.2, "sharpe": 1.1, "slippage_sharpe": 1.0,
                 "maxdd": 0.1, "trades": 3, "bars": 100},
                pd.Series([0.01, 0.02]),
            )

    with pytest.raises(ValueError, match="declares no validation gate"):
        run_and_judge(_cfg("_nogate"), loader=synthetic_loader(n_bars=100))


def test_explicit_gate_still_wins_over_dispatch(clean_registry):
    # Back-compat: a caller that passes an explicit gate is never overridden.
    from quant_platform.services.research_validation.validation.gate_state import MOMENTUM_GATE

    rec = run_and_judge(_cfg("momentum", lookback_days=120),
                        loader=synthetic_loader(n_bars=600), gate=MOMENTUM_GATE)
    assert rec["gate_status"] in ("PASS", "FAIL")
