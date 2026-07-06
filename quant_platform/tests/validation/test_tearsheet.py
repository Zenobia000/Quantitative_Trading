"""Tests for validation/tearsheet.py — quantstats HTML tear sheet integration.

Covers the graceful-degradation contract (missing quantstats or insufficient
bars ⇒ ``None`` + a logged warning, never an exception) and the happy path
(synthetic returns ⇒ a non-empty HTML file actually lands on disk). The happy
path is ``skip``-ped when quantstats is not importable so the suite stays green
in a minimal (non-``validation``-extra) environment.

All fixtures are synthetic; nothing here touches the parquet cache.
"""
from __future__ import annotations

import importlib
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_platform.services.research_validation.validation import tearsheet

HAS_QUANTSTATS = importlib.util.find_spec("quantstats") is not None
requires_qs = pytest.mark.skipif(
    not HAS_QUANTSTATS, reason="quantstats not installed (validation extra)"
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


def _synthetic_returns(n: int = 252, seed: int = 7) -> pd.Series:
    """A DatetimeIndex-ed daily-returns series with mild positive drift."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    return pd.Series(rng.normal(0.0006, 0.011, n), index=idx, name="strategy")


# --------------------------------------------------------------------------- #
# graceful degradation — never raise
# --------------------------------------------------------------------------- #


def test_write_tearsheet_returns_none_on_empty_series(tmp_path, caplog):
    out = tmp_path / "empty.html"
    with caplog.at_level(logging.WARNING):
        result = tearsheet.write_tearsheet(pd.Series(dtype=float), out)
    assert result is None
    assert not out.exists()
    assert any("bar" in r.message.lower() or "data" in r.message.lower()
               for r in caplog.records)


def test_write_tearsheet_returns_none_on_single_bar(tmp_path, caplog):
    idx = pd.date_range("2022-01-03", periods=1, freq="B")
    one = pd.Series([0.01], index=idx)
    with caplog.at_level(logging.WARNING):
        result = tearsheet.write_tearsheet(one, tmp_path / "one.html")
    assert result is None
    assert caplog.records  # a warning was emitted


def test_write_tearsheet_returns_none_when_quantstats_missing(tmp_path, monkeypatch, caplog):
    """Simulate ImportError: should warn + return None, not crash."""
    import builtins

    real_import = builtins.__import__

    def _no_quantstats(name, *args, **kwargs):
        if name == "quantstats" or name.startswith("quantstats."):
            raise ImportError("quantstats missing (simulated)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_quantstats)
    with caplog.at_level(logging.WARNING):
        result = tearsheet.write_tearsheet(_synthetic_returns(), tmp_path / "q.html")
    assert result is None
    assert any("quantstats" in r.message.lower() for r in caplog.records)


def test_write_tearsheet_handles_non_datetime_index(tmp_path):
    """A plain RangeIndex must be coerced to DatetimeIndex, not raise."""
    plain = pd.Series(_synthetic_returns().to_numpy())  # RangeIndex
    result = tearsheet.write_tearsheet(plain, tmp_path / "coerced.html")
    # With quantstats present this produces a file; without it returns None.
    # The core assertion is that coercion does not raise.
    if HAS_QUANTSTATS:
        assert result is not None
        assert Path(result).exists()


# --------------------------------------------------------------------------- #
# happy path — file actually written (skipped without quantstats)
# --------------------------------------------------------------------------- #


@requires_qs
def test_write_tearsheet_creates_file(tmp_path):
    out = tmp_path / "tearsheet.html"
    result = tearsheet.write_tearsheet(_synthetic_returns(), out, title="My Strat")
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.suffix == ".html"


@requires_qs
def test_write_tearsheet_accepts_str_path(tmp_path):
    out = tmp_path / "as_str.html"
    result = tearsheet.write_tearsheet(_synthetic_returns(), str(out))
    assert result is not None
    assert Path(result).exists()


@requires_qs
def test_write_tearsheet_creates_parent_dirs(tmp_path):
    out = tmp_path / "nested" / "deep" / "tearsheet.html"
    result = tearsheet.write_tearsheet(_synthetic_returns(), out)
    assert result == out
    assert out.exists()


# --------------------------------------------------------------------------- #
# summary_stats — thin wrapper
# --------------------------------------------------------------------------- #


@requires_qs
def test_summary_stats_returns_float_dict():
    stats = tearsheet.summary_stats(_synthetic_returns())
    assert isinstance(stats, dict)
    assert stats  # non-empty
    for key, val in stats.items():
        assert isinstance(key, str)
        assert isinstance(val, float)
        assert not np.isnan(val)


@requires_qs
def test_summary_stats_has_core_keys():
    stats = tearsheet.summary_stats(_synthetic_returns())
    for key in ("sharpe", "cagr", "max_drawdown"):
        assert key in stats


def test_summary_stats_empty_series_returns_empty_dict():
    assert tearsheet.summary_stats(pd.Series(dtype=float)) == {}
