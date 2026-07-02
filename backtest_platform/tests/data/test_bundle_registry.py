"""Tests for ``data.bundle_registry`` — scan parquet caches → bundle entries.

Uses ``tmp_path`` with synthetic manifests written in the exact schemas produced by
``engines.zipline_adapter.bundles.parquet_cache.write_manifest`` (default cache) and
``research.workflows.universe._write_manifest`` (survivorship universe build). No real
data, no network.
"""
from __future__ import annotations

import json
from pathlib import Path

from backtest_platform.data.bundle_registry import (
    compute_bundle_quality,
    scan_bundles,
)

_DEFAULT_MANIFEST = {
    "schema_version": 1,
    "stocks": {
        "2330": {"start": "2020-01-02", "end": "2024-12-31", "rows": 1200, "data_hash": "aaa"},
        "2317": {"start": "2020-01-02", "end": "2024-12-31", "rows": 1100, "data_hash": "bbb"},
    },
    "stock_count": 2,
    "coverage": {"start": "2020-01-02", "end": "2024-12-31"},
    "data_hash": "deadbeefcafef00d",
    "generated_at": "2026-07-01T00:00:00+00:00",
}

_UNIVERSE_MANIFEST = {
    "strategy": "inst_flow",
    "params": {
        "span_start": "2010-01-01",
        "span_end": "2024-12-31",
        "top_n": 200,
        "min_turnover": 50_000_000.0,
        "rebalance": "quarterly",
        "n_rebalances": 60,
        "cache_dir": "data/parquet_finlab_universe",
    },
    "symbols": ["2330", "2317", "2454"],
    "n_symbols": 3,
    "n_alive": 2,
    "n_delisted": 1,
    "ingest": {"ok": 3, "failed": 0, "failed_symbols": []},
    "generated_at": "2026-07-02T00:00:00+00:00",
}


def _write(root: Path, dirname: str, filename: str, manifest: dict) -> Path:
    d = root / dirname
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(json.dumps(manifest), encoding="utf-8")
    return d


def test_scan_missing_root_returns_empty(tmp_path):
    # never raises, even when the data root does not exist (typed-empty contract)
    assert scan_bundles(tmp_path / "does_not_exist") == []


def test_scan_default_manifest_maps_to_bundle(tmp_path):
    _write(tmp_path, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    bundles = scan_bundles(tmp_path)
    assert len(bundles) == 1
    b = bundles[0]
    assert b.id == "parquet"
    assert b.kind == "default"
    assert b.stock_count == 2
    assert b.coverage_start == "2020-01-02"
    assert b.coverage_end == "2024-12-31"
    assert b.data_hash == "deadbeefcafef00d"
    assert b.strategy is None
    assert b.path.endswith("parquet")


def test_scan_universe_manifest_maps_to_bundle(tmp_path):
    _write(tmp_path, "parquet_finlab_universe", "universe_manifest.json", _UNIVERSE_MANIFEST)
    bundles = scan_bundles(tmp_path)
    assert len(bundles) == 1
    b = bundles[0]
    assert b.id == "parquet_finlab_universe"
    assert b.kind == "universe"
    assert b.stock_count == 3
    assert b.coverage_start == "2010-01-01"
    assert b.coverage_end == "2024-12-31"
    assert b.strategy == "inst_flow"
    assert b.data_hash is None  # universe manifest carries no aggregate hash


def test_scan_finds_both_caches_sorted_by_id(tmp_path):
    _write(tmp_path, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    _write(tmp_path, "parquet_finlab_universe", "universe_manifest.json", _UNIVERSE_MANIFEST)
    bundles = scan_bundles(tmp_path)
    assert [b.id for b in bundles] == ["parquet", "parquet_finlab_universe"]
    assert [b.kind for b in bundles] == ["default", "universe"]


def test_scan_only_globs_parquet_prefixed_dirs(tmp_path):
    # a non-parquet sibling dir with a manifest must be ignored
    _write(tmp_path, "reports", "manifest.json", _DEFAULT_MANIFEST)
    _write(tmp_path, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    bundles = scan_bundles(tmp_path)
    assert [b.id for b in bundles] == ["parquet"]


def test_scan_skips_corrupt_manifest_without_raising(tmp_path):
    d = tmp_path / "parquet"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text("{ not valid json", encoding="utf-8")
    # corrupt manifest is skipped, not fatal
    assert scan_bundles(tmp_path) == []


def test_universe_manifest_takes_precedence_when_both_present(tmp_path):
    d = _write(tmp_path, "parquet_mixed", "manifest.json", _DEFAULT_MANIFEST)
    (d / "universe_manifest.json").write_text(json.dumps(_UNIVERSE_MANIFEST), encoding="utf-8")
    bundles = scan_bundles(tmp_path)
    assert len(bundles) == 1
    assert bundles[0].kind == "universe"


def test_quality_default_derives_row_stats(tmp_path):
    _write(tmp_path, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    q = compute_bundle_quality("parquet", tmp_path)
    assert q is not None
    assert q.kind == "default"
    assert q.stock_count == 2
    assert q.total_rows == 2300
    assert q.min_rows == 1100
    assert q.max_rows == 1200
    assert q.data_hash == "deadbeefcafef00d"


def test_quality_universe_derives_alive_delisted_ingest(tmp_path):
    _write(tmp_path, "parquet_finlab_universe", "universe_manifest.json", _UNIVERSE_MANIFEST)
    q = compute_bundle_quality("parquet_finlab_universe", tmp_path)
    assert q is not None
    assert q.kind == "universe"
    assert q.n_alive == 2
    assert q.n_delisted == 1
    assert q.n_ingested_ok == 3
    assert q.n_ingested_failed == 0


def test_quality_unknown_bundle_returns_none(tmp_path):
    _write(tmp_path, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    assert compute_bundle_quality("ghost", tmp_path) is None
