"""Research-only what-if simulation over an already-computed run (rebuild Goal 8).

Given a run's *persisted* series (the ``run_series_store`` equity curve + trades
sidecar) this module answers "what if costs / slippage / capacity / a stop-loss /
a take-profit had been different?" — **without re-running the backtest and without
touching the original config, ledger, or report pack**. Everything here is a pure
read-only recomputation over numbers we already have on disk; the caller (the
``/research/simulate`` endpoint) never persists the result (research sandbox, not a
verdict — spec Goal 8 acceptance).

Two honest metric spaces, because the two data shapes support different what-ifs:

* **portfolio-equity space** — cost multiplier / slippage / capacity are applied by
  reconstructing per-bar returns from the equity curve and re-deriving the eight
  headline metrics. This works for *every* run that persisted an equity sidecar.
* **trade-population space** — stop-loss / take-profit clamp each closed trade's
  return, then re-derive trade-quality metrics. This only works for strategies that
  persist *per-trade* returns (``four_layer_resonance`` emits ``{ret, hold, …}``);
  **panel strategies persist a rebalance count with no per-trade pnl (the #188 /
  contract §11 P1 blocker), so their stop-loss / take-profit knobs honestly degrade
  to ``not_available`` with a reason** (spec rule #6), never fabricated.

Why per-bar returns cannot inherit a per-trade clamp: the daily equity curve nets
*overlapping* positions, so clamping one trade's return does not map onto a single
bar. Stop-loss / take-profit therefore move only the trade-population metrics; the
portfolio-equity metrics stay at baseline (disclosed, not silently zeroed).

Cost model (portfolio-equity space), deliberately simple so it is hand-checkable:

    returns   = eq[i]/eq[i-1] - 1                      # per-bar, from the sidecar
    scaled    = capacity_scale * returns               # exposure (leverage) scaling
    extra     = slippage_cost + multiplier_cost        # incremental fractional cost
    drag      = extra / n_bars                          # spread uniformly per bar
    adjusted  = scaled - drag
    after_eq  = cumprod(1 + adjusted)

where ``slippage_cost = slippage_bps * 1e-4 * turnover_units`` (additive, needs no
baseline) and ``multiplier_cost = (cost_multiplier - 1) * base_round_trip_cost *
turnover_units`` (needs the run's declared round-trip cost; ``not_available`` when
the run params expose none). ``turnover_units`` = ``avg_turnover * n_rebalances``
for panel runs, or the closed-trade count for four-layer runs.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from backtest_platform.validation import metrics

#: One basis point as a fraction.
_BPS = 1e-4
#: Trading days per year — matches ``validation.metrics.ANNUALIZATION`` for the
#: annualized volatility figure (the one headline metric metrics.py does not expose).
_TRADING_DAYS = 252

#: Reason strings (single source, reused by per_param + data_gaps + the two spaces).
_NO_EQUITY = "run persisted no equity series sidecar — portfolio-space what-if unavailable"
_NO_PER_TRADE = (
    "strategy trades carry no per-trade return (panel rebalance count only, "
    "contract §11 P1 blocker) — stop-loss / take-profit what-if unavailable"
)
_NO_BASE_COST = (
    "run params declare no transaction-cost rate — a cost multiplier needs a "
    "baseline to scale (slippage_bps is unaffected)"
)


# --------------------------------------------------------------------------- #
# Pure numeric helpers                                                         #
# --------------------------------------------------------------------------- #
def reconstruct_returns(equity: Sequence[float]) -> list[float]:
    """Per-bar simple returns ``eq[i]/eq[i-1] - 1`` from an equity curve.

    Mirrors ``api.routers.runs_report._returns_from_equity`` (one convention for
    turning the sidecar equity back into returns). A zero/absent prior point → 0.0.
    """
    eq = [float(x) for x in equity]
    out: list[float] = []
    for i in range(1, len(eq)):
        prev = eq[i - 1]
        out.append(eq[i] / prev - 1.0 if prev else 0.0)
    return out


def has_per_trade_returns(trades: Sequence[dict[str, Any]]) -> bool:
    """True when trades carry a numeric per-trade return (``ret``) — the feasibility
    test for stop-loss / take-profit. Panel runs (empty / count-only) → False."""
    if not trades:
        return False
    for t in trades:
        v = t.get("ret")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
    return True


def base_round_trip_cost(params: dict[str, Any] | None) -> float | None:
    """The run's declared round-trip transaction cost from its params, or ``None``.

    Honest, strategy-agnostic extraction (no import of strategy configs):
      * ``cost_round_rate`` present (inst_flow / panel mechanics) → use it verbatim.
      * fee / tax / slippage rates present (four_layer) → ``2·fee + tax + 2·slip``
        (buy+sell fee, sell-side tax, both-legs slippage — matches the sim's
        entry/exit cost application).
      * otherwise → ``None`` (cost multiplier degrades to ``not_available``).
    """
    if not params:
        return None
    if isinstance(params.get("cost_round_rate"), (int, float)):
        return float(params["cost_round_rate"])
    fee = params.get("fee_rate")
    if isinstance(fee, (int, float)):
        tax = params.get("tax_stock_rate", 0.0) or 0.0
        slip = params.get("slip_rate", 0.0) or 0.0
        return float(2.0 * fee + tax + 2.0 * slip)
    return None


def annualized_volatility(returns: Sequence[float]) -> float:
    """Annualized population std of per-bar returns (``std·√252``); empty → 0.0.

    Pure-Python reduction (no ``ndarray.std``) so the figure is deterministic and
    free of the numpy-reload sentinel artefact coverage sub-module runs can trigger.
    """
    vals = [float(x) for x in returns if not _isnan(x)]
    n = len(vals)
    if n == 0:
        return 0.0
    mean = sum(vals) / n
    var = sum((x - mean) ** 2 for x in vals) / n
    return (var**0.5) * (_TRADING_DAYS**0.5)


def _isnan(x: float) -> bool:
    """True for NaN (``x != x``) — avoids importing math into a hot list-comp."""
    return x != x


def portfolio_metrics(returns: Sequence[float]) -> dict[str, float]:
    """The eight headline portfolio metrics from a per-bar returns series.

    Reuses ``validation.metrics`` so a what-if is judged by the same canonical
    estimators as every real run (no bespoke Sharpe here).
    """
    s = pd.Series([float(x) for x in returns], dtype=float)
    return {
        "total_return": metrics.total_return(s),
        "cagr": metrics.cagr(s),
        "sharpe": metrics.sharpe(s),
        "sortino": metrics.sortino(s),
        "calmar": metrics.calmar(s),
        "max_drawdown": metrics.max_drawdown(s),
        "ulcer_index": metrics.ulcer_index(s),
        "volatility": annualized_volatility(returns),
    }


def trade_metrics(trades: Sequence[dict[str, Any]]) -> dict[str, float]:
    """Trade-population quality metrics from a list of ``{ret, hold?}`` dicts.

    Pure-Python reductions (trade lists are small) — deterministic and free of the
    numpy-reload sentinel artefact, and exact for the hand-checked test examples.
    """
    rets = [float(t["ret"]) for t in trades] if trades else []
    n = len(rets)
    if n == 0:
        return {
            "n_trades": 0, "win_rate": 0.0, "avg_trade_return": 0.0,
            "total_trade_return": 0.0, "profit_factor": 0.0, "avg_hold": 0.0,
        }
    wins = [r for r in rets if r > 0]
    gross_loss = abs(sum(r for r in rets if r < 0))
    compounded = 1.0
    for r in rets:
        compounded *= 1.0 + r
    holds = [
        float(t["hold"])
        for t in trades
        if isinstance(t.get("hold"), (int, float)) and not isinstance(t.get("hold"), bool)
    ]
    return {
        "n_trades": n,
        "win_rate": len(wins) / n,
        "avg_trade_return": sum(rets) / n,
        "total_trade_return": compounded - 1.0,
        "profit_factor": (sum(wins) / gross_loss) if gross_loss > 0 else 0.0,
        "avg_hold": (sum(holds) / len(holds)) if holds else 0.0,
    }


def apply_equity_whatif(
    returns: Sequence[float],
    *,
    capacity_scale: float,
    extra_cost_total: float,
) -> list[float]:
    """Transform per-bar returns: exposure-scale, then subtract a uniform cost drag.

    ``drag = extra_cost_total / n_bars`` (arithmetic spread — the simplest
    hand-checkable distribution of an aggregate cost across the window).
    """
    r = [float(x) for x in returns]
    if not r:
        return []
    drag = extra_cost_total / len(r)
    return [capacity_scale * x - drag for x in r]


def clamp_trades(
    trades: Sequence[dict[str, Any]],
    *,
    stop_loss_pct: float | None,
    take_profit_pct: float | None,
) -> tuple[list[dict[str, Any]], int]:
    """Clamp each trade's ``ret`` to ``[-stop_loss_pct, +take_profit_pct]``.

    A loss beyond the stop would have exited at the stop (``ret = -stop_loss_pct``);
    a gain beyond the target would have exited at the target. Returns the new trade
    list (new dicts — immutability) and the count of trades actually moved.
    """
    out: list[dict[str, Any]] = []
    affected = 0
    for t in trades:
        ret = float(t["ret"])
        new = ret
        if stop_loss_pct is not None and ret < -stop_loss_pct:
            new = -stop_loss_pct
        if take_profit_pct is not None and new > take_profit_pct:
            new = take_profit_pct
        if new != ret:
            affected += 1
        out.append({**t, "ret": new})
    return out, affected


def _deltas(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    """``after - before`` per shared key (absolute delta; UI colours by sign)."""
    return {k: float(after[k] - before[k]) for k in before if k in after}


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #
def simulate(
    equity: Sequence[float] | None,
    trades: Sequence[dict[str, Any]] | None,
    *,
    strategy: str | None = None,
    cost_multiplier: float = 1.0,
    slippage_bps: float = 0.0,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    capacity_scale: float = 1.0,
    n_trades: int | None = None,
    turnover_units: float | None = None,
    round_trip_cost: float | None = None,
) -> dict[str, Any]:
    """Compute a :data:`SimulationResult`-shaped dict (read-only, never persisted).

    ``equity`` / ``trades`` come straight from ``run_series_store.read_series``;
    ``n_trades`` / ``turnover_units`` / ``round_trip_cost`` are scalar hints the
    caller derives from the run record (cost model inputs). Every unsupported knob
    is reported ``not_available`` with a reason (spec rule #6), never silently
    dropped. The ``schema_version`` / field shape follow
    ``dev_docs/contracts/simulation_result.example.json``.
    """
    equity = list(equity) if equity else []
    trades = list(trades) if trades else []
    has_equity = len(equity) >= 2
    has_trades = has_per_trade_returns(trades)

    n_cost_events = n_trades if n_trades is not None else len(trades)
    turnover = turnover_units if turnover_units is not None else float(n_cost_events)

    # ---- resolve which knobs actually apply (per_param audit) -------------- #
    per_param: list[dict[str, Any]] = []
    data_gaps: list[dict[str, str]] = []

    def _record(param: str, requested: Any, space: str, applied: bool,
                status: str, reason: str | None = None) -> None:
        entry = {"param": param, "requested": requested, "space": space,
                 "applied": applied, "status": status}
        if reason:
            entry["reason"] = reason
            data_gaps.append({"field": param, "reason": reason})
        per_param.append(entry)

    # cost multiplier (portfolio-equity) — needs a baseline round-trip cost.
    mult_applies = cost_multiplier != 1.0
    if not mult_applies:
        _record("cost_multiplier", cost_multiplier, "portfolio_equity", False, "noop")
    elif not has_equity:
        _record("cost_multiplier", cost_multiplier, "portfolio_equity", False, "not_available", _NO_EQUITY)
    elif round_trip_cost is None:
        _record("cost_multiplier", cost_multiplier, "portfolio_equity", False, "not_available", _NO_BASE_COST)
    else:
        _record("cost_multiplier", cost_multiplier, "portfolio_equity", True, "applied")

    # slippage (portfolio-equity) — additive, no baseline needed.
    slip_applies = slippage_bps != 0.0
    if not slip_applies:
        _record("slippage_bps", slippage_bps, "portfolio_equity", False, "noop")
    elif not has_equity:
        _record("slippage_bps", slippage_bps, "portfolio_equity", False, "not_available", _NO_EQUITY)
    else:
        _record("slippage_bps", slippage_bps, "portfolio_equity", True, "applied")

    # capacity scale (portfolio-equity) — exposure/leverage multiplier.
    cap_applies = capacity_scale != 1.0
    if not cap_applies:
        _record("capacity_scale", capacity_scale, "portfolio_equity", False, "noop")
    elif not has_equity:
        _record("capacity_scale", capacity_scale, "portfolio_equity", False, "not_available", _NO_EQUITY)
    else:
        _record("capacity_scale", capacity_scale, "portfolio_equity", True, "applied")

    # stop-loss / take-profit (trade-population) — need per-trade returns.
    for param, val in (("stop_loss_pct", stop_loss_pct), ("take_profit_pct", take_profit_pct)):
        if val is None:
            _record(param, None, "trade_population", False, "noop")
        elif not has_trades:
            _record(param, val, "trade_population", False, "not_available", _NO_PER_TRADE)
        else:
            _record(param, val, "trade_population", True, "applied")

    applied_mult = mult_applies and has_equity and round_trip_cost is not None
    applied_slip = slip_applies and has_equity
    applied_cap = cap_applies and has_equity
    applied_sl = stop_loss_pct is not None and has_trades
    applied_tp = take_profit_pct is not None and has_trades

    # ---- portfolio-equity space ------------------------------------------- #
    if has_equity:
        base_returns = reconstruct_returns(equity)
        before_p = portfolio_metrics(base_returns)
        slip_cost = slippage_bps * _BPS * turnover if applied_slip else 0.0
        mult_cost = ((cost_multiplier - 1.0) * round_trip_cost * turnover) if applied_mult else 0.0
        after_returns = apply_equity_whatif(
            base_returns,
            capacity_scale=capacity_scale if applied_cap else 1.0,
            extra_cost_total=slip_cost + mult_cost,
        )
        after_p = portfolio_metrics(after_returns)
        portfolio_block = {
            "available": True, "reason": None, "space": "portfolio_equity",
            "before": before_p, "after": after_p, "deltas": _deltas(before_p, after_p),
        }
    else:
        portfolio_block = {
            "available": False, "reason": _NO_EQUITY, "space": "portfolio_equity",
            "before": None, "after": None, "deltas": None,
        }

    # ---- trade-population space ------------------------------------------- #
    clamp_affected = 0
    if has_trades:
        before_t = trade_metrics(trades)
        if applied_sl or applied_tp:
            clamped, clamp_affected = clamp_trades(
                trades,
                stop_loss_pct=stop_loss_pct if applied_sl else None,
                take_profit_pct=take_profit_pct if applied_tp else None,
            )
        else:
            clamped = trades
        after_t = trade_metrics(clamped)
        trade_block = {
            "available": True, "reason": None, "space": "trade_population",
            "before": before_t, "after": after_t, "deltas": _deltas(before_t, after_t),
        }
    else:
        trade_block = {
            "available": False, "reason": _NO_PER_TRADE, "space": "trade_population",
            "before": None, "after": None, "deltas": None,
        }

    # ---- affected trades count -------------------------------------------- #
    # A per-trade clamp names the exact moved trades; an equity-space knob touches
    # every cost-incurring trade/rebalance (report the whole cost-event count).
    if applied_sl or applied_tp:
        affected = clamp_affected
    elif applied_mult or applied_slip or applied_cap:
        affected = int(n_cost_events)
    else:
        affected = 0

    return {
        "schema_version": "1.0",
        "strategy": strategy,
        "research_only": True,
        "applied_params": {
            "cost_multiplier": cost_multiplier,
            "slippage_bps": slippage_bps,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "capacity_scale": capacity_scale,
        },
        "portfolio_metrics": portfolio_block,
        "trade_metrics": trade_block,
        "affected_trades_count": affected,
        "per_param": per_param,
        "branch_suggestion": _branch_suggestion(
            cost_multiplier=cost_multiplier if applied_mult else None,
            slippage_bps=slippage_bps if applied_slip else None,
            capacity_scale=capacity_scale if applied_cap else None,
            stop_loss_pct=stop_loss_pct if applied_sl else None,
            take_profit_pct=take_profit_pct if applied_tp else None,
        ),
        "data_gaps": data_gaps,
    }


def _branch_suggestion(
    *,
    cost_multiplier: float | None,
    slippage_bps: float | None,
    capacity_scale: float | None,
    stop_loss_pct: float | None,
    take_profit_pct: float | None,
) -> dict[str, Any] | None:
    """A config-delta *description* for the applied what-if — never applied here.

    Goal 8 output is a *suggestion*: the operator would fork this into a branch
    experiment (Goal 9) to actually change the config. ``actionable = false`` so
    the UI wires the button disabled with the honest "待分支實驗 (Goal 9)" note.
    Returns ``None`` when nothing was applied (nothing to suggest).
    """
    deltas: list[dict[str, Any]] = []
    if cost_multiplier is not None:
        deltas.append({"key": "cost_multiplier", "from": 1.0, "to": cost_multiplier,
                       "note": "stress the transaction-cost assumption"})
    if slippage_bps is not None:
        deltas.append({"key": "slippage_bps", "from": 0.0, "to": slippage_bps,
                       "note": "add slippage stress"})
    if capacity_scale is not None:
        deltas.append({"key": "capacity_scale", "from": 1.0, "to": capacity_scale,
                       "note": "scale deployed exposure"})
    if stop_loss_pct is not None:
        deltas.append({"key": "stop_loss_pct", "from": None, "to": stop_loss_pct,
                       "note": "add a per-trade stop-loss exit"})
    if take_profit_pct is not None:
        deltas.append({"key": "take_profit_pct", "from": None, "to": take_profit_pct,
                       "note": "add a per-trade take-profit exit"})
    if not deltas:
        return None
    return {
        "label": "fork_as_branch_experiment",
        "description": (
            "Fork this run into a branch experiment to test the parameters above "
            "against the parent — this simulation does not change any config."
        ),
        "config_delta": deltas,
        "actionable": False,
        "actionable_reason": "branch experiments land in Goal 9 (not yet implemented)",
    }
