"""Statistical validation + run gate-as-code.

v0.1 — ``gate_state``: ADR-016 edge gate (K1/K2/K3) + ADR-019 health checks as
pure functions; the strategy-agnostic '審判庭' that judges any run objectively.

v0.2 — statistical-validation pipeline (pure functions, dev_docs/18 §4 + López de
Prado): ``metrics`` (A/B/C/E performance), ``dsr`` (Deflated/Probabilistic Sharpe),
``pbo`` (Probability of Backtest Overfitting, CSCV), ``wfa`` (walk-forward splitter
with purge+embargo).

v0.3 — ``gate_machine`` (IS→WFA→OOS irreversible state machine + OOS sealed vault),
``trials`` (trials-counter → DSR-deflated gate criterion), ``tearsheet`` (quantstats).
"""
from quant_platform.services.research_validation.validation import dsr, metrics, pbo, wfa
from quant_platform.services.research_validation.validation.dsr import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    psr,
)
from quant_platform.services.research_validation.validation.gate_machine import (
    GateState,
    OOSSealedError,
    ValidationGate,
)
from quant_platform.services.research_validation.validation.gate_state import (
    DEFAULT_GATE,
    MOMENTUM_GATE,
    PANEL_GATE,
    Criterion,
    CriterionResult,
    GateResult,
    GateStatus,
    cross_window_consistent,
    evaluate_gate,
)
from quant_platform.services.research_validation.validation.pbo import probability_of_backtest_overfitting
from quant_platform.services.research_validation.validation.tearsheet import summary_stats, write_tearsheet
from quant_platform.services.research_validation.validation.trials import (
    DSR_THRESHOLD,
    TrialsCounter,
    TrialsDeflatedResult,
    deflated_sharpe_pass,
    trials_deflated_criterion,
)
from quant_platform.services.research_validation.validation.wfa import walk_forward_splits

__all__ = [
    # gate (v0.1)
    "DEFAULT_GATE", "MOMENTUM_GATE", "PANEL_GATE", "Criterion", "CriterionResult",
    "GateResult", "GateStatus", "cross_window_consistent", "evaluate_gate",
    # statistical pipeline (v0.2)
    "metrics", "dsr", "pbo", "wfa",
    "psr", "expected_max_sharpe", "deflated_sharpe_ratio",
    "probability_of_backtest_overfitting", "walk_forward_splits",
    # gate machine + trials + tearsheet (v0.3)
    "GateState", "OOSSealedError", "ValidationGate",
    "TrialsCounter", "TrialsDeflatedResult", "deflated_sharpe_pass",
    "trials_deflated_criterion", "DSR_THRESHOLD",
    "summary_stats", "write_tearsheet",
]
