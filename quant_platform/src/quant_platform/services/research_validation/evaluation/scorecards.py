"""The five FinLab-style scorecards (rebuild Goal 3).

Builds the ``scorecards[]`` block of an ``EvaluationResult`` from a strategy run's
returns / metrics / trades (+ optional truth-gate extras), exactly matching
``dev_docs/contracts/evaluation_result.example.json``. Every metric is judged
per-metric ``pass | warn | fail | missing | not_applicable | not_available`` — a
scorecard is never a single binary verdict (research plan §6.2).

Honesty rule (spec §8 #6): a metric that CANNOT be produced from the current
stores is emitted as ``not_available`` with a ``reason``, never fabricated. The 12
``not_available`` field families are the contract's §11 register (benchmark
alpha/beta, VaR/CVaR, per-trade pnl/excursion for the whole Win-Rate card, ADV
liquidity metrics, git_sha) — this module reproduces them verbatim.

Thresholds are DATA, not logic: a scorecard metric's soft reference bar comes from
(1) the profile's ``gates[]`` when a gate names that metric (the authoritative,
severity-graded, profile-defined threshold), else (2) the module-level
``_SOFT_REFS`` table of the well-known ADR-016 K1/K2 + panel display bars — the
same "thresholds live in constants" convention as ``validation.gate_state``.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from quant_platform.services.research_validation.evaluation.profiles import EvaluationProfile
from quant_platform.services.research_validation.validation import metrics as vmetrics
from quant_platform.services.research_validation.validation.report import drawdown_events

# The five FinLab-style scorecard categories (contract order).
CATEGORIES: tuple[str, ...] = ("profitability", "risk", "risk_adjusted", "win_rate", "liquidity")

#: Well-known display reference bars for scorecard metrics that are NOT profile
#: gates (data, not logic — mirrors ``gate_state.DEFAULT_GATE``). A profile gate on
#: the same metric always wins (``_resolve_threshold``).
_SOFT_REFS: dict[str, tuple[float, str]] = {
    "cagr": (0.18, ">"),          # ADR-016 K1 edge bar
    "sharpe": (1.0, ">"),         # ADR-016 K2
    "avg_holdings": (5.0, ">="),  # panel diversification floor (gate_state.PANEL_GATE)
}

# not_available reasons — verbatim from the contract §11 register / example.
_NA = {
    "alpha": "No benchmark return series is joined in the current run/series stores; Alpha/Beta need a benchmark feed (rule #6 gap).",
    "beta": "Same benchmark-series gap as Alpha.",
    "max_holdings": "panel_metrics tracks avg_holdings only; per-rebalance holdings max is not persisted.",
    "var_95": "validation.metrics implements downside_deviation but not VaR/CVaR; needs a new quantile estimator (P1 metric gap).",
    "cvar_95": "Same VaR/CVaR gap.",
    "profit_factor": "Panel `trades` is a rebalance count, not a per-trade pnl list; validation.metrics.profit_factor needs trade dicts with a `pnl` key (rule #6 P1 blocker).",
    "tail_ratio": "Not implemented in validation.metrics; needs return-distribution percentile ratio.",
    "trade_win_rate": "Panel `trades` is a rebalance count, not a per-trade pnl list; validation.metrics.win_rate needs trade dicts with `pnl`/`ret`.",
    "payoff_ratio": "Needs per-trade pnl distribution (same schema gap).",
    "expectancy": "Needs per-trade pnl (same schema gap).",
    "rolling_12m_win_rate": "Needs per-trade timestamps to bucket by month; not persisted in the v1 sidecar.",
    "mae": "No entry-to-extreme excursion tracking anywhere in the codebase; needs intrabar trade path (P1).",
    "mfe": "Same excursion-tracking gap as MAE.",
    "volume_bucket_distribution": "Needs per-trade notional joined against per-bar ADV; the trades schema carries no notional/volume field (rule #6, P1).",
    "safe_trade_fraction": "Needs trade notional vs ADV cap; same trade-schema gap.",
    "capacity_proxy": "Needs ADV + position-size join to estimate max deployable capital; not derivable from current stores.",
}

_ROLLUP_RANK = {"pass": 0, "warn": 1, "fail": 2}


def _resolve_threshold(profile: EvaluationProfile, metric_id: str) -> tuple[float | None, str | None]:
    """Threshold + op for a scorecard metric: profile gate wins, else the soft ref."""
    for g in profile.gates:
        if g.metric == metric_id and isinstance(g.threshold, (int, float)) and not isinstance(g.threshold, bool):
            return float(g.threshold), g.op
    if metric_id in _SOFT_REFS:
        thr, op = _SOFT_REFS[metric_id]
        return thr, op
    return None, None


def _status_for(value: float | None, threshold: float | None, op: str | None) -> str:
    """pass / warn from a value vs a soft display bar (info-severity display metric)."""
    if value is None:
        return "missing"
    if threshold is None or op is None:
        return "pass"
    ok = {">": value > threshold, ">=": value >= threshold, "<": value < threshold, "<=": value <= threshold}.get(op, True)
    return "pass" if ok else "warn"


def _cell(
    metric_id: str,
    label: str,
    value: float | None,
    unit: str,
    *,
    profile: EvaluationProfile,
    severity: str = "info",
    source_module: str | None,
    note: str | None = None,
    reason: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """One scorecard metric object (contract shape)."""
    threshold: float | None = None
    op: str | None = None
    if reason is not None:
        status = "not_available"
        value = None
    else:
        threshold, op = _resolve_threshold(profile, metric_id)
        if status is None:
            status = _status_for(value, threshold, op)
    cell: dict[str, Any] = {
        "id": metric_id,
        "label": label,
        "value": value,
        "unit": unit,
        "threshold": threshold,
        "op": op,
        "status": status,
        "severity": severity,
        "source_module": source_module,
    }
    if note is not None:
        cell["note"] = note
    if reason is not None:
        cell["reason"] = reason
    return cell


def _rollup(cells: list[dict[str, Any]]) -> str:
    """Category status: worst of pass/warn/fail; not_available if every cell is."""
    scored = [c["status"] for c in cells if c["status"] in _ROLLUP_RANK]
    if not scored:
        return "not_available"
    return max(scored, key=lambda s: _ROLLUP_RANK[s])


def _equity(returns: pd.Series) -> list[float]:
    if returns is None or len(returns) == 0:
        return []
    return [float(x) for x in (1.0 + returns.astype(float)).cumprod()]


def _trade_outcomes(trades: list[dict[str, Any]]) -> np.ndarray | None:
    """Per-trade numeric outcome (``pnl`` or four-layer ``ret``); None if unavailable."""
    if not trades:
        return None
    for key in ("pnl", "ret"):
        if all(key in t for t in trades):
            try:
                return np.asarray([float(t[key]) for t in trades], dtype=float)
            except (TypeError, ValueError):
                return None
    return None


def build_scorecards(
    returns: pd.Series,
    metrics: dict[str, Any],
    trades: list[dict[str, Any]],
    profile: EvaluationProfile,
    *,
    truth_extras: dict[str, Any] | None = None,
    data_issue: bool = False,
) -> list[dict[str, Any]]:
    """Assemble the five scorecards for one evaluation (contract ``scorecards[]``).

    ``truth_extras`` carries gate-derived numbers a plain run cannot (``oos_holdout_sharpe``,
    ``dsr``, ``wfa_oos_positive_frac``, ``slippage_sharpe``). ``data_issue`` (empty
    series / zero bars) forces every scorecard to ``not_available`` — a data gap must
    read differently from a real weak result.
    """
    extras = truth_extras or {}
    if data_issue:
        return [
            {
                "category": cat,
                "status": "not_available",
                "note": "Empty equity series — the run yielded no tradable bars (data quality gap).",
                "metrics": [],
            }
            for cat in CATEGORIES
        ]

    r = pd.Series(returns, dtype=float) if returns is not None else pd.Series(dtype=float)
    slip = metrics.get("slippage_sharpe")
    sharpe_val = metrics.get("sharpe", vmetrics.sharpe(r) if len(r) else 0.0)

    return [
        _profitability(r, metrics, profile),
        _risk(r, profile),
        _risk_adjusted(r, metrics, trades, profile, extras),
        _win_rate(trades, profile),
        _liquidity(metrics, sharpe_val, slip, profile),
    ]


def _profitability(r: pd.Series, metrics: dict[str, Any], profile: EvaluationProfile) -> dict[str, Any]:
    cells = [
        _cell("cagr", "CAGR", metrics.get("cagr", vmetrics.cagr(r) if len(r) else 0.0), "fraction",
              profile=profile, source_module="validation.metrics.cagr"),
        _cell("total_return", "Total return", vmetrics.total_return(r) if len(r) else 0.0, "fraction",
              profile=profile, source_module="validation.metrics.total_return"),
        _cell("avg_holdings", "Avg holdings", metrics.get("avg_holdings"), "count",
              profile=profile, source_module="strategies.common.panel.panel_metrics")
        if metrics.get("avg_holdings") is not None else
        _cell("avg_holdings", "Avg holdings", None, "count", profile=profile,
              source_module=None, reason="This strategy does not emit avg_holdings (non-panel run)."),
        _cell("alpha", "Alpha (vs benchmark)", None, "fraction", profile=profile,
              source_module=None, reason=_NA["alpha"]),
        _cell("beta", "Beta (vs benchmark)", None, "ratio", profile=profile,
              source_module=None, reason=_NA["beta"]),
        _cell("max_holdings", "Max holdings", None, "count", profile=profile,
              source_module=None, reason=_NA["max_holdings"]),
    ]
    return {"category": "profitability", "status": _rollup(cells), "metrics": cells}


def _risk(r: pd.Series, profile: EvaluationProfile) -> dict[str, Any]:
    events = drawdown_events(_equity(r)) if len(r) else []
    avg_dd = float(np.mean([e["depth"] for e in events])) if events else 0.0
    worst_recovery = max((e["duration_bars"] for e in events), default=0)
    cells = [
        _cell("max_drawdown", "Max drawdown", vmetrics.max_drawdown(r) if len(r) else 0.0, "fraction",
              profile=profile, source_module="validation.metrics.max_drawdown"),
        _cell("ulcer_index", "Ulcer index", vmetrics.ulcer_index(r) if len(r) else 0.0, "fraction",
              profile=profile, source_module="validation.metrics.ulcer_index"),
        _cell("avg_drawdown", "Avg drawdown", avg_dd, "fraction",
              profile=profile, source_module="validation.report.drawdown_events"),
        _cell("recovery_days_worst", "Worst recovery (bars)", float(worst_recovery), "bars",
              profile=profile, source_module="validation.report.drawdown_events",
              note="Bar-indexed; the v1 series sidecar persists no date index."),
        _cell("var_95", "VaR 95%", None, "fraction", profile=profile, source_module=None, reason=_NA["var_95"]),
        _cell("cvar_95", "CVaR 95%", None, "fraction", profile=profile, source_module=None, reason=_NA["cvar_95"]),
    ]
    return {"category": "risk", "status": _rollup(cells), "metrics": cells}


def _risk_adjusted(
    r: pd.Series, metrics: dict[str, Any], trades: list[dict[str, Any]],
    profile: EvaluationProfile, extras: dict[str, Any],
) -> dict[str, Any]:
    cells = [
        _cell("sharpe", "Sharpe (IS)", metrics.get("sharpe", vmetrics.sharpe(r) if len(r) else 0.0), "ratio",
              profile=profile, source_module="validation.metrics.sharpe"),
        _cell("sortino", "Sortino", vmetrics.sortino(r) if len(r) else 0.0, "ratio",
              profile=profile, source_module="validation.metrics.sortino"),
        _cell("calmar", "Calmar", vmetrics.calmar(r) if len(r) else 0.0, "ratio",
              profile=profile, source_module="validation.metrics.calmar"),
    ]
    if extras.get("oos_holdout_sharpe") is not None:
        cells.append(_cell(
            "oos_holdout_sharpe", "OOS holdout Sharpe", float(extras["oos_holdout_sharpe"]), "ratio",
            profile=profile, severity="block_deploy", source_module="workflows.truth_gate"))
    outcomes = _trade_outcomes(trades)
    if outcomes is not None and outcomes.size:
        pf = vmetrics.profit_factor([{"pnl": x} for x in outcomes])
        cells.append(_cell("profit_factor", "Profit factor", pf, "ratio",
                           profile=profile, source_module="validation.metrics.profit_factor"))
    else:
        cells.append(_cell("profit_factor", "Profit factor", None, "ratio",
                           profile=profile, source_module=None, reason=_NA["profit_factor"]))
    cells.append(_cell("tail_ratio", "Tail ratio", None, "ratio",
                       profile=profile, source_module=None, reason=_NA["tail_ratio"]))
    return {"category": "risk_adjusted", "status": _rollup(cells), "metrics": cells}


def _win_rate(trades: list[dict[str, Any]], profile: EvaluationProfile) -> dict[str, Any]:
    outcomes = _trade_outcomes(trades)
    if outcomes is None or outcomes.size == 0:
        cells = [
            _cell(mid, label, None, unit, profile=profile, source_module=None, reason=_NA[mid])
            for mid, label, unit in (
                ("trade_win_rate", "Trade win rate", "fraction"),
                ("payoff_ratio", "Payoff ratio", "ratio"),
                ("expectancy", "Expectancy", "fraction"),
                ("rolling_12m_win_rate", "Rolling 12M win rate", "fraction"),
                ("mae", "Max adverse excursion", "fraction"),
                ("mfe", "Max favorable excursion", "fraction"),
            )
        ]
        return {
            "category": "win_rate",
            "status": "not_available",
            "note": "Whole scorecard is not_available for panel strategies until the trades "
                    "schema carries per-trade pnl / entry / exit / excursion fields (rule #6).",
            "metrics": cells,
        }
    # Partial availability: per-trade outcomes exist (e.g. four_layer_resonance ret).
    wins = outcomes[outcomes > 0]
    losses = outcomes[outcomes < 0]
    win_rate = float(wins.size / outcomes.size)
    payoff = float(wins.mean() / abs(losses.mean())) if wins.size and losses.size and losses.mean() != 0 else None
    expectancy = float(outcomes.mean())
    cells = [
        _cell("trade_win_rate", "Trade win rate", win_rate, "fraction",
              profile=profile, source_module="validation.metrics.win_rate (per-trade ret)"),
        _cell("payoff_ratio", "Payoff ratio", payoff, "ratio", profile=profile,
              source_module="validation.metrics (per-trade ret)")
        if payoff is not None else
        _cell("payoff_ratio", "Payoff ratio", None, "ratio", profile=profile,
              source_module=None, reason="No losing trades to estimate payoff odds."),
        _cell("expectancy", "Expectancy", expectancy, "fraction",
              profile=profile, source_module="mean per-trade ret"),
        _cell("rolling_12m_win_rate", "Rolling 12M win rate", None, "fraction",
              profile=profile, source_module=None, reason=_NA["rolling_12m_win_rate"]),
        _cell("mae", "Max adverse excursion", None, "fraction",
              profile=profile, source_module=None, reason=_NA["mae"]),
        _cell("mfe", "Max favorable excursion", None, "fraction",
              profile=profile, source_module=None, reason=_NA["mfe"]),
    ]
    return {"category": "win_rate", "status": _rollup(cells), "metrics": cells}


def _liquidity(
    metrics: dict[str, Any], sharpe_val: float | None, slip: float | None,
    profile: EvaluationProfile,
) -> dict[str, Any]:
    turnover = metrics.get("avg_turnover")
    cells = []
    if turnover is not None:
        cells.append(_cell("avg_turnover", "Avg turnover", float(turnover), "fraction",
                           profile=profile, source_module="strategies.common.panel.panel_metrics"))
    else:
        cells.append(_cell("avg_turnover", "Avg turnover", None, "fraction", profile=profile,
                           source_module=None, reason="This strategy does not emit avg_turnover (non-panel run)."))
    if sharpe_val is not None and slip is not None:
        decay = float(sharpe_val) - float(slip)
        cells.append(_cell(
            "cost_sensitivity", "Cost sensitivity (Sharpe decay under K3 slippage)", decay, "ratio_delta",
            profile=profile, status="warn" if decay > 0 else "pass",
            source_module="strategies (sharpe vs slippage_sharpe)",
            note=f"Sharpe falls {decay:.3f} under K3 stress." if decay > 0 else None))
    else:
        cells.append(_cell("cost_sensitivity", "Cost sensitivity", None, "ratio_delta", profile=profile,
                           source_module=None, reason="slippage_sharpe unavailable for this run."))
    for mid, label, unit in (
        ("volume_bucket_distribution", "Volume-bucket distribution", "distribution"),
        ("safe_trade_fraction", "Safe-trade fraction", "fraction"),
        ("capacity_proxy", "Capacity proxy (TWD)", "currency"),
    ):
        cells.append(_cell(mid, label, None, unit, profile=profile, source_module=None, reason=_NA[mid]))
    return {"category": "liquidity", "status": _rollup(cells), "metrics": cells}
