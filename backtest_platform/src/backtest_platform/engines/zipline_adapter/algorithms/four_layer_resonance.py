"""Four-Layer Resonance zipline Algorithm (ADR-013, plan v3.0 §4.2).

Wraps M1 pure functions (`compute_scores` + `evaluate_bar`) as a zipline
TradingAlgorithm. The algorithm is mode-agnostic: same code runs under
`zipline run -b finmind` (backtest) and future paper/live modes (ADR-008
three-mode shared strategy code).

Evaluation contract (Sprint 2 fix 2026-06-01):
    Per-bar evaluation uses M1's `evaluate_bar(EvaluateBar, config)` with
    position state read from `context.portfolio.positions[asset]` — the
    canonical event-driven path. Earlier Sprint 1 wrapper used
    `compute_signals(window).iloc[-1]` which restarts the M1 walk-loop
    state machine from window-start every bar (position=0), causing
    actions to diverge from real portfolio state. Regression test
    (validation/regression_vs_m1) catches such divergences.

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

import pandas as pd
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
from backtest_platform.strategies.four_layer_resonance.signals import (
    EvaluateBar,
    SignalName,
    compute_signals,
    evaluate_bar,
)

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
    """Daily evaluation: per-stock event-driven `evaluate_bar` + emit orders.

    Uses M1's per-bar `evaluate_bar(EvaluateBar, config)` with position
    state read from zipline's portfolio (the engine's source of truth).
    This is the canonical live-mode path; do NOT use compute_signals'
    terminal walk-loop output here — that re-walks state from window-start
    and ignores actual portfolio state (see Sprint 2 regression bug fix).
    """
    as_of = context.get_datetime()
    n_eval = 0
    actions_summary: dict[str, int] = {}

    for sym_str, asset in zip(context.symbol_strs, context.assets):
        merged = context.merged_frames.get(sym_str)
        if merged is None:
            continue

        window = get_history_window(merged, as_of, _HISTORY_BARS)
        if len(window) < context.config.box_period + 5:
            # Not enough warmup yet
            continue

        in_position, entry_cost = _portfolio_state(context, asset)
        try:
            action = evaluate_window_with_state(
                window, context.config, in_position, entry_cost
            )
        except Exception as exc:  # noqa: BLE001 — single-symbol error must not abort whole backtest
            logger.error("evaluate failed for {} on {}: {}", sym_str, as_of.date(), exc)
            continue

        actions_summary[action] = actions_summary.get(action, 0) + 1
        n_eval += 1

        _execute_action(context, asset, action)

    # Daily recorder for performance tearsheet
    record(n_evaluated=n_eval, **{f"action_{k}": v for k, v in actions_summary.items()})


def _portfolio_state(context, asset) -> tuple[int, float]:
    """Read (in_position, entry_cost_price) from zipline portfolio.

    zipline's Position.cost_basis includes commissions paid on entry, so
    it already matches M1's convention of cost-adjusted entry price.
    """
    pos = context.portfolio.positions.get(asset)
    if pos is None or pos.amount == 0:
        return 0, 0.0
    return 1, float(pos.cost_basis)


def _build_evaluate_bar(
    last: pd.Series,
    prev: pd.Series,
    in_position: int,
    entry_cost_price: float,
) -> EvaluateBar:
    """Construct EvaluateBar from the last two rows of prepared columns.

    `prepared` is the output of `compute_signals` — we use it only as a
    column-preparation pass (it computes risk_swing_low/avg_volume_5/
    candle_body_size/upper_shadow/volatility_rate plus compute_states
    columns). Its terminal walk-loop action is discarded; the caller
    supplies the real position state.
    """
    def _f(val, default: float = 0.0) -> float:
        return float(val) if pd.notna(val) else default

    return EvaluateBar(
        in_position=in_position,
        entry_cost_price=entry_cost_price,
        close=_f(last["close"]),
        high=_f(last["high"]),
        open=_f(last["open"]),
        box_lower=_f(last.get("box_lower")),
        risk_swing_low=_f(last.get("risk_swing_low")),
        volume=_f(last["volume"]),
        avg_volume_5=_f(last.get("avg_volume_5")),
        body_high=_f(max(last["close"], last["open"])),
        body_low=_f(min(last["close"], last["open"])),
        upper_shadow=_f(last.get("upper_shadow")),
        candle_body_size=_f(last.get("candle_body_size")),
        structure_score=int(last.get("structure_score", 0) or 0),
        direction_score=int(last.get("direction_score", 0) or 0),
        chip_score=int(last.get("chip_score", 0) or 0),
        momentum_score=int(last.get("momentum_score", 0) or 0),
        total_score=int(last.get("total_score", 0) or 0),
        prev_total_score=_f(prev.get("total_score")),
        prev_momentum_score=_f(prev.get("momentum_score")),
        prev_high=_f(prev.get("high")),
        state_flameout=int(last.get("state_flameout", 0) or 0),
        state_strong_buy=int(last.get("state_strong_buy", 0) or 0),
        state_hold=int(last.get("state_hold", 0) or 0),
        state_warning=int(last.get("state_warning", 0) or 0),
        volatility_rate=_f(last.get("volatility_rate")),
    )


def evaluate_window_with_state(
    window: pd.DataFrame,
    config: StrategyConfig,
    in_position: int,
    entry_cost_price: float,
) -> SignalName:
    """Score + prepare a history window, then evaluate the last bar with
    caller-owned position state.

    This is the canonical event-driven evaluation. Both the live algorithm
    (reading from `context.portfolio.positions`) and the regression
    harness (maintaining its own sequential state) call this helper, so
    they share identical evaluation logic.
    """
    if len(window) < 2:
        return "none"

    history = window.reset_index().rename(columns={"trade_date": "trade_date"})
    if not pd.api.types.is_datetime64_any_dtype(history["trade_date"]):
        history["trade_date"] = pd.to_datetime(history["trade_date"])
    history["trade_date"] = history["trade_date"].dt.date

    scored = compute_scores(history, config)
    prepared = compute_signals(scored, config)  # column-prep pass; .action ignored

    if len(prepared) < 2:
        return "none"

    last = prepared.iloc[-1]
    prev = prepared.iloc[-2]
    eb = _build_evaluate_bar(last, prev, in_position, entry_cost_price)
    return evaluate_bar(eb, config)


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
