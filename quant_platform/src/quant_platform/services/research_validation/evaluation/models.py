"""Shared evaluation dataclasses (rebuild Goal 3).

``RunBundle`` is the neutral hand-off between the orchestrator's primitive-running
layer (which wraps ``doe`` / ``go_gates`` / ``truth_gate`` / single-run dispatch) and
the pure ``result_builder`` that assembles the contract ``EvaluationResult``. Keeping
it here avoids a circular import (orchestrator ↔ result_builder both import this).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class RunBundle:
    """Everything one profile's primitive run produced, before result assembly.

    ``metrics`` / ``returns`` / ``trades`` are the primary IS run (for scorecards +
    headline). ``extras`` carries gate-derived numbers a plain run cannot
    (``oos_holdout_sharpe`` / ``dsr`` / ``wfa_oos_positive_frac`` / ``slippage_sharpe`` /
    ``pbo``). ``truth_verdict`` is set ONLY when a real truth gate ran
    (deployment_strict); ``None`` for triage/candidate profiles.
    """

    metrics: dict[str, Any]
    returns: pd.Series
    trades: list[dict[str, Any]]
    params: dict[str, Any]
    symbols: list[str]
    window: dict[str, Any]                       # {is_start, oos_start?, is_end}
    n_trials: int
    survivorship_clean: bool
    bundle_ref: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)
    truth_verdict: str | None = None
    truth_reasons: tuple[str, ...] = ()
    position_size: float = 0.0

    @property
    def data_issue(self) -> bool:
        """A run that yielded no tradable bars is a data-quality gap, not a weak edge."""
        return len(self.returns) == 0 or int(self.metrics.get("bars", 0) or 0) == 0
