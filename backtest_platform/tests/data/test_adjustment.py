"""Tests for forward-adjustment computation."""
from __future__ import annotations

import warnings
from datetime import date

import pandas as pd
import pytest

from backtest_platform.data.adjustment import (
    _extract_ex_dividend_events,
    _find_previous_close,
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


# ---------------------------------------------------------------------------
# Edge case + branch coverage tests (TEST-007: 29.4% → 80%+)
# ---------------------------------------------------------------------------


def test_bad_ratio_zero_pre_close_skipped() -> None:
    """pre_close == 0 → skip the event, factor stays 1.0 for all bars."""
    daily = _daily([("2024-01-02", 0.0), ("2024-01-03", 0.0), ("2024-01-04", 5.0)])
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2024-01-04",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 1.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    factor = compute_adj_factor(daily, dividends)
    assert (factor == 1.0).all()


def test_bad_ratio_cash_exceeds_pre_close_skipped(caplog) -> None:
    """cash_div > pre_close → ratio <= 0 → skip with warning."""
    daily = _daily(
        [
            ("2024-01-02", 10.0),
            ("2024-01-03", 10.0),
            ("2024-01-04", 8.0),
        ]
    )
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2024-01-04",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 100.0,  # absurd, > pre_close
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    factor = compute_adj_factor(daily, dividends)
    # event skipped → factor remains 1.0 everywhere
    assert (factor == 1.0).all()


def test_malformed_date_string_skipped() -> None:
    """Garbage in CashExDividendTradingDate → event skipped, no exception."""
    daily = _daily([("2024-01-02", 100.0), ("2024-01-03", 95.0)])
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "not-a-date",
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


def test_both_ex_dividend_dates_empty_skipped() -> None:
    """Both Cash & Stock ex-div dates blank → row skipped."""
    daily = _daily([("2024-01-02", 100.0), ("2024-01-03", 95.0)])
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "",
                "StockExDividendTradingDate": None,
                "CashEarningsDistribution": 5.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    factor = compute_adj_factor(daily, dividends)
    assert (factor == 1.0).all()


def test_stock_dividend_warns_and_applies() -> None:
    """Pure stock dividend (1 share per 10) reduces factor proportionally."""
    daily = _daily(
        [
            ("2024-01-02", 100.0),
            ("2024-01-03", 100.0),
            ("2024-01-04", 90.0),  # ex-stock-div
            ("2024-01-05", 91.0),
        ]
    )
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "",
                "StockExDividendTradingDate": "2024-01-04",
                "CashEarningsDistribution": 0.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 1.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        factor = compute_adj_factor(daily, dividends)
    # pre_close=100, stock_value = 100 * 1 / 10 = 10, ratio = 90/100 = 0.9
    assert factor.iloc[0] == pytest.approx(0.9)
    assert factor.iloc[1] == pytest.approx(0.9)
    assert factor.iloc[2] == pytest.approx(1.0)
    assert any("stock dividend" in str(w.message).lower() for w in caught)


def test_combined_cash_and_stock_dividend() -> None:
    """Both cash + stock: ratio = (pre - cash - stock_value) / pre."""
    daily = _daily(
        [
            ("2024-01-02", 100.0),
            ("2024-01-03", 100.0),
            ("2024-01-04", 85.0),
        ]
    )
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2024-01-04",
                "StockExDividendTradingDate": "2024-01-04",
                "CashEarningsDistribution": 3.0,
                "CashStatutorySurplus": 2.0,  # total cash 5
                "StockEarningsDistribution": 0.5,
                "StockStatutorySurplus": 0.5,  # total stock shares 1
            }
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        factor = compute_adj_factor(daily, dividends)
    # stock_value = 100 * 1 / 10 = 10, cash = 5, ratio = (100-5-10)/100 = 0.85
    assert factor.iloc[0] == pytest.approx(0.85)
    assert factor.iloc[1] == pytest.approx(0.85)
    assert factor.iloc[2] == pytest.approx(1.0)


def test_zero_total_distribution_skipped() -> None:
    """cash + stock_value == 0 → no adjustment."""
    daily = _daily([("2024-01-02", 100.0), ("2024-01-03", 100.0)])
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2024-01-03",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 0.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    factor = compute_adj_factor(daily, dividends)
    assert (factor == 1.0).all()


