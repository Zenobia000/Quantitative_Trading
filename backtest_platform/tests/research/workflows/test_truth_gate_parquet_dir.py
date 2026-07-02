"""truth_gate parquet_dir wiring (sub-project ②) — config override reaches the loader.

``TruthGateConfig.parquet_dir`` lets a strategy point the truth gate at a dedicated
cache (e.g. the survivorship-clean FinLab universe) without callers passing a loader.
``run_truth_gate(cfg)`` with no explicit loader must resolve reads to that directory.
"""
from __future__ import annotations

import functools
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_platform.data.finmind_etl import write_parquet
from backtest_platform.data.schemas import ETLBundle
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import TruthGateConfig
from backtest_platform.research.workflows.truth_gate import (
    TruthGateResult,
    _resolve_loader,
    run_truth_gate,
)
from backtest_platform.strategies.momentum.strategy import MomentumConfig


def _cfg(parquet_dir: str | None, symbols):
    return TruthGateConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(lookback_days=120),
        symbols=symbols,
        is_start=date(2015, 1, 1),
        oos_start=date(2020, 1, 1),
        is_end=date(2022, 12, 31),
        n_trials=8,
        n_wfa_folds=3,
        parquet_dir=parquet_dir,
    )


def test_config_parquet_dir_defaults_none():
    assert _cfg(None, ["2330"]).parquet_dir is None


def test_config_parquet_dir_can_be_set():
    assert _cfg("data/parquet_finlab_universe", ["2330"]).parquet_dir == (
        "data/parquet_finlab_universe"
    )


# --- _resolve_loader ------------------------------------------------------- #
def test_resolve_loader_explicit_wins():
    sentinel = lambda s: pd.DataFrame()  # noqa: E731
    assert _resolve_loader(_cfg("whatever", ["2330"]), sentinel) is sentinel


def test_resolve_loader_default_when_no_parquet_dir():
    assert _resolve_loader(_cfg(None, ["2330"]), None) is load_merged_parquet


def test_resolve_loader_binds_parquet_dir():
    resolved = _resolve_loader(_cfg("/tmp/some_cache", ["2330"]), None)
    assert isinstance(resolved, functools.partial)
    assert resolved.func is load_merged_parquet
    assert resolved.keywords["parquet_dir"] == "/tmp/some_cache"


# --- integration: run_truth_gate reads from parquet_dir -------------------- #
def _write_synth_parquet(root: Path, symbols, start: date, end: date, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="B")
    n = len(dates)
    trade_dates = [d.date() for d in dates]
    for sid in symbols:
        close = 100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
        daily = pd.DataFrame({
            "stock_id": sid, "trade_date": trade_dates,
            "open": close, "high": close * 1.01, "low": close * 0.99,
            "close": close, "volume": rng.integers(1_000_000, 9_000_000, n),
            "adj_factor": 1.0,
        })
        inst = pd.DataFrame({
            "stock_id": sid, "trade_date": trade_dates,
            "foreign_buy": rng.integers(-100_000, 100_000, n),
            "trust_buy": rng.integers(-50_000, 50_000, n),
            "dealer_buy": rng.integers(-30_000, 30_000, n),
        })
        chips = pd.DataFrame({"stock_id": sid, "trade_date": trade_dates})
        write_parquet(
            ETLBundle(
                stock_id=sid, start_date=start, end_date=end,
                daily_bars=daily, institutional=inst, broker_chips=chips,
            ),
            root,
        )


def test_run_truth_gate_reads_from_parquet_dir(tmp_path):
    """No explicit loader → cfg.parquet_dir must route reads to the tmp cache.

    The default ``data/parquet`` cache does not contain these synthetic symbols, so
    a wrong resolution would raise FileNotFoundError — a returned result proves the
    parquet_dir override reached the loader.
    """
    symbols = ["SYNA", "SYNB", "SYNC"]
    _write_synth_parquet(tmp_path, symbols, date(2015, 1, 1), date(2022, 12, 31))
    result = run_truth_gate(_cfg(str(tmp_path), symbols))  # no explicit loader
    assert isinstance(result, TruthGateResult)
    assert result.verdict in ("REAL", "REJECTED", "INCOMPLETE")
