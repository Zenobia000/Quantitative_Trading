"""reversal research_config — the TRUTH_GATE declaration tracks the FinLab cache.

ADR-030 anti-self-deception: the survivorship-clean claim must follow the *evidence*.
When the FinLab survivorship universe cache exists, TRUTH_GATE declares it clean and
points at that cache; when absent, it falls back to the survivor-only ``_WIDE`` set
with ``survivorship_clean`` left False so the truth gate hard-fails until rebuilt.

The module resolves this at import time from ``cached_universe_symbols`` on a relative
path, so we drive the two states by controlling the working directory + reloading.
"""
from __future__ import annotations

import importlib
import os
from datetime import date


def _reload_reversal_config():
    from backtest_platform.strategies.reversal import research_config as rc
    return importlib.reload(rc)


def test_grid_is_twelve_configs():
    orig = os.getcwd()
    try:
        os.chdir(orig)
        mod = _reload_reversal_config()
        # 2 (rebalance) × 3 (lookback) × 2 (top_fraction) = 12; TRUTH_GATE n_trials matches.
        assert mod.DOE.n_configs == 12
        assert mod.TRUTH_GATE.n_trials == 12
        assert mod.GO_GATES.n_landscape_configs == 12
    finally:
        _reload_reversal_config()


def test_fixed_config_is_preregistered_literature_values():
    mod = _reload_reversal_config()
    fixed = mod._FIXED
    assert fixed.rebalance == "weekly"
    assert fixed.lookback_days == 5
    assert fixed.skip_days == 1
    assert fixed.top_fraction == 0.1
    assert fixed.cost_mode == "lump"


def test_truth_gate_falls_back_when_cache_absent(tmp_path):
    orig = os.getcwd()
    try:
        os.chdir(tmp_path)  # empty cwd → no data/parquet_finlab_universe
        mod = _reload_reversal_config()
        assert mod.TRUTH_GATE.survivorship_clean is False
        assert mod.TRUTH_GATE.parquet_dir is None
        assert list(mod.TRUTH_GATE.symbols) == list(mod._WIDE)
        assert mod.TRUTH_GATE.is_start == date(2015, 1, 1)
        assert mod.TRUTH_GATE.pre_registered is True
    finally:
        os.chdir(orig)
        _reload_reversal_config()  # restore real module state in the real cwd


def test_truth_gate_uses_cache_when_present(tmp_path):
    orig = os.getcwd()
    try:
        os.chdir(tmp_path)
        cache = tmp_path / "data" / "parquet_finlab_universe"
        cache.mkdir(parents=True)
        for sid in ("1101", "2330", "2454"):
            (cache / f"daily_bars__{sid}.parquet").write_bytes(b"")
        mod = _reload_reversal_config()
        assert mod.TRUTH_GATE.survivorship_clean is True
        assert mod.TRUTH_GATE.parquet_dir == "data/parquet_finlab_universe"
        assert set(mod.TRUTH_GATE.symbols) == {"1101", "2330", "2454"}
        assert mod.TRUTH_GATE.is_start == date(2010, 1, 1)
        assert mod.TRUTH_GATE.oos_start == date(2021, 1, 1)
        assert mod.TRUTH_GATE.is_end == date(2024, 12, 31)
    finally:
        os.chdir(orig)
        _reload_reversal_config()
