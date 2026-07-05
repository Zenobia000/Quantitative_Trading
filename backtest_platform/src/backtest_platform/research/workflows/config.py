"""Workflow config models — the per-strategy research declaration contract (ADR-029).

Each strategy's ``research_config.py`` instantiates these models to declare HOW it
should be researched (grid, universe, windows, the pre-registered fixed config).
The workflow functions read these models and drive the platform's dispatch layer
(ADR-028) — never calling strategy functions directly.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator


def _grid_size(grid: dict[str, list[Any]] | None) -> int:
    """Product of all grid-axis lengths (1 for an empty/None grid)."""
    if not grid:
        return 1
    return max(1, math.prod(len(v) for v in grid.values()))


def revalidate_with_overrides(cfg: BaseModel, overrides: dict[str, Any]) -> BaseModel:
    """Apply ``overrides`` to a frozen workflow config by RE-VALIDATING at the boundary.

    ``cfg.model_copy(update=overrides)`` mutates fields without running any of the
    validation gate — wrong types, unknown fields (``extra="forbid"``) and illegal
    windows (the ``_window_ordered`` model validators) all slip past and only blow up
    deep inside the workflow thread (審查缺陷 #11). Round-tripping through
    ``model_validate`` re-runs the full gate, so a bad override fails HERE, at the
    system edge, with a clear ``ValidationError`` the caller maps to a 422 / clean
    CLI error.

    Uses a SHALLOW field dict (``dict(cfg)``) rather than ``cfg.model_dump()``:
    ``model_dump`` recursively serializes nested ``fixed_config: BaseModel`` (an
    arbitrary type) to a plain dict, and re-validation then degrades it to a bare
    ``BaseModel`` — silently losing every strategy field. The shallow dict keeps the
    real strategy-config instance while still re-validating the overridden fields.
    """
    if not overrides:
        return cfg
    return type(cfg).model_validate({**dict(cfg), **overrides})


class UniverseConfig(BaseModel):
    """Survivorship-clean universe build declaration (sub-project ②, ADR-032).

    Declares HOW a strategy's factor universe is (re)built from the FinLab wide
    frames: the point-in-time span, the per-quarter liquidity/size cut, and the
    parquet cache the ingested bars land in. Rebalance cadence is fixed quarterly
    (the ADR-024/025 methodology), so it is not a knob. The ``build_universe``
    workflow reads this and drives ``select_survivorship_universe`` +
    ``ingest_universe_finlab`` — never a strategy's backtest function.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    strategy: str
    span_start: date
    span_end: date
    top_n: int = Field(..., ge=1, description="per-quarter top-N by market cap")
    min_turnover: float = Field(..., ge=0, description="trailing-20d avg turnover floor (TWD)")
    cache_dir: str
    # Eligibility (ADR-007 Slice 3) — both opt-in, default off = unchanged behaviour.
    exchange: str | None = Field(
        None,
        description="Board filter via finlab set_universe (e.g. 'TWSE' | 'TPEx'); None = ALL",
    )
    exclude_flagged: bool = Field(
        False,
        description="Exclude 全額交割/處置/注意 names as-of each rebalance (time-varying mask)",
    )

    @model_validator(mode="after")
    def _span_ordered(self) -> UniverseConfig:
        if self.span_start >= self.span_end:
            raise ValueError("span_start must be before span_end")
        return self


class DOEConfig(BaseModel):
    """DOE (Design of Experiments) first-read configuration.

    Declares the parameter grid to scan and the IS window. ``n_configs`` is the
    product of all grid-axis lengths.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    strategy: str
    grid: dict[str, list[Any]] = Field(..., min_length=1)
    symbols: list[str] = Field(..., min_length=1)
    is_start: date
    is_end: date
    hypothesis_prefix: str = "DOE"

    @property
    def n_configs(self) -> int:
        return _grid_size(self.grid)

    @model_validator(mode="after")
    def _window_ordered(self) -> DOEConfig:
        if self.is_start >= self.is_end:
            raise ValueError("is_start must be before is_end")
        return self


class GOGatesConfig(BaseModel):
    """GO-gates configuration: WFA + PBO over a wide universe.

    ``fixed_config``  : the single config being tested (WFA).
    ``config_grid``   : landscape of alternatives for the PBO matrix; None → PBO
                        skipped (only WFA checked).
    """

    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy: str
    fixed_config: BaseModel
    config_grid: dict[str, list[Any]] | None = None
    symbols: list[str] = Field(..., min_length=1)
    is_start: date
    is_end: date
    n_wfa_folds: int = Field(5, ge=2, le=20)
    pbo_n_splits: int = Field(16, ge=2)

    @property
    def n_landscape_configs(self) -> int:
        return _grid_size(self.config_grid)

    @model_validator(mode="after")
    def _window_ordered(self) -> GOGatesConfig:
        if self.is_start >= self.is_end:
            raise ValueError("is_start must be before is_end")
        return self


class TruthGateConfig(BaseModel):
    """ADR-025 two-stage truth gate configuration.

    ``fixed_config``       : pre-registered config (never re-selected after OOS commit).
    ``n_trials``           : landscape size used for DSR deflation.
    ``oos_start``          : OOS boundary; IS = [is_start, oos_start), OOS = [oos_start, is_end].
    ``pre_registered``     : if True, uses OOS-breadth + DSR (not landscape PBO) as overfit control.
    ``survivorship_clean`` : must be declared True by the strategy's ``research_config``
        (or its universe builder) BEFORE the truth gate can pass. Defaults to False —
        the ADR-025 hard precondition is a claim to be proven, never a hardwired green
        light (ADR-030). Leaving it unset keeps the survivorship hard-fail armed.
    ``parquet_dir``        : optional data-cache override (ADR-032). None → the default
        ``data/parquet``; set it to a dedicated cache (e.g. the survivorship-clean
        FinLab universe built by the ``build_universe`` workflow) and ``run_truth_gate``
        routes reads there without callers passing a loader.
    """

    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy: str
    fixed_config: BaseModel
    symbols: list[str] = Field(..., min_length=1)
    is_start: date
    oos_start: date
    is_end: date
    n_trials: int = Field(..., ge=1, description="landscape config count for DSR")
    pre_registered: bool = True
    survivorship_clean: bool = False
    parquet_dir: str | None = None
    slippage_stress: float = Field(0.003, ge=0, le=0.05)
    n_wfa_folds: int = Field(5, ge=2)

    @model_validator(mode="after")
    def _window_ordered(self) -> TruthGateConfig:
        if not (self.is_start < self.oos_start < self.is_end):
            raise ValueError("is_start < oos_start < is_end required")
        return self


class PaperReplayConfig(BaseModel):
    """Paper replay configuration: run ``fixed_config`` through the standard dispatch.

    Runs ``runner.run(symbols, as_of - lookback_buffer_days, as_of, fixed_config,
    loader)`` so the runner has enough history, then judges via the gate.
    """

    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy: str
    fixed_config: BaseModel
    symbols: list[str] = Field(..., min_length=1)
    as_of: date
    initial_cash: float = Field(10_000_000.0, gt=0)
    lookback_buffer_days: int = Field(400, ge=30)
    run_id_prefix: str = "paper_replay"
