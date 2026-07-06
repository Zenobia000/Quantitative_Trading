"""Evaluation profile registry (rebuild Goal 3 / ADR-039).

A *profile* is a high-level, reusable evaluation recipe that sits ABOVE the
low-level ADR-029 workflow primitives (``doe`` / ``go_gates`` / ``truth_gate`` /
``paper_replay``). A profile declares HOW a strategy is evaluated — which
primitives it wraps, which of the five FinLab-style scorecards it emits, which
severity-graded gates it applies, and how expensive it is — and NEVER replaces
the primitives; it orchestrates them (``orchestrator.evaluate``).

The four built-ins are the authoritative contract in
``packages/contracts/schemas/evaluation_profile.schema.json`` ``examples[]``. They live
here as validated Pydantic models so the orchestrator, the CLI and the API all
read one source; ``tests/research/evaluation/test_profiles.py`` asserts these
built-ins are byte-identical to the contract examples, so the schema stays the
single truth and this module can never silently drift from it.

``severity`` replaces a single binary verdict (research plan §6.2):
``info`` (display) → ``warn`` (poolable note) → ``block_live_oos`` (don't spend
live OOS without a human override) → ``block_deploy`` (never allocate capital).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Profile schema (mirrors packages/contracts/schemas/evaluation_profile.schema.json) #
# --------------------------------------------------------------------------- #


class MetricSpec(BaseModel):
    """Per-metric enable/param declaration (research plan §6.2 MetricSpec)."""

    model_config = {"frozen": True, "extra": "forbid"}

    id: str
    enabled: bool
    params: dict[str, Any] | None = None
    source_module: str | None = None


class GateRule(BaseModel):
    """One severity-graded gate rule (research plan §6.2 GateRule).

    ``severity`` REPLACES a single binary verdict; ``applies_when`` guards
    applicability (ADR-025: landscape PBO applies only to grid-selected configs,
    DSR-band only to pre-registered configs).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    metric: str
    op: str = Field(..., pattern=r"^(>|>=|<|<=|between|exists|is_true)$")
    threshold: float | bool | str | list[Any] | None
    severity: str = Field(..., pattern=r"^(info|warn|block_live_oos|block_deploy)$")
    label: str
    applies_when: str = "always"
    source_module: str | None = None


class LiveOOSPolicy(BaseModel):
    """The profile's DEFAULT live-OOS recommendation + human-selection rules."""

    model_config = {"frozen": True, "extra": "forbid"}

    default_recommendation: str = Field(..., pattern=r"^(eligible|not_recommended|blocked)$")
    requires_human_selection: bool
    override_requires_reason: bool


class EvaluationProfile(BaseModel):
    """A high-level evaluation recipe above the ADR-029 primitives (see module doc)."""

    model_config = {"frozen": True, "extra": "forbid"}

    name: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    version: str
    title: str
    description: str | None = None
    stage: str = Field(..., pattern=r"^(triage|candidate|deployment)$")
    run_mode: str = Field(..., pattern=r"^(single_config|grid|random|bayesian|none)$")
    wraps_primitives: tuple[str, ...] = Field(..., min_length=1)
    scorecards: tuple[str, ...] = ()
    metrics: tuple[MetricSpec, ...] = ()
    gates: tuple[GateRule, ...] = ()
    report_pack: str = Field(..., pattern=r"^(triage_basic|scorecard_pack|grid_landscape|deployment_full)$")
    produces_sheets: tuple[str, ...] = ()
    live_oos_policy: LiveOOSPolicy
    persist_failed: bool
    runtime_magnitude: str = Field(..., pattern=r"^(seconds|minutes|tens_of_minutes|hours)$")
    source_modules: tuple[str, ...] = Field(..., min_length=1)


# --------------------------------------------------------------------------- #
# The four built-in profiles — verbatim from the contract examples[].          #
# Kept as dicts (validated into models below) so the contract-fidelity test    #
# can compare `_BUILTIN_DICTS` directly against the schema examples.           #
# --------------------------------------------------------------------------- #

