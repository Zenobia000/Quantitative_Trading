"""StrategyConfig defaults must mirror v2.md 2.7.1 / 6.1.1 exactly.

When v2.md updates a default, this test fails and forces the engineer to
either propagate the change here or roll it back — preventing silent drift.

Post-ADR-028: config lives with its strategy
(``strategies.four_layer_resonance.config``); the central ``config.strategy_config``
module — and its ``PRESETS`` / ``get_preset`` / ``DEFAULT_CONFIG`` — is gone.
Named presets are no longer a config concern (a run names a ``strategy`` + ``params``).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from quant_platform.services.research_validation.strategies.four_layer_resonance.config import StrategyConfig


def test_strategy_config_constructs_with_defaults() -> None:
    # config_model()-style construction with no args must succeed (contract invariant).
    c = StrategyConfig()
    assert isinstance(c, StrategyConfig)


def test_defaults_match_v2_spec() -> None:
    c = StrategyConfig()
    assert c.box_period == 60
    assert c.chip_strong_threshold == 0.10
    assert c.strong_buy_threshold == 5
    assert c.warning_threshold == 2
    assert c.add_score_threshold == 6
    assert c.takeprofit_volume_rate == 1.5
    assert c.takeprofit_shadow_rate == 1.5
    assert c.fee_rate == 0.001425
    assert c.fee_discount == 0.6
    assert c.tax_stock_rate == 0.003
    assert c.slip_rate == 0.001
    assert c.min_edge_rate == 0.006
    assert c.tp_min_net_rate == 0.015


def test_derived_cost_rates() -> None:
    c = StrategyConfig()
    expected_buy = 0.001425 * 0.6 + 0.001
    expected_sell = 0.001425 * 0.6 + 0.003 + 0.001
    assert c.cost_buy_rate == pytest.approx(expected_buy)
    assert c.cost_sell_rate == pytest.approx(expected_sell)
    assert c.cost_round_rate == pytest.approx(expected_buy + expected_sell)


def test_with_extra_slippage_adds_round_trip_slip() -> None:
    c = StrategyConfig()
    stressed = c.with_extra_slippage(0.002)
    assert stressed.slip_rate == pytest.approx(c.slip_rate + 0.002)
    # immutability: the original is untouched (returns a copy)
    assert c.slip_rate == 0.001
    assert isinstance(stressed, StrategyConfig)


def test_warning_threshold_must_be_below_strong_buy() -> None:
    with pytest.raises(ValidationError, match="warning_threshold"):
        StrategyConfig(warning_threshold=5, strong_buy_threshold=5)


def test_add_threshold_must_be_at_or_above_strong_buy() -> None:
    with pytest.raises(ValidationError, match="add_score_threshold"):
        StrategyConfig(add_score_threshold=4, strong_buy_threshold=5)


def test_config_is_immutable() -> None:
    c = StrategyConfig()
    with pytest.raises(ValidationError):
        c.box_period = 30  # type: ignore[misc]


def test_v3_entry_fields_default_to_v2_behavior() -> None:
    """New v3 entry params must default to v2-reproducing values (no baseline drift)."""
    c = StrategyConfig()
    assert c.entry_min_layers == 4
    assert c.entry_min_structure == 2
    assert c.entry_first_cross_only is True
    assert c.entry_confirm_days == 1
    assert c.entry_cooldown_bars == 0
    assert c.exit_flameout_confirm_bars == 1


def test_v3_entry_field_bounds() -> None:
    with pytest.raises(ValidationError):
        StrategyConfig(entry_min_layers=5)
    with pytest.raises(ValidationError):
        StrategyConfig(entry_min_structure=3)
    with pytest.raises(ValidationError):
        StrategyConfig(entry_confirm_days=0)


def test_retest_band_bounds() -> None:
    with pytest.raises(ValidationError):
        StrategyConfig(entry_retest_band=0.5)   # > le=0.2
    with pytest.raises(ValidationError):
        StrategyConfig(entry_retest_band=-0.01)  # < 0
