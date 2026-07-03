"""``/system`` — System-zone endpoints (data management + alert config).

Most system data stores (bundle manifest, ingest jobs, alert history, channel
secrets) are not yet wired to a live source, so these ship as **typed-empty
stubs** tagged ``meta.data_source="pending"`` (ADR-021 §5.4) — stable shapes for
the frontend, no fabricated data. Secrets are always masked (``rules/security.md``):
``/system/alerts/channels`` never returns a real ``bot_token``.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from backtest_platform.api.deps import get_data_root
from backtest_platform.api.envelope import DataSource, Envelope, ok, page_meta
from backtest_platform.api.response_models import AlertRuleRow, RiskSpecData
from backtest_platform.jobs import job_store, submit
from backtest_platform.monitoring.alert_rules import rules_spec as _alert_rules_spec
from backtest_platform.risk.risk_gate import risk_spec as _risk_spec


class IngestRequest(BaseModel):
    """Trigger a bundle ingest as an async job (8.H.6)."""

    symbols: list[str] = Field(..., min_length=1)
    start: date
    end: date
    source: str = "finlab"  # "finlab" (ADR-006 primary) | "finmind" (fallback)


class UniverseBuildRequest(BaseModel):
    """Trigger a survivorship-clean universe build as an async job (ADR-032).

    Mirrors ``research.workflows.config.UniverseConfig`` — the params the
    ``build_universe`` workflow needs — and re-runs the same span-ordering gate at
    the API boundary so a bad window fails 422 here, not deep in the job thread.
    """

    strategy: str = Field(..., min_length=1)
    span_start: date
    span_end: date
    top_n: int = Field(..., ge=1, description="per-quarter top-N by market cap")
    min_turnover: float = Field(..., ge=0, description="trailing-20d avg turnover floor (TWD)")
    cache_dir: str = Field(..., min_length=1, description="dedicated parquet cache for this build")

    @model_validator(mode="after")
    def _span_ordered(self) -> UniverseBuildRequest:
        if self.span_start >= self.span_end:
            raise ValueError("span_start must be before span_end")
        return self


class BundleRow(BaseModel):
    """One discovered parquet bundle cache (``GET /system/bundles`` row)."""

    id: str
    path: str
    kind: str  # "default" | "universe"
    stock_count: int
    coverage_start: str | None = None
    coverage_end: str | None = None
    data_hash: str | None = None
    generated_at: str | None = None
    strategy: str | None = None


class BundleQuality(BaseModel):
    """Manifest-derived quality summary (``GET /system/bundles/{id}/quality``)."""

    id: str
    kind: str
    stock_count: int
    coverage_start: str | None = None
    coverage_end: str | None = None
    data_hash: str | None = None
    generated_at: str | None = None
    total_rows: int | None = None
    min_rows: int | None = None
    max_rows: int | None = None
    n_alive: int | None = None
    n_delisted: int | None = None
    n_ingested_ok: int | None = None
    n_ingested_failed: int | None = None


class DatasetCard(BaseModel):
    """One ``GET /system/datasets`` card — a strategy author's data-dictionary row.

    Answers the three authoring-first questions: *what is this data* (key / name /
    category / freq / history / description), *is it local* (``local`` binary), and
    *which of my strategies use it* (``used_by``). No freshness / coverage — that is
    a runtime concern, out of scope by design (see :mod:`data.finlab_catalog`)."""

    key: str
    name_zh: str
    category: str
    freq: str
    history_start: str
    description: str
    local: str  # "cached" | "not_cached"
    used_by: list[str]


router = APIRouter(prefix="/system", tags=["system"])


def _stub(
    data: Any, ttl: int = 300, *, total: int | None = None, page: int = 1, limit: int = 50
) -> Envelope:
    """Typed-empty stub (``DataSource.PENDING``); paginated stubs echo real page/limit."""
    meta: dict[str, Any] = {"data_source": DataSource.PENDING, "ttl": ttl}
    if total is not None:
        meta |= page_meta(total, page, limit)
    return ok(data, meta=meta)


# ---- risk spec (sys_alerts / mon_d config) ------------------------------
@router.get("/risk/spec", response_model=Envelope[RiskSpecData])
def risk_spec() -> Envelope:
    """The 12 ex-ante risk rules + active thresholds. Real config projection — this
    is rule *definitions* (not live telemetry), so it ships now, not at the M4 daemon."""
    return ok(_risk_spec())


@router.post("/risk/evaluate", response_model=Envelope)
def risk_evaluate() -> Envelope:
    return _stub({"results": []})


# ---- alerts (sys_alerts) ------------------------------------------------
@router.get("/alerts/rules", response_model=Envelope[list[AlertRuleRow]])
def alert_rules() -> Envelope:
    """The built-in §4.2 alert rules (real config projection). Rule definitions
    ship now; create/update (POST/PUT) and history stay pending on a rule store /
    the M4 producer."""
    rules = _alert_rules_spec()
    return ok(rules, meta={"total": len(rules), "page": 1, "limit": 50, "ttl": 300})


@router.get("/alerts/channels", response_model=Envelope)
def alert_channels() -> Envelope:
    # 秘密一律遮罩（rules/security.md §4）
    return _stub({"discord": {"enabled": False, "bot_token": "***"}})


@router.post("/alerts/test", response_model=Envelope)
def alert_test() -> Envelope:
    return _stub({"delivered": False})


@router.put("/alerts/channels", response_model=Envelope)
def alert_channels_put() -> Envelope:
    return _stub({"ok": True})


@router.post("/alerts/rules", response_model=Envelope)
def alert_rules_post() -> Envelope:
    return _stub({"id": "stub"})


@router.put("/alerts/rules", response_model=Envelope)
def alert_rules_put() -> Envelope:
    return _stub({"ok": True})


@router.get("/alerts/history", response_model=Envelope)
def alert_history(page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=500)) -> Envelope:
    """Alert history — offset-paginated (A3). No producer yet, so the slice is empty,
    but ``page``/``limit`` are echoed honestly rather than hard-coded."""
    return _stub([], total=0, page=page, limit=limit)


@router.post("/alerts/history/{event_id}/ack", response_model=Envelope)
def alert_ack(event_id: str) -> Envelope:
    return _stub({"id": event_id, "acked": True})


# ---- bundles / ingest (sys_data) ----------------------------------------
@router.get("/bundles", response_model=Envelope[list[BundleRow]])
def bundles(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    data_root: Path = Depends(get_data_root),
) -> Envelope:
    """Real bundle manifest scan (ADR-021 §5.4 → live). Discovers the default parquet
    cache + any ``data/parquet_*`` universe caches by their lineage manifests. Missing
    data root / corrupt manifests degrade to typed-empty (``data_source`` explains),
    never 500."""
    from backtest_platform.data.bundle_registry import scan_bundles

    try:
        infos = scan_bundles(data_root)
    except Exception:  # never let a data-dir hiccup 500 the API
        infos = []
    rows = [BundleRow(**asdict(i)) for i in infos]
    total = len(rows)
    start = (page - 1) * limit
    window = rows[start : start + limit]
    return ok(
        window,
        meta={"data_source": DataSource.PARQUET_SCAN, **page_meta(total, page, limit), "ttl": 300},
    )


@router.get("/bundles/{bundle_id}/quality", response_model=Envelope[BundleQuality])
def bundle_quality(bundle_id: str, data_root: Path = Depends(get_data_root)) -> Envelope:
    """Cheap manifest-derived quality for one bundle (row stats / alive-delisted /
    ingest tallies). Unknown id → **404 NOT_FOUND** (A4 — an unknown resource is an
    error, not a 200 with ``data:null``). The heavier per-column freshness/gap audit
    is left to a future producer."""
    from backtest_platform.data.bundle_registry import compute_bundle_quality

    try:
        info = compute_bundle_quality(bundle_id, data_root)
    except Exception:  # degrade, never 500
        info = None
    if info is None:
        raise HTTPException(status_code=404, detail={"resource": "bundle", "id": bundle_id})
    return ok(BundleQuality(**asdict(info)), meta={"data_source": DataSource.PARQUET_SCAN, "ttl": 300})


# ---- dataset catalog (sys_data) — authoring-first data dictionary --------
@router.get("/datasets", response_model=Envelope[list[DatasetCard]])
def datasets(
    category: str | None = Query(None, description="filter by category slug (exact)"),
    q: str | None = Query(None, description="case-insensitive substring on key / name_zh"),
    data_root: Path = Depends(get_data_root),
) -> Envelope:
    """The FinLab dataset catalog as authoring-first cards (:mod:`data.finlab_catalog`).

    Each card layers three request-time facts onto the curated snapshot: local
    presence (``data.dataset_presence`` — the honest three-table bundle binary),
    the strategy reverse-index (``data.strategy_data_index``), and the two author
    filters (``?category`` exact, ``?q`` substring on key/name). Deliberately no
    manifest read / staleness — the catalog is a data *dictionary*, not a cache
    monitor."""
    from backtest_platform.data.dataset_presence import presence_for_category
    from backtest_platform.data.finlab_catalog import CATALOG_VERSION, load_catalog
    from backtest_platform.data.strategy_data_index import (
        build_strategy_data_index,
        default_strategies_root,
    )

    specs = load_catalog()
    if category:
        specs = tuple(s for s in specs if s.category == category)
    if q:
        needle = q.casefold()
        specs = tuple(
            s for s in specs
            if needle in s.key.casefold() or needle in s.name_zh.casefold()
        )

    index = build_strategy_data_index(default_strategies_root())
    cards = [
        DatasetCard(
            key=s.key,
            name_zh=s.name_zh,
            category=s.category,
            freq=s.freq,
            history_start=s.history_start,
            description=s.description,
            local=presence_for_category(s.category, data_root),
            used_by=index.get(s.key, []),
        )
        for s in specs
    ]
    return ok(
        cards,
        meta={
            "catalog_version": CATALOG_VERSION,
            "data_source": DataSource.CATALOG,
            "total": len(cards),
            "ttl": 300,
        },
    )


@router.post("/ingest", response_model=Envelope, status_code=202)
def ingest(req: IngestRequest) -> Envelope:
    """Enqueue a bundle ingest as an async job (8.H.6); returns ``{job_id, status}``
    (202). The job runs the real ETL (FinLab/FinMind via ``make_ingest``) off-thread
    so the API never blocks; poll :func:`ingest_status`."""
    from backtest_platform.orchestration.collaborators import make_ingest

    ing = make_ingest(start=req.start, end=req.end, source=req.source)

    def _run() -> dict[str, Any]:
        result = ing(list(req.symbols))
        return {
            "requested": len(req.symbols),
            "ok": sorted(s for s, good in result.items() if good),
            "failed": sorted(s for s, good in result.items() if not good),
        }

    key = f"{req.source}|{req.start}|{req.end}|{','.join(req.symbols)}"
    job = submit("ingest", key, _run)
    return ok({"job_id": job.job_id, "status": job.status.value})


def _job_status(job_id: str) -> Envelope:
    """Shared async-job poll: real state, or **404 NOT_FOUND** if the id is unknown
    (A4 / doc 25 §5.2 — an unknown or expired job is an error, so pollers surface an
    error state instead of an infinite ``pending``)."""
    job = job_store.read_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"resource": "job", "id": job_id})
    return ok(job.to_dict())


@router.get("/ingest/{job_id}/status", response_model=Envelope)
def ingest_status(job_id: str) -> Envelope:
    """Poll an ingest job's status/result; 404 if the id is unknown."""
    return _job_status(job_id)


