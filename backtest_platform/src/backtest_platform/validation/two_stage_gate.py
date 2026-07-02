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
#: Min trials-deflated Sharpe Ratio for a PRE-REGISTERED config to DEPLOY capital.
DSR_MIN: float = 0.95
#: Floor of the ADR-033 Paper-Watch band. A pre-registered config that clears EVERY
#: hard-fail clause but lands DSR ∈ [PAPER_WATCH_DSR_MIN, DSR_MIN) is not a false edge
#: (still ≥ 90% prob of beating the max-of-N-trials noise floor) — it enters a
#: ZERO-CAPITAL 3-month observation艙 to collect live OOS. This is an evidence channel,
#: NOT a deployment-threshold relaxation: DSR_MIN (0.95) still gates every allocation.
PAPER_WATCH_DSR_MIN: float = 0.90
#: K3 robustness: OOS must not collapse under 0.3% per-leg slippage (Sharpe > 0).
SLIPPAGE_SHARPE_MIN: float = 0.0
#: The locked OOS holdout [oos_start, is_end] must not lose money (Sharpe > 0). This
#: is the never-touched period; a negative Sharpe there is definitive overfit (ADR-030).
OOS_HOLDOUT_SHARPE_MIN: float = 0.0


class TruthVerdict(str, Enum):
    """Anti-self-deception verdict. REAL/REJECTED are the deploy dichotomy; PAPER_WATCH
    (ADR-033) is the zero-capital observation tier between them; INCOMPLETE is explicit."""

    REAL = "REAL"            # cleared every truth check AND DSR ≥ 0.95 → deployable
    PAPER_WATCH = "PAPER_WATCH"  # every hard-fail cleared but DSR ∈ [0.90, 0.95) → 觀察艙, 0 capital
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

    @property
    def is_paper_watch(self) -> bool:
        """True only for the ADR-033 zero-capital observation tier."""
        return self.verdict is TruthVerdict.PAPER_WATCH


def _classify_dsr(dsr: float | None) -> tuple[str, str]:
    """Band a PRE-REGISTERED config's DSR, returning ``(band, human_line)`` where
    band ∈ {"ok", "watch", "reject", "missing"}. The band is judged SEPARATELY from
    the other hard-fails so a near-miss (ADR-033 Paper-Watch) is distinguished from a
    definitive deflation failure: "reject" (< 0.90) is a dead edge; "watch"
    ([0.90, 0.95)) is high-but-sub-deployment evidence → zero-capital observation.
    """
    if dsr is None:
        return "missing", "dsr missing (trials-deflated SR unverifiable)"
    if dsr >= DSR_MIN:
        return "ok", ""
    if dsr >= PAPER_WATCH_DSR_MIN:
        return "watch", (
            f"DSR {dsr:.3g} ∈ [{PAPER_WATCH_DSR_MIN:.3g}, {DSR_MIN:.3g}) — paper-watch "
            "band (ADR-033): zero-capital 3-month live-OOS observation艙, NOT deployable"
        )
    return "reject", f"DSR {dsr:.3g} < {PAPER_WATCH_DSR_MIN:.3g} (deflated significance)"


def _universal_hard_fails(inp: TruthGateInput) -> tuple[list[str], list[str]]:
    """Preconditions on EVERY path: survivorship, K3 slippage, locked OOS holdout.
    Returns ``(rejected, missing)``; the holdout is optional (None ⇒ not evaluated)."""
    rejected: list[str] = []
    missing: list[str] = []
    if not inp.survivorship_clean:
        rejected.append("survivorship not clean (survivor-only universe inflates edge)")
    if inp.slippage_sharpe is None:
        missing.append("slippage_sharpe missing (K3 robustness unverifiable)")
    elif inp.slippage_sharpe <= SLIPPAGE_SHARPE_MIN:
        rejected.append(
            f"slippage Sharpe {inp.slippage_sharpe:.3g} <= {SLIPPAGE_SHARPE_MIN:.3g} "
            "(OOS collapses under 0.3% per-leg slippage)"
        )
    if inp.oos_holdout_sharpe is not None and inp.oos_holdout_sharpe <= OOS_HOLDOUT_SHARPE_MIN:
        rejected.append(
            f"OOS holdout Sharpe {inp.oos_holdout_sharpe:.3g} <= {OOS_HOLDOUT_SHARPE_MIN:.3g} "
            "(edge does not survive the locked out-of-sample holdout)"
        )
    return rejected, missing


def _overfit_control(inp: TruthGateInput) -> tuple[list[str], list[str], list[str]]:
    """Overfit control, branched on how the config was obtained. Returns
    ``(rejected, missing, watch)``. Pre-registered ⇒ OOS breadth + DSR band (the
    only path that can yield a Paper-Watch ``watch`` line); selected ⇒ landscape PBO.
    """
    rejected: list[str] = []
    missing: list[str] = []
    watch: list[str] = []
    if inp.pre_registered:
        if inp.wfa_oos_positive_frac is None:
            missing.append("wfa_oos_positive_frac missing (pre-registered OOS breadth)")
        elif inp.wfa_oos_positive_frac < WFA_OOS_POSITIVE_MIN:
            rejected.append(
                f"WFA OOS>0 frac {inp.wfa_oos_positive_frac:.3g} < {WFA_OOS_POSITIVE_MIN:.3g} "
                "(out-of-sample breadth too thin)"
            )
        band, line = _classify_dsr(inp.dsr)
        if band != "ok":  # ok ⇒ DSR clears the deploy bar, no line to record
            {"reject": rejected, "missing": missing, "watch": watch}[band].append(line)
    elif inp.pbo is None:
        missing.append("pbo missing (selection-overfit control unverifiable)")
    elif inp.pbo >= PBO_MAX:
        rejected.append(f"PBO {inp.pbo:.3g} >= {PBO_MAX:.3g} (config-selection overfit)")
    return rejected, missing, watch


def evaluate_truth_gate(inp: TruthGateInput) -> TruthGateResult:
    """Judge an edge across four verdicts. Priority: REJECTED ≻ INCOMPLETE ≻
    PAPER_WATCH ≻ REAL. A definitive hard-fail (dirty survivorship, thin OOS breadth,
    DSR < 0.90 …) dominates everything — the Paper-Watch band (ADR-033) is reachable
    ONLY when every hard-fail clause passes and the *sole* shortfall is a DSR in
    [0.90, 0.95); any missing metric collapses to INCOMPLETE, never the觀察艙.
    """
    r1, m1 = _universal_hard_fails(inp)
    r2, m2, watch = _overfit_control(inp)
    rejected, missing = r1 + r2, m1 + m2
    if rejected:
        return TruthGateResult(TruthVerdict.REJECTED, tuple(rejected + missing))
    if missing:
        return TruthGateResult(TruthVerdict.INCOMPLETE, tuple(missing))
    if watch:
        return TruthGateResult(TruthVerdict.PAPER_WATCH, tuple(watch))
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
    the hard precondition: any non-REAL verdict forces ``size == 0.0`` regardless
    of how strong the sizing inputs look. In particular PAPER_WATCH (ADR-033) is a
    ZERO-CAPITAL observation tier — it is deliberately NOT ``is_real``, so the艙
    never produces an allocation; live OOS is collected at position_size 0.0."""
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
