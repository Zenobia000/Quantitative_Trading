"""Tests for `data/finmind_bundle.py` — universe + cache-dir resolution.

The zipline daily-bar normalizers (`_to_zipline_daily_frame` / `_build_asset_metadata`
/ `_iter_daily_bars`) were removed with the engines/ tree (ADR-037); only the
data-layer ingest helpers remain here.
"""
from __future__ import annotations

from quant_platform.services.data_platform.finmind_bundle import (
    DEFAULT_UNIVERSE,
    _resolve_cache_dir,
    _resolve_universe,
)

# ===== _resolve_universe =====


def test_resolve_universe_default_when_no_env():
    assert _resolve_universe({}) == list(DEFAULT_UNIVERSE)


def test_resolve_universe_env_var_overrides_default():
    universe = _resolve_universe({"UNIVERSE_FINMIND": "2330,2454,2317"})
    assert universe == ["2330", "2454", "2317"]


def test_resolve_universe_env_var_handles_whitespace():
    universe = _resolve_universe({"UNIVERSE_FINMIND": " 2330 , 2454 ,  ,2317 "})
    assert universe == ["2330", "2454", "2317"]


def test_resolve_universe_file_path(tmp_path):
    f = tmp_path / "universe.txt"
    f.write_text("2330\n2454\n# 註解\n  \n2317\n", encoding="utf-8")
    universe = _resolve_universe({"UNIVERSE_FILE": str(f)})
    # Implementation does not strip comments; current behavior keeps them
    assert "2330" in universe
    assert "2454" in universe
    assert "2317" in universe


# ===== _resolve_cache_dir =====


def test_resolve_cache_dir_default():
    from quant_platform.services.data_platform.finmind_bundle import DEFAULT_CACHE_DIR

    assert _resolve_cache_dir({}) == DEFAULT_CACHE_DIR


def test_resolve_cache_dir_env_override(tmp_path):
    assert _resolve_cache_dir({"FINMIND_PARQUET_CACHE": str(tmp_path)}) == tmp_path
