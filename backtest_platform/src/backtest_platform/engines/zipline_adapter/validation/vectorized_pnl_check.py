"""Self-written vectorized PnL cross-check (no framework dependency).

ADR-013 §J recovery: vectorbt cap pandas<2, can't co-install with our
zipline-reloaded stack. Rather than 引入兩個 venv (overengineering) or
giving up cross-check entirely, we hand-write a minimal vectorized PnL
to validate zipline's portfolio arithmetic.

What this validates:
- Given M1's action sequence (already validated by regression_vs_m1),
  did zipline apply fee/tax/slippage and cash/position accounting
  correctly?

What it does NOT validate:
- Order routing nuances (partial fills, market-on-close vs limit)
- Multi-strategy attribution
- Real-time event ordering

For Sprint 2 M2 acceptance this is sufficient — zipline-reloaded is
mature OSS; the most likely source of bugs is our Algorithm wrapper
(covered by regression_vs_m1), not zipline's portfolio internals.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig


@dataclass(frozen=True)
class VectorizedRun:
    """Output of `simulate_vectorized_long_only`."""

    equity_curve: pd.Series
    n_trades: int
    final_equity: float
    total_return: float
    total_fees: float
    total_tax: float
    total_slippage_cost: float


def simulate_vectorized_long_only(
    prices: pd.Series,  # close prices indexed by trade_date
    actions: pd.Series,  # action labels aligned to prices
    *,
    config: StrategyConfig | None = None,
    initial_cash: float = 1_000_000.0,
    target_weight: float = 0.05,
) -> VectorizedRun:
    """Minimal long-only vectorized backtest.

    Action semantics (matches algorithms.four_layer_resonance):
        buy / add → target_weight (single position, not pyramiding)
        reduce → halve current position
        exit / stoploss / takeprofit → flatten
        hold / none / NaN → no-op

    Cost model uses StrategyConfig:
        buy_cost = fee_rate × fee_discount  (broker only)
        sell_cost = buy_cost + tax_stock_rate
        slip = slip_rate × notional (one-sided per trade leg)

    All trades execute at the SAME-bar close (M1 convention). This is
    slightly more aggressive than zipline's next-bar open default, so
    expect O(0.5%) divergence in absolute return that doesn't indicate
    a bug.
    """
    config = config or StrategyConfig()
    broker_rate = config.fee_rate * config.fee_discount
    tax_rate = config.tax_stock_rate
    slip_rate = config.slip_rate

    assert prices.index.equals(actions.index), "prices and actions must be aligned"

    cash = initial_cash
    shares = 0
    equity = [initial_cash]
    n_trades = 0
    total_fees = 0.0
    total_tax = 0.0
    total_slippage = 0.0

    for ts in prices.index[1:]:  # skip warmup row
        price = prices.loc[ts]
        action = actions.loc[ts]

        if pd.isna(price) or price <= 0:
            equity.append(cash + shares * (price if price > 0 else 0))
            continue

        # Effective buy/sell prices include slippage on respective side
        buy_price = price * (1 + slip_rate)
        sell_price = price * (1 - slip_rate)

        if action == "buy" and shares == 0:
            notional = (cash + shares * price) * target_weight
            qty = int(notional / buy_price)
            if qty > 0:
                gross = qty * buy_price
                fee = gross * broker_rate
                slip_cost = qty * (buy_price - price)
                cash -= gross + fee
                shares += qty
                n_trades += 1
                total_fees += fee
                total_slippage += slip_cost
        elif action == "add" and shares > 0:
            # Add 2pp to current weight
            current_value = shares * price
            current_equity = cash + current_value
            target_add_value = current_equity * 0.02
            qty = int(target_add_value / buy_price)
            if qty > 0 and cash >= qty * buy_price:
                gross = qty * buy_price
                fee = gross * broker_rate
                slip_cost = qty * (buy_price - price)
                cash -= gross + fee
                shares += qty
                n_trades += 1
                total_fees += fee
                total_slippage += slip_cost
        elif action == "reduce" and shares > 0:
            qty = shares // 2  # halve
            if qty > 0:
                gross = qty * sell_price
                fee = gross * broker_rate
                tax = gross * tax_rate
                slip_cost = qty * (price - sell_price)
                cash += gross - fee - tax
                shares -= qty
                n_trades += 1
                total_fees += fee
                total_tax += tax
                total_slippage += slip_cost
        elif action in ("exit", "stoploss", "takeprofit") and shares > 0:
            gross = shares * sell_price
            fee = gross * broker_rate
            tax = gross * tax_rate
            slip_cost = shares * (price - sell_price)
            cash += gross - fee - tax
            shares = 0
            n_trades += 1
            total_fees += fee
            total_tax += tax
            total_slippage += slip_cost

        equity.append(cash + shares * price)

    equity_series = pd.Series(equity, index=prices.index, name="equity")
    final_equity = float(equity_series.iloc[-1])

    return VectorizedRun(
        equity_curve=equity_series,
        n_trades=n_trades,
        final_equity=final_equity,
        total_return=(final_equity / initial_cash) - 1.0,
        total_fees=total_fees,
        total_tax=total_tax,
        total_slippage_cost=total_slippage,
    )
