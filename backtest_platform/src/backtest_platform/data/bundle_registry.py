"""Bundle registry — discover parquet data caches from their lineage manifests.

The platform writes two kinds of provenance sidecar next to a parquet cache:

* ``manifest.json`` — the default FinMind/FinLab ETL cache
  (``data.parquet_cache.write_manifest``): aggregate
  ``stock_count`` / ``coverage`` / ``data_hash`` over the ingested symbols.
* ``universe_manifest.json`` — a survivorship-clean universe build
  (``research.workflows.universe._write_manifest``, ADR-032): the strategy, the
  point-in-time span, the selected symbols and the ingest ok/failed counts.

This module scans a data root for ``parquet*`` cache dirs, reads whichever
manifest each carries, and normalises both schemas into a single ``BundleInfo``
row — the read model behind ``GET /system/bundles``. It is pure filesystem + JSON
with ZERO heavy dependencies, and is defensive by construction: a missing root,
an unreadable dir or a corrupt manifest is skipped, never raised, so the API
degrades to typed-empty rather than 500 (ADR-021 §5.4).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: Default root holding the parquet caches. Mirrors the parent of
#: ``finlab_source._DEFAULT_CACHE_DIR`` (``data/parquet``); universe builds land in
#: siblings like ``data/parquet_finlab_universe``. Relative to cwd, exactly like
#: every other ``data/parquet`` reference in the codebase — no absolute paths.
DEFAULT_DATA_ROOT = Path("data")

#: Only these prefixed subdirs of the data root are treated as bundle caches.
_CACHE_GLOB = "parquet*"

_DEFAULT_MANIFEST_NAME = "manifest.json"
_UNIVERSE_MANIFEST_NAME = "universe_manifest.json"

_KIND_DEFAULT = "default"
_KIND_UNIVERSE = "universe"


@dataclass(frozen=True, slots=True)
class BundleInfo:
    """One discovered bundle cache — the ``GET /system/bundles`` row shape."""

    id: str
    path: str
    kind: str  # "default" | "universe"
    stock_count: int
    coverage_start: str | None
    coverage_end: str | None
    data_hash: str | None
    generated_at: str | None
    strategy: str | None = None


@dataclass(frozen=True, slots=True)
class BundleQualityInfo:
    """Cheap manifest-derived quality summary (``/system/bundles/{id}/quality``).

    Every field is read straight out of the manifest (no parquet re-scan), so this
    stays O(1)-ish per bundle. Row stats are populated for default caches; the
    alive/delisted + ingest tallies for universe builds.
    """

    id: str
    kind: str
    stock_count: int
    coverage_start: str | None
    coverage_end: str | None
    data_hash: str | None
    generated_at: str | None
    total_rows: int | None = None
    min_rows: int | None = None
    max_rows: int | None = None
    n_alive: int | None = None
    n_delisted: int | None = None
    n_ingested_ok: int | None = None
    n_ingested_failed: int | None = None


def _load_manifest(path: Path) -> dict | None:
    """Read a manifest JSON object, or None on any read/parse failure."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _resolve_manifest(cache_dir: Path) -> tuple[str, dict] | None:
    """Return ``(kind, manifest)`` for a cache dir, universe manifest taking priority.

    A universe build only writes ``universe_manifest.json`` (its per-symbol ingest
    reuses ``write_parquet`` but not ``write_manifest``), so the two rarely coexist;
    if they do, the richer universe provenance wins and the dir yields one bundle.
    """
    uni = cache_dir / _UNIVERSE_MANIFEST_NAME
    if uni.is_file():
        manifest = _load_manifest(uni)
        if manifest is not None:
            return _KIND_UNIVERSE, manifest
    default = cache_dir / _DEFAULT_MANIFEST_NAME
    if default.is_file():
        manifest = _load_manifest(default)
        if manifest is not None:
            return _KIND_DEFAULT, manifest
    return None


