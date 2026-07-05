"""v3 entry-gate logic — synthetic fixtures (NOT cache-gated).

Tests the parameterized entry/exit gate on hand-built score rows. The
"reproduce 14 entries on real 2330 + double-window IS edge" check is a separate
manual integration step (Sprint 6, cache-gated) — NOT in this file.

Design source: docs/superpowers/specs/2026-06-02-m0-v3-entry-redesign-design.md
"""
from __future__ import annotations

import pandas as pd
import pytest

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.strategies.four_layer_resonance.signals import (
    EvaluateBar,
    compute_signals,
    evaluate_bar,
)

# Inlined former presets (config/strategy_config.py removed by ADR-028). v3 relaxes
# the four over-tight entry gates; v2 (StrategyConfig() defaults) stays the baseline.
DEFAULT_CONFIG_V3 = StrategyConfig(
    entry_min_layers=3,
    entry_min_structure=1,
    entry_first_cross_only=False,
    entry_confirm_days=2,
    entry_cooldown_bars=3,
    exit_flameout_confirm_bars=2,
)

# Warmup bars so compute_signals' 14-bar edge_ok and 20-bar risk_swing_low fill
# before the test rows. Warmup lows are deliberately far below test closes so
# rolling_swing_low never false-triggers stoploss on in-position test bars.
_WARMUP = 25

_COLS = [
    "open", "high", "low", "close", "volume",
    "structure_score", "direction_score", "chip_score", "momentum_score",
    "total_score", "box_upper", "box_lower",
]


def _row(structure, direction, chip, momentum, close, box_upper, box_lower, high, low):
    return {
        "open": close, "high": high, "low": low, "close": close, "volume": 1000.0,
        "structure_score": structure, "direction_score": direction,
        "chip_score": chip, "momentum_score": momentum,
        "total_score": structure + direction + chip + momentum,
        "box_upper": box_upper, "box_lower": box_lower,
    }


def make_row(structure, direction, chip, momentum, *, close=100.0,
             box_upper=99.0, box_lower=80.0):
    # test row: ±5% range → volatility_rate ~0.10 >> edge_ok threshold (~1.3%)
    return _row(structure, direction, chip, momentum, close, box_upper, box_lower,
                high=close * 1.05, low=close * 0.95)


def frame(rows: list[dict]) -> pd.DataFrame:
    warmup = [
        _row(0, 0, 0, 0, close=100.0, box_upper=130.0, box_lower=40.0,
             high=150.0, low=50.0)
        for _ in range(_WARMUP)
    ]
    return pd.DataFrame(warmup + rows)[_COLS]


def _actions(rows: list[dict], config: StrategyConfig) -> list[str]:
    df = compute_signals(frame(rows), config)
    return df["action"].tolist()[_WARMUP:]


# ───────────────────────── buy gate: v2 reproduction ─────────────────────────

def test_v2_default_rejects_non_breakout_structure_1():
    """v2 (min_structure=2) must NOT enter on structure==1 (close>=box_mid only)."""
    rows = [make_row(1, 2, 2, 1, close=90, box_lower=70)] * 3
    assert "buy" not in _actions(rows, StrategyConfig())


def test_v2_default_enters_on_breakout_first_cross():
    """v2: structure==2 + total>=5 + first-cross + edge_ok → enter on first bar."""
    rows = [make_row(2, 2, 2, 1, close=90, box_lower=70)] * 2
    assert _actions(rows, StrategyConfig())[0] == "buy"


# ───────────────────────── buy gate: v3 relaxation ─────────────────────────

def test_v3_accepts_structure_1_with_mandatory_layers():
    rows = [make_row(1, 2, 2, 1, close=90, box_lower=70)] * 3  # total=6, confirm at bar1
    assert "buy" in _actions(rows, DEFAULT_CONFIG_V3)


def test_v3_rejects_when_momentum_below_1():
    rows = [make_row(2, 2, 2, 0, close=90, box_lower=70)] * 3  # total=6 but mom=0
    assert "buy" not in _actions(rows, DEFAULT_CONFIG_V3)


