"""workflow.config — the per-strategy research declaration models (ADR-029)."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backtest_platform.research.workflows.config import (
    DOEConfig,
    GOGatesConfig,
    PaperReplayConfig,
    TruthGateConfig,
)


def test_doe_config_validates_fields():
    cfg = DOEConfig(
        strategy="momentum",
        grid={"lookback_days": [120, 252], "rebalance": ["monthly", "quarterly"]},
        symbols=["2330", "2317"],
        is_start=date(2020, 1, 1),
        is_end=date(2023, 12, 31),
    )
    assert cfg.strategy == "momentum"
    assert cfg.n_configs == 4  # 2x2


def test_doe_config_rejects_empty_grid():
    with pytest.raises(ValidationError):
        DOEConfig(strategy="m", grid={}, symbols=["2330"],
                  is_start=date(2020, 1, 1), is_end=date(2023, 1, 1))


def test_doe_config_rejects_inverted_window():
    with pytest.raises(ValidationError):
        DOEConfig(strategy="m", grid={"x": [1]}, symbols=["2330"],
                  is_start=date(2023, 1, 1), is_end=date(2020, 1, 1))


def test_go_gates_config_valid():
    from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
    cfg = GOGatesConfig(
        strategy="four_layer",
        fixed_config=StrategyConfig(),
        config_grid={"entry_min_layers": [3, 4]},
        symbols=["2330"],
        is_start=date(2015, 1, 1),
        is_end=date(2024, 12, 31),
    )
    assert cfg.n_landscape_configs == 2


def test_go_gates_config_no_grid_one_landscape():
    from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
    cfg = GOGatesConfig(
        strategy="four_layer", fixed_config=StrategyConfig(), symbols=["2330"],
        is_start=date(2015, 1, 1), is_end=date(2024, 12, 31),
    )
    assert cfg.n_landscape_configs == 1  # None grid → PBO skipped


def test_truth_gate_config_valid():
    from backtest_platform.strategies.momentum.strategy import MomentumConfig
    cfg = TruthGateConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(),
        symbols=["2330"],
        is_start=date(2015, 1, 1),
        oos_start=date(2021, 1, 1),
        is_end=date(2024, 12, 31),
        n_trials=8,
        slippage_stress=0.003,
    )
    assert cfg.n_trials == 8
    assert cfg.pre_registered is True


def test_truth_gate_rejects_unordered_oos():
    from backtest_platform.strategies.momentum.strategy import MomentumConfig
    with pytest.raises(ValidationError):
        TruthGateConfig(
            strategy="momentum", fixed_config=MomentumConfig(), symbols=["2330"],
            is_start=date(2015, 1, 1), oos_start=date(2025, 1, 1), is_end=date(2024, 12, 31),
            n_trials=8,
        )


def test_paper_replay_config_valid():
    from backtest_platform.strategies.momentum.strategy import MomentumConfig
    cfg = PaperReplayConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(),
        symbols=["2330"],
        as_of=date(2023, 1, 3),
    )
    assert cfg.initial_cash == 10_000_000.0
    assert cfg.lookback_buffer_days == 400