def _to_bundle_info(cache_dir: Path, kind: str, manifest: dict) -> BundleInfo:
    """Normalise either manifest schema into a single :class:`BundleInfo`."""
    if kind == _KIND_UNIVERSE:
        params = manifest.get("params") or {}
        symbols = manifest.get("symbols") or []
        return BundleInfo(
            id=cache_dir.name,
            path=str(cache_dir),
            kind=_KIND_UNIVERSE,
            stock_count=int(manifest.get("n_symbols", len(symbols))),
            coverage_start=params.get("span_start"),
            coverage_end=params.get("span_end"),
            data_hash=None,  # universe manifest carries no aggregate data hash
            generated_at=manifest.get("generated_at"),
            strategy=manifest.get("strategy"),
        )
    stocks = manifest.get("stocks") or {}
    coverage = manifest.get("coverage") or {}
    return BundleInfo(
        id=cache_dir.name,
        path=str(cache_dir),
        kind=_KIND_DEFAULT,
        stock_count=int(manifest.get("stock_count", len(stocks))),
        coverage_start=coverage.get("start"),
        coverage_end=coverage.get("end"),
        data_hash=manifest.get("data_hash"),
        generated_at=manifest.get("generated_at"),
        strategy=None,
    )


def _to_quality(cache_dir: Path, kind: str, manifest: dict) -> BundleQualityInfo:
    """Derive a cheap quality summary from the manifest (no parquet re-scan)."""
    base = _to_bundle_info(cache_dir, kind, manifest)
    common = {
        "id": base.id,
        "kind": base.kind,
        "stock_count": base.stock_count,
        "coverage_start": base.coverage_start,
        "coverage_end": base.coverage_end,
        "data_hash": base.data_hash,
        "generated_at": base.generated_at,
    }
    if kind == _KIND_UNIVERSE:
        ingest = manifest.get("ingest") or {}
        return BundleQualityInfo(
            **common,
            n_alive=manifest.get("n_alive"),
            n_delisted=manifest.get("n_delisted"),
            n_ingested_ok=ingest.get("ok"),
            n_ingested_failed=ingest.get("failed"),
        )
    stocks = manifest.get("stocks") or {}
    row_counts = [int(v.get("rows", 0)) for v in stocks.values() if isinstance(v, dict)]
    return BundleQualityInfo(
        **common,
        total_rows=sum(row_counts) if row_counts else None,
        min_rows=min(row_counts) if row_counts else None,
        max_rows=max(row_counts) if row_counts else None,
    )


def _iter_cache_dirs(data_root: Path):
    """Yield ``parquet*`` subdirs of ``data_root`` (sorted; empty if root absent)."""
    if not data_root.is_dir():
        return
    for entry in sorted(data_root.glob(_CACHE_GLOB)):
        if entry.is_dir():
            yield entry


def scan_bundles(data_root: Path | None = None) -> list[BundleInfo]:
    """Discover every parquet bundle cache under ``data_root`` (default ``data/``).

    Returns one :class:`BundleInfo` per cache dir that carries a readable manifest,
    sorted by id. Never raises: a missing root or a corrupt manifest yields fewer
    (or zero) rows so the caller can serve a typed-empty envelope.
    """
    root = data_root if data_root is not None else DEFAULT_DATA_ROOT
    bundles: list[BundleInfo] = []
    for cache_dir in _iter_cache_dirs(root):
        resolved = _resolve_manifest(cache_dir)
        if resolved is None:
            continue
        kind, manifest = resolved
        try:
            bundles.append(_to_bundle_info(cache_dir, kind, manifest))
        except (TypeError, ValueError):
            continue  # malformed manifest field — skip this cache, never abort
    return bundles


def compute_bundle_quality(
    bundle_id: str, data_root: Path | None = None
) -> BundleQualityInfo | None:
    """Manifest-derived quality summary for one bundle, or None if not found.

    Cheap by design — read straight from the manifest, no parquet re-scan (that
    heavier per-column freshness/gap audit is left for a future producer).
    """
    root = data_root if data_root is not None else DEFAULT_DATA_ROOT
    for cache_dir in _iter_cache_dirs(root):
        if cache_dir.name != bundle_id:
            continue
        resolved = _resolve_manifest(cache_dir)
        if resolved is None:
            return None
        kind, manifest = resolved
        try:
            return _to_quality(cache_dir, kind, manifest)
        except (TypeError, ValueError):
            return None
    return None
