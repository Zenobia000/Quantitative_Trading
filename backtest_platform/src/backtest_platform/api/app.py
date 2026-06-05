"""FastAPI application factory for the backtest-platform research API.

``create_app`` builds a fresh app each call (so tests get isolated instances and
dependency overrides), mounts the resource routers, and installs two exception
handlers that re-wrap FastAPI's default error responses in the project's uniform
``{success, data, error, meta}`` envelope — so a 404 or 422 looks like every
other response, never a bare ``{"detail": ...}``.

A module-level ``app = create_app()`` is provided for ``uvicorn
backtest_platform.api.app:app`` in production.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backtest_platform.api.envelope import Envelope, fail, ok
from backtest_platform.api.routers import gate, metrics, presets, research, runs

API_VERSION = "0.6.0"


def _format_validation_errors(errors: Sequence[dict[str, Any]]) -> str:
    """Collapse pydantic/FastAPI validation errors into one readable string."""
    parts = []
    for err in errors:
        loc = ".".join(str(p) for p in err.get("loc", ()))
        parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
    return "; ".join(parts)


def create_app() -> FastAPI:
    """Construct a fully-wired FastAPI app (routers + envelope error handlers)."""
    app = FastAPI(title="Backtest Platform Research API", version=API_VERSION)

    @app.get("/health", response_model=Envelope, tags=["health"])
    def health() -> Envelope:
        """Liveness probe — returns the API version."""
        return ok({"status": "ok", "version": API_VERSION})

    app.include_router(runs.router)
    app.include_router(gate.router)
    app.include_router(metrics.router)
    app.include_router(presets.router)
    app.include_router(research.router)

    @app.exception_handler(HTTPException)
    async def _http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(str(exc.detail)).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=fail(_format_validation_errors(exc.errors())).model_dump(),
        )

    return app


app = create_app()
