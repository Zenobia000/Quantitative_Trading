"""Taiwan stock cost & rule model (plan v3.0 §4.3).

Configures zipline's commission/slippage to match TWSE reality:
- 手續費（broker commission）：0.1425% × discount, **buy and sell both**
- 證交稅（securities transaction tax）：0.3%, **sell only**
- 滑點（slippage）：configurable basis-points (default 10 bps)
- 漲跌停（price limit）：±10% from prev_close — implemented as `TradingControl`
- 只做多（long-only）：set via `set_long_only`

The directional fee (buy ≠ sell) is the awkward part — zipline's built-in
`PerDollar` doesn't support side-specific rates. We subclass
`CommissionModel` to implement it.

Single source of truth for cost rates: `StrategyConfig` derived properties
(M1 既有 ADR-004). Avoids parameter drift between M1 pipeline + this engine.
"""
from __future__ import annotations

from zipline.api import set_commission, set_long_only, set_slippage
from zipline.finance.commission import CommissionModel
from zipline.finance.slippage import FixedBasisPointsSlippage

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig


class TaiwanCommission(CommissionModel):
    """Directional fee — buy vs sell different rates.

    zipline calls `calculate(order, transaction)` per fill. We use the
    `transaction.amount` sign (positive=buy, negative=sell) to pick rate.
    Returns total $ cost; zipline applies it to the order's cash impact.

    Rate convention here is **commission only** (no slippage) — zipline's
    slippage model handles slip_rate separately via `set_slippage`. If we
    used `StrategyConfig.cost_buy_rate` (which includes slip_rate for
    M1/vectorbt simplicity), we would double-count slippage.

    Rates:
        buy_rate  = fee_rate × fee_discount   (broker only)
        sell_rate = fee_rate × fee_discount + tax_stock_rate (broker + tax)
    """

    def __init__(self, buy_rate: float, sell_rate: float):
        self.buy_rate = buy_rate
        self.sell_rate = sell_rate

    def calculate(self, order, transaction):  # noqa: ARG002 — zipline signature
        gross = abs(transaction.amount * transaction.price)
        if transaction.amount > 0:
            return gross * self.buy_rate
        return gross * self.sell_rate

    def __repr__(self):
        return (
            f"TaiwanCommission(buy_rate={self.buy_rate:.6f}, "
            f"sell_rate={self.sell_rate:.6f})"
        )


def _broker_only_rates(config: StrategyConfig) -> tuple[float, float]:
    """Strip slip_rate from cost_*_rate — zipline applies slip via slippage model.

    Avoids double-counting (M1/vectorbt lumps slip into cost_*_rate; zipline
    splits them).
    """
    broker = config.fee_rate * config.fee_discount
    return (broker, broker + config.tax_stock_rate)


def apply_taiwan_stock_rules(config: StrategyConfig) -> None:
    """Wire up commission + slippage + long-only for current zipline algorithm.

    Must be called from inside `initialize(context)` — zipline's set_*
    functions write into the algorithm being constructed (uses module-level
    state in zipline.api).

    Cost split (avoid double-counting slip):
        commission = fee_rate × fee_discount (+ tax for sell)
        slippage   = slip_rate × 10000 bps via FixedBasisPointsSlippage

    FixedBasisPointsSlippage applies to all fills with no volume impact;
    M3 may upgrade to volume-share slippage when we have realistic Taiwan
    microstructure data.
    """
    buy_rate, sell_rate = _broker_only_rates(config)
    set_commission(TaiwanCommission(buy_rate=buy_rate, sell_rate=sell_rate))

    # Slippage: convert rate (e.g. 0.001) to basis points (10)
    set_slippage(FixedBasisPointsSlippage(basis_points=config.slip_rate * 10_000))

    # No shorting (台股不允許融券放空 for retail without margin account)
    set_long_only()

    # NOTE: ±10% price-limit reject is NOT yet implemented as TradingControl.
    # zipline's `register_trading_control()` API requires subclassing
    # `TradingControl` and access to `_trading_control_max_order_size` etc.
    # Plan v3.0 §11 R5 lists this for Sprint 2; M2 backtest 對 limit-up
    # 的訂單 zipline 預設 fill_at_open，會略樂觀。
