"""strategies.common.mechanics — neutral backtest primitives shared by strategies.

These were extracted out of ``momentum.strategy`` (ADR-026); inst_flow + the
paper daemon now depend on them in production, so they get first-class tests here
instead of riding along inside one strategy's test module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_platform.strategies.common import (
    clean_returns,
    rebalance_dates,
    vol_target,
)

# --- vol_target ----------------------------------------------------------

def test_vol_target_de_risks_high_vol_without_levering():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0, 0.03, 300))  # ~3%/day ≈ 47% annual, well above target
    scaled = vol_target(r, target_annual=0.15, lookback=20, max_lev=1.0)
    # after warmup, realized vol is cut toward target
    assert scaled.iloc[40:].std() < r.iloc[40:].std()
    # max_lev=1.0 → only de-risk, never amplify a daily move
    assert (scaled.abs() <= r.abs() + 1e-12).all()


def test_vol_target_warmup_is_identity():
    r = pd.Series(np.linspace(-0.01, 0.01, 50))
    scaled = vol_target(r, target_annual=0.15, lookback=20, max_lev=1.0)
    # before vol is estimable (first ``lookback`` points) scale defaults to 1.0
    assert scaled.iloc[0] == r.iloc[0]


# --- rebalance_dates -----------------------------------------------------

def test_rebalance_dates_monthly_picks_first_trading_day():
    idx = pd.bdate_range("2020-01-01", "2020-03-31")
    dates = rebalance_dates(idx, "monthly")
    assert len(dates) == 3  # Jan / Feb / Mar
    assert dates[0] == idx[idx.month == 1][0]


def test_rebalance_dates_quarterly_fewer_than_monthly():
    idx = pd.bdate_range("2020-01-01", "2020-12-31")
    assert len(rebalance_dates(idx, "quarterly")) == 4
    assert len(rebalance_dates(idx, "quarterly")) < len(rebalance_dates(idx, "monthly"))


def test_rebalance_dates_weekly_picks_first_trading_day_of_each_iso_week():
    # Jan 2020 business days span 5 ISO weeks; the first trading day of each is
    # the rebalance day (Wed 1st for the stub week, then each following Monday).
    idx = pd.bdate_range("2020-01-01", "2020-01-31")
    dates = rebalance_dates(idx, "weekly")
    assert dates == [
        pd.Timestamp("2020-01-01"),  # Wed — first trading day of ISO week 1
        pd.Timestamp("2020-01-06"),  # Mon week 2
        pd.Timestamp("2020-01-13"),  # Mon week 3
        pd.Timestamp("2020-01-20"),  # Mon week 4
        pd.Timestamp("2020-01-27"),  # Mon week 5
    ]


def test_rebalance_dates_weekly_more_frequent_than_monthly():
    idx = pd.bdate_range("2020-01-01", "2020-12-31")
    weekly = rebalance_dates(idx, "weekly")
    assert len(weekly) > len(rebalance_dates(idx, "monthly"))
    assert 50 <= len(weekly) <= 53  # ~52 ISO weeks in a year


def test_rebalance_dates_weekly_handles_iso_year_boundary():
    # 2021-01-01 is a Friday → ISO week 53 of 2020, so it must NOT open a new
    # rebalance week separate from the late-Dec-2020 days (ISO year avoids the split).
    idx = pd.bdate_range("2020-12-21", "2021-01-08")
    dates = rebalance_dates(idx, "weekly")
    # 2020-W52 (starts 2020-12-21), 2020-W53 (starts 2020-12-28, includes 2021-01-01),
    # 2021-W01 (starts 2021-01-04) → exactly 3 rebalances, none isolated on Jan 1.
    assert dates == [
        pd.Timestamp("2020-12-21"),
        pd.Timestamp("2020-12-28"),
        pd.Timestamp("2021-01-04"),
    ]


# --- clean_returns -------------------------------------------------------

def test_clean_returns_winsorizes_data_error_spike():
    idx = pd.bdate_range("2020-01-01", periods=5)
    px = pd.DataFrame({"A": [100.0, 101.0, 600.0, 102.0, 103.0]}, index=idx)  # 6x spike
    r = clean_returns(px, max_daily=0.5)
    assert r["A"].abs().max(skipna=True) <= 0.5  # the >50% jump is winsorized to NaN
    assert r["A"].isna().any()


def test_clean_returns_drops_inf():
    idx = pd.bdate_range("2020-01-01", periods=3)
    px = pd.DataFrame({"A": [0.0, 100.0, 101.0]}, index=idx)  # 0 → 100 = inf return
    r = clean_returns(px, max_daily=0.5)
    assert np.isfinite(r["A"].dropna()).all()
