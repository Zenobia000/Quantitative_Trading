"""Uniform API response envelope (rules/patterns.md §API 回應格式).

Every endpoint returns the same shape — ``{success, data, error, meta}``:

* ``success`` — boolean status flag.
* ``data``    — the payload (``null`` on error).
* ``error``   — a structured ``{code, message, detail}`` object (``null`` on success).
* ``meta``    — optional metadata (pagination: ``total`` / ``page`` / ``limit``).

Centralizing the contract here keeps every router consistent and lets the
frontend rely on a single response shape regardless of which endpoint it hit.

``error`` is a structured object (doc 25 §2 / ADR-021), not a bare string: the
``code`` is a stable enum the frontend switches on, ``message`` is human-readable,
and ``detail`` carries per-error context (e.g. per-field validation errors). The
status↔code mapping lives in ``app.py``; ``fail`` defaults ``code`` to
``INTERNAL`` so legacy single-arg callers keep working.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class DataSource(str, Enum):
    """Canonical ``meta.data_source`` tokens — the single vocabulary every router
    tags a response with (doc 25 §5.4 / §5.1).

    Before this enum, seven uncoordinated string literals (``"pending"`` /
    ``"pending_m4"`` / ``"timescaledb"`` / ``"partial"`` / ``"parquet_scan"`` /
    ``"watch_registry"`` / ``"catalog"``) were scattered across routers; a typo
    silently shipped an un-renderable state to the frontend. Centralising them
    here lets ``check_openapi_drift.py`` Check D static-scan every ``data_source``
    assignment against this membership.

    Two lifecycle tokens (``PENDING`` / ``PARTIAL``) plus the live-source tokens:

    * ``PENDING``        — typed-empty envelope; the feature's producer has not landed
      (was both ``"pending"`` and the now-retired ``"pending_m4"`` — one concept).
    * ``PARTIAL``        — real data with an honestly-disclosed gap (e.g. WFA folds
      shipped while the per-fold scatter stays parquet-gated).
    * ``TIMESCALEDB``    — live paper/live telemetry read from TimescaleDB.
    * ``WATCH_REGISTRY`` — event-sourced Paper-Watch berths (JSONL registry).
    * ``PARQUET_SCAN``   — bundle-manifest scan over the parquet cache.
    * ``LEDGER``         — projection over the append-only runs ledger.
    * ``CATALOG``        — the curated FinLab dataset dictionary.
    """

    PENDING = "pending"
    PARTIAL = "partial"
    TIMESCALEDB = "timescaledb"
    WATCH_REGISTRY = "watch_registry"
    PARQUET_SCAN = "parquet_scan"
    LEDGER = "ledger"
    CATALOG = "catalog"


class ApiError(BaseModel):
    """Structured error body shared by every failure response."""

    code: str
    message: str
    detail: Any | None = None


class Envelope(BaseModel, Generic[T]):
    """The single response shape shared by every endpoint.

    Generic over the ``data`` payload: ``response_model=Envelope[RunRow]`` types
    the OpenAPI ``data`` schema (and the frontend's generated types) per endpoint.
    Unparametrised ``Envelope`` ≡ ``Envelope[Any]`` — the ``ok``/``fail``/``pending``
    helpers and any endpoint without a specific shape keep working untyped, with
    no field loss.
    """

    success: bool
    data: T | None = None
    error: ApiError | None = None
    meta: dict[str, Any] | None = None


def ok(data: Any = None, meta: dict[str, Any] | None = None) -> Envelope:
    """Build a success envelope (``error`` is always ``None``)."""
    return Envelope(success=True, data=data, error=None, meta=meta)


def fail(
    message: str,
    code: str = "INTERNAL",
    detail: Any | None = None,
    data: Any = None,
) -> Envelope:
    """Build an error envelope (``meta`` is always ``None``).

    ``code`` defaults to ``INTERNAL`` so legacy ``fail("msg")`` callers keep
    working; the exception handlers in ``app.py`` pass the contract code.
    """
    return Envelope(
        success=False,
        data=data,
        error=ApiError(code=code, message=message, detail=detail),
        meta=None,
    )


def page_meta(total: int, page: int, limit: int) -> dict[str, int]:
    """Pagination metadata block for list endpoints."""
    return {"total": total, "page": page, "limit": limit}


def pending(data: Any = None, ttl: int = 300) -> Envelope:
    """Typed-empty success envelope for endpoints awaiting persistence/logic.

    Carries the real response *shape* with ``meta.data_source = DataSource.PENDING``
    so the frontend can wire against the contract before the backend feature lands.
    Shared by the research/runs sub-routers split out in the M3 seam
    (research_validate / research_registry / runs_series). ``ttl`` defaults to 300 —
    the one default for the one pending concept (monitor's ``_stub`` matches).
    """
    return ok(data, meta={"data_source": DataSource.PENDING, "ttl": ttl})
