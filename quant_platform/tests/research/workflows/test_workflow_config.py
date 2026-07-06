"""workflow.config — the per-strategy research declaration models (ADR-029)."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from quant_platform.services.research_validation.workflows.config import (
    DOEConfig,
    GOGatesConfig,
    PaperReplayConfig,
    TruthGateConfig,
    revalidate_with_overrides,
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
    from quant_platform.services.research_validation.strategies.four_layer_resonance.config import StrategyConfig
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
    from quant_platform.services.research_validation.strategies.four_layer_resonance.config import StrategyConfig
    cfg = GOGatesConfig(
        strategy="four_layer", fixed_config=StrategyConfig(), symbols=["2330"],
        is_start=date(2015, 1, 1), is_end=date(2024, 12, 31),
    )
    assert cfg.n_landscape_configs == 1  # None grid → PBO skipped


def test_truth_gate_config_valid():
    from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig
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


def test_truth_gate_survivorship_clean_defaults_false():
    # ADR-030: survivorship cleanliness must be an explicit declaration, never a
    # hardwired green light. Default False → the truth gate hard-fails until a
    # strategy proves its universe is survivorship-clean.
    from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig
    cfg = TruthGateConfig(
        strategy="momentum", fixed_config=MomentumConfig(), symbols=["2330"],
        is_start=date(2015, 1, 1), oos_start=date(2021, 1, 1), is_end=date(2024, 12, 31),
        n_trials=8,
    )
    assert cfg.survivorship_clean is False


def test_truth_gate_survivorship_clean_can_be_declared():
    from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig
    cfg = TruthGateConfig(
        strategy="momentum", fixed_config=MomentumConfig(), symbols=["2330"],
        is_start=date(2015, 1, 1), oos_start=date(2021, 1, 1), is_end=date(2024, 12, 31),
        n_trials=8, survivorship_clean=True,
    )
    assert cfg.survivorship_clean is True


def test_truth_gate_rejects_unordered_oos():
    from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig
    with pytest.raises(ValidationError):
        TruthGateConfig(
            strategy="momentum", fixed_config=MomentumConfig(), symbols=["2330"],
            is_start=date(2015, 1, 1), oos_start=date(2025, 1, 1), is_end=date(2024, 12, 31),
            n_trials=8,
        )


def test_paper_replay_config_valid():
    from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig
    cfg = PaperReplayConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(),
        symbols=["2330"],
        as_of=date(2023, 1, 3),
    )
    assert cfg.initial_cash == 10_000_000.0
    assert cfg.lookback_buffer_days == 400


# --- revalidate_with_overrides (審查缺陷 #11 — boundary re-validation) --------
# ``model_copy(update=...)`` bypasses field validators / extra=forbid / model
# validators. The boundary override path must re-validate so a bad override fails
# at the edge, not deep inside the workflow.


def _doe() -> DOEConfig:
    return DOEConfig(
        strategy="momentum",
        grid={"lookback_days": [120, 252]},
        symbols=["2330", "2317"],
        is_start=date(2020, 1, 1),
        is_end=date(2023, 12, 31),
    )


def test_revalidate_no_overrides_returns_same_instance():
    cfg = _doe()
    assert revalidate_with_overrides(cfg, {}) is cfg


def test_revalidate_applies_valid_override():
    out = revalidate_with_overrides(_doe(), {"is_start": date(2019, 1, 1)})
    assert out.is_start == date(2019, 1, 1)
    assert out.is_end == date(2023, 12, 31)  # untouched field preserved


def test_revalidate_coerces_iso_date_string():
    out = revalidate_with_overrides(_doe(), {"is_start": "2019-06-01"})
    assert out.is_start == date(2019, 6, 1)


def test_revalidate_rejects_wrong_type():
    with pytest.raises(ValidationError):
        revalidate_with_overrides(_doe(), {"is_start": "not-a-date"})


def test_revalidate_rejects_unknown_field():
    # extra=forbid must fire — model_copy(update=) would silently attach it.
    with pytest.raises(ValidationError):
        revalidate_with_overrides(_doe(), {"nonexistent_knob": 1})


def test_revalidate_rejects_inverted_window():
    # The _window_ordered model_validator must run — model_copy skips it.
    with pytest.raises(ValidationError):
        revalidate_with_overrides(_doe(), {"is_start": date(2025, 1, 1)})


def test_revalidate_preserves_nested_arbitrary_type_config():
    # GOGates/Truth/Paper carry ``fixed_config: BaseModel`` (arbitrary type). A
    # naive model_dump() round-trip degrades it to a bare BaseModel, losing every
    # field. The shallow dict() approach must keep the real strategy config.
    from quant_platform.services.research_validation.strategies.momentum.strategy import MomentumConfig

    cfg = GOGatesConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(),
        symbols=["2330"],
        is_start=date(2015, 1, 1),
        is_end=date(2024, 12, 31),
    )
    out = revalidate_with_overrides(cfg, {"n_wfa_folds": 6})
    assert out.n_wfa_folds == 6
    assert type(out.fixed_config).__name__ == "MomentumConfig"
    assert out.fixed_config == cfg.fixed_config