@router.post("/universe/build", response_model=Envelope, status_code=202)
def universe_build(req: UniverseBuildRequest) -> Envelope:
    """Enqueue a survivorship-clean universe build as an async job (ADR-032); returns
    ``{job_id, status}`` (202). Mirrors :func:`ingest` exactly — the job runs the real
    ``run_build_universe`` workflow (FinLab wide frames → point-in-time union → parquet
    cache + ``universe_manifest.json``) off-thread; poll :func:`universe_build_status`.

    The workflow is imported + called via its module at run time so a test can
    monkeypatch ``research.workflows.universe.run_build_universe`` and never touch
    FinLab / the network."""
    from backtest_platform.research.workflows import universe as _universe
    from backtest_platform.research.workflows.config import UniverseConfig

    def _run() -> dict[str, Any]:
        cfg = UniverseConfig(
            strategy=req.strategy,
            span_start=req.span_start,
            span_end=req.span_end,
            top_n=req.top_n,
            min_turnover=req.min_turnover,
            cache_dir=req.cache_dir,
        )
        result = _universe.run_build_universe(cfg)
        return {
            "strategy": result.strategy,
            "n_symbols": len(result.universe),
            "n_alive": result.n_alive,
            "n_delisted": result.n_delisted,
            "n_ingested_ok": result.n_ingested_ok,
            "n_ingested_failed": result.n_ingested_failed,
            "manifest_path": result.manifest_path,
        }

    key = f"{req.strategy}|{req.span_start}|{req.span_end}|{req.top_n}|{req.min_turnover}|{req.cache_dir}"
    job = submit("universe_build", key, _run)
    return ok({"job_id": job.job_id, "status": job.status.value})


@router.get("/universe/build/{job_id}/status", response_model=Envelope)
def universe_build_status(job_id: str) -> Envelope:
    """Poll a universe-build job's status/result; 404 if the id is unknown."""
    return _job_status(job_id)
