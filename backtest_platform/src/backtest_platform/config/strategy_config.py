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

    # --- v3 entry gate (M0 v3 redesign; defaults reproduce v2 baseline) ---
    # See docs/superpowers/specs/2026-06-02-m0-v3-entry-redesign-design.md
    entry_min_layers: int = Field(
        4, ge=1, le=4, description="N-of-4 冗餘計數上限門 (v2=4 全AND, v3=3)"
    )
    entry_min_structure: int = Field(
        2, ge=0, le=2, description="進場最低結構分 (v2=2 箱型突破, v3=1 站上箱中)"
    )
    entry_first_cross_only: bool = Field(
        True, description="僅單日首次站上進場 (v2=True, v3=False 放行持續站上)"
    )
    entry_confirm_days: int = Field(
        1, ge=1, le=10, description="structure 持續站穩確認天數 (v2=1, v3=2)"
    )
    entry_cooldown_bars: int = Field(
        0, ge=0, le=20, description="出場後 re-entry 冷卻 bar (v2=0, v3=3)"
    )
    exit_flameout_confirm_bars: int = Field(
        1, ge=1, le=5, description="flameout momentum 觸發確認 bar (v2=1, v3=2)"
    )

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

# v3 entry-redesign preset (M0 v0.1). Relaxes the four over-tight entry gates
# per the trader-pressure-tested design spec. Use explicitly; DEFAULT_CONFIG
# (v2) remains the baseline-reproducing default.
DEFAULT_CONFIG_V3 = StrategyConfig(
    entry_min_layers=3,
    entry_min_structure=1,
    entry_first_cross_only=False,
    entry_confirm_days=2,
    entry_cooldown_bars=3,
    exit_flameout_confirm_bars=2,
)

# v3 IS gate FAIL smoking gun: min_structure=1 floods structure==1 mid-box entries
# (72-76%). Direction B (ADR-019 §4) — keep structure==2 strict, relax ONLY the
# transition gates. Minimal causal-isolation: was the over-tight *transition*, not
# the structure, the constraint? IS result: dirB beats both v2 and v3 in both
# windows with structure1%=0 (gate review §7).
DEFAULT_CONFIG_V3_1B = StrategyConfig(
    entry_min_layers=3,
    entry_min_structure=2,           # <-- kept strict (breakout only), unlike v3
    entry_first_cross_only=False,
    entry_confirm_days=2,
    entry_cooldown_bars=3,
    exit_flameout_confirm_bars=2,
)

# Named presets for engine/CLI config injection (STRATEGY_PRESET env / `backtest-run
# --config` / research `run-is --preset`).
PRESETS: dict[str, StrategyConfig] = {
    "v2": DEFAULT_CONFIG,
    "v3": DEFAULT_CONFIG_V3,
    "v3.1b": DEFAULT_CONFIG_V3_1B,
}


def get_preset(name: str) -> StrategyConfig:
    """Return the named StrategyConfig preset ('v2' baseline / 'v3' relaxed)."""
    try:
        return PRESETS[name]
    except KeyError:
        raise ValueError(
            f"unknown strategy preset {name!r}; choose from {sorted(PRESETS)}"
        ) from None