_QUICK_TRIAGE: dict[str, Any] = {
    "name": "quick_triage",
    "version": "1.0",
    "title": "Quick Triage",
    "description": (
        "Fastest look: one single-config backtest + the five scorecards. Answers "
        "'is this worth researching?' with no PBO / DSR / full WFA / paper replay. "
        "Every result is persisted, including failures."
    ),
    "stage": "triage",
    "run_mode": "single_config",
    "wraps_primitives": ["single_run"],
    "scorecards": ["profitability", "risk", "risk_adjusted", "win_rate", "liquidity"],
    "metrics": [
        {"id": "cagr", "enabled": True, "source_module": "validation.metrics.cagr"},
        {"id": "total_return", "enabled": True, "source_module": "validation.metrics.total_return"},
        {"id": "sharpe", "enabled": True, "source_module": "validation.metrics.sharpe"},
        {"id": "sortino", "enabled": True, "source_module": "validation.metrics.sortino"},
        {"id": "calmar", "enabled": True, "source_module": "validation.metrics.calmar"},
        {"id": "max_drawdown", "enabled": True, "source_module": "validation.metrics.max_drawdown"},
        {"id": "ulcer_index", "enabled": True, "source_module": "validation.metrics.ulcer_index"},
        {"id": "avg_turnover", "enabled": True, "source_module": "strategies.common.panel.panel_metrics"},
        {"id": "avg_holdings", "enabled": True, "source_module": "strategies.common.panel.panel_metrics"},
        {"id": "cost_sensitivity", "enabled": True, "source_module": "strategies (sharpe vs slippage_sharpe)"},
        {"id": "pbo", "enabled": False},
        {"id": "dsr", "enabled": False},
        {"id": "wfa_oos_positive_frac", "enabled": False},
    ],
    "gates": [
        {
            "metric": "survivorship_clean", "op": "is_true", "threshold": True,
            "severity": "warn", "label": "Survivorship-clean universe", "applies_when": "always",
            "source_module": "research_config declaration / build_universe cache",
        }
    ],
    "report_pack": "scorecard_pack",
    "produces_sheets": ["summary", "headline_metrics", "scorecards", "equity_drawdown", "trade_quality"],
    "live_oos_policy": {
        "default_recommendation": "not_recommended",
        "requires_human_selection": True,
        "override_requires_reason": True,
    },
    "persist_failed": True,
    "runtime_magnitude": "seconds",
    "source_modules": [
        "strategies.protocol.get_strategy (dispatch, ADR-028)",
        "validation.metrics",
        "validation.report (monthly_returns_matrix, drawdown_events)",
        "research.run_series_store (equity/drawdown/trades sidecar)",
    ],
}

_FIXED_HYPOTHESIS_OOS: dict[str, Any] = {
    "name": "fixed_hypothesis_oos",
    "version": "1.0",
    "title": "Fixed Hypothesis IS/OOS",
    "description": (
        "Evaluates a pre-registered, locked hypothesis: IS/OOS split, WFA-lite OOS "
        "breadth, OOS holdout Sharpe, and cost stress. PBO disabled (config was not "
        "selected from a sweep); DSR optional."
    ),
    "stage": "candidate",
    "run_mode": "single_config",
    "wraps_primitives": ["single_run", "go_gates"],
    "scorecards": ["profitability", "risk", "risk_adjusted", "win_rate", "liquidity"],
    "metrics": [
        {"id": "cagr", "enabled": True, "source_module": "validation.metrics.cagr"},
        {"id": "sharpe", "enabled": True, "source_module": "validation.metrics.sharpe"},
        {"id": "wfa_oos_positive_frac", "enabled": True, "source_module": "workflows.go_gates + validation.wfa.walk_forward_splits"},
        {"id": "oos_holdout_sharpe", "enabled": True, "source_module": "strategies dispatch on locked OOS window"},
        {"id": "slippage_sharpe", "enabled": True, "source_module": "strategies K3 slippage seam (with_extra_slippage)"},
        {"id": "dsr", "enabled": True, "params": {"optional": True}, "source_module": "validation.dsr.deflated_sharpe_from_returns"},
        {"id": "pbo", "enabled": False},
    ],
    "gates": [
        {"metric": "wfa_oos_positive_frac", "op": ">=", "threshold": 0.6, "severity": "block_live_oos", "label": "WFA OOS>0 breadth ≥ 60%", "applies_when": "pre_registered", "source_module": "validation.two_stage_gate.WFA_OOS_POSITIVE_MIN"},
        {"metric": "oos_holdout_sharpe", "op": ">", "threshold": 0.0, "severity": "warn", "label": "OOS holdout Sharpe > 0", "applies_when": "always", "source_module": "validation.two_stage_gate.OOS_HOLDOUT_SHARPE_MIN"},
        {"metric": "slippage_sharpe", "op": ">", "threshold": 0.0, "severity": "warn", "label": "K3 slippage Sharpe > 0", "applies_when": "always", "source_module": "validation.two_stage_gate.SLIPPAGE_SHARPE_MIN"},
        {"metric": "dsr", "op": ">=", "threshold": 0.95, "severity": "info", "label": "DSR ≥ 0.95 (reference)", "applies_when": "pre_registered", "source_module": "validation.two_stage_gate.DSR_MIN"},
    ],
    "report_pack": "scorecard_pack",
    "produces_sheets": ["summary", "headline_metrics", "scorecards", "equity_drawdown", "is_oos_split", "wfa_folds", "cost_sensitivity"],
    "live_oos_policy": {
        "default_recommendation": "eligible",
        "requires_human_selection": True,
        "override_requires_reason": True,
    },
    "persist_failed": True,
    "runtime_magnitude": "minutes",
    "source_modules": [
        "workflows.go_gates.run_go_gates (WFA breadth)",
        "validation.wfa",
        "validation.dsr",
        "validation.metrics",
        "strategies.protocol dispatch",
    ],
}

