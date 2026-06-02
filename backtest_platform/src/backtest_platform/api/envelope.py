"""Uniform API response envelope (rules/patterns.md §API 回應格式).

Every endpoint returns the same shape — ``{success, data, error, meta}``:

* ``success`` — boolean status flag.
* ``data``    — the payload (``null`` on error).
* ``error``   — a human-readable message (``null`` on success).
* ``meta``    — optional metadata (pagination: ``total`` / ``page`` / ``limit``).

Centralizing the contract here keeps every router consistent and lets the
frontend rely on a single response shape regardless of which endpoint it hit.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Envelope(BaseModel):
    """The single response shape shared by every endpoint."""

    success: bool
    data: Any | None = None
    error: str | None = None
    meta: dict[str, Any] | None = None


def ok(data: Any = None, meta: dict[str, Any] | None = None) -> Envelope:
    """Build a success envelope (``error`` is always ``None``)."""
    return Envelope(success=True, data=data, error=None, meta=meta)


def fail(error: str, data: Any = None) -> Envelope:
    """Build an error envelope (``meta`` is always ``None``)."""
    return Envelope(success=False, data=data, error=error, meta=None)


def page_meta(total: int, page: int, limit: int) -> dict[str, int]:
    """Pagination metadata block for list endpoints."""
    return {"total": total, "page": page, "limit": limit}
