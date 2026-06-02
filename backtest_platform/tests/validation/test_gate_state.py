"""gate_state — ADR-016 edge gate + ADR-019 health checks as a pure-function dict.

Strategy-agnostic: feed a run's metrics dict, get per-criterion PASS/FAIL + gap.
No IO. This is the '審判庭' that judges any run (v2/v3/v3.1...) objectively.
"""
from __future__ import annotations

import pytest

from backtest_platform.validation.gate_state import (
    DEFAULT_GATE,
    GateStatus,
    cross_window_consistent,
    evaluate_gate,
)

_PASS = {
    "cagr": 0.25, "sharpe": 1.5, "slippage_sharpe": 1.2,
    "struct1_pct": 0.10, "churn_pct": 0.10, "avg_hold": 8.0,
}


def test_all_pass() -> None:
    r = evaluate_gate(_PASS)
    assert r.status is GateStatus.PASS
    assert r.passed is True
    assert r.failing() == []


def test_edge_fail_on_low_cagr_and_sharpe() -> None:
    m = {**_PASS, "cagr": -0.02, "sharpe": -0.43}
    r = evaluate_gate(m)
    assert r.passed is False
    assert r.status is GateStatus.FAIL
    keys = {c.criterion.key for c in r.failing()}
    assert {"cagr", "sharpe"} <= keys


def test_health_fail_on_structure1_flood() -> None:
    m = {**_PASS, "struct1_pct": 0.76}
    r = evaluate_gate(m)
    assert r.passed is False
    assert any(c.criterion.key == "struct1_pct" for c in r.failing())


def test_missing_metric_yields_incomplete_not_pass() -> None:
    m = {k: v for k, v in _PASS.items() if k != "slippage_sharpe"}
    r = evaluate_gate(m)
    assert r.status is GateStatus.INCOMPLETE
    assert r.passed is False  # cannot PASS a gate you cannot fully evaluate


def test_gap_is_signed_toward_pass() -> None:
    m = {**_PASS, "cagr": 0.10}  # below 0.18 threshold
    r = evaluate_gate(m)
    cagr = next(c for c in r.results if c.criterion.key == "cagr")
    assert cagr.passed is False
    assert cagr.gap == pytest.approx(0.10 - 0.18)  # -0.08, how far short


def test_actual_v3_metrics_fail_the_gate() -> None:
    """The real v3 2020-2024 portfolio numbers must be judged FAIL."""
    v3 = {
        "cagr": -0.024, "sharpe": -0.43, "slippage_sharpe": -0.43,
        "struct1_pct": 0.716, "churn_pct": 0.274, "avg_hold": 5.5,
    }
    r = evaluate_gate(v3)
    assert r.passed is False
    failed = {c.criterion.key for c in r.failing()}
    assert {"cagr", "sharpe", "struct1_pct", "churn_pct"} <= failed


def test_summary_renders_per_criterion_marks() -> None:
    r = evaluate_gate(_PASS)
    s = r.summary()
    assert "K1" in s and "PASS" in s


def test_cross_window_consistency() -> None:
    assert cross_window_consistent({"cagr": 0.2, "sharpe": 1.1}, {"cagr": 0.15, "sharpe": 0.9}) is True
    assert cross_window_consistent({"cagr": 0.2, "sharpe": 1.1}, {"cagr": -0.1, "sharpe": 0.9}) is False


def test_default_gate_has_adr016_edge_and_adr019_health() -> None:
    keys = {c.key for c in DEFAULT_GATE}
    assert {"cagr", "sharpe", "slippage_sharpe"} <= keys  # ADR-016 edge
    assert {"struct1_pct", "churn_pct", "avg_hold"} <= keys  # ADR-019 health
