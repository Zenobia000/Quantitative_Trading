"""``/metrics`` — performance metrics over a posted return / trade series.

Stateless calculators exposing the A/B/C (return / risk / risk-adjusted) and E
(trade-quality) families from ``validation.metrics``. Useful for ad-hoc scoring
of any series a client holds, independent of the runs ledger.
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from quant_platform.apps.api.envelope import Envelope, ok
from quant_platform.apps.api.response_models import MetricsData
from quant_platform.apps.api.schemas import MetricsSummaryRequest, TradeMetricsRequest
from quant_platform.services.research_validation.validation import metrics as M

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/summary", response_model=Envelope[MetricsData])
def metrics_summary(req: MetricsSummaryRequest) -> Envelope:
    """A/B/C metrics (total return, CAGR, drawdown, Sharpe, Sortino, Calmar)."""
    s = pd.Series(req.daily_returns, dtype=float)
    data = {
        "total_return": M.total_return(s),
        "cagr": M.cagr(s),
        "max_drawdown": M.max_drawdown(s),
        "ulcer_index": M.ulcer_index(s),
        "downside_deviation": M.downside_deviation(s),
        "sharpe": M.sharpe(s, risk_free=req.risk_free),
        "sortino": M.sortino(s, risk_free=req.risk_free),
        "calmar": M.calmar(s),
    }
    return ok(data)


@router.post("/trades", response_model=Envelope[MetricsData])
def metrics_trades(req: TradeMetricsRequest) -> Envelope:
    """E metrics (win rate, profit factor, avg hold, Kelly fraction).

    The trade records must carry the ``pnl`` (and, for avg hold, ``hold_days``)
    keys; a missing key is a 400 (client sent the wrong shape) rather than a 500.
    """
    trades = req.trades
    try:
        data = {
            "win_rate": M.win_rate(trades),
            "profit_factor": M.profit_factor(trades),
            "avg_hold": M.avg_hold(trades),
            "kelly_fraction": M.kelly_fraction(trades),
        }
    except (KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=400, detail=f"trade record missing required key: {exc}"
        ) from None
    return ok(data)
