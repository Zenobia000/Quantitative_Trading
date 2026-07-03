"""RunConfig — a backtest run as a first-class object.

``hypothesis`` is mandatory (anti-overfit pre-registration discipline).
``run_id`` is a deterministic hash over (strategy, params, engine, stocks,
window) so the same run is identifiable without a wall-clock id.
``strategy`` names a registered StrategyRunner; ``params`` is validated
against that runner's ``config_model`` at dispatch time (_run_is_core),
not here — so RunConfig stays decoupled from concrete strategy types.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class RunConfig(BaseModel):
    """One IS run: which strategy, which params, which stocks, which window."""

    model_config = {"frozen": True, "extra": "forbid"}

    hypothesis: str = Field(..., min_length=1, description="預先註冊：這個 run 在驗什麼")
    strategy:   str = Field(..., description="registered strategy name (see list_strategies())")
    params:     dict[str, Any] = Field(default_factory=dict, description="strategy params — validated at dispatch")
    stocks:     tuple[str, ...] = Field(..., min_length=1)
    is_start:   date
    is_end:     date
    engine:     str = Field("sim", description="sim (zipline/vectorbt removed 2026-07-03, ADR-037)")

    @field_validator("hypothesis")
    @classmethod
    def _hypothesis_nonblank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hypothesis must not be blank")
        return v.strip()

    @field_validator("engine")
    @classmethod
    def _engine_known(cls, v: str) -> str:
        # ``sim`` is the only live engine; ``zipline`` retained solely so historical
        # run configs (persisted engine='zipline') still validate (ADR-037 removed
        # the zipline engine, but the runs DDL column keeps the value as metadata).
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
        """Deterministic 12-char id from the run's defining inputs."""
        key = "|".join([
            self.strategy,
            json.dumps(self.params, sort_keys=True, default=str),
            self.engine,
            ",".join(sorted(self.stocks)),
            self.is_start.isoformat(),
            self.is_end.isoformat(),
        ])
        return hashlib.sha1(key.encode()).hexdigest()[:12]
