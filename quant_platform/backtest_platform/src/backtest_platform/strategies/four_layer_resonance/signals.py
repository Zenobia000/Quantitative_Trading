"""State machine and execution signals — v2.md 2.4.

Two layers:

* **State layer** (4 states) — purely a function of the row's scores. Vectorized.
* **Execution layer** (7 signals) — depends on position state, prior bar values,
  and cost model. Walks bars sequentially because each bar's position depends
  on the previous bar's signal outcome.

Engines integrate two ways:

* ``compute_signals(df_scored, config)`` — for vectorbt-style sweeps where a
  single long-only position is simulated greedily. Returns a DataFrame with
  state columns, signal columns, and an ``action`` column carrying the
  highest-priority signal name per bar.
* ``EvaluateBar`` (dataclass) — for event-driven engines (rqalpha) that own
  the position state. Pass per-bar metrics and current position, get back the
  highest-priority signal.

Priority (highest first): ``stoploss > exit > takeprofit > reduce > add > buy > hold``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from .indicators import rolling_swing_low

SIGNAL_PRIORITY: tuple[str, ...] = (
    "stoploss",
    "exit",
    "takeprofit",
    "reduce",
    "add",
    "buy",
    "hold",
)


def compute_states(df_scored: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """Append state_flameout / state_strong_buy / state_hold / state_warning columns.

    Vectorized — depends only on score columns and box_lower.
    """
    out = df_scored.copy()

    flameout = (out["momentum_score"] == -1) | (out["close"] < out["box_lower"])
    strong_buy = (
        (out["structure_score"] >= 1)
        & (out["direction_score"] >= 1)
        & (out["chip_score"] >= 1)
        & (out["momentum_score"] >= 1)
        & (out["total_score"] >= config.strong_buy_threshold)
    )
    hold = (
        (out["structure_score"] >= 1)
        & (out["momentum_score"] >= 1)
        & (out["total_score"] >= 3)
        & (out["total_score"] < config.strong_buy_threshold)
    )
    warning = (out["total_score"] <= config.warning_threshold) & (~flameout)

    out["state_flameout"] = flameout.astype(int)
    out["state_strong_buy"] = strong_buy.astype(int)
    out["state_hold"] = hold.astype(int)
    out["state_warning"] = warning.astype(int)
    return out


def compute_signals(df_scored: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """Walk bars, simulate a single long-only position, emit highest-priority signal.

    Returns ``df`` plus all state and signal columns. Use this for vectorbt
    sweeps and for offline reproduction. Real-time engines should use
    ``evaluate_bar`` instead so the engine remains the source of truth on
    position state.
    """
    df = compute_states(df_scored, config)
    df["risk_swing_low"] = rolling_swing_low(df["low"], 20)
    df["avg_volume_5"] = df["volume"].rolling(5, min_periods=5).mean()

    candle_top = np.where(df["close"] >= df["open"], df["close"], df["open"])
    candle_bottom = np.where(df["close"] >= df["open"], df["open"], df["close"])
    df["candle_body_size"] = candle_top - candle_bottom
    df["upper_shadow"] = df["high"] - candle_top

    df["volatility_rate"] = (df["high"] - df["low"]).rolling(14, min_periods=14).mean() / df["close"]
    df["edge_ok"] = (df["volatility_rate"] >= config.cost_round_rate + config.min_edge_rate).astype(int)

    n = len(df)
    in_position = np.zeros(n, dtype=np.int8)
    entry_cost = np.zeros(n, dtype=np.float64)
    actions: list[str] = []

    sig_cols = {f"signal_{name}": np.zeros(n, dtype=np.int8) for name in SIGNAL_PRIORITY}

    pos = 0
    cost_price = 0.0
    prev_total = np.nan
    prev_momentum = np.nan
    consec_structure = 0          # consecutive bars with structure_score >= 1
    bars_since_exit = 10**9       # cooldown counter; large = no prior exit

    rows = df.reset_index(drop=True)

    for i in range(n):
        row = rows.iloc[i]
        prev_high = rows["high"].iloc[i - 1] if i > 0 else np.nan
        prev_total_score = rows["total_score"].iloc[i - 1] if i > 0 else np.nan
        prev_total_warning = rows["total_score"].iloc[i - 1] if i > 0 else np.nan
        prev_box_upper = rows["box_upper"].iloc[i - 1] if i > 0 else np.nan
        consec_structure = consec_structure + 1 if bool(row["structure_score"] >= 1) else 0

        # Cost-adjusted exit price and net profit (only meaningful when in position).
        net_profit_rate = (
            (row["close"] * (1 - config.cost_sell_rate)) / cost_price - 1.0
            if cost_price > 0
            else 0.0
        )

        signals = _evaluate_priority(
            row=row,
            config=config,
            in_position=pos,
            prev_high=prev_high,
            prev_total=prev_total_score,
            prev_total_for_warning=prev_total_warning,
            prev_momentum=prev_momentum if pd.notna(prev_momentum) else 0,
            net_profit_rate=net_profit_rate,
            consec_structure_bars=consec_structure,
            bars_since_exit=bars_since_exit,
            prev_box_upper=prev_box_upper,
        )

        action = next((name for name in SIGNAL_PRIORITY if signals[name]), "none")
        actions.append(action)
        for name, fired in signals.items():
            sig_cols[f"signal_{name}"][i] = int(fired)

        # Update position state after the action.
        if pos == 0 and action == "buy":
            pos = 1
            cost_price = row["close"] * (1 + config.cost_buy_rate)
        elif pos == 1 and action in ("stoploss", "exit"):
            pos = 0
            cost_price = 0.0

        bars_since_exit = 0 if action in ("stoploss", "exit") else bars_since_exit + 1

        in_position[i] = pos
        entry_cost[i] = cost_price
        prev_total = row["total_score"]
        prev_momentum = row["momentum_score"]

    for col, arr in sig_cols.items():
        df[col] = arr
    df["in_position"] = in_position
    df["entry_cost_price"] = entry_cost
    df["action"] = actions
    return df


@dataclass
class EvaluateBar:
    """Per-bar inputs for event-driven engines.

    Engine constructs this from its own position state and the scored row,
    then calls :func:`evaluate_bar` to get the priority-ordered action.
    """

    in_position: int
    entry_cost_price: float
    close: float
    high: float
    open: float
    box_lower: float
    risk_swing_low: float
    volume: float
    avg_volume_5: float
    body_high: float
    body_low: float
    upper_shadow: float
    candle_body_size: float
    structure_score: int
    direction_score: int
    chip_score: int
    momentum_score: int
    total_score: int
    prev_total_score: float
    prev_momentum_score: float
    prev_high: float
    state_flameout: int
    state_strong_buy: int
    state_hold: int
    state_warning: int
    volatility_rate: float
    # v3 entry state (engine tracks these; defaults reproduce v2 behavior).
    consec_structure_bars: int = 1
    bars_since_exit: int = 10**9
    prev_box_upper: float = float("nan")


SignalName = Literal["stoploss", "exit", "takeprofit", "reduce", "add", "buy", "hold", "none"]


def evaluate_bar(bar: EvaluateBar, config: StrategyConfig) -> SignalName:
    """Return highest-priority signal name for a bar given current position state."""
    net_profit_rate = (
        (bar.close * (1 - config.cost_sell_rate)) / bar.entry_cost_price - 1.0
        if bar.entry_cost_price > 0
        else 0.0
    )
    edge_ok = bar.volatility_rate >= config.cost_round_rate + config.min_edge_rate

    row = pd.Series(
        {
            "close": bar.close,
            "high": bar.high,
            "open": bar.open,
            "box_lower": bar.box_lower,
            "risk_swing_low": bar.risk_swing_low,
            "volume": bar.volume,
            "avg_volume_5": bar.avg_volume_5,
            "upper_shadow": bar.upper_shadow,
            "candle_body_size": bar.candle_body_size,
            "structure_score": bar.structure_score,
            "direction_score": bar.direction_score,
            "chip_score": bar.chip_score,
            "momentum_score": bar.momentum_score,
            "total_score": bar.total_score,
            "state_flameout": bar.state_flameout,
            "state_strong_buy": bar.state_strong_buy,
            "edge_ok": int(edge_ok),
        }
    )
    signals = _evaluate_priority(
        row=row,
        config=config,
        in_position=bar.in_position,
        prev_high=bar.prev_high,
        prev_total=bar.prev_total_score,
        prev_total_for_warning=bar.prev_total_score,
        prev_momentum=bar.prev_momentum_score,
        net_profit_rate=net_profit_rate,
        consec_structure_bars=bar.consec_structure_bars,
        bars_since_exit=bar.bars_since_exit,
        prev_box_upper=bar.prev_box_upper,
    )
    for name in SIGNAL_PRIORITY:
        if signals[name]:
            return name  # type: ignore[return-value]
    return "none"


def _evaluate_priority(
    row: pd.Series,
    config: StrategyConfig,
    in_position: int,
    prev_high: float,
    prev_total: float,
    prev_total_for_warning: float,
    prev_momentum: float,
    net_profit_rate: float,
    consec_structure_bars: int = 1,
    bars_since_exit: int = 10**9,
    prev_box_upper: float = float("nan"),
) -> dict[str, bool]:
    """Compute boolean firing for each signal type. Caller picks by priority.

    Entry/exit follow the v3 redesign spec
    (docs/superpowers/specs/2026-06-02-m0-v3-entry-redesign-design.md); the
    StrategyConfig v3 fields default to values that reproduce the v2 baseline.
    Stoploss and exit ignore the cost filter per 2.5.3 — risk signals cannot be
    blocked by economic gating.
    """
    in_pos = in_position == 1

    stoploss = in_pos and (
        row["close"] < row["box_lower"] or row["close"] < row["risk_swing_low"]
    )

    # flameout exit: box_lower break is immediate; the momentum trigger needs
    # `exit_flameout_confirm_bars` consecutive bars (v2=1 reproduces single-bar
    # behavior). Computed inline so state_flameout (used by `warning`) is untouched.
    mom_flameout = row["momentum_score"] == -1
    if config.exit_flameout_confirm_bars >= 2:
        mom_flameout = mom_flameout and (prev_momentum == -1)
    flameout = mom_flameout or (row["close"] < row["box_lower"])
    two_warnings = (
        row["total_score"] <= config.warning_threshold
        and pd.notna(prev_total_for_warning)
        and prev_total_for_warning <= config.warning_threshold
    )
    exit_sig = in_pos and (flameout or two_warnings)

    body = row["candle_body_size"]
    takeprofit = (
        in_pos
        and body > 0
        and row["upper_shadow"] > body * config.takeprofit_shadow_rate
        and pd.notna(row["avg_volume_5"])
        and row["volume"] > row["avg_volume_5"] * config.takeprofit_volume_rate
        and pd.notna(prev_total)
        and row["total_score"] < prev_total
        and net_profit_rate >= config.tp_min_net_rate
    )

    reduce_strong_drop = (
        pd.notna(prev_total)
        and row["total_score"] < config.strong_buy_threshold
        and prev_total >= config.strong_buy_threshold
    )
    reduce_momentum_drop = row["momentum_score"] == 1 and prev_momentum == 2
    reduce_sig = (
        in_pos
        and net_profit_rate > config.cost_round_rate
        and (reduce_strong_drop or reduce_momentum_drop)
    )

    add_sig = (
        in_pos
        and row["total_score"] >= config.add_score_threshold
        and row["momentum_score"] == 2
        and pd.notna(prev_high)
        and row["close"] > prev_high
        and net_profit_rate >= config.cost_round_rate + config.min_edge_rate
    )

    # --- v3 parameterized entry gate (v2 defaults reproduce baseline) ---
    layers_hit = sum(
        s >= 1
        for s in (
            row["structure_score"], row["direction_score"],
            row["chip_score"], row["momentum_score"],
        )
    )
    mandatory_layers = (
        row["momentum_score"] >= 1                      # 動能強制守門 (不豁免)
        and row["structure_score"] >= 1                 # 結構必含
        and (row["direction_score"] >= 1 or row["chip_score"] >= 1)  # 機構共識至少一邊
    )
    negative_veto = row["direction_score"] == -1 or row["chip_score"] == -1
    first_cross_ok = (
        not config.entry_first_cross_only
        or (pd.notna(prev_total) and prev_total < config.strong_buy_threshold)
    )
    confirm_ok = consec_structure_bars >= config.entry_confirm_days
    breakout_exempt = (
        row["structure_score"] == 2
        and pd.notna(prev_box_upper)
        and row["close"] > prev_box_upper
    )
    cooldown_ok = bars_since_exit >= config.entry_cooldown_bars or breakout_exempt
    # structure gate: breakout (>= entry_min_structure) OR, when entry_retest_band>0,
    # a box-top retest (close within band of box_upper while still above box_mid,
    # i.e. structure>=1). Keeps structure quality without the v3 mid-box flood.
    _box_upper = row.get("box_upper")
    structure_breakout = row["structure_score"] >= config.entry_min_structure
    structure_retest = (
        config.entry_retest_band > 0
        and row["structure_score"] >= 1
        and pd.notna(_box_upper)
        and float(_box_upper) > 0
        and row["close"] >= float(_box_upper) * (1 - config.entry_retest_band)
    )
    structure_ok = structure_breakout or structure_retest
    buy_sig = (
        not in_pos
        and cooldown_ok
        and mandatory_layers
        and not negative_veto
        and layers_hit >= config.entry_min_layers
        and structure_ok
        and row["total_score"] >= config.strong_buy_threshold
        and first_cross_ok
        and confirm_ok
        and bool(row.get("edge_ok", 0))
    )

    hold_sig = in_pos and row["total_score"] >= 3 and row["momentum_score"] >= 1

    return {
        "stoploss": stoploss,
        "exit": exit_sig,
        "takeprofit": takeprofit,
        "reduce": reduce_sig,
        "add": add_sig,
        "buy": buy_sig,
        "hold": hold_sig,
    }
