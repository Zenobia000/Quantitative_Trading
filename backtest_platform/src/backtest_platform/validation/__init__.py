"""Statistical validation + run gate-as-code.

``gate_state`` (v0.1): ADR-016 edge gate (K1/K2/K3) + ADR-019 health checks as
pure functions — the strategy-agnostic '審判庭' that judges any run objectively.

PBO / WFA / Monte Carlo / DSR (IS→WFA→OOS sealed-vault state machine) land in
v0.2 (M3); see dev_docs/adrs/ADR-018.
"""
from backtest_platform.validation.gate_state import (
    DEFAULT_GATE,
    Criterion,
    CriterionResult,
    GateResult,
    GateStatus,
    cross_window_consistent,
    evaluate_gate,
)

__all__ = [
    "DEFAULT_GATE",
    "Criterion",
    "CriterionResult",
    "GateResult",
    "GateStatus",
    "cross_window_consistent",
    "evaluate_gate",
]
