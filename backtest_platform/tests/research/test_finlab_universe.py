"""Tests for the FinLab survivorship-clean universe selector (② re-validation).

Pure functions on synthetic wide frames — no live FinLab call.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from backtest_platform.research.finlab_universe import (
    cached_universe_symbols,
    ineligible_asof,
    select_survivorship_universe,
)


def _frames():
    idx = pd.date_range("2020-01-01", "2021-12-31", freq="B")
    cols = ["BIG", "MID", "DEAD", "ILLIQUID"]
    mv = pd.DataFrame(
        {"BIG": 9e9, "MID": 3e9, "DEAD": 4e9, "ILLIQUID": 2e9},
        index=idx,
    )
    close = pd.DataFrame(50.0, index=idx, columns=cols)
    close.loc["2020-07-01":, "DEAD"] = float("nan")  # DEAD delists mid-2020
    turnover = pd.DataFrame(
        {"BIG": 5e8, "MID": 5e7, "DEAD": 5e7, "ILLIQUID": 1e6},  # ILLIQUID below floor
        index=idx,
    )
    return mv, close, turnover


def test_delisted_included_while_alive_then_dropped():
    mv, close, turnover = _frames()
    uni = select_survivorship_universe(
        mv, close, turnover,
        [date(2020, 4, 1), date(2020, 10, 1)],
        top_n=10, min_turnover=2e7,
    )
    assert "DEAD" in uni  # alive + liquid at 2020-04-01 → in the survivorship-clean union
    assert "BIG" in uni and "MID" in uni
    assert "ILLIQUID" not in uni  # below the turnover floor at every rebalance


def test_topn_cap_keeps_largest_by_market_cap():
    mv, close, turnover = _frames()
    uni = select_survivorship_universe(
        mv, close, turnover,
        [date(2020, 4, 1)],  # all alive here
        top_n=2, min_turnover=2e7,
    )
    # top-2 by market cap among liquid alive = BIG (9e9), DEAD (4e9)
    assert set(uni) == {"BIG", "DEAD"}


def test_no_lookahead_excludes_delisted_after_death():
    mv, close, turnover = _frames()
    uni = select_survivorship_universe(
        mv, close, turnover,
        [date(2021, 1, 1)],  # DEAD already delisted (no close since 2020-07)
        top_n=10, min_turnover=2e7,
    )
    assert "DEAD" not in uni  # not alive at this rebalance → excluded (no look-ahead)


# --- cached_universe_symbols (sub-project ②) ------------------------------- #
def test_cached_universe_symbols_empty_when_dir_absent(tmp_path):
    assert cached_universe_symbols(str(tmp_path / "does_not_exist")) == []


def test_cached_universe_symbols_empty_when_no_bars(tmp_path):
    (tmp_path / "institutional__2330.parquet").write_bytes(b"")  # not a daily_bars file
    assert cached_universe_symbols(str(tmp_path)) == []


def test_cached_universe_symbols_reads_daily_bars_filenames(tmp_path):
    for sid in ("2330", "1101", "2454"):
        (tmp_path / f"daily_bars__{sid}.parquet").write_bytes(b"")
    (tmp_path / "institutional__2330.parquet").write_bytes(b"")  # ignored
    assert cached_universe_symbols(str(tmp_path)) == ["1101", "2330", "2454"]


# --- eligibility mask (ADR-007 Slice 3) ------------------------------------ #
def _elig_frame(idx, values: dict, dtype: str):
    """A date×stock status frame; ``values`` maps stock → per-date column list."""
    return pd.DataFrame(values, index=idx).astype(dtype)


def test_ineligible_asof_float_flag_and_bool_true():
    idx = pd.date_range("2020-01-01", "2020-01-10", freq="D")
    # change_transaction: Float64, 1.0 = flagged (變更交易含全額交割)
    ct = _elig_frame(idx, {"AAA": 1.0, "BBB": 0.0}, "Float64")
    # disposal: bool, True during window
    disp = _elig_frame(idx, {"CCC": True, "DDD": False}, "bool")
    got = ineligible_asof([ct, disp], pd.Timestamp("2020-01-05"))
    assert got == {"AAA", "CCC"}  # 0.0 / False excluded, NaN-safe


def test_ineligible_asof_no_lookahead():
    idx = pd.date_range("2020-01-01", "2020-01-10", freq="D")
    ct = _elig_frame(idx, {"AAA": 0.0}, "Float64")
    ct.loc["2020-01-08":, "AAA"] = 1.0  # flagged only from 01-08
    assert ineligible_asof([ct], pd.Timestamp("2020-01-05")) == set()   # before flag
    assert ineligible_asof([ct], pd.Timestamp("2020-01-09")) == {"AAA"}  # after flag


def test_ineligible_asof_empty_frames_is_empty():
    assert ineligible_asof([], pd.Timestamp("2020-01-05")) == set()


def test_select_excludes_flagged_names_per_rebalance():
    mv, close, turnover = _frames()
    # BIG is under 變更交易 as-of the (only) rebalance → dropped despite largest cap
    flag = pd.DataFrame(0.0, index=close.index, columns=close.columns).astype("Float64")
    flag.loc[:, "BIG"] = 1.0
    uni = select_survivorship_universe(
        mv, close, turnover,
        [date(2020, 4, 1)],
        top_n=10, min_turnover=2e7,
        exclude_frames=[flag],
    )
    assert "BIG" not in uni
    assert "MID" in uni and "DEAD" in uni  # unaffected names still selected


def test_select_no_exclude_frames_unchanged():
    mv, close, turnover = _frames()
    base = select_survivorship_universe(mv, close, turnover, [date(2020, 4, 1)], top_n=10, min_turnover=2e7)
    with_empty = select_survivorship_universe(
        mv, close, turnover, [date(2020, 4, 1)], top_n=10, min_turnover=2e7, exclude_frames=[]
    )
    assert base == with_empty  # opt-in: empty exclusion is a no-op
