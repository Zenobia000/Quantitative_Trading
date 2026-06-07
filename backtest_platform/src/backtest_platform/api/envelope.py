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

from typing import Any

from pydantic import BaseModel


class ApiError(BaseModel):
    """Structured error body shared by every failure response."""

    code: str
    message: str
    detail: Any | None = None


class Envelope(BaseModel):
    """The single response shape shared by every endpoint."""

    success: bool
    data: Any | None = None
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
