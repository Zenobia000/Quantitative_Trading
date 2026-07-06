"""Assemble a contract ``EvaluationResult`` from a ``RunBundle`` (rebuild Goal 3).

Pure functions (no IO) — unit-testable against
``dev_docs/contracts/evaluation_result.example.json``. The orchestrator runs the
primitives into a :class:`RunBundle`; this module turns that + the profile into the
persisted result: verdict + recommendation, headline metrics, the five scorecards,
the severity-graded ``checks[]`` (profile gates evaluated against real numbers),
sizing, lineage, and the honest ``data_gaps[]`` register.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from quant_platform.services.research_validation.evaluation.models import RunBundle
from quant_platform.services.research_validation.evaluation.profiles import EvaluationProfile
from quant_platform.services.research_validation.evaluation.scorecards import build_scorecards

SCHEMA_VERSION = "1.0"

# truth_verdict → (evaluation label, live-OOS recommendation, recommendation action, confidence)
_VERDICT_MAP: dict[str, tuple[str, str, str, str]] = {
    "REAL": ("Strong", "eligible", "eligible_for_deploy", "high"),
    "PAPER_WATCH": ("Weak", "eligible", "eligible_for_live_oos", "medium"),
    "REJECTED": ("Negative", "blocked", "archive_or_iterate", "high"),
    "INCOMPLETE": ("Incomplete", "blocked", "needs_more_evidence", "low"),
}
_RECO_ACTION = {
    "eligible": "eligible_for_live_oos",
    "not_recommended": "needs_more_research",
    "blocked": "not_deployable",
}
_CMP = {">": lambda v, t: v > t, ">=": lambda v, t: v >= t, "<": lambda v, t: v < t, "<=": lambda v, t: v <= t}


def _num(x: Any) -> float | None:
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _volatility(r: pd.Series) -> float:
    if r is None or len(r) == 0:
        return 0.0
    return float(pd.Series(r, dtype=float).std(ddof=0) * np.sqrt(252))


def _headline(bundle: RunBundle, returns: pd.Series) -> dict[str, Any]:
    from quant_platform.services.research_validation.validation import metrics as vmetrics
    m = bundle.metrics
    ex = bundle.extras
    r = returns
    out = {
        "cagr": _num(m.get("cagr")),
        "total_return": _num(vmetrics.total_return(r)) if len(r) else None,
        "sharpe": _num(m.get("sharpe")),
        "sortino": _num(vmetrics.sortino(r)) if len(r) else None,
        "calmar": _num(vmetrics.calmar(r)) if len(r) else None,
        "max_drawdown": _num(m.get("maxdd")),
        "volatility": _num(_volatility(r)),
        "oos_holdout_sharpe": _num(ex.get("oos_holdout_sharpe")),
        "slippage_sharpe": _num(ex.get("slippage_sharpe") if ex.get("slippage_sharpe") is not None else m.get("slippage_sharpe")),
        "dsr": _num(ex.get("dsr")),
        "wfa_oos_positive_frac": _num(ex.get("wfa_oos_positive_frac")),
        "n_trials": bundle.n_trials,
        "trades": int(m.get("trades", 0) or 0),
        "avg_holdings": _num(m.get("avg_holdings")),
        "avg_turnover": _num(m.get("avg_turnover")),
    }
    return out


def _gate_values(bundle: RunBundle) -> dict[str, Any]:
    ex = bundle.extras
    return {
        "survivorship_clean": bundle.survivorship_clean,
        "slippage_sharpe": ex.get("slippage_sharpe") if ex.get("slippage_sharpe") is not None else bundle.metrics.get("slippage_sharpe"),
        "oos_holdout_sharpe": ex.get("oos_holdout_sharpe"),
        "wfa_oos_positive_frac": ex.get("wfa_oos_positive_frac"),
        "dsr": ex.get("dsr"),
        "pbo": ex.get("pbo"),
    }


def _eval_check(gate: Any, values: dict[str, Any], run_mode: str) -> dict[str, Any]:
    guarded = (
        (gate.applies_when == "selected_from_grid" and run_mode != "grid")
        or (gate.applies_when == "pre_registered" and run_mode != "single_config")
    )
    value = values.get(gate.metric)
    check: dict[str, Any] = {
        "metric": gate.metric, "label": gate.label, "value": value,
        "threshold": gate.threshold, "op": gate.op, "severity": gate.severity,
    }
    if guarded:
        check["status"] = "not_applicable"
        check["reason"] = f"applies_when={gate.applies_when} does not match run_mode={run_mode}."
        return check
    if value is None:
        check["status"] = "missing"
        check["reason"] = f"{gate.metric} not produced by this profile run."
        return check
    if gate.op == "is_true":
        ok = bool(value) is True
    else:
        ok = _CMP.get(gate.op, lambda v, t: True)(value, gate.threshold)
    check["status"] = "pass" if ok else "fail"
    return check


def _scorecard_summary(scorecards: list[dict[str, Any]]) -> dict[str, str]:
    return {sc["category"]: sc["status"] for sc in scorecards}


def _triage_label(summary: dict[str, str]) -> str:
    ra = summary.get("risk_adjusted")
    prof = summary.get("profitability")
    if ra == "pass" and prof != "fail":
        return "Promising"
    if ra == "fail" or prof == "fail":
        return "Negative"
    return "Weak"


def _data_gaps(scorecards: list[dict[str, Any]]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for sc in scorecards:
        cat = sc["category"]
        if sc["status"] == "not_available" and not sc.get("metrics"):
            gaps.append({"field": f"{cat}.*", "reason": sc.get("note", "not available")})
            continue
        for cell in sc.get("metrics", []):
            if cell["status"] == "not_available":
                gaps.append({"field": f"{cat}.{cell['id']}", "reason": cell.get("reason", "not available")})
    gaps.append({"field": "lineage.git_sha", "reason": "run ledger carries no source-tree SHA today"})
    return gaps


def _recommendation(
    profile: EvaluationProfile, bundle: RunBundle, summary: dict[str, str],
) -> tuple[str, str, str, str]:
    """Return ``(label, live_oos_recommendation, action, confidence)``."""
    if bundle.data_issue:
        return "Data Issue", "blocked", "resolve_data_issue", "high"
    if bundle.truth_verdict in _VERDICT_MAP:
        label, reco, action, conf = _VERDICT_MAP[bundle.truth_verdict]
        return label, reco, action, conf
    reco = profile.live_oos_policy.default_recommendation
    return _triage_label(summary), reco, _RECO_ACTION[reco], "medium"


def _reasons(bundle: RunBundle, label: str, action: str, summary: dict[str, str]) -> list[str]:
    if bundle.data_issue:
        return ["Run produced no tradable bars — resolve data ingestion before re-evaluating."]
    if bundle.truth_verdict:
        base = [f"Truth gate verdict: {bundle.truth_verdict}."]
        base += list(bundle.truth_reasons[:4])
        return base
    passed = [k for k, v in summary.items() if v == "pass"]
    weak = [k for k, v in summary.items() if v in ("warn", "fail")]
    return [
        f"Triage label {label!r} from scorecard health.",
        f"Passing scorecards: {', '.join(passed) or 'none'}.",
        f"Attention scorecards: {', '.join(weak) or 'none'}.",
    ]


def assemble_result(
    profile: EvaluationProfile,
    bundle: RunBundle,
    *,
    strategy: str,
    run_id: str,
    evaluation_id: str,
    created_at: str,
) -> dict[str, Any]:
    """Build the full contract ``EvaluationResult`` dict from a run bundle + profile."""
    returns = pd.Series(bundle.returns, dtype=float) if bundle.returns is not None else pd.Series(dtype=float)
    scorecards = build_scorecards(
        returns, bundle.metrics, bundle.trades, profile,
        truth_extras=bundle.extras, data_issue=bundle.data_issue,
    )
    summary = _scorecard_summary(scorecards)
    label, live_reco, action, confidence = _recommendation(profile, bundle, summary)

    checks = [_eval_check(g, _gate_values(bundle), profile.run_mode) for g in profile.gates]
    headline = _headline(bundle, returns)

    sizing_reason = (
        "PAPER_WATCH / non-REAL is a zero-capital tier — sizing runs only when "
        "truth_verdict is REAL (validation.two_stage_gate.evaluate_two_stage)."
        if bundle.truth_verdict != "REAL" else "Sized from OOS Sharpe (ADR-025 SizingGate)."
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "run_id": run_id,
        "strategy": strategy,
        "profile": profile.name,
        "profile_version": profile.version,
        "created_at": created_at,
        "window": bundle.window,
        "universe": {
            "symbols_count": len(bundle.symbols),
            "bundle_ref": bundle.bundle_ref,
            "survivorship_clean": bundle.survivorship_clean,
        },
        "verdict": {
            "label": label,
            "truth_verdict": bundle.truth_verdict,
            "live_oos_recommendation": live_reco,
            "recommendation": {
                "action": action,
                "confidence": confidence,
                "reasons": _reasons(bundle, label, action, summary),
            },
        },
        "headline_metrics": headline,
        "scorecards": scorecards,
        "checks": checks,
        "sizing": {"position_size": bundle.position_size, "reason": sizing_reason},
        "lineage": {
            "config_hash": run_id,
            "config_hash_source": "research.run_config.RunConfig.run_id (sha1 over strategy|params|engine|stocks|window)",
            "params": bundle.params,
            "engine": "sim",
            "bundle_ref": bundle.bundle_ref,
            "n_trials": bundle.n_trials,
            "survivorship_clean": bundle.survivorship_clean,
            "git_sha": None,
            "git_sha_status": "not_available",
            "git_sha_reason": "Run ledger records carry no git_sha field today (run_id is a config hash, not a source-tree hash).",
        },
        "report_pack": profile.report_pack,
        "report_pack_ref": f"reports/research_runs/{run_id}/manifest.json",
        "data_gaps": _data_gaps(scorecards),
    }
