"""Four-layer-resonance offline portfolio sim — pure helpers (ADR-027).

These were the private helpers inside ``research.is_harness``; they are pure
functions over a merged per-stock frame + a ``StrategyConfig`` (no IO, no preset
lookup), so they belong with the strategy, not the research harness. Moving them
here lets the strategy runner (``research.runners.FourLayerRunner``) and the
research harness share ONE implementation of the close-to-close sim without an
upward ``strategies → research`` dependency.

``research.is_harness`` re-exports these names for backward compatibility, so
existing importers (``research.sweep`` + tests) keep working unchanged.

NOTE: ``_metrics`` / ``_sharpe`` are four-layer-local metric calcs kept verbatim
for now; unifying them onto ``validation.metrics`` is Stage 2 (metrics dedup).
"""
from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from quant_platform.services.research_validation.strategies.four_layer_resonance.config import StrategyConfig
from quant_platform.services.research_validation.strategies.four_layer_resonance.scoring import compute_scores
from quant_platform.services.research_validation.strategies.four_layer_resonance.signals import compute_signals
from quant_platform.services.research_validation.validation.metrics import cagr as _cagr
from quant_platform.services.research_validation.validation.metrics import sharpe as _sharpe

TRADING_DAYS = 252
_SLIP_STRESS = 0.003  # 0.3% slippage for the K3 robustness Sharpe

# Minimum bars in the signaled window before a stock contributes to the portfolio.
MIN_BARS = 30


def signaled_window(
    merged: pd.DataFrame, cfg: StrategyConfig, start: date | str, end: date | str
) -> pd.DataFrame:
    """Score + signal a stock's history, sliced to ``[start, end]``."""
    m = merged.copy()
    m["trade_date"] = pd.to_datetime(m["trade_date"])
    m = m.sort_values("trade_date").reset_index(drop=True)
    hist = m[m["trade_date"] <= pd.Timestamp(end)].reset_index(drop=True)
    sig = compute_signals(compute_scores(hist, cfg), cfg)
    win = sig[(sig["trade_date"] >= pd.Timestamp(start)) & (sig["trade_date"] <= pd.Timestamp(end))]
    return win.reset_index(drop=True)


def daily_returns(sig: pd.DataFrame, cfg: StrategyConfig) -> pd.Series:
    """Position-lagged daily returns net of entry/exit costs."""
    ret = sig["close"].astype(float).pct_change().fillna(0.0)
    pos_prev = sig["in_position"].shift(1).fillna(0).astype(float)
    strat = pos_prev * ret
    is_buy = (sig["action"] == "buy").astype(float)
    is_exit = sig["action"].isin(["stoploss", "exit"]).astype(float)
    strat = strat - is_buy * cfg.cost_buy_rate - is_exit * cfg.cost_sell_rate
    return strat.reset_index(drop=True)


def trades(sig: pd.DataFrame, cfg: StrategyConfig) -> list[dict[str, Any]]:
    """Closed-trade list ({ret, hold, entry_structure}) from a signaled window."""
    out: list[dict[str, Any]] = []
    entry_i = None
    s = sig.reset_index(drop=True)
    for i, row in s.iterrows():
        if entry_i is None and row["action"] == "buy":
            entry_i = i
        elif entry_i is not None and row["action"] in ("stoploss", "exit"):
            e, x = s.iloc[entry_i], s.iloc[i]
            entry_px = float(e["close"]) * (1 + cfg.cost_buy_rate)
            exit_px = float(x["close"]) * (1 - cfg.cost_sell_rate)
            out.append({"ret": exit_px / entry_px - 1.0, "hold": i - entry_i,
                        "entry_structure": int(e["structure_score"])})
            entry_i = None
    return out


def sharpe(strat: pd.Series) -> float:
    """Annualized Sharpe — delegates to the canonical ``validation.metrics.sharpe``.

    Kept as a named function because ``research.is_harness`` re-exports it as
    ``_sharpe`` (back-compat). ADR-027 Stage 2: the four-layer sim no longer
    carries its own Sharpe formula — every strategy is now judged by one estimator.
    """
    return _sharpe(strat)


def metrics(
    strat: pd.Series, strat_slip: pd.Series, trade_list: list[dict[str, Any]], n_buys: int
) -> dict[str, Any]:
    """Gate-ready metrics dict from portfolio returns + closed trades.

    ``cagr`` / ``sharpe`` come from ``validation.metrics`` (single source). ``maxdd``
    keeps the four-layer *signed* convention (<= 0; not a gated criterion) for
    tear-sheet continuity — panel strategies report it as a positive fraction.
    """
    n = len(strat)
    eq = (1 + strat).cumprod()
    dd = float((eq / eq.cummax() - 1).min()) if n else 0.0
    rets = [t["ret"] for t in trade_list]
    wins = [r for r in rets if r > 0]
    return {
        "trades": n_buys,
        "closed": len(trade_list),
        "cagr": _cagr(strat),
        "sharpe": sharpe(strat),
        "slippage_sharpe": sharpe(strat_slip),
        "maxdd": dd,
        "win": (len(wins) / len(rets)) if rets else 0.0,
        "avg_hold": float(np.mean([t["hold"] for t in trade_list])) if trade_list else 0.0,
        "struct1_pct": (sum(t["entry_structure"] == 1 for t in trade_list) / len(trade_list)) if trade_list else 0.0,
        "churn_pct": (sum(t["hold"] < 3 for t in trade_list) / len(trade_list)) if trade_list else 0.0,
    }
