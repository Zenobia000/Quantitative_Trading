"""v3 entry state wiring into the event-driven (zipline) evaluation path.

Verifies the algorithm threads consec_structure / bars_since_exit / prev_box_upper
into EvaluateBar so DEFAULT_CONFIG_V3 actually changes behavior in the engine
(it was hardcoded to StrategyConfig() before — v3 never reached the engine).
"""
from __future__ import annotations

import pandas as pd

from backtest_platform.engines.zipline_adapter.algorithms.four_layer_resonance import (
    _bars_since_exit,
    _build_evaluate_bar,
    _trailing_consec_structure,
)


def test_trailing_consec_structure_counts_recent_run():
    assert _trailing_consec_structure(pd.DataFrame({"structure_score": [2, 0, 1, 1, 1]})) == 3
    assert _trailing_consec_structure(pd.DataFrame({"structure_score": [1, 1, 0]})) == 0
    assert _trailing_consec_structure(pd.DataFrame({"structure_score": [2]})) == 1


def test_bars_since_exit_counts_from_last_exit():
    assert _bars_since_exit(pd.DataFrame({"action": ["buy", "hold", "exit", "none", "none"]})) == 2
    assert _bars_since_exit(pd.DataFrame({"action": ["buy", "hold", "stoploss"]})) == 0
    assert _bars_since_exit(pd.DataFrame({"action": ["buy", "hold", "hold"]})) >= 10**6


def test_build_evaluate_bar_threads_v3_fields():
    last = pd.Series({
        "close": 90.0, "high": 94.0, "open": 90.0, "volume": 1000.0, "box_lower": 70.0,
        "structure_score": 1, "direction_score": 2, "chip_score": 2,
        "momentum_score": 1, "total_score": 6,
    })
    prev = pd.Series({"total_score": 3, "momentum_score": 1, "high": 89.0, "box_upper": 88.0})
    eb = _build_evaluate_bar(
        last, prev, 0, 0.0,
        consec_structure_bars=2, bars_since_exit=99, prev_box_upper=88.0,
    )
    assert eb.consec_structure_bars == 2
    assert eb.bars_since_exit == 99
    assert eb.prev_box_upper == 88.0


def test_build_evaluate_bar_defaults_are_v2_safe():
    last = pd.Series({"close": 90.0, "high": 94.0, "open": 90.0, "volume": 1000.0})
    prev = pd.Series({"total_score": 3})
    eb = _build_evaluate_bar(last, prev, 0, 0.0)
    assert eb.consec_structure_bars == 1
    assert eb.bars_since_exit == 10**9
