"""Paper/live signal adapter for the inst-flow factor (7.A.4).

W3.1 / W5.1d: relocated from ``strategies.inst_flow.signal_fn`` into
``services.strategy_runtime`` — the qty-sizing / stop-loss / priority logic is
layer-4/5 execution, not research. The pure cross-sectional ``flow_intensity``
ranking stays in research (``strategies.inst_flow.strategy``); this adapter only
imports it. The old ``strategies.inst_flow.signal_fn`` path is a re-export shim.


Turns the cross-sectional inst-flow ranking into a daily-flow ``signal_fn`` so the
*validated* fixed config (ADR-024 / inst_flow_truth_gate REAL) can drive the real
ETL→signals→risk→orders→log chain. On an as-of date it ranks the universe by
trailing net-buy intensity (reusing ``flow_intensity`` so the live signal matches
the backtest factor exactly) and emits equal-weight BUY signals for the top names.

The signal dicts use the exact schema the chain proved out (test_chain_integration
+ collaborators): ``side='buy'`` string, plus the risk-gate fields
(stop_loss / prev_close / avg_volume_20d / industry).

NOTE — ``max_names`` deliberately caps below the factor's top-fraction breadth
(~1/3 of the universe ≈ 38 names): the RiskGate EX-007 limit is 15 concurrent
holdings, so a faithful full-breadth basket would be rejected. Position sizing
here is a conservative paper-replay default; portfolio-level sizing is the
SizingGate's job (8.G.10).
"""
from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date
from typing import Any

import pandas as pd

from quant_platform.services.research_validation.strategies.inst_flow.strategy import InstFlowConfig, flow_intensity

#: Conservative paper-replay sizing defaults (gate-safe; see module docstring).
DEFAULT_MAX_NAMES = 8
DEFAULT_PER_NAME_CAP = 450_000.0  # < EX-001 single-order NT$500k
STOP_LOSS_FRAC = 0.04  # 4% stop — safely inside EX-008 (>= entry × 0.95) with margin
                       # for price rounding (a flat 5% can round below the threshold)


def compute_inst_flow_signals(
    close: pd.DataFrame,
    flow: pd.DataFrame,
    volume: pd.DataFrame,
    cfg: InstFlowConfig,
    as_of: date,
    *,
    equity: float,
    max_names: int = DEFAULT_MAX_NAMES,
    per_name_cap: float = DEFAULT_PER_NAME_CAP,
) -> list[dict[str, Any]]:
    """Rank by inst-flow intensity as-of ``as_of`` and emit equal-weight BUY signals.

    Uses the latest score row on or before ``as_of`` (so a non-trading as-of date
    falls back to the prior session). Returns the chain's signal-dict schema.
    """
    score = flow_intensity(flow, volume, cfg.lookback_days)
    if cfg.signal_lag_days:
        score = score.shift(cfg.signal_lag_days)

    asof_ts = pd.Timestamp(as_of)
    avail = score.index[score.index <= asof_ts]
    if len(avail) == 0:
        return []
    as_row = avail[-1]
    ranked = score.loc[as_row].dropna().sort_values(ascending=False)
    if ranked.empty:
        return []

    k = max(1, int(len(ranked) * cfg.top_fraction))
    held = [s for s in ranked.index[:k] if ranked[s] > 0][:max_names]
    if not held:
        return []

    per_name = min(equity / len(held), per_name_cap)
    prices = close.loc[as_row] if as_row in close.index else close.iloc[-1]

    signals: list[dict[str, Any]] = []
    for rank, sid in enumerate(held, start=1):
        price = float(prices.get(sid, float("nan")))
        if not math.isfinite(price) or price <= 0:
            continue
        qty = int(per_name // price)
        if qty <= 0:
            continue
        avg_vol = float(volume[sid].tail(20).mean()) if sid in volume else 0.0
        signals.append({
            "stock_id": sid,
            "side": "buy",
            "qty": qty,
            "price": round(price, 4),
            "action": "buy",
            "priority": 2,
            "reason": {
                "factor": "inst_flow_intensity",
                "rank": rank,
                "score": float(ranked[sid]),
                "as_of": str(as_row.date()),
            },
            "stop_loss": round(price * (1.0 - STOP_LOSS_FRAC), 4),
            "prev_close": round(price, 4),
            "avg_volume_20d": avg_vol,
            "industry": "",
        })
    return signals


def make_inst_flow_signal_fn(
    close: pd.DataFrame,
    flow: pd.DataFrame,
    volume: pd.DataFrame,
    cfg: InstFlowConfig,
    as_of: date,
    *,
    equity: float,
    max_names: int = DEFAULT_MAX_NAMES,
    per_name_cap: float = DEFAULT_PER_NAME_CAP,
) -> Callable[[Any], list[dict[str, Any]]]:
    """Bind the panel + as-of date into a daily-flow ``signal_fn`` (ignores ctx —
    the panel is the data source for a historical replay)."""

    def signal_fn(_ctx: Any) -> list[dict[str, Any]]:
        return compute_inst_flow_signals(
            close, flow, volume, cfg, as_of,
            equity=equity, max_names=max_names, per_name_cap=per_name_cap,
        )

    return signal_fn
