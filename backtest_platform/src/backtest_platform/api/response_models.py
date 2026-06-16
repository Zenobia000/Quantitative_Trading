"""Typed ``data`` payload models for ``Envelope[T]`` response typing.

Each model declares an endpoint's stable contract fields so the OpenAPI schema
(and the frontend's generated ``api.gen.ts``) carries real types instead of a
generic blob. Every model is ``extra="allow"`` — declaring the contract never
*drops* an undeclared field (FastAPI would otherwise filter them), so typing a
response can never break an existing consumer. Add fields here as contracts firm
up; the stubs stay ``Envelope[Any]`` until their producer lands.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Data(BaseModel):
    """Base for response payloads: typed contract fields, but never lossy."""

    model_config = ConfigDict(extra="allow")


# ---- runs ledger ---------------------------------------------------------- #
class RunSummary(_Data):
    """One row of ``GET /runs`` (``_SUMMARY_KEYS`` projection)."""

    run_id: str
    strategy: str | None = None
    gate_status: str | None = None
    hypothesis: str | None = None
    metrics: dict[str, Any] | None = None
    is_start: str | None = None
    is_end: str | None = None


class RunRecord(_Data):
    """A full ledger record (``GET /runs/{id}`` / ``POST /runs``). Shape varies by
    run; only the identity field is guaranteed, the rest pass through."""

    run_id: str


class SweepEstimate(_Data):
    """``GET /runs/estimate`` — grid cardinality + time estimate."""

    n_configs: int
    est_minutes: float
    axes: dict[str, int] = Field(default_factory=dict)


class RunComparisonRow(_Data):
    """One run's reading in a compare report."""

    run_id: str
    is_baseline: bool
    metrics: dict[str, Any] = Field(default_factory=dict)
    delta: dict[str, Any] = Field(default_factory=dict)
    rank: dict[str, Any] = Field(default_factory=dict)
    gate_status: str | None = None
    hypothesis: str | None = None


class CompareReportData(_Data):
    """``GET /runs/compare`` — per-metric delta vs baseline + ranks + sign."""

    baseline_id: str | None = None
    metric_keys: list[str] = Field(default_factory=list)
    sign_consistent: dict[str, Any] = Field(default_factory=dict)
    rankings: dict[str, Any] = Field(default_factory=dict)
    comparisons: list[RunComparisonRow] = Field(default_factory=list)


# ---- gate ----------------------------------------------------------------- #
class GateCriterion(_Data):
    """One ADR-016/019 gate criterion (``GET /gate/spec``)."""

    key: str
    op: str
    threshold: float
    kind: str | None = None
    label: str | None = None


class GateSpecData(_Data):
    criteria: list[GateCriterion] = Field(default_factory=list)


class GateEvalData(_Data):
    """``POST /gate/evaluate`` verdict; per-criterion detail via extra='allow'."""

    status: str | None = None


# ---- metrics -------------------------------------------------------------- #
class MetricsData(_Data):
    """``POST /metrics/{summary,trades}`` — metric keys vary by request; the named
    object is enough for typing, extra='allow' carries the computed values."""


# ---- presets -------------------------------------------------------------- #
class PresetsListData(_Data):
    presets: list[str] = Field(default_factory=list)
    configs: dict[str, Any] = Field(default_factory=dict)


class PresetData(_Data):
    """One preset's StrategyConfig dump (``GET /presets/{name}``); shape varies."""


# ---- research strategies / universe --------------------------------------- #
class StrategyRow(_Data):
    strategy_id: str
    version: str | None = None
    validation_status: str | None = None
    stage: str | None = None
    runs_count: int | None = None
    best_kpi: dict[str, Any] | None = None


class UniverseFiltersData(_Data):
    markets: list[str] = Field(default_factory=list)


# ---- research registry ---------------------------------------------------- #
class SavedView(_Data):
    id: str
    name: str | None = None
    query: dict[str, Any] | None = None


class TrialsData(_Data):
    cumulative_trials: int


# ---- promotion ------------------------------------------------------------ #
class PromotionStateData(_Data):
    strategy_id: str
    stage: str | None = None
    gates: list[dict[str, Any]] | None = None
    history: list[dict[str, Any]] | None = None


class PromotionEvent(_Data):
    """One immutable promotion audit event (``GET /research/promote/{id}/audit``)."""


# ---- system config -------------------------------------------------------- #
class RiskRule(_Data):
    id: str
    order: int | None = None
    description: str | None = None


class RiskSpecData(_Data):
    rules: list[RiskRule] = Field(default_factory=list)
    thresholds: dict[str, Any] = Field(default_factory=dict)


class AlertRuleRow(_Data):
    rule_id: str
    level: str | None = None
    title: str | None = None
