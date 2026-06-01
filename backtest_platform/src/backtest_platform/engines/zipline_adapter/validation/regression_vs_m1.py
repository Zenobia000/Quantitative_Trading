"""Regression: zipline_adapter actions sequence vs M1 pipeline.py.

M1 `pipeline.py:run_pipeline()` is the ground truth — it calls the same
`compute_scores` + `compute_signals` pure functions our Algorithm uses.
Both must produce **identical** action sequence per trading day for any
stock+date range, because:

1. Same input frame (M1 merged ETLBundle)
2. Same pure functions (no engine-specific divergence)
3. Same StrategyConfig (frozen Pydantic)

This file is the regression harness — any divergence indicates either
(a) Algorithm wrapper bug (e.g. wrong bar_count, wrong history window)
or (b) data pipeline bug (e.g. preload vs M1 read differs).

Usage:
    >>> from backtest_platform.engines.zipline_adapter.validation.regression_vs_m1 import (
    ...     compare_actions
    ... )
    >>> result = compare_actions("2330", date(2024, 1, 1), date(2024, 12, 31))
    >>> assert result.match_pct >= 0.999
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
from loguru import logger

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.engines.zipline_adapter.algorithms.base import (
    preload_merged_frames,
)
from backtest_platform.engines.zipline_adapter.algorithms.four_layer_resonance import (
    _build_evaluate_bar,
)
from backtest_platform.strategies.four_layer_resonance.scoring import compute_scores
from backtest_platform.strategies.four_layer_resonance.signals import (
    compute_signals,
    evaluate_bar,
)

# Calendar buffer before `start` so both M1 and zipline emulation have full
# indicator warmup. 180 calendar days ≈ 120 trading bars (matches
# Algorithm._HISTORY_BARS).
_WARMUP_CALENDAR_DAYS = 180


@dataclass(frozen=True)
class ComparisonResult:
    """Outcome of a single stock+range regression run."""

    stock_id: str
    start_date: date
    end_date: date
    total_bars: int
    matches: int
    mismatches: int
    match_pct: float
    mismatch_details: list[dict]

    def __repr__(self):
        return (
            f"ComparisonResult(stock={self.stock_id}, "
            f"bars={self.total_bars}, match={self.match_pct:.4%}, "
            f"mismatches={self.mismatches})"
        )


def compute_m1_actions(
    stock_id: str,
    start: date,
    end: date,
    config: StrategyConfig | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Run M1 pipeline pure functions on cached merged frame.

    Reads with a 180-calendar-day warmup buffer BEFORE `start` so the
    box_period (default 60 trading bars) + indicator lookbacks have valid
    data on the first bar of `[start, end]`. Without warmup, M1
    compute_scores returns NaN total_score on early range bars, causing
    actions to default to 'none' and diverging from a real backtest
    engine (which always has prior data).

    Output rows are filtered to `trade_date >= start`.
    """
    config = config or StrategyConfig()
    frames = preload_merged_frames([stock_id], cache_dir=cache_dir)
    merged = frames[stock_id]

    warmup_start_ts = pd.Timestamp(start) - pd.Timedelta(days=_WARMUP_CALENDAR_DAYS)
    end_ts = pd.Timestamp(end)
    sliced = merged.loc[warmup_start_ts:end_ts].reset_index()
    sliced["trade_date"] = sliced["trade_date"].dt.date

    if sliced.empty:
        return pd.DataFrame(columns=["trade_date", "action"])

    scored = compute_scores(sliced, config)
    signaled = compute_signals(scored, config)

    out = signaled.loc[
        signaled["trade_date"] >= start, ["trade_date", "action"]
    ].copy()
    return out.reset_index(drop=True)


def compute_zipline_actions(
    stock_id: str,
    start: date,
    end: date,
    config: StrategyConfig | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Emulate live zipline Algorithm output: sequential evaluate_bar walk.

    Mirrors what `algorithms/four_layer_resonance.evaluate_and_trade` does
    under a real zipline run — at each bar, the algorithm reads its
    position state from zipline's portfolio and calls `evaluate_bar` with
    that state. Here we maintain (in_position, entry_cost_price)
    ourselves with the same update rules zipline's blotter+algorithm
    combination produces.

    For correctness vs M1: both this and `compute_m1_actions` walk the
    same warmup-padded data, both share `_evaluate_priority` (the only
    decision function), and both apply identical state transitions.
    Therefore their action sequences MUST agree on `[start, end]` —
    divergence indicates a real wrapper bug.
    """
    config = config or StrategyConfig()
    frames = preload_merged_frames([stock_id], cache_dir=cache_dir)
    merged = frames[stock_id]

    warmup_start_ts = pd.Timestamp(start) - pd.Timedelta(days=_WARMUP_CALENDAR_DAYS)
    end_ts = pd.Timestamp(end)
    sliced = merged.loc[warmup_start_ts:end_ts].reset_index()
    sliced["trade_date"] = sliced["trade_date"].dt.date

    if sliced.empty:
        return pd.DataFrame(columns=["trade_date", "action"])

    # Single pass: produce all derived columns (state, candle, vol_rate)
    scored = compute_scores(sliced, config)
    prepared = compute_signals(scored, config)  # column-prep only; .action ignored

    in_position = 0
    entry_cost = 0.0
    rows = []

    for i in range(1, len(prepared)):
        last = prepared.iloc[i]
        prev = prepared.iloc[i - 1]
        eb = _build_evaluate_bar(last, prev, in_position, entry_cost)
        action = evaluate_bar(eb, config)

        if last["trade_date"] >= start:
            rows.append({"trade_date": last["trade_date"], "action": action})

        # State machine update — must match compute_signals walk-loop exactly
        # (see strategies/four_layer_resonance/signals.py:139)
        if in_position == 0 and action == "buy":
            in_position = 1
            entry_cost = float(last["close"]) * (1 + config.cost_buy_rate)
        elif in_position == 1 and action in ("stoploss", "exit"):
            in_position = 0
            entry_cost = 0.0

    return pd.DataFrame(rows)


def compare_actions(
    stock_id: str,
    start: date,
    end: date,
    config: StrategyConfig | None = None,
    cache_dir: Path | None = None,
) -> ComparisonResult:
    """Run both M1 and zipline-style action computations, return diff summary.

    Acceptance threshold for M2 (per plan v3.0): match_pct >= 0.999
    (i.e. < 0.1% divergence on a typical 1-year run).
    """
    config = config or StrategyConfig()
    m1 = compute_m1_actions(stock_id, start, end, config, cache_dir)
    z = compute_zipline_actions(stock_id, start, end, config, cache_dir)

    merged = m1.merge(z, on="trade_date", suffixes=("_m1", "_zipline"), how="outer")
    merged["match"] = merged["action_m1"] == merged["action_zipline"]

    total = len(merged)
    matches = int(merged["match"].sum())
    mismatches = total - matches
    match_pct = matches / total if total else 0.0

    mismatch_details: list[dict] = []
    if mismatches:
        for _, row in merged.loc[~merged["match"]].iterrows():
            mismatch_details.append(
                {
                    "date": str(row["trade_date"]),
                    "m1": row.get("action_m1"),
                    "zipline": row.get("action_zipline"),
                }
            )

    result = ComparisonResult(
        stock_id=stock_id,
        start_date=start,
        end_date=end,
        total_bars=total,
        matches=matches,
        mismatches=mismatches,
        match_pct=match_pct,
        mismatch_details=mismatch_details[:20],  # cap to keep result readable
    )
    logger.info("regression: {}", result)
    return result