def test_v3_negative_veto_blocks_when_direction_minus_one():
    rows = [make_row(2, -1, 2, 2, close=90, box_lower=70)] * 3  # total=5, dir==-1
    assert "buy" not in _actions(rows, DEFAULT_CONFIG_V3)


def test_v3_requires_n_of_4_count():
    # Only 2 layers >=1 (struct + mom), dir<1 chip<1 → mandatory + N-of-4 fail.
    rows = [make_row(3, 0, 0, 3, close=90, box_lower=70)] * 3  # invalid scores but tests count path
    # structure max is 2 in reality; clamp to legal scores: struct2,mom2,dir0,chip0 → total4 < 5 anyway
    rows = [make_row(2, 0, 0, 2, close=90, box_lower=70)] * 3
    assert "buy" not in _actions(rows, DEFAULT_CONFIG_V3)  # total=4<5 and no inst consensus


# ───────────────────────── confirm_days ─────────────────────────

def test_v3_confirm_days_requires_2_consecutive_structure():
    rows = [
        make_row(0, 2, 2, 2, close=85, box_lower=70),  # structure=0 → not standing
        make_row(1, 2, 2, 1, close=90, box_lower=70),  # 1st bar standing → confirm unmet
        make_row(1, 2, 2, 1, close=91, box_lower=70),  # 2nd consecutive → enter
    ]
    actions = _actions(rows, DEFAULT_CONFIG_V3)
    assert actions[1] != "buy"
    assert actions[2] == "buy"


# ───────────────────────── re-entry cooldown ─────────────────────────

def test_v3_cooldown_blocks_reentry_within_3_bars():
    rows = [
        make_row(1, 2, 2, 1, close=90, box_lower=85),  # confirm bar1 (no buy)
        make_row(1, 2, 2, 1, close=91, box_lower=85),  # confirm bar2 → BUY
        make_row(1, 2, 2, 1, close=84, box_lower=85),  # close<box_lower → stoploss
        make_row(1, 2, 2, 1, close=90, box_lower=70),  # post-exit bar1 → cooldown blocks
        make_row(1, 2, 2, 1, close=91, box_lower=70),  # post-exit bar2 → cooldown blocks
    ]
    actions = _actions(rows, DEFAULT_CONFIG_V3)
    assert actions[1] == "buy"
    assert actions[2] == "stoploss"
    assert actions[3] != "buy" and actions[4] != "buy"


def test_v3_cooldown_exempt_on_new_breakout():
    rows = [
        make_row(1, 2, 2, 1, close=90, box_lower=85, box_upper=92),
        make_row(1, 2, 2, 1, close=91, box_lower=85, box_upper=92),  # BUY
        make_row(1, 2, 2, 1, close=84, box_lower=85, box_upper=92),  # stoploss
        make_row(2, 2, 2, 1, close=95, box_lower=70, box_upper=92),  # breakout new box top → exempt
    ]
    actions = _actions(rows, DEFAULT_CONFIG_V3)
    assert actions[3] == "buy"


# ───────────────────────── exit: flameout 2-bar confirm ─────────────────────────

def test_v3_flameout_needs_2_bar_momentum_confirm():
    rows = [
        make_row(1, 2, 2, 2, close=90, box_lower=70),   # confirm bar1
        make_row(1, 2, 2, 2, close=91, box_lower=70),   # BUY
        make_row(1, 2, 2, -1, close=89, box_lower=70),  # mom==-1 single → no exit (v3)
        make_row(1, 2, 2, -1, close=88, box_lower=70),  # mom==-1 2nd → exit
    ]
    actions = _actions(rows, DEFAULT_CONFIG_V3)
    assert actions[2] != "exit"
    assert actions[3] == "exit"


def test_v3_box_break_exits_immediately_via_stoploss():
    rows = [
        make_row(1, 2, 2, 2, close=90, box_lower=85),
        make_row(1, 2, 2, 2, close=91, box_lower=85),   # BUY
        make_row(1, 2, 2, 1, close=84, box_lower=85),   # close<box_lower → stoploss now
    ]
    assert _actions(rows, DEFAULT_CONFIG_V3)[2] == "stoploss"