_GRID_SEARCH_SELECTION: dict[str, Any] = {
    "name": "grid_search_selection",
    "version": "1.0",
    "title": "Grid Search + Selection",
    "description": (
        "For strategies whose config was chosen from a parameter landscape: DOE grid "
        "scan, plateau/heatmap, landscape PBO (config-selection overfit), "
        "trials-deflated DSR, and top-N comparison."
    ),
    "stage": "candidate",
    "run_mode": "grid",
    "wraps_primitives": ["doe", "go_gates"],
    "scorecards": ["profitability", "risk", "risk_adjusted", "win_rate", "liquidity"],
    "metrics": [
        {"id": "grid_metrics", "enabled": True, "source_module": "workflows.doe.run_doe (per-combo metrics)"},
        {"id": "pbo", "enabled": True, "source_module": "workflows.go_gates + validation.pbo.probability_of_backtest_overfitting"},
        {"id": "dsr", "enabled": True, "params": {"use_n_trials": True}, "source_module": "validation.dsr.deflated_sharpe_from_returns"},
        {"id": "wfa_oos_positive_frac", "enabled": True, "source_module": "workflows.go_gates + validation.wfa"},
        {"id": "cagr", "enabled": True, "source_module": "validation.metrics.cagr"},
        {"id": "sharpe", "enabled": True, "source_module": "validation.metrics.sharpe"},
    ],
    "gates": [
        {"metric": "pbo", "op": "<", "threshold": 0.3, "severity": "block_live_oos", "label": "Landscape PBO < 30%", "applies_when": "selected_from_grid", "source_module": "validation.two_stage_gate.PBO_MAX"},
        {"metric": "dsr", "op": ">=", "threshold": 0.95, "severity": "info", "label": "Trials-deflated DSR ≥ 0.95 (reference)", "applies_when": "selected_from_grid", "source_module": "validation.two_stage_gate.DSR_MIN"},
        {"metric": "wfa_oos_positive_frac", "op": ">=", "threshold": 0.6, "severity": "warn", "label": "WFA OOS>0 breadth ≥ 60%", "applies_when": "always", "source_module": "workflows.go_gates._WFA_PASS"},
    ],
    "report_pack": "grid_landscape",
    "produces_sheets": ["summary", "headline_metrics", "scorecards", "grid_csv", "heatmap", "plateau", "top_n", "pbo_matrix", "cherry_pick_audit"],
    "live_oos_policy": {
        "default_recommendation": "not_recommended",
        "requires_human_selection": True,
        "override_requires_reason": True,
    },
    "persist_failed": True,
    "runtime_magnitude": "tens_of_minutes",
    "source_modules": [
        "workflows.doe.run_doe",
        "workflows.go_gates.run_go_gates",
        "validation.pbo",
        "validation.dsr",
        "validation.wfa",
    ],
}

