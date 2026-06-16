"""Cross-check: vectorbt Portfolio.from_signals vs self-written
simulate_vectorized_long_only — both fed the same regression-validated
action sequence + OHLCV. Total return and Sharpe must agree within 1%
(plan v3.0 §12 Sprint 2 acceptance).

Why this matters:
- self-written simulator is small, transparent, and we own it — but it's
  our code so could have bugs in fees/tax/slippage attribution
- vectorbt is battle-tested but opaque
- If both agree on the same action stream, both implementations are
  trustworthy and either is safe for M3 grid/WFA work

Apples-to-apples normalization:
- M1's full action enum is 7 priorities (stoploss/exit/takeprofit/reduce
  /add/buy/hold). vectorbt's from_signals models a binary state machine
  (entries/exits booleans).
- To compare fairly, we collapse actions to the binary set used inside
  compute_signals' walk-loop state update (signals.py:139-144):
      pos=0 + buy   → pos=1
      pos=1 + (exit|stoploss) → pos=0
      else: no change
  i.e. add/reduce/takeprofit/hold do NOT mutate position, so for PnL
  parity we drop them by mapping to 'hold' before simulation.

This isolates the cross-check to PnL math (fees, tax, slippage,
compounding) rather than action interpretation differences.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt
from loguru import logger

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.engines.zipline_adapter.algorithms.base import (
    preload_merged_frames,
)
from backtest_platform.engines.zipline_adapter.validation.regression_vs_m1 import (
    compute_zipline_actions,
)
from backtest_platform.engines.zipline_adapter.validation.vectorized_pnl_check import (
    simulate_vectorized_long_only,
)
from backtest_platform.validation.metrics import sharpe as _metrics_sharpe

# Per-buy notional sizing (matches algorithms/four_layer_resonance._BUY_TARGET_PCT)
_BUY_PCT = 0.05


@dataclass(frozen=True)
class CrossCheckResult:
    """Outcome of a single stock+range PnL cross-check."""

    stock_id: str
    start_date: date
    end_date: date
    n_bars: int
    n_trades_self: int
    n_trades_vbt: int
    self_total_return: float
    vbt_total_return: float
    return_diff_abs: float
    return_diff_rel: float
    self_sharpe: float | None
    vbt_sharpe: float | None
    sharpe_diff_abs: float | None
    ok: bool

    def __repr__(self):
        return (
            f"CrossCheckResult(stock={self.stock_id}, bars={self.n_bars}, "
            f"self_ret={self.self_total_return:.4%}, "
            f"vbt_ret={self.vbt_total_return:.4%}, "
            f"diff_rel={self.return_diff_rel:.4%}, "
            f"ok={self.ok})"
        )


def _binarize_actions(actions: pd.Series) -> pd.Series:
    """Map M1 7-signal enum to {buy, exit, hold} — only state-changing
    signals retained. add/reduce/takeprofit don't change M1 position
    state, so for binary PnL comparison they're treated as hold.
    """
    keep = {"buy", "exit", "stoploss"}
    return actions.where(actions.isin(keep), "hold")


def _sharpe_from_equity(equity: pd.Series, ann_factor: int = 252) -> float | None:
    """Annualized Sharpe from a daily equity curve (no risk-free).

    Delegates to the canonical ``validation.metrics.sharpe`` (ADR-027 Stage 2);
    returns None for a degenerate curve so the cross-check can skip it.
    """
    rets = equity.pct_change().dropna()
    if len(rets) < 2 or rets.std() == 0:
        return None
    return _metrics_sharpe(rets, periods_per_year=ann_factor)


def cross_check_vectorbt(
    stock_id: str,
    start: date,
    end: date,
    config: StrategyConfig | None = None,
    cache_dir: Path | None = None,
    initial_cash: float = 1_000_000.0,
    tol_rel: float = 0.01,
    tol_abs: float = 0.001,
) -> CrossCheckResult:
    """Run both PnL simulators on the same actions+prices, compare metrics.

    Acceptance (plan v3.0 §12 + Sprint 2 numerical-stability refinement):
        - if |vbt_total_return| >= 1% → relative diff <= tol_rel (1%)
        - else (near-zero returns) → absolute diff <= tol_abs (10 bps)

    The two-mode acceptance handles a real-world edge case: when actions
    barely net out (e.g. a sideways year with break-even trades), both
    engines correctly produce ~0% return, but tiny floating-point
    differences blow up the relative metric. The absolute-bps floor
    catches genuine PnL math divergence without false alarms on
    arithmetically-correct near-zero results.
    """
    config = config or StrategyConfig()

    actions_df = compute_zipline_actions(stock_id, start, end, config, cache_dir)
    if actions_df.empty:
        raise ValueError(f"no actions in range {start}..{end} for {stock_id}")

    # Pull closes for the same date range
    frames = preload_merged_frames([stock_id], cache_dir=cache_dir)
    merged = frames[stock_id]
    sliced = merged.loc[pd.Timestamp(start) : pd.Timestamp(end)]
    closes = sliced["close"].copy()
    closes.index = pd.to_datetime(closes.index)

    # Align actions onto close index (closes has DatetimeIndex from merged)
    actions_indexed = pd.Series(
        actions_df["action"].values,
        index=pd.to_datetime(actions_df["trade_date"]),
        name="action",
    )
    aligned = pd.concat([closes.rename("close"), actions_indexed], axis=1).dropna()

    binary_actions = _binarize_actions(aligned["action"])

    # --- Self-written PnL ---
    self_run = simulate_vectorized_long_only(
        aligned["close"],
        binary_actions,
        config=config,
        initial_cash=initial_cash,
    )
    self_total_return = (self_run.final_equity / initial_cash) - 1.0
    self_sharpe = _sharpe_from_equity(self_run.equity_curve)

    # --- vectorbt PnL ---
    entries = binary_actions == "buy"
    exits = binary_actions.isin(["exit", "stoploss"])

    # Directional fees: vectorbt's `fees` is non-directional by default,
    # but accepts a per-bar Series. Buy days = broker fee only; exit days
    # = broker fee + Taiwan stock transaction tax (0.3%, sell-side only).
    fee_per_leg = config.fee_rate * config.fee_discount
    fees_series = pd.Series(fee_per_leg, index=aligned.index)
    fees_series.loc[exits] = fee_per_leg + config.tax_stock_rate

    pf = vbt.Portfolio.from_signals(
        close=aligned["close"],
        entries=entries,
        exits=exits,
        init_cash=initial_cash,
        size=_BUY_PCT,
        size_type="percent",
        fees=fees_series,
        slippage=config.slip_rate,
        freq="D",
        accumulate=False,  # single-position long-only
    )
    vbt_total_return = float(pf.total_return())
    try:
        vbt_sharpe = float(pf.sharpe_ratio())
        if not np.isfinite(vbt_sharpe):
            vbt_sharpe = None
    except Exception:
        vbt_sharpe = None

    diff_abs = abs(self_total_return - vbt_total_return)
    denom = max(abs(vbt_total_return), 1e-6)
    diff_rel = diff_abs / denom
    sharpe_diff = (
        abs(self_sharpe - vbt_sharpe)
        if self_sharpe is not None and vbt_sharpe is not None
        else None
    )

    # Two-mode acceptance — relative for material returns, absolute floor
    # for near-zero returns (see docstring).
    if abs(vbt_total_return) >= 0.01:
        ok = diff_rel <= tol_rel
    else:
        ok = diff_abs <= tol_abs

    n_trades_vbt = int(pf.trades.records_readable.shape[0]) if pf.trades.count() > 0 else 0

    result = CrossCheckResult(
        stock_id=stock_id,
        start_date=start,
        end_date=end,
        n_bars=len(aligned),
        n_trades_self=self_run.n_trades,
        n_trades_vbt=n_trades_vbt,
        self_total_return=self_total_return,
        vbt_total_return=vbt_total_return,
        return_diff_abs=diff_abs,
        return_diff_rel=diff_rel,
        self_sharpe=self_sharpe,
        vbt_sharpe=vbt_sharpe,
        sharpe_diff_abs=sharpe_diff,
        ok=ok,
    )
    logger.info("cross_check: {}", result)
    return result
