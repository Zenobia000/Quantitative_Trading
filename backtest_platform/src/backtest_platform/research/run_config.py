"""RunConfig — a backtest run as a first-class object.

The ``hypothesis`` field is mandatory: every run must pre-register what it is
testing (the cheapest anti-overfit discipline — it removes post-hoc story
fitting). ``run_id`` is a deterministic hash of the inputs so the same run is
identifiable across the runs store without a wall-clock id.
"""
from __future__ import annotations

import hashlib
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from backtest_platform.config.strategy_config import PRESETS


class RunConfig(BaseModel):
    """One IS run: which strategy preset, which stocks, which window, what engine."""

    model_config = {"frozen": True, "extra": "forbid"}

    hypothesis: str = Field(..., min_length=1, description="預先註冊：這個 run 在驗什麼")
    preset: str = Field(..., description="StrategyConfig preset name (v2 / v3 / ...)")
    stocks: tuple[str, ...] = Field(..., min_length=1)
    is_start: date
    is_end: date
    engine: str = Field("sim", description="sim (offline close-to-close) | zipline")

    @field_validator("hypothesis")
    @classmethod
    def _hypothesis_nonblank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hypothesis must not be blank (pre-registration required)")
        return v.strip()

    @field_validator("preset")
    @classmethod
    def _preset_known(cls, v: str) -> str:
        if v not in PRESETS:
            raise ValueError(f"unknown preset {v!r}; choose from {sorted(PRESETS)}")
        return v

    @field_validator("engine")
    @classmethod
    def _engine_known(cls, v: str) -> str:
        if v not in ("sim", "zipline"):
            raise ValueError(f"unknown engine {v!r}")
        return v

    @model_validator(mode="after")
    def _window_ordered(self) -> RunConfig:
        if self.is_start >= self.is_end:
            raise ValueError("is_start must be before is_end")
        return self

    @property
    def run_id(self) -> str:
        """Deterministic short id from the run's defining inputs (no wall-clock)."""
        key = "|".join([
            self.preset, self.engine,
            ",".join(self.stocks),
            self.is_start.isoformat(), self.is_end.isoformat(),
        ])
        return hashlib.sha1(key.encode()).hexdigest()[:12]