_DEPLOYMENT_STRICT: dict[str, Any] = {
    "name": "deployment_strict",
    "version": "1.0",
    "title": "Deployment Strict (Truth Gate)",
    "description": (
        "The existing ADR-025/030 two-stage truth gate, unchanged, exposed as a "
        "deployment-level profile: survivorship-clean precondition, WFA OOS breadth, "
        "trials-deflated DSR, locked OOS holdout, K3 slippage stress, then continuous "
        "sizing. This is NOT the only evaluation path — it is the capital-protection "
        "profile a human selects after triage."
    ),
    "stage": "deployment",
    "run_mode": "single_config",
    "wraps_primitives": ["truth_gate"],
    "scorecards": ["profitability", "risk", "risk_adjusted", "win_rate", "liquidity"],
    "metrics": [
        {"id": "survivorship_clean", "enabled": True, "source_module": "TruthGateConfig.survivorship_clean / build_universe cache"},
        {"id": "wfa_oos_positive_frac", "enabled": True, "source_module": "workflows.truth_gate._wfa_oos_breadth + validation.wfa"},
        {"id": "dsr", "enabled": True, "source_module": "validation.dsr.deflated_sharpe_from_returns"},
        {"id": "oos_holdout_sharpe", "enabled": True, "source_module": "workflows.truth_gate (locked OOS run)"},
        {"id": "slippage_sharpe", "enabled": True, "source_module": "workflows.truth_gate._slippage_sharpe"},
        {"id": "position_size", "enabled": True, "source_module": "validation.two_stage_gate.compute_position_size"},
    ],
    "gates": [
        {"metric": "survivorship_clean", "op": "is_true", "threshold": True, "severity": "block_deploy", "label": "Survivorship-clean (hard precondition)", "applies_when": "always", "source_module": "validation.two_stage_gate._universal_hard_fails"},
        {"metric": "slippage_sharpe", "op": ">", "threshold": 0.0, "severity": "block_deploy", "label": "K3 slippage Sharpe > 0", "applies_when": "always", "source_module": "validation.two_stage_gate.SLIPPAGE_SHARPE_MIN"},
        {"metric": "oos_holdout_sharpe", "op": ">", "threshold": 0.0, "severity": "block_deploy", "label": "OOS holdout Sharpe > 0", "applies_when": "always", "source_module": "validation.two_stage_gate.OOS_HOLDOUT_SHARPE_MIN"},
        {"metric": "wfa_oos_positive_frac", "op": ">=", "threshold": 0.6, "severity": "block_deploy", "label": "WFA OOS>0 breadth ≥ 60%", "applies_when": "pre_registered", "source_module": "validation.two_stage_gate.WFA_OOS_POSITIVE_MIN"},
        {"metric": "dsr", "op": ">=", "threshold": 0.95, "severity": "block_deploy", "label": "Trials-deflated DSR ≥ 0.95", "applies_when": "pre_registered", "source_module": "validation.two_stage_gate.DSR_MIN"},
        {"metric": "pbo", "op": "<", "threshold": 0.3, "severity": "block_deploy", "label": "Landscape PBO < 30%", "applies_when": "selected_from_grid", "source_module": "validation.two_stage_gate.PBO_MAX"},
        {"metric": "dsr", "op": ">=", "threshold": 0.9, "severity": "block_live_oos", "label": "Paper-Watch DSR floor ≥ 0.90 (ADR-033 observation band)", "applies_when": "pre_registered", "source_module": "validation.two_stage_gate.PAPER_WATCH_DSR_MIN"},
    ],
    "report_pack": "deployment_full",
    "produces_sheets": ["summary", "headline_metrics", "scorecards", "truth_gate_verdict", "wfa_folds", "dsr_deflation", "oos_holdout", "slippage_stress", "sizing"],
    "live_oos_policy": {
        "default_recommendation": "blocked",
        "requires_human_selection": True,
        "override_requires_reason": True,
    },
    "persist_failed": True,
    "runtime_magnitude": "tens_of_minutes",
    "source_modules": [
        "workflows.truth_gate.run_truth_gate",
        "validation.two_stage_gate (evaluate_two_stage, thresholds)",
        "validation.dsr",
        "validation.wfa",
        "research.watch_registry (ADR-033 Paper-Watch berth)",
    ],
}

#: Raw contract dicts, in registry order — the fidelity test compares these to
#: ``evaluation_profile.schema.json`` ``examples[]``.
_BUILTIN_DICTS: list[dict[str, Any]] = [
    _QUICK_TRIAGE,
    _FIXED_HYPOTHESIS_OOS,
    _GRID_SEARCH_SELECTION,
    _DEPLOYMENT_STRICT,
]

#: name → validated EvaluationProfile (the single in-process registry).
_REGISTRY: dict[str, EvaluationProfile] = {
    d["name"]: EvaluationProfile.model_validate(d) for d in _BUILTIN_DICTS
}


def list_profiles() -> list[EvaluationProfile]:
    """Every built-in profile, in registry (triage → deployment) order."""
    return [_REGISTRY[d["name"]] for d in _BUILTIN_DICTS]


def list_profile_names() -> list[str]:
    """The built-in profile names, in registry order."""
    return [d["name"] for d in _BUILTIN_DICTS]


def get_profile(name: str) -> EvaluationProfile:
    """Resolve a profile by name; ``ValueError`` (→ API 404 / clean CLI error) if unknown."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown evaluation profile {name!r}; choose from {list_profile_names()}"
        ) from None
