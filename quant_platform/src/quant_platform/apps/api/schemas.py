"""Request schemas — the system-boundary validation layer (coding-style.md §輸入驗證).

Every POST body is a frozen-ish Pydantic model with ``extra="forbid"`` so unknown
fields fail fast with a clear 422 rather than being silently dropped. These mirror
(but are deliberately separate from) the domain models in ``research`` /
``validation`` — the API contract can evolve independently of the internals, and
the boundary never trusts external JSON.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    """Trigger one IS run — the HTTP form of a ``RunConfig`` (validated downstream)."""

    model_config = {"extra": "forbid"}

    hypothesis: str = Field(..., min_length=1, description="預先註冊：這個 run 在驗什麼")
    strategy: str = Field(..., description="Registered strategy name (see GET /strategies)")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy params — validated at dispatch")
    # SPEC-01 Slice 2 / ADR-007: pool selection resolves server-side. Precedence —
    # explicit ``stocks`` > named ``universe`` > the system default universe. So a
    # run NEVER *requires* a hand-typed symbol list: omit both → system default.
    stocks: list[str] = Field(
        default_factory=list,
        description="Explicit stock ids. Empty → resolved from `universe`, else the system default.",
    )
    universe: str | None = Field(
        None,
        description="Named universe id (GET /system/universes); resolved to symbols "
        "server-side. Ignored when `stocks` is non-empty.",
    )
    is_start: date
    is_end: date
    engine: str = Field("sim", description="sim (zipline/vectorbt removed 2026-07-03, ADR-037)")


class GateEvaluateRequest(BaseModel):
    """Judge an arbitrary metrics dict against the審判庭 (ADR-016 + ADR-019)."""

    model_config = {"extra": "forbid"}

    metrics: dict[str, float] = Field(
        ..., description="run metrics, e.g. {cagr, sharpe, struct1_pct, ...}"
    )
    strategy: str | None = Field(
        None,
        description="registered strategy name → judge by ITS declared gate; "
        "omit for the four-layer DEFAULT_GATE (審查缺陷 #8)",
    )


class MetricsSummaryRequest(BaseModel):
    """Compute the A/B/C performance metrics over a daily-returns series."""

    model_config = {"extra": "forbid"}

    daily_returns: list[float] = Field(..., min_length=1, description="per-period returns")
    risk_free: float = Field(0.0, description="annual risk-free rate")


class TradeMetricsRequest(BaseModel):
    """Compute the E (trade-quality) metrics over a list of trade records."""

    model_config = {"extra": "forbid"}

    trades: list[dict] = Field(
        ..., min_length=1, description="trade records carrying pnl / hold_days keys"
    )
