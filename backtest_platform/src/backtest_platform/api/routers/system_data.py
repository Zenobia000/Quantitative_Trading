"""``/system`` data-platform endpoints — bundles, universes, datasets, ingest.

Split out of the former ``system.py`` monolith (W6.1a). Bundle/universe scans and
the dataset catalog are **real** projections (parquet manifest scan / FinLab
catalog); ingest and universe-build enqueue real async jobs. Missing/corrupt data
roots degrade to typed-empty (``data_source`` explains), never 500 (ADR-021 §5.4).
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
from backtest_platform.jobs import job_store, submit


class IngestRequest(BaseModel):
    """Trigger a bundle ingest as an async job (8.H.6).

    ``symbols`` is optional (ADR-007 Slice 4): an empty/omitted list resolves to the
    named ``universe`` if provided, else the system default universe, so the
    data-dictionary "download to local" one-click can fire without the user
    re-typing a symbol list."""

    symbols: list[str] = Field(default_factory=list)
    universe: str | None = Field(
        None,
        description="Named universe id (GET /system/universes); resolved server-side. "
        "Ignored when `symbols` is non-empty.",
    )
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
    # Eligibility (ADR-007 Slice 3) — opt-in, mirror UniverseConfig.
    exchange: str | None = Field(
        None, description="board filter via finlab set_universe ('TWSE' | 'TPEx'); None = ALL"
    )
    exclude_flagged: bool = Field(
        False, description="exclude 全額交割/處置/注意 names as-of each rebalance"
    )

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


class UniverseRow(BaseModel):
    """One ``GET /system/universes`` row — a named, selectable universe (ADR-007).

    Projects ``universe_manifest.json`` so the New Run form can *select* a
    survivorship-clean population by name (SPEC-01 Slice 2) instead of re-typing raw
    symbols, and so a strategy can *reference* it (N:1 via ``strategies``)."""

    id: str
    name: str
    symbols_count: int
    span_start: str | None = None
    span_end: str | None = None
    top_n: int | None = None
    min_turnover: float | None = None
    strategies: list[str] = Field(default_factory=list)
    cache_dir: str
    generated_at: str | None = None


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
    # True → this category lands in a local parquet bundle (downloadable); False →
    # fetch-at-runtime only via ``data.get`` (財報/月營收/融資融券). Lets the UI stop
    # showing a misleading "not_cached" grey for data that never caches (ADR-007 Q1).
    bundle_backed: bool


router = APIRouter(prefix="/system", tags=["system"])


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


# ---- universes (sys_data) — named, selectable survivorship-clean pools ---
@router.get("/universes", response_model=Envelope[list[UniverseRow]])
def universes(data_root: Path = Depends(get_data_root)) -> Envelope:
    """List named universes discovered from ``universe_manifest.json`` (ADR-007).

    A thin projection over ``data.universe_registry.list_universes`` — the read model
    the New Run form selects from (SPEC-01 Slice 2) and strategies reference (N:1).
    Missing data root / corrupt manifests degrade to typed-empty (``data_source``
    explains), never 500 — mirrors :func:`bundles`."""
    from backtest_platform.data.universe_registry import list_universes

    try:
        refs = list_universes(data_root)
    except Exception:  # never let a data-dir hiccup 500 the API
        refs = []
    rows = [UniverseRow(**asdict(r)) for r in refs]
    return ok(
        rows,
        meta={"data_source": DataSource.PARQUET_SCAN, "total": len(rows), "ttl": 300},
    )


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
    from backtest_platform.data.dataset_presence import (
        presence_for_category,
        table_for_category,
    )
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
            bundle_backed=table_for_category(s.category) is not None,
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
    from backtest_platform.config.universe import DEFAULT_UNIVERSE
    from backtest_platform.data.universe_registry import symbols_for
    from backtest_platform.orchestration.collaborators import make_ingest

    # ADR-007 Slice 4: explicit symbols > named universe > system default universe.
    symbols = list(req.symbols)
    if not symbols:
        if req.universe:
            resolved = symbols_for(req.universe)
            if resolved is None:
                raise HTTPException(
                    status_code=422,
                    detail={"resource": "universe", "id": req.universe},
                )
            symbols = list(resolved)
        else:
            symbols = list(DEFAULT_UNIVERSE)
    ing = make_ingest(start=req.start, end=req.end, source=req.source)

    def _run() -> dict[str, Any]:
        result = ing(symbols)
        return {
            "requested": len(symbols),
            "ok": sorted(s for s, good in result.items() if good),
            "failed": sorted(s for s, good in result.items() if not good),
        }

    pool_key = req.universe or "default"
    key = f"{req.source}|{req.start}|{req.end}|{pool_key}|{','.join(symbols)}"
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
            exchange=req.exchange,
            exclude_flagged=req.exclude_flagged,
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
