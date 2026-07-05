"""Tests for ``data.universe_registry`` — project universe manifests → UniverseRef.

Mirrors ``test_bundle_registry`` conventions: synthetic ``universe_manifest.json``
under ``tmp_path`` in the exact schema ``research.workflows.universe._write_manifest``
writes. No real data, no network. Covers the ADR-007 N:1 read-compat: a manifest may
carry the legacy singular ``strategy`` or the new plural ``strategies``.
"""
from __future__ import annotations

import json
from pathlib import Path

from backtest_platform.data.universe_registry import UniverseRef, list_universes

_UNIVERSE_MANIFEST = {
    "strategy": "inst_flow",
    "params": {
        "span_start": "2010-01-01",
        "span_end": "2024-12-31",
        "top_n": 200,
        "min_turnover": 50_000_000.0,
        "cache_dir": "data/parquet_finlab_universe",
    },
    "symbols": ["2330", "2317", "2454"],
    "n_symbols": 3,
    "n_alive": 2,
    "n_delisted": 1,
    "ingest": {"ok": 3, "failed": 0, "failed_symbols": []},
    "generated_at": "2026-07-02T00:00:00+00:00",
}

_DEFAULT_MANIFEST = {
    "schema_version": 1,
    "stocks": {"2330": {"start": "2020-01-02", "end": "2024-12-31", "rows": 1200, "data_hash": "a"}},
    "stock_count": 1,
    "coverage": {"start": "2020-01-02", "end": "2024-12-31"},
    "data_hash": "deadbeefcafef00d",
    "generated_at": "2026-07-01T00:00:00+00:00",
}


def _write(root: Path, dirname: str, filename: str, manifest: dict) -> Path:
    d = root / dirname
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(json.dumps(manifest), encoding="utf-8")
    return d


def test_missing_root_returns_empty(tmp_path):
    # typed-empty contract: never raises on an absent data root
    assert list_universes(tmp_path / "nope") == []


def test_default_bundles_are_excluded(tmp_path):
    # a default ETL cache is NOT a universe — must not surface here
    _write(tmp_path, "parquet", "manifest.json", _DEFAULT_MANIFEST)
    assert list_universes(tmp_path) == []


def test_universe_manifest_projects_to_ref(tmp_path):
    _write(tmp_path, "parquet_finlab_universe", "universe_manifest.json", _UNIVERSE_MANIFEST)
    refs = list_universes(tmp_path)
    assert len(refs) == 1
    ref = refs[0]
    assert isinstance(ref, UniverseRef)
    assert ref.id == "parquet_finlab_universe"
    assert ref.name == "parquet_finlab_universe"  # no explicit name → id
    assert ref.symbols_count == 3
    assert ref.span_start == "2010-01-01"
    assert ref.span_end == "2024-12-31"
    assert ref.top_n == 200
    assert ref.min_turnover == 50_000_000.0
    assert ref.cache_dir == "data/parquet_finlab_universe"
    assert ref.generated_at == "2026-07-02T00:00:00+00:00"


def test_legacy_singular_strategy_reads_as_one_element_list(tmp_path):
    # ADR-007 read-compat: legacy ``strategy: str`` → ``strategies == ("inst_flow",)``
    _write(tmp_path, "parquet_finlab_universe", "universe_manifest.json", _UNIVERSE_MANIFEST)
    (ref,) = list_universes(tmp_path)
    assert ref.strategies == ("inst_flow",)


def test_plural_strategies_list_is_preserved(tmp_path):
    # ADR-007 N:1: multiple strategies share one factor-agnostic universe
    manifest = {**_UNIVERSE_MANIFEST, "strategies": ["inst_flow", "reversal"]}
    del manifest["strategy"]
    _write(tmp_path, "parquet_shared", "universe_manifest.json", manifest)
    (ref,) = list_universes(tmp_path)
    assert ref.strategies == ("inst_flow", "reversal")


def test_explicit_name_wins_over_id(tmp_path):
    manifest = {**_UNIVERSE_MANIFEST, "name": "liquid-large-cap-top200"}
    _write(tmp_path, "parquet_finlab_universe", "universe_manifest.json", manifest)
    (ref,) = list_universes(tmp_path)
    assert ref.name == "liquid-large-cap-top200"


def test_no_strategy_field_yields_empty_tuple(tmp_path):
    manifest = {k: v for k, v in _UNIVERSE_MANIFEST.items() if k != "strategy"}
    _write(tmp_path, "parquet_orphan", "universe_manifest.json", manifest)
    (ref,) = list_universes(tmp_path)
    assert ref.strategies == ()


def test_corrupt_manifest_is_skipped_not_raised(tmp_path):
    d = tmp_path / "parquet_bad"
    d.mkdir(parents=True)
    (d / "universe_manifest.json").write_text("{not json", encoding="utf-8")
    assert list_universes(tmp_path) == []


def test_results_sorted_by_id(tmp_path):
    _write(tmp_path, "parquet_zeta", "universe_manifest.json", _UNIVERSE_MANIFEST)
    _write(tmp_path, "parquet_alpha", "universe_manifest.json", _UNIVERSE_MANIFEST)
    ids = [r.id for r in list_universes(tmp_path)]
    assert ids == ["parquet_alpha", "parquet_zeta"]
