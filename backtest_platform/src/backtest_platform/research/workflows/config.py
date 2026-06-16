"""Workflow config models — per-strategy research declaration contract.

Each strategy's ``research_config.py`` instantiates these models to declare
how it should be validated. Workflow functions read these and drive the
ADR-028 dispatch layer — never calling strategy functions directly.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DOEConfig(BaseModel):
    """DOE (Design of Experiments) first-read configuration."""
    model_config = {"frozen": True, "extra": "forbid"}

    strategy:          str
    grid:              dict[str, list[Any]] = Field(..., min_length=1)
    symbols:           list[str]            = Field(..., min_length=1)
    is_start:          date
    is_end:            date
    hypothesis_prefix: str = "DOE"

    @property
    def n_configs(self) -> int:
        return max(1, int(math.prod(len(v) for v in self.grid.values())))

    @model_validator(mode="after")
    def _window_ordered(self) -> DOEConfig:
        if self.is_start >= self.is_end:
            raise ValueError("is_start must be before is_end")
        return self


class GOGatesConfig(BaseModel):
    """GO-gates configuration: WFA + PBO over a wide universe."""
    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy:     str
    fixed_config: BaseModel
    config_grid:  dict[str, list[Any]] | None = None
    symbols:      list[str] = Field(..., min_length=1)
    is_start:     date
    is_end:       date
    n_wfa_folds:  int = Field(5, ge=2, le=20)
    pbo_n_splits: int = Field(16, ge=2)

    @property
    def n_landscape_configs(self) -> int:
        if not self.config_grid:
            return 1
        return max(1, int(math.prod(len(v) for v in self.config_grid.values())))

    @model_validator(mode="after")
    def _window_ordered(self) -> GOGatesConfig:
        if self.is_start >= self.is_end:
            raise ValueError("is_start must be before is_end")
        return self


class TruthGateConfig(BaseModel):
    """ADR-025 two-stage truth gate configuration."""
    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy:        str
    fixed_config:    BaseModel
    symbols:         list[str] = Field(..., min_length=1)
    is_start:        date
    oos_start:       date
    is_end:          date
    n_trials:        int   = Field(..., ge=1)
    pre_registered:  bool  = True
    slippage_stress: float = Field(0.003, ge=0, le=0.05)
    n_wfa_folds:     int   = Field(5, ge=2)

    @model_validator(mode="after")
    def _window_ordered(self) -> TruthGateConfig:
        if not (self.is_start < self.oos_start < self.is_end):
            raise ValueError("is_start < oos_start < is_end required")
        return self


class PaperReplayConfig(BaseModel):
    """Paper replay configuration."""
    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy:             str
    fixed_config:         BaseModel
    symbols:              list[str] = Field(..., min_length=1)
    as_of:                date
    initial_cash:         float = Field(10_000_000.0, gt=0)
    lookback_buffer_days: int   = Field(400, ge=30)
    run_id_prefix:        str   = "paper_replay"