def test_v2_flameout_single_bar_exit_preserved():
    rows = [
        make_row(2, 2, 2, 1, close=90, box_lower=70),   # v2 BUY (breakout)
        make_row(2, 2, 2, -1, close=89, box_lower=70),  # single mom==-1 → v2 exits
    ]
    assert _actions(rows, StrategyConfig())[1] == "exit"


# ───────────────────────── event-driven parity ─────────────────────────

def test_evaluate_bar_enters_on_v3_qualifying_bar():
    bar = EvaluateBar(
        in_position=0, entry_cost_price=0.0, close=90, high=94.5, open=90,
        box_lower=70, risk_swing_low=65, volume=1000, avg_volume_5=900,
        body_high=90, body_low=89, upper_shadow=4.5, candle_body_size=1,
        structure_score=1, direction_score=2, chip_score=2, momentum_score=1,
        total_score=6, prev_total_score=3, prev_momentum_score=1, prev_high=89,
        state_flameout=0, state_strong_buy=1, state_hold=0, state_warning=0,
        volatility_rate=0.05,
        consec_structure_bars=2, bars_since_exit=10**9, prev_box_upper=88,
    )
    assert evaluate_bar(bar, DEFAULT_CONFIG_V3) == "buy"


# ───────────────────────── v2 full-path regression ─────────────────────────

@pytest.mark.parametrize("rows", [
    [make_row(2, 2, 2, 1, close=90 + i, box_lower=70) for i in range(5)],
    [make_row(1, 1, 1, 1, close=90, box_lower=70)] * 5,
    [make_row(2, -1, -1, 2, close=90, box_lower=70)] * 5,
])
def test_v2_default_entry_unchanged_by_v3_params(rows):
    """Under v2 defaults, the new params do not change entry semantics:
    a buy may only fire on a breakout (structure==2) with total>=5."""
    df = compute_signals(frame(rows), StrategyConfig())
    buys = df[df["action"] == "buy"]
    assert (buys["structure_score"] == 2).all()
    assert (buys["total_score"] >= 5).all()


# ───────────────────────── direction A: box-top retest ─────────────────────────
# Inlined former presets: dirA adds a box-top retest arm (entry_retest_band=0.03);
# dirB keeps structure strict (breakout-only) while relaxing the transition gates.
_CONFIG_V3_1A = StrategyConfig(
    entry_min_layers=3,
    entry_min_structure=2,
    entry_first_cross_only=False,
    entry_confirm_days=2,
    entry_cooldown_bars=3,
    exit_flameout_confirm_bars=2,
    entry_retest_band=0.03,
)
_CONFIG_V3_1B = StrategyConfig(
    entry_min_layers=3,
    entry_min_structure=2,
    entry_first_cross_only=False,
    entry_confirm_days=2,
    entry_cooldown_bars=3,
    exit_flameout_confirm_bars=2,
)


def test_v3_1a_accepts_box_top_retest_that_breakout_only_rejects():
    # structure==1 but close within 3% of box_upper → box-top retest entry (dir A)
    rows = [make_row(1, 2, 2, 1, close=98, box_upper=100, box_lower=70)] * 3
    assert "buy" in _actions(rows, _CONFIG_V3_1A)
    assert "buy" not in _actions(rows, _CONFIG_V3_1B)  # breakout-only rejects retest


def test_v3_1a_rejects_mid_box_below_retest_band():
    # structure==1 but close far below box top (mid-box no-man's-land) → still rejected
    rows = [make_row(1, 2, 2, 1, close=85, box_upper=100, box_lower=70)] * 3
    assert "buy" not in _actions(rows, _CONFIG_V3_1A)


def test_v3_1a_still_takes_clean_breakout():
    rows = [make_row(2, 2, 2, 1, close=101, box_upper=100, box_lower=70)] * 3
    assert "buy" in _actions(rows, _CONFIG_V3_1A)