def test_ex_div_uses_stock_date_when_cash_missing() -> None:
    """StockExDividendTradingDate fallback when CashExDividendTradingDate empty."""
    daily = _daily(
        [
            ("2024-01-02", 100.0),
            ("2024-01-03", 100.0),
            ("2024-01-04", 90.0),
        ]
    )
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "",
                "StockExDividendTradingDate": "2024-01-04",
                "CashEarningsDistribution": 0.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 1.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        factor = compute_adj_factor(daily, dividends)
    # Should pick up the stock-only event
    assert factor.iloc[0] < 1.0
    assert factor.iloc[1] < 1.0


def test_apply_adjustment_length_mismatch_raises() -> None:
    """factor length != daily length → ValueError."""
    daily = _daily([("2024-01-02", 100.0), ("2024-01-03", 95.0)])
    factor = pd.Series([0.95])  # length 1, daily length 2
    with pytest.raises(ValueError, match="adj_factor length"):
        apply_adjustment(daily, factor)


def test_find_previous_close_empty_eligible_returns_none() -> None:
    """ex_date earlier than any bar in closes → None."""
    closes = pd.Series(
        [100.0, 101.0],
        index=[date(2024, 6, 1), date(2024, 6, 2)],
    )
    assert _find_previous_close(closes, date(2024, 1, 1)) is None


def test_find_previous_close_returns_last_bar_strictly_before() -> None:
    """Returns close of last bar with date < ex_date (strict)."""
    closes = pd.Series(
        [100.0, 101.0, 102.0],
        index=[date(2024, 6, 1), date(2024, 6, 2), date(2024, 6, 3)],
    )
    # ex_date == 6/3: eligible is 6/1 and 6/2, returns 101.0
    assert _find_previous_close(closes, date(2024, 6, 3)) == pytest.approx(101.0)


def test_extract_no_events_within_range_returns_empty_list() -> None:
    """All ex-div dates fall outside trading-day range → empty list."""
    daily = _daily([("2024-06-01", 100.0), ("2024-06-02", 101.0)])
    daily_sorted = daily.sort_values("trade_date").reset_index(drop=True)
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2023-01-01",  # before range
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 5.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            },
            {
                "CashExDividendTradingDate": "2025-01-01",  # after range
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 5.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            },
        ]
    )
    assert _extract_ex_dividend_events(dividends, daily_sorted) == []


def test_extract_event_with_pre_close_unavailable_skipped() -> None:
    """ex_date == first bar → no prior close → event skipped."""
    daily = _daily([("2024-01-02", 100.0), ("2024-01-03", 95.0)])
    daily_sorted = daily.sort_values("trade_date").reset_index(drop=True)
    dividends = pd.DataFrame(
        [
            {
                "CashExDividendTradingDate": "2024-01-02",  # == first bar
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 5.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            }
        ]
    )
    assert _extract_ex_dividend_events(dividends, daily_sorted) == []


def test_extract_events_sorted_chronologically() -> None:
    """Multi-event input returns sorted-by-date list regardless of input order."""
    daily = _daily(
        [
            ("2024-01-02", 100.0),
            ("2024-01-03", 100.0),
            ("2024-01-04", 90.0),
            ("2024-01-05", 90.0),
            ("2024-01-06", 80.0),
        ]
    )
    daily_sorted = daily.sort_values("trade_date").reset_index(drop=True)
    dividends = pd.DataFrame(
        [
            # Out-of-order input — later date first
            {
                "CashExDividendTradingDate": "2024-01-06",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 10.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            },
            {
                "CashExDividendTradingDate": "2024-01-04",
                "StockExDividendTradingDate": "",
                "CashEarningsDistribution": 10.0,
                "CashStatutorySurplus": 0.0,
                "StockEarningsDistribution": 0.0,
                "StockStatutorySurplus": 0.0,
            },
        ]
    )
    events = _extract_ex_dividend_events(dividends, daily_sorted)
    assert len(events) == 2
    assert events[0]["date"] == date(2024, 1, 4)
    assert events[1]["date"] == date(2024, 1, 6)


def test_compute_adj_factor_handles_unsorted_daily() -> None:
    """daily passed in unsorted order — function sorts internally."""
    daily = _daily(
        [
            ("2024-01-05", 96.0),
            ("2024-01-02", 100.0),  # out of order
            ("2024-01-04", 95.0),
            ("2024-01-03", 100.0),
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
    # After sort: indices map to dates 01/02, 01/03, 01/04, 01/05
    # Bars before 01/04 (indices 0,1) get ratio 0.95
    assert factor.iloc[0] == pytest.approx(0.95)
    assert factor.iloc[1] == pytest.approx(0.95)
    assert factor.iloc[2] == pytest.approx(1.0)
    assert factor.iloc[3] == pytest.approx(1.0)
