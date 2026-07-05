"""REST API (FastAPI) — v0.6 Wave B.

Exposes the research-loop + validation backend (runs ledger, the gate審判庭,
performance metrics, strategy presets) over HTTP per dev_docs/21 §8 / ADR-015.

The package is a thin adapter layer: routers translate HTTP ↔ the pure backend
modules (``research`` + ``validation``), and every response is wrapped in the
uniform ``{success, data, error, meta}`` envelope (rules/patterns.md §API 回應格式).
No business logic lives here — only request validation, serialization, and the
dependency wiring that lets tests inject a temp ledger / stub executor.
"""
from __future__ import annotations

from backtest_platform.api.app import API_VERSION, create_app

__all__ = ["API_VERSION", "create_app"]
