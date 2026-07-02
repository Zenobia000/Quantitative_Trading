"""workflow.universe — survivorship-clean universe build workflow (sub-project ②).

Drives ``run_build_universe`` with an injected fake FinLab getter (synthetic wide
frames) so the suite never imports finlab or hits the network. Asserts the selected
universe, the manifest contents, and that the ingest parquet landed in the cache.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from backtest_platform.data import finlab_source as fl
from backtest_platform.research.workflows.config import UniverseConfig
from backtest_platform.research.workflows.universe import (
    UniverseBuildResult,
    run_build_universe,
)

_COLS = ("BIG", "MID", "SMALL", "DEAD")
_DEAD_FROM = "2020-07-01"


def _fake_getter():
    """A ``finlab.data.get``-like callable over synthetic 2020 wide frames.

    ``DEAD`` delists mid-year (adj-close all NaN from 2020-07-01) so it is alive +
    liquid at the Q1/Q2 rebalances (→ in the survivorship-clean union) but not at
    the Q3/Q4 rebalances, and counts as delisted at span end.
    """
    idx = pd.date_range("2020-01-01", "2020-12-31", freq="B")
    cols = list(_COLS)
    close = pd.DataFrame(50.0, index=idx, columns=cols)
    close.loc[_DEAD_FROM:, "DEAD"] = np.nan
    mv = pd.DataFrame(
        {"BIG": 9e9, "MID": 5e9, "SMALL": 3e9, "DEAD": 4e9}, index=idx
    )
    turnover = pd.DataFrame(5e8, index=idx, columns=cols)  # all clear the 2e7 floor
    volume = pd.DataFrame(1e6, index=idx, columns=cols)
    flow = pd.DataFrame(1000.0, index=idx, columns=cols)

    key_map = {
        fl._MARKET_VALUE: mv,
        fl._TURNOVER: turnover,
        fl._VOLUME: volume,
        fl._ADJ["close"]: close,
        fl._ADJ["open"]: close * 0.99,
        fl._ADJ["high"]: close * 1.01,
        fl._ADJ["low"]: close * 0.98,
    }
    for k in (*fl._FOREIGN, *fl._TRUST, *fl._DEALER):
        key_map[k] = flow

    def getter(key: str) -> pd.DataFrame:
        return key_map[key].copy()

    return getter


def _cfg(cache_dir: Path) -> UniverseConfig:
    return UniverseConfig(
        strategy="inst_flow",
        span_start=date(2020, 1, 1),
        span_end=date(2020, 12, 31),
        top_n=10,
        min_turnover=2e7,
        cache_dir=str(cache_dir),
    )


# --- UniverseConfig -------------------------------------------------------- #
def test_universe_config_frozen_and_validated():
    cfg = _cfg(Path("data/parquet_finlab_universe"))
    assert cfg.strategy == "inst_flow"
    assert cfg.top_n == 10
    with pytest.raises(ValidationError):
        cfg.top_n = 5  # frozen


def test_universe_config_rejects_inverted_span():
    with pytest.raises(ValidationError):
        UniverseConfig(
            strategy="x", span_start=date(2024, 1, 1), span_end=date(2010, 1, 1),
            top_n=200, min_turnover=2e7, cache_dir="data/x",
        )


# --- run_build_universe ---------------------------------------------------- #
def test_run_build_universe_selects_survivorship_clean_set(tmp_path):
    cache = tmp_path / "cache"
    result = run_build_universe(_cfg(cache), getter=_fake_getter())
    assert isinstance(result, UniverseBuildResult)
    # DEAD is alive + liquid at Q1/Q2 → retained in the union despite delisting.
    assert set(result.universe) == {"BIG", "MID", "SMALL", "DEAD"}


def test_run_build_universe_counts_alive_and_delisted(tmp_path):
    result = run_build_universe(_cfg(tmp_path / "cache"), getter=_fake_getter())
    assert result.n_alive == 3        # BIG / MID / SMALL alive at span end
    assert result.n_delisted == 1     # DEAD delisted mid-year


def test_run_build_universe_ingests_all_selected(tmp_path):
    cache = tmp_path / "cache"
    result = run_build_universe(_cfg(cache), getter=_fake_getter())
    assert result.n_ingested_ok == 4
    assert result.n_ingested_failed == 0
    for sid in ("BIG", "MID", "SMALL", "DEAD"):
        assert (cache / f"daily_bars__{sid}.parquet").exists()


def test_run_build_universe_writes_manifest(tmp_path):
    cache = tmp_path / "cache"
    result = run_build_universe(_cfg(cache), getter=_fake_getter())
    manifest_path = Path(result.manifest_path)
    assert manifest_path == cache / "universe_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["strategy"] == "inst_flow"
    assert set(manifest["symbols"]) == {"BIG", "MID", "SMALL", "DEAD"}
    assert manifest["n_alive"] == 3
    assert manifest["n_delisted"] == 1
    assert manifest["ingest"]["ok"] == 4
    assert manifest["ingest"]["failed"] == 0
    assert manifest["params"]["top_n"] == 10
    assert manifest["params"]["rebalance"] == "quarterly"
    assert manifest["params"]["span_start"] == "2020-01-01"
    assert "generated_at" in manifest


def test_run_build_universe_surfaces_ingest_failures(tmp_path, monkeypatch):
    """Ingest failures must reach BOTH the result and the manifest — never swallowed.

    A selected symbol can only fail ingest on infrastructure grounds (write error,
    partial data), which consistent synthetic frames won't produce, so we inject a
    failing ``FinlabIngestResult`` at the ingest seam and assert it propagates.
    """
    import backtest_platform.research.workflows.universe as uni_mod
    from backtest_platform.data.finlab_source import FinlabIngestResult

    def fake_ingest(symbols, start, end, *, cache_dir=None, getter=None):
        syms = list(symbols)
        return FinlabIngestResult(ok_symbols=tuple(syms[:-1]), failed_symbols=(syms[-1],))

    monkeypatch.setattr(uni_mod, "ingest_universe_finlab", fake_ingest)

    cache = tmp_path / "cache"
    result = run_build_universe(_cfg(cache), getter=_fake_getter())
    manifest = json.loads((cache / "universe_manifest.json").read_text(encoding="utf-8"))

    assert result.n_ingested_failed == 1
    assert manifest["ingest"]["failed"] == 1
    assert len(manifest["ingest"]["failed_symbols"]) == 1
    assert result.n_ingested_ok == manifest["ingest"]["ok"] == len(result.universe) - 1
