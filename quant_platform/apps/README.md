# apps/

Deployable entrypoints (ADR-R05). Thin composition roots — wiring/DI only, no domain logic.

- `api/` — FastAPI composition root (from `backtest_platform/api/`; `app.py` stays the `backtest_platform.api.app:app` uvicorn/drift anchor via re-export shim).
- `web_console/` — React SPA (from `frontend/`; big-bang, moves last, needs quiet repo — collides with active frontend work).
- `workers/` — after-close daemon / cron entrypoints (from `services/strategy_runtime/{cli,after_close,paper_daemon}`).
