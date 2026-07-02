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
from backtest_platform.api.routers import (
    gate,
    home,
    metrics,
    monitor,
    research,
    research_promote,
    research_registry,
    research_sweep,
    research_validate,
    research_workflows,
    runs,
    runs_series,
    runs_tags,
    strategies,
    system,
    watch,
)

API_VERSION = "0.6.0"

#: HTTP status → contract error code (doc 25 §2, one-to-one). Anything unmapped
#: (incl. 500) falls back to ``INTERNAL``.
_STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    404: "NOT_FOUND",
    409: "IS_GATE_NOT_PASSED",
    422: "VALIDATION_ERROR",
    423: "OOS_VAULT_LOCKED",
    504: "QUERY_TIMEOUT",
}


def _format_validation_errors(errors: Sequence[dict[str, Any]]) -> str:
    """Collapse pydantic/FastAPI validation errors into one readable string."""
    parts = []
    for err in errors:
        loc = ".".join(str(p) for p in err.get("loc", ()))
        parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
    return "; ".join(parts)


def _validation_detail(errors: Sequence[dict[str, Any]]) -> list[dict[str, str]]:
    """Per-field ``[{loc, msg}]`` detail for VALIDATION_ERROR (doc 25 §2)."""
    return [
        {"loc": ".".join(str(p) for p in err.get("loc", ())), "msg": str(err.get("msg"))}
        for err in errors
    ]


def create_app() -> FastAPI:
    """Construct a fully-wired FastAPI app (routers + envelope error handlers)."""
    app = FastAPI(title="Backtest Platform Research API", version=API_VERSION)

    @app.get("/health", response_model=Envelope, tags=["health"])
    def health() -> Envelope:
        """Liveness probe — returns the API version."""
        return ok({"status": "ok", "version": API_VERSION})

    app.include_router(runs.router)
    app.include_router(runs_series.router)  # M3 seam: S4 computed series (8.H.3)
    app.include_router(runs_tags.router)  # M3 seam: S5 run tagging (8.H.4)
    app.include_router(gate.router)
    app.include_router(metrics.router)
    app.include_router(strategies.router)  # GET /strategies — replaces GET /presets (ADR-028)
    app.include_router(research.router)
    app.include_router(research_validate.router)  # M3 seam: S3 validate (8.H.7)
    app.include_router(research_promote.router)  # M3 seam: S3 promote (8.H.7)
    app.include_router(research_registry.router)  # M3 seam: S5 saved-views/trials (8.H.4/5)
    app.include_router(research_sweep.router)  # M3 seam: S2 async sweep (8.H.6)
    app.include_router(research_workflows.router)  # ADR-029: research workflow jobs (①.5)
    app.include_router(monitor.router)
    app.include_router(watch.router)  # ADR-033: Paper-Watch 觀察艙 overview + pause/resume
    app.include_router(system.router)
    app.include_router(home.router)

    @app.exception_handler(HTTPException)
    async def _http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "INTERNAL")
        # A dict detail (e.g. {"resource", "id"}) becomes the structured ``detail``;
        # its optional ``message`` key is lifted out as the human-readable message.
        if isinstance(exc.detail, dict):
            message = str(exc.detail.get("message", code.replace("_", " ").lower()))
            detail = {k: v for k, v in exc.detail.items() if k != "message"} or None
        else:
            message, detail = str(exc.detail), None
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(message, code=code, detail=detail).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=fail(
                _format_validation_errors(exc.errors()),
                code="VALIDATION_ERROR",
                detail=_validation_detail(exc.errors()),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Global fallback: never leak stack/secrets (rules/security.md §錯誤訊息).
        return JSONResponse(
            status_code=500,
            content=fail("internal server error", code="INTERNAL").model_dump(),
        )

    return app


app = create_app()
