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
    preset: str | None = None
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
