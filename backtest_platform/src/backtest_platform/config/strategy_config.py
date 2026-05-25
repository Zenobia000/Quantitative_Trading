"""Strategy parameters. Single source of truth — mirrors v2.md 2.7.1 / 6.1.1.

Any default change here MUST be recorded in v2.md Part 6.3 changelog.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class StrategyConfig(BaseModel):
    """Strategy parameters for the four-layer resonance system.

    Defaults match v2.md XScript inputs (section 2.7). Use immutable instances
    (``model_config = {"frozen": True}``) when passing into pure scoring/signal
    functions so the parameter set cannot mutate mid-backtest.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    # --- Structure layer (L1) ---
    box_period: int = Field(60, ge=10, le=250, description="箱型計算天數")

    # --- Chip layer (L3) ---
    chip_strong_threshold: float = Field(
        0.10, gt=0, le=1.0, description="籌碼強多門檻 (chip_total / net_volume)"
    )

    # --- Scoring thresholds ---
    strong_buy_threshold: int = Field(5, ge=1, le=8, description="強多總分門檻")
    warning_threshold: int = Field(2, ge=-3, le=8, description="警告總分門檻")
    add_score_threshold: int = Field(6, ge=1, le=8, description="加碼總分門檻")

    # --- Take-profit triggers ---
    takeprofit_volume_rate: float = Field(1.5, gt=0, description="停利爆量倍數")
    takeprofit_shadow_rate: float = Field(1.5, gt=0, description="停利上影線倍數")

    # --- Cost model (Part 2.5) ---
    fee_rate: float = Field(0.001425, ge=0, le=0.01, description="券商手續費率")
    fee_discount: float = Field(0.6, gt=0, le=1.0, description="手續費折扣")
    tax_stock_rate: float = Field(0.003, ge=0, le=0.01, description="證交稅率 (賣方)")
    slip_rate: float = Field(0.001, ge=0, le=0.05, description="滑價估計")
    min_edge_rate: float = Field(0.006, ge=0, le=0.1, description="最低交易優勢")
    tp_min_net_rate: float = Field(0.015, ge=0, le=1.0, description="停利最低淨利")

    # --- Derived cost rates (computed, not configurable) ---
    @property
    def cost_buy_rate(self) -> float:
        return self.fee_rate * self.fee_discount + self.slip_rate

    @property
    def cost_sell_rate(self) -> float:
        return self.fee_rate * self.fee_discount + self.tax_stock_rate + self.slip_rate

    @property
    def cost_round_rate(self) -> float:
        return self.cost_buy_rate + self.cost_sell_rate

    @model_validator(mode="after")
    def _validate_thresholds(self) -> StrategyConfig:
        if self.warning_threshold >= self.strong_buy_threshold:
            raise ValueError("warning_threshold must be < strong_buy_threshold")
        if self.add_score_threshold < self.strong_buy_threshold:
            raise ValueError("add_score_threshold must be >= strong_buy_threshold")
        return self


DEFAULT_CONFIG = StrategyConfig()
