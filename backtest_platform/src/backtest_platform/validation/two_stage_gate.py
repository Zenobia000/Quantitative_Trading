"""two_stage_gate — ADR-025 two-stage validation gate.

The single binary ADR-016 gate (CAGR>18% / Sharpe>1.0 / slippage-Sharpe>1.0)
conflated two questions a real trading desk keeps separate:

  * **Is the edge real?** — an anti-self-deception question. Answered by the
    **TruthGate**: survivorship-clean + overfit controls, *binary hard-fail*. A
    strategy that cannot clear this is a false positive (selection overfit or
    survivor inflation) and is killed — sizing never runs.
  * **How much capital?** — a portfolio question. Answered by the **SizingGate**:
    a *continuous* map from (OOS Sharpe, correlation, capacity) to a position
    weight. A 0.9-Sharpe, zero-correlation sleeve is a *small allocation*, not a
    rejection. Absolute CAGR is demoted to reference and never drives sizing.

The crux refinement (ADR-025 §3.1): landscape **PBO measures config-SELECTION
overfit**. For a *pre-registered* single config (hypothesis locked, never chosen
from a sweep) PBO does not apply — its truth is judged on out-of-sample breadth
(WFA OOS>0 fraction) + a trials-deflated DSR. This is exactly what separates
inst_flow's survivorship-clean WFA median OOS 1.30 from its landscape PBO 0.43.

This does NOT resurrect ADR-023/024's dead candidates: momentum / multi-factor /
long-short were *selected* configs with landscape PBO 0.43-0.77 → they fail the
TruthGate's PBO check. inst_flow's pre-registered fixed config is the one that
can clear the TruthGate and proceed to sizing → paper.

Pure functions, no IO. Thresholds live in module-level constants (data, not
logic) so tuning one is a visible, recordable decision.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

import pandas as pd

# --------------------------------------------------------------------------- #
# Truth-gate thresholds (data, not logic — see module docstring)
# --------------------------------------------------------------------------- #
#: Max acceptable Probability of Backtest Overfitting for a SELECTED config (CSCV).
PBO_MAX: float = 0.30
#: Min fraction of WFA folds with OOS Sharpe > 0 for a PRE-REGISTERED config.
WFA_OOS_POSITIVE_MIN: float = 0.60
#: Min trials-deflated Sharpe Ratio for a PRE-REGISTERED config.
DSR_MIN: float = 0.95
#: K3 robustness: OOS must not collapse under 0.3% per-leg slippage (Sharpe > 0).
SLIPPAGE_SHARPE_MIN: float = 0.0
#: The locked OOS holdout [oos_start, is_end] must not lose money (Sharpe > 0). This
#: is the never-touched period; a negative Sharpe there is definitive overfit (ADR-030).
OOS_HOLDOUT_SHARPE_MIN: float = 0.0


class TruthVerdict(str, Enum):
    """Binary anti-self-deception verdict (with an explicit INCOMPLETE)."""

    REAL = "REAL"            # cleared every truth check → edge is not a false positive
    REJECTED = "REJECTED"    # hard-fail (survivor inflation / overfit / slippage collapse)
    INCOMPLETE = "INCOMPLETE"  # a required metric was missing → cannot claim REAL


@dataclass(frozen=True)
class TruthGateInput:
    """Evidence the TruthGate judges. ``pre_registered`` selects which overfit
    control applies: PBO (selected-from-sweep) vs OOS-breadth + DSR (a priori).
    """

    survivorship_clean: bool
    pre_registered: bool
    pbo: float | None = None                    # selection overfit (selected configs)
    wfa_oos_positive_frac: float | None = None  # OOS>0 fold fraction (pre-registered)
    dsr: float | None = None                    # trials-deflated SR (pre-registered)
    slippage_sharpe: float | None = None        # K3 robustness (all paths)
    oos_holdout_sharpe: float | None = None      # locked OOS holdout Sharpe (all paths)


@dataclass(frozen=True)
class TruthGateResult:
    verdict: TruthVerdict
    reasons: tuple[str, ...]  # one human-readable line per failed/missing check

    @property
    def is_real(self) -> bool:
        return self.verdict is TruthVerdict.REAL


def evaluate_truth_gate(inp: TruthGateInput) -> TruthGateResult:
    """Judge whether an edge is real (binary hard-fail). REJECTED dominates
    INCOMPLETE: a definitive failure (e.g. dirty survivorship) is reported even
    if some other metric is missing, because the candidate is already dead.
    """
    rejected: list[str] = []
    missing: list[str] = []

    # 1. survivorship-clean — a hard precondition for every path.
    if not inp.survivorship_clean:
        rejected.append("survivorship not clean (survivor-only universe inflates edge)")

    # 2. K3 slippage robustness — applies to every path.
    if inp.slippage_sharpe is None:
        missing.append("slippage_sharpe missing (K3 robustness unverifiable)")
    elif inp.slippage_sharpe <= SLIPPAGE_SHARPE_MIN:
        rejected.append(
            f"slippage Sharpe {inp.slippage_sharpe:.3g} <= {SLIPPAGE_SHARPE_MIN:.3g} "
            "(OOS collapses under 0.3% per-leg slippage)"
        )

    # 2b. Locked OOS holdout — optional (None ⇒ not evaluated), but when supplied a
    # non-positive Sharpe on the never-touched period is definitive overfit (ADR-030).
    if inp.oos_holdout_sharpe is not None and inp.oos_holdout_sharpe <= OOS_HOLDOUT_SHARPE_MIN:
        rejected.append(
            f"OOS holdout Sharpe {inp.oos_holdout_sharpe:.3g} <= {OOS_HOLDOUT_SHARPE_MIN:.3g} "
            "(edge does not survive the locked out-of-sample holdout)"
        )

    # 3. overfit control — branch on how the config was obtained.
    if inp.pre_registered:
        # PBO (a selection metric) is deliberately ignored here.
        if inp.wfa_oos_positive_frac is None:
            missing.append("wfa_oos_positive_frac missing (pre-registered OOS breadth)")
        elif inp.wfa_oos_positive_frac < WFA_OOS_POSITIVE_MIN:
            rejected.append(
                f"WFA OOS>0 frac {inp.wfa_oos_positive_frac:.3g} < {WFA_OOS_POSITIVE_MIN:.3g} "
                "(out-of-sample breadth too thin)"
            )
        if inp.dsr is None:
            missing.append("dsr missing (trials-deflated SR unverifiable)")
        elif inp.dsr < DSR_MIN:
            rejected.append(f"DSR {inp.dsr:.3g} < {DSR_MIN:.3g} (deflated significance)")
    else:
        if inp.pbo is None:
            missing.append("pbo missing (selection-overfit control unverifiable)")
        elif inp.pbo >= PBO_MAX:
            rejected.append(
                f"PBO {inp.pbo:.3g} >= {PBO_MAX:.3g} (config-selection overfit)"
            )

    if rejected:
        return TruthGateResult(TruthVerdict.REJECTED, tuple(rejected + missing))
    if missing:
        return TruthGateResult(TruthVerdict.INCOMPLETE, tuple(missing))
    return TruthGateResult(TruthVerdict.REAL, ())


# --------------------------------------------------------------------------- #
# Sizing gate — continuous capital allocation for a strategy that passed truth
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SizingConfig:
    """Tunable sizing parameters (data). ``max_weight`` caps a single sleeve;
    ``reference_sharpe`` is the Sharpe at which conviction saturates to full."""

    max_weight: float = 0.25
    reference_sharpe: float = 1.0


@dataclass(frozen=True)
class SizingInput:
    """Inputs to the continuous sizing map. ``cagr`` is carried for the record
    only — ADR-025 demotes absolute CAGR to reference, so it never sizes."""

    oos_sharpe: float
    correlation_to_fleet: float = 0.0  # [-1, 1]; lower/negative = more diversifying
    capacity_fraction: float = 1.0     # [0, 1]; room available before impact bites
    cagr: float | None = None          # reference only — NOT used in sizing


def compute_position_size(
    inp: SizingInput, cfg: SizingConfig = SizingConfig()
) -> float:
    """Map a truth-cleared strategy to a continuous position weight in
    ``[0, max_weight]``.

    size = max_weight × conviction × diversification × capacity, where
      * conviction = min(OOS Sharpe / reference_sharpe, 1)   — saturates at reference
      * diversification = 1 − max(0, correlation)            — neg-corr ≈ zero-corr
      * capacity = clip(capacity_fraction, 0, 1)

    A non-positive Sharpe yields 0 (no edge to size). A 0.9-Sharpe sleeve yields a
    real, smaller-than-full allocation — the ADR's core correction to binary
    pass/fail.
    """
    if inp.oos_sharpe <= 0.0:
        return 0.0
    conviction = min(inp.oos_sharpe / cfg.reference_sharpe, 1.0)
    diversification = 1.0 - max(0.0, min(inp.correlation_to_fleet, 1.0))
    capacity = max(0.0, min(inp.capacity_fraction, 1.0))
    return cfg.max_weight * conviction * diversification * capacity


# --------------------------------------------------------------------------- #
# Two-stage orchestration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GateDecision:
    """The full two-stage verdict: a truth result plus the sized allocation
    (``0.0`` whenever the truth gate did not return REAL)."""

    truth: TruthGateResult
    size: float


def evaluate_two_stage(
    truth_input: TruthGateInput,
    sizing_input: SizingInput,
    sizing_cfg: SizingConfig = SizingConfig(),
) -> GateDecision:
    """Run the truth gate, then size only if the edge is REAL. The truth gate is
    the hard precondition: a non-REAL verdict forces ``size == 0.0`` regardless
    of how strong the sizing inputs look."""
    truth = evaluate_truth_gate(truth_input)
    size = compute_position_size(sizing_input, sizing_cfg) if truth.is_real else 0.0
    return GateDecision(truth=truth, size=size)


def fleet_correlation(candidate: pd.Series, fleet: Sequence[pd.Series]) -> float:
    """Compute ``SizingInput.correlation_to_fleet`` from real return series.

    Mean pairwise Pearson correlation of the ``candidate`` daily-return series vs
    each live-fleet member, each aligned on its shared dates. An **empty fleet**
    returns ``0.0`` — the first sleeve carries no diversification penalty (ADR-025
    §sizing). Degenerate pairs (< 2 overlapping points, or a NaN correlation from a
    constant series) are skipped; if none survive, returns ``0.0``.

    This is the compute side of 8.G.10: feeding it the *actual* running fleet's
    returns is gated on a live multi-strategy fleet (ADR-022), but the mapping
    itself is exercised here against historical strategy returns.
    """
    if not fleet:
        return 0.0
    corrs: list[float] = []
    for member in fleet:
        joined = pd.concat([candidate, member], axis=1, join="inner").dropna()
        if len(joined) < 2:
            continue
        c = joined.iloc[:, 0].corr(joined.iloc[:, 1])
        if c == c:  # skip NaN (e.g. a constant series)
            corrs.append(float(c))
    return float(sum(corrs) / len(corrs)) if corrs else 0.0
