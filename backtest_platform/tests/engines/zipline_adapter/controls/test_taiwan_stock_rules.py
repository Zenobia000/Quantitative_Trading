"""Tests for `taiwan_stock_rules.TaiwanCommission` directional fee.

zipline `set_commission` / `set_long_only` / `set_slippage` write to a
process-global trading algorithm context — too painful to fixture, so we
only unit-test the calculation logic of `TaiwanCommission.calculate()`.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from backtest_platform.config.strategy_config import StrategyConfig
from backtest_platform.engines.zipline_adapter.controls.taiwan_stock_rules import (
    TaiwanCommission,
)


@dataclass
class StubTransaction:
    """Mimics zipline `Transaction` shape — only fields TaiwanCommission reads."""

    amount: int
    price: float


def test_buy_commission_applies_buy_rate_only():
    """Buy: cost = qty × price × buy_rate (no tax)."""
    fee = TaiwanCommission(buy_rate=0.001, sell_rate=0.004)
    tx = StubTransaction(amount=1000, price=500.0)  # 500_000 gross

    cost = fee.calculate(order=None, transaction=tx)
    assert cost == pytest.approx(500_000 * 0.001)  # = 500


def test_sell_commission_applies_sell_rate():
    """Sell: cost = qty × price × sell_rate (commission + transaction tax)."""
    fee = TaiwanCommission(buy_rate=0.001, sell_rate=0.004)
    tx = StubTransaction(amount=-1000, price=500.0)  # negative = sell

    cost = fee.calculate(order=None, transaction=tx)
    assert cost == pytest.approx(500_000 * 0.004)  # = 2000


def test_commission_with_strategyconfig_default_rates_broker_only():
    """End-to-end with default StrategyConfig, broker-only (no slip):
        buy_rate  = 0.001425 × 0.6           = 0.000855 (broker × discount)
        sell_rate = 0.000855 + 0.003         = 0.003855 (broker + tax)

    Slip is stripped — zipline applies it via set_slippage separately.
    """
    from backtest_platform.engines.zipline_adapter.controls.taiwan_stock_rules import (
        _broker_only_rates,
    )

    config = StrategyConfig()
    buy_rate, sell_rate = _broker_only_rates(config)
    fee = TaiwanCommission(buy_rate=buy_rate, sell_rate=sell_rate)

    buy_tx = StubTransaction(amount=1000, price=500.0)
    sell_tx = StubTransaction(amount=-1000, price=500.0)

    buy_cost = fee.calculate(order=None, transaction=buy_tx)
    sell_cost = fee.calculate(order=None, transaction=sell_tx)

    assert buy_cost == pytest.approx(500_000 * 0.000855)
    assert sell_cost == pytest.approx(500_000 * 0.003855)
    # Round-trip cost: sell side ~4.5× larger (tax dominates)
    assert sell_cost > buy_cost * 4


def test_broker_only_rates_strips_slippage():
    """Regression: _broker_only_rates must NOT include slip_rate (avoid
    double-counting with zipline FixedBasisPointsSlippage).
    """
    from backtest_platform.engines.zipline_adapter.controls.taiwan_stock_rules import (
        _broker_only_rates,
    )

    config = StrategyConfig()  # slip_rate=0.001 included in cost_*_rate
    buy_rate, sell_rate = _broker_only_rates(config)

    # broker-only excludes slip
    assert buy_rate == pytest.approx(config.fee_rate * config.fee_discount)
    assert buy_rate == pytest.approx(config.cost_buy_rate - config.slip_rate)
    assert sell_rate == pytest.approx(config.cost_sell_rate - config.slip_rate)


def test_zero_amount_yields_zero_cost():
    fee = TaiwanCommission(buy_rate=0.001, sell_rate=0.004)
    tx = StubTransaction(amount=0, price=500.0)
    assert fee.calculate(order=None, transaction=tx) == 0


def test_repr_includes_both_rates():
    """Helps debugging — strategists should see fee config in logs."""
    fee = TaiwanCommission(buy_rate=0.000855, sell_rate=0.003855)
    rep = repr(fee)
    assert "0.000855" in rep
    assert "0.003855" in rep
