"""Tests for the FinLab survivorship-clean universe selector (② re-validation).

Pure functions on synthetic wide frames — no live FinLab call.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from backtest_platform.research.finlab_universe import select_survivorship_universe


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
