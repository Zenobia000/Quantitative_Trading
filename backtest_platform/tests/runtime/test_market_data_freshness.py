"""Tests for the no-data signal that the after-close scheduler degrades on.

``check_panel_freshness`` is the explicit ``NoMarketDataError`` seam: a weekday the
approximate calendar wrongly thinks is a session (a Taiwan public holiday) yields a
live panel whose last row is the PRIOR session — running the chain on it would place
orders on stale data. The scheduler turns this one explicit signal into a benign skip
instead of a FAILED alert.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backtest_platform.runtime.market_data_errors import NoMarketDataError
from backtest_platform.services.strategy_runtime.live_session import check_panel_freshness


def _panel(last: date) -> pd.DataFrame:
    idx = pd.to_datetime([date(2026, 6, 29), date(2026, 6, 30), last])
    return pd.DataFrame({"2330": [100.0, 101.0, 102.0]}, index=idx)


def test_fresh_panel_with_asof_row_does_not_raise():
    as_of = date(2026, 7, 2)
    check_panel_freshness(_panel(as_of), as_of, strategy="inst_flow")  # must not raise


def test_stale_panel_missing_asof_raises_no_market_data():
    as_of = date(2026, 7, 2)  # holiday: FinLab's latest row is 2026-07-01
    with pytest.raises(NoMarketDataError) as exc:
        check_panel_freshness(_panel(date(2026, 7, 1)), as_of, strategy="inst_flow")
    assert exc.value.strategy == "inst_flow"
    assert exc.value.as_of == as_of


def test_empty_panel_raises_no_market_data():
    with pytest.raises(NoMarketDataError):
        check_panel_freshness(pd.DataFrame(), date(2026, 7, 2), strategy="inst_flow")
