"""Four-Layer Resonance zipline Algorithm (ADR-013, plan v3.0 §4.2).

Wraps M1 pure functions (`compute_scores` + `compute_signals`) as a
zipline TradingAlgorithm. The algorithm is mode-agnostic: same code runs
under `zipline run -b finmind` (backtest) and future paper/live modes
(ADR-008 three-mode shared strategy code).

CLI usage:
    uv run zipline run -f \
      src/backtest_platform/engines/zipline_adapter/algorithms/four_layer_resonance.py \
      -b finmind --start 2024-01-15 --end 2024-03-15 \
      --capital-base 1000000

Bar count rationale:
    - StrategyConfig.box_period default = 60 (Bollinger-like window)
    - Plus indicator lookbacks (KD/MACD ~30 days)
    - Buffer for warmup → bar_count = 120 (覆蓋 box_period 兩倍以上)
"""
from __future__ import annotations

import os

from loguru import logger
from zipline.api import (
    order_target_percent,
    record,
    schedule_function,
    symbol,
)
from zipline.utils.events import date_rules, time_rules

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.engines.zipline_adapter.algorithms.base import (
    get_history_window,
    preload_merged_frames,
)
from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
    DEFAULT_UNIVERSE,
)
from backtest_platform.engines.zipline_adapter.controls.taiwan_stock_rules import (
    apply_taiwan_stock_rules,
)
from backtest_platform.strategies.four_layer_resonance.scoring import compute_scores
from backtest_platform.strategies.four_layer_resonance.signals import compute_signals

# How many bars to feed compute_scores each evaluation — enough for
# box_period warmup + indicator lookbacks (KD/MACD).
_HISTORY_BARS = 120

# Per-position target weight when entering. 5% × 10 stocks = 50% max exposure
# at full universe entry, leaves room for adds.
_BUY_TARGET_PCT = 0.05
_ADD_INCREMENT_PCT = 0.02
_REDUCE_DECREMENT_PCT = 0.02


def initialize(context):
    """zipline hook — called once at backtest start.

    Preloads merged frames from parquet cache for all symbols and
    registers the daily evaluation callback for market_close - 5min.
    """
    context.config = StrategyConfig()

    universe_env = os.environ.get("UNIVERSE_FINMIND")
    universe_syms = (
        [s.strip() for s in universe_env.split(",") if s.strip()]
        if universe_env
        else list(DEFAULT_UNIVERSE)
    )

    context.symbol_strs = universe_syms
    context.assets = [symbol(s) for s in universe_syms]

    # Preload M1 merged frames (OHLCV + institutional + chips) from
    # parquet cache. Per-bar lookups will slice these in-memory.
    context.merged_frames = preload_merged_frames(universe_syms)
    logger.info(
        "FourLayerResonance initialized: {} symbols, {} bars history window",
        len(universe_syms),
        _HISTORY_BARS,
    )

    # Apply Taiwan stock-specific commission/slippage/long-only/etc.
    apply_taiwan_stock_rules(context.config)

    # Schedule per-bar evaluation 5 min before close so we have the day's
    # OHLCV but enough headroom to submit market-on-close orders.
    schedule_function(
        evaluate_and_trade,
        date_rules.every_day(),
        time_rules.market_close(minutes=5),
    )


def evaluate_and_trade(context, data):
    """Daily evaluation: compute scores+signals per stock, emit orders.

    Reuses M1 vectorized `compute_signals` (calls `compute_scores`
    internally via REQUIRED_COLUMNS). The last row's `action` column is
    the realized signal for today, with priority resolution already done
    inside compute_signals.
    """
    as_of = context.get_datetime()
    n_eval = 0
    actions_summary: dict[str, int] = {}

    for sym_str, asset in zip(context.symbol_strs, context.assets):
        merged = context.merged_frames.get(sym_str)
        if merged is None:
            continue

        history = get_history_window(merged, as_of, _HISTORY_BARS)
        if len(history) < context.config.box_period + 5:
            # Not enough warmup yet
            continue

        # M1 functions expect trade_date column, not index
        history = history.reset_index().rename(columns={"trade_date": "trade_date"})
        history["trade_date"] = history["trade_date"].dt.date

        try:
            scored = compute_scores(history, context.config)
            signaled = compute_signals(scored, context.config)
        except Exception as exc:  # noqa: BLE001 — single-symbol error must not abort whole backtest
            logger.error("scoring failed for {} on {}: {}", sym_str, as_of.date(), exc)
            continue

        action = signaled["action"].iloc[-1]
        actions_summary[action] = actions_summary.get(action, 0) + 1
        n_eval += 1

        _execute_action(context, asset, action)

    # Daily recorder for performance tearsheet
    record(n_evaluated=n_eval, **{f"action_{k}": v for k, v in actions_summary.items()})


def _execute_action(context, asset, action: str):
    """Translate M1 action enum to zipline orders.

    Action semantics (v2.md §2.4.2 priority):
        stoploss / exit / takeprofit → close position (target 0%)
        reduce → trim 2 pp off current weight
        add → add 2 pp to current weight
        buy → enter at _BUY_TARGET_PCT
        hold / none → no-op
    """
    if action in ("stoploss", "exit", "takeprofit"):
        order_target_percent(asset, 0)
    elif action == "buy":
        order_target_percent(asset, _BUY_TARGET_PCT)
    elif action == "add":
        current = _current_weight(context, asset)
        order_target_percent(asset, current + _ADD_INCREMENT_PCT)
    elif action == "reduce":
        current = _current_weight(context, asset)
        order_target_percent(asset, max(0.0, current - _REDUCE_DECREMENT_PCT))
    # hold/none → no order


def _current_weight(context, asset) -> float:
    """Read current portfolio weight for an asset (0.0 if no position).

    zipline's Portfolio object exposes positions dict; weight =
    position.market_value / portfolio.portfolio_value.
    """
    pos = context.portfolio.positions.get(asset)
    if pos is None or pos.amount == 0:
        return 0.0
    total_value = context.portfolio.portfolio_value
    if total_value <= 0:
        return 0.0
    return (pos.last_sale_price * pos.amount) / total_value


# zipline `-f <file>` discovery: looks for module-level `initialize` and
# `handle_data` or scheduled functions. We use schedule_function in
# initialize(), so handle_data is a no-op stub.
def handle_data(context, data):  # noqa: ARG001 — required signature
    """No-op; actual trading driven by scheduled `evaluate_and_trade`."""
    pass
