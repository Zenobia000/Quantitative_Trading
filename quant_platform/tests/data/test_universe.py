"""Universe filter tests — v2.md 2.2 mapping."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from quant_platform.services.data_platform.universe import (
    UNIVERSE_METADATA_COLUMNS,
    UniverseConfig,
    apply_filters,
    rejection_summary,
    survivors,
)


def _row(**overrides) -> dict:
    """Build a single-row metadata dict that passes every filter by default.

    Uses a mid-cap example (price 300) since v2.md 2.2 caps price at 500 —
    the strategy explicitly targets 中小型股, so TSMC at >1000 would be
    excluded by spec.
    """
    base = {
        "stock_id": "9999",
        "market": "TWSE",
        "market_cap": 5e10,
        "listed_date": date(2010, 1, 4),
        "industry": "電子",
        "avg_volume_60": 5_000,
        "avg_amount_60": 5e8,
        "current_price": 300.0,
        "is_etf": False,
        "is_warrant": False,
        "is_convertible": False,
        "is_attention": False,
        "is_full_delivery": False,
        "governance_grade": "A++",
        "days_since_ex_dividend": 90,
        "days_until_ex_dividend": 90,
    }
    base.update(overrides)
    return base


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=list(UNIVERSE_METADATA_COLUMNS))


def test_required_columns_validated() -> None:
    bad = pd.DataFrame({"stock_id": ["2330"]})  # missing nearly everything
    with pytest.raises(ValueError, match="missing columns"):
        apply_filters(bad)


def test_clean_pass_through() -> None:
    df = _frame([_row()])
    out = apply_filters(df, snapshot_date=date(2024, 12, 31))
    assert out["excluded_reason"].iloc[0] == ""
    assert len(survivors(out)) == 1


def test_low_market_cap_rejected() -> None:
    df = _frame([_row(stock_id="9999", market_cap=1e9)])
    out = apply_filters(df)
    assert out["excluded_reason"].iloc[0] == "market_cap_too_low"


def test_low_volume_rejected() -> None:
    df = _frame([_row(avg_volume_60=500)])
    assert apply_filters(df)["excluded_reason"].iloc[0] == "volume_too_low"


def test_price_outside_range_rejected() -> None:
    too_cheap = _frame([_row(current_price=5.0)])
    assert apply_filters(too_cheap)["excluded_reason"].iloc[0] == "price_below_floor"
    too_pricey = _frame([_row(current_price=600.0)])
    assert apply_filters(too_pricey)["excluded_reason"].iloc[0] == "price_above_cap"


def test_etf_warrant_convertible_rejected() -> None:
    rows = [
        _row(stock_id="0050", is_etf=True),
        _row(stock_id="W1234", is_warrant=True),
        _row(stock_id="C0001", is_convertible=True),
    ]
    out = apply_filters(_frame(rows))
    reasons = out["excluded_reason"].tolist()
    assert reasons == ["etf", "warrant", "convertible_bond"]


def test_newly_listed_rejected() -> None:
    snapshot = date(2024, 6, 30)
    new = _row(stock_id="9988", listed_date=date(2024, 1, 1))
    out = apply_filters(_frame([new]), snapshot_date=snapshot)
    assert out["excluded_reason"].iloc[0] == "newly_listed"


def test_bad_governance_grade_rejected() -> None:
    df = _frame([_row(governance_grade="D")])
    assert apply_filters(df)["excluded_reason"].iloc[0] == "bad_governance"


def test_ex_dividend_quiet_period_rejected() -> None:
    recent = _row(stock_id="A", days_since_ex_dividend=5)
    upcoming = _row(stock_id="B", days_until_ex_dividend=5)
    out = apply_filters(_frame([recent, upcoming]))
    assert (out["excluded_reason"] == "ex_dividend_quiet").all()


def test_rejection_summary_aggregates() -> None:
    rows = [
        _row(stock_id="A"),
        _row(stock_id="B", market_cap=1e9),
        _row(stock_id="C", avg_volume_60=100),
        _row(stock_id="D", is_etf=True),
        _row(stock_id="E", market_cap=2e9),
    ]
    out = apply_filters(_frame(rows))
    summary = rejection_summary(out)
    assert summary["market_cap_too_low"] == 2
    assert summary["volume_too_low"] == 1
    assert summary["etf"] == 1
    assert len(survivors(out)) == 1
