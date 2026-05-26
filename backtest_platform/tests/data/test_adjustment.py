"""Tests for forward-adjustment computation."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backtest_platform.data.adjustment import (
    apply_adjustment,
    compute_adj_factor,
)


def _daily(rows: list[tuple[str, float]]) -> pd.DataFrame:
    """Build a minimal daily frame from (date_str, close) pairs."""
    return pd.DataFrame(
        {
            "trade_date": [pd.to_datetime(d).date() for d, _ in rows],
            "open": [c for _, c in rows],
            "high": [c for _, c in rows],
            "low": [c for _, c in rows],
            "close": [c for _, c in rows],
            "volume": [1000] * len(rows),
        }
    )


def test_empty_daily_returns_empty_factor() -> None:
    factor = compute_adj_factor(pd.DataFrame(columns=["trade_date", "close"]), pd.DataFrame())
    assert factor.empty


def test_no_dividends_returns_all_ones() -> None:
    daily = _daily([("2024-01-02", 100), ("2024-01-03", 101)])
    factor = compute_adj_factor(daily, pd.DataFrame())
    assert (factor == 1.0).all()


def test_single_cash_dividend_scales_prior_bars() -> None:
    """Pre-ex close 100, cash div 5 → ratio 0.95, applied to bars before ex-date."""
    daily = _daily(
        [
            ("2024-01-02", 100.0),
            ("2024-01-03", 100.0),
            ("2024-01-04", 95.0),  # ex-div date
            ("2024-01-05", 96.0),
        ]
    )
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2024-01-04",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 5.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    factor = compute_adj_factor(daily, dividends)
    # bars before 2024-01-04 should have factor 0.95
    assert factor.iloc[0] == pytest.approx(0.95)
    assert factor.iloc[1] == pytest.approx(0.95)
    # ex-div day and after stay at 1.0
    assert factor.iloc[2] == pytest.approx(1.0)
    assert factor.iloc[3] == pytest.approx(1.0)


def test_apply_adjustment_preserves_raw_columns() -> None:
    daily = _daily([("2024-01-02", 100.0), ("2024-01-03", 95.0)])
    factor = pd.Series([0.95, 1.0])
    adjusted = apply_adjustment(daily, factor)
    assert adjusted["close"].iloc[0] == pytest.approx(95.0)
    assert adjusted["raw_close"].iloc[0] == pytest.approx(100.0)
    assert adjusted["adj_factor"].iloc[0] == pytest.approx(0.95)


def test_dividend_outside_range_is_ignored() -> None:
    daily = _daily([("2024-06-01", 100.0), ("2024-06-02", 101.0)])
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2023-12-01",  # before range
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 5.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    factor = compute_adj_factor(daily, dividends)
    assert (factor == 1.0).all()


def test_compounding_two_dividends() -> None:
    """Two ex-div events: older event compounds into newer one."""
    daily = _daily(
        [
            ("2024-01-02", 100.0),
            ("2024-01-03", 100.0),
            ("2024-01-04", 90.0),  # first ex-div
            ("2024-01-05", 90.0),
            ("2024-01-06", 80.0),  # second ex-div
            ("2024-01-07", 81.0),
        ]
    )
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2024-01-04",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 10.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            },
            {
                "CashExDividendTradingDate": "2024-01-06",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 10.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            },
        ]
    )
    factor = compute_adj_factor(daily, dividends)
    # First event: pre_close=100, ratio=0.9 → bars before 01/04 → indices 0,1
    # Second event: pre_close on 01/05 = 90, ratio = 80/90 ≈ 0.8889
    #   applies to bars before 01/06 → indices 0,1,2,3
    expected_0 = 0.9 * (80 / 90)
    expected_2 = 80 / 90  # only second event applies
    assert factor.iloc[0] == pytest.approx(expected_0, rel=1e-6)
    assert factor.iloc[1] == pytest.approx(expected_0, rel=1e-6)
    assert factor.iloc[2] == pytest.approx(expected_2, rel=1e-6)
    assert factor.iloc[3] == pytest.approx(expected_2, rel=1e-6)
    assert factor.iloc[4] == pytest.approx(1.0)
    assert factor.iloc[5] == pytest.approx(1.0)
