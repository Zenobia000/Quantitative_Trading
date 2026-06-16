"""GET /strategies — strategy catalog endpoint (ADR-028)."""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.research import runners as _runners  # noqa: F401 — registers all strategies
from backtest_platform.strategies.protocol import describe_strategies

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=Envelope)
def list_strategies_endpoint() -> Envelope:
    """Return all registered strategies with name, title, description, and config JSON-schema."""
    infos = describe_strategies()
    return ok([
        {
            "name": s.name,
            "title": s.title,
            "description": s.description,
            "config_schema": s.config_schema,
        }
        for s in infos
    ])
