"""Report pure functions — monthly-return matrix + drawdown-event oracles.

Hand-computed small-series oracles for the two Run-Report v1 aggregations
(``validation.report``): the year×month compounded-return grid and the top-N
drawdown-event table (incl. an unrecovered case). Pure functions, no IO — the
report endpoint feeds them the sidecar series with a reconstructed date index.
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from backtest_platform.validation.report import (
    drawdown_events,
    dsr_band,
    monthly_returns_matrix,
)


# --------------------------------------------------------------------------- #
# monthly_returns_matrix                                                       #
# --------------------------------------------------------------------------- #
def test_monthly_matrix_compounds_within_month_and_spans_years():
    # Dec-2020: single +0.10 day. Jan-2021: 0.02 then 0.05 → (1.02*1.05)-1.
    idx = pd.to_datetime(["2020-12-31", "2021-01-15", "2021-01-31"])
    returns = pd.Series([0.10, 0.02, 0.05], index=idx)

    out = monthly_returns_matrix(returns)

    assert out["years"] == [2020, 2021]
    # matrix rows are 12-wide (Jan..Dec), null where a month has no data.
    dec_2020 = out["matrix"][0][11]
    jan_2021 = out["matrix"][1][0]
    assert dec_2020 == pytest.approx(0.10)
    assert jan_2021 == pytest.approx(1.02 * 1.05 - 1.0)
    # empty months are null (not 0.0 — 0.0 would read as a real flat month).
    assert out["matrix"][0][0] is None
    assert out["matrix"][1][11] is None
    # annual = compounded whole-year total.
    assert out["annual"][0] == pytest.approx(0.10)
    assert out["annual"][1] == pytest.approx(1.02 * 1.05 - 1.0)


def test_monthly_matrix_empty_series_is_empty_grid():
    out = monthly_returns_matrix(pd.Series(dtype=float))
    assert out == {"years": [], "matrix": [], "annual": []}


def test_monthly_matrix_no_nan_leaks():
    idx = pd.to_datetime(["2022-03-01", "2022-03-02"])
    out = monthly_returns_matrix(pd.Series([0.01, -0.02], index=idx))
    mar = out["matrix"][0][2]
    assert mar == pytest.approx(1.01 * 0.98 - 1.0)
    # every populated cell is a finite float; every other cell is None.
    for row in out["matrix"]:
        for cell in row:
            assert cell is None or (isinstance(cell, float) and math.isfinite(cell))


# --------------------------------------------------------------------------- #
# drawdown_events                                                              #
# --------------------------------------------------------------------------- #
def test_drawdown_events_recovered_and_unrecovered():
    # 100 →(dd1 -10%)→ recover to 100 →(dd2 -20%, never recovers)→ 85 (still under).
    equity = [100.0, 90.0, 95.0, 100.0, 80.0, 85.0]
    dates = [f"2020-01-0{i + 1}" for i in range(6)]

    events = drawdown_events(equity, dates=dates, top_n=5)

    assert len(events) == 2
    # sorted deepest-first: the -20% unrecovered event leads.
    deep, shallow = events
    assert deep["depth"] == pytest.approx(0.20)
    assert deep["recovered"] is False
    assert deep["recovery_idx"] is None
    assert deep["recovery_date"] is None
    assert deep["peak_idx"] == 3
    assert deep["trough_idx"] == 4
    assert deep["peak_date"] == "2020-01-04"
    assert deep["trough_date"] == "2020-01-05"

    assert shallow["depth"] == pytest.approx(0.10)
    assert shallow["recovered"] is True
    assert shallow["recovery_idx"] == 3
    assert shallow["recovery_date"] == "2020-01-04"
    assert shallow["peak_idx"] == 0
    assert shallow["trough_idx"] == 1
    # duration = peak→recovery in bars (recovered) / peak→last (unrecovered).
    assert shallow["duration_bars"] == 3
    assert deep["duration_bars"] == 2


def test_drawdown_events_top_n_caps_and_sorts():
    # three separate drawdowns of depths 0.05, 0.20, 0.10 — top_n=2 keeps deepest two.
    equity = [100, 95, 100, 80, 100, 90, 100]
    events = drawdown_events([float(x) for x in equity], top_n=2)
    depths = [e["depth"] for e in events]
    assert len(events) == 2
    assert depths[0] == pytest.approx(0.20)
    assert depths[1] == pytest.approx(0.10)


def test_drawdown_events_no_dates_yields_null_labels():
    events = drawdown_events([100.0, 80.0, 100.0])
    assert events[0]["peak_date"] is None
    assert events[0]["trough_date"] is None
    assert events[0]["recovery_date"] is None


def test_drawdown_events_monotonic_up_has_no_events():
    assert drawdown_events([1.0, 1.1, 1.2, 1.3]) == []


def test_drawdown_events_empty_equity():
    assert drawdown_events([]) == []


# --------------------------------------------------------------------------- #
# dsr_band                                                                     #
# --------------------------------------------------------------------------- #
def test_dsr_band_thresholds():
    assert dsr_band(0.97) == "REAL"          # >= 0.95
    assert dsr_band(0.95) == "REAL"
    assert dsr_band(0.92) == "PAPER_WATCH"   # [0.90, 0.95)
    assert dsr_band(0.90) == "PAPER_WATCH"
    assert dsr_band(0.80) == "REJECTED"      # < 0.90
    assert dsr_band(None) is None            # honest null, never fabricated
