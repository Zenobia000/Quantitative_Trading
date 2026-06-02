"""Tests for cross_check_vectorbt — vectorbt vs self-written PnL parity.

Per plan v3.0 §12 Sprint 2 acceptance: total_return must agree within
1% (relative) for material-return ranges or 10 bps (absolute) for
near-zero returns. The two-mode acceptance handles numerical sensitivity
when both engines correctly produce ~0% (relative metric blows up).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
    ParquetCache,
)
from backtest_platform.engines.zipline_adapter.validation.cross_check_vectorbt import (
    _binarize_actions,
    cross_check_vectorbt,
)


def _cache_has(symbol: str) -> bool:
    return ParquetCache(root=Path("data/parquet")).exists(symbol)


@pytest.fixture
def stock_2330() -> str:
    if not _cache_has("2330"):
        pytest.skip("2330 parquet cache missing — run `zipline ingest -b finmind`")
    return "2330"


# ---------------------------------------------------------------------------
# Integration tests — require cached bundle data
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_2330_2024_passes_absolute_tolerance(stock_2330):
    """Single-year near-zero return → absolute-tolerance path.

    Both engines agree on the trade dates and the small net PnL; the
    only divergence is rounding (slippage timing, share rounding). The
    absolute-bps floor (10 bps) catches this without falsely failing on
    a relative metric near 0.
    """
    r = cross_check_vectorbt(stock_2330, date(2024, 1, 1), date(2024, 12, 31))
    assert r.n_bars > 0
    assert r.ok, (
        f"2024 cross-check failed: self_ret={r.self_total_return:.4%} "
        f"vbt_ret={r.vbt_total_return:.4%} diff_abs={r.return_diff_abs:.6f}"
    )
    # Sanity: trade counts must align — self counts legs (2 × round-trips),
    # vectorbt counts round-trips
    assert r.n_trades_self == 2 * r.n_trades_vbt


@pytest.mark.integration
def test_2330_multi_year_relative_or_absolute(stock_2330):
    """Multi-year exercises whichever acceptance mode applies."""
    r = cross_check_vectorbt(stock_2330, date(2022, 1, 1), date(2024, 12, 31))
    assert r.ok, (
        f"multi-year cross-check failed: self_ret={r.self_total_return:.4%} "
        f"vbt_ret={r.vbt_total_return:.4%} diff_abs={r.return_diff_abs:.6f} "
        f"diff_rel={r.return_diff_rel:.4%}"
    )


@pytest.mark.integration
def test_round_trip_counts_match(stock_2330):
    """Both engines must identify the same trades regardless of PnL math."""
    r = cross_check_vectorbt(stock_2330, date(2024, 1, 1), date(2024, 12, 31))
    # self_n_trades counts buy + exit legs separately; vbt counts round-trips
    assert r.n_trades_self == 2 * r.n_trades_vbt, (
        f"trade counts diverge: self={r.n_trades_self} vbt={r.n_trades_vbt}"
    )


# ---------------------------------------------------------------------------
# Unit tests — no bundle cache required
# ---------------------------------------------------------------------------


def test_binarize_keeps_buy_exit_stoploss_drops_rest():
    """add/reduce/takeprofit/hold/none must collapse to 'hold' — they
    don't mutate position in M1's state machine, so binary-PnL parity
    requires they're no-ops in vectorbt too.
    """
    actions = pd.Series(
        ["buy", "add", "reduce", "takeprofit", "hold", "exit", "stoploss", "none"]
    )
    out = _binarize_actions(actions)
    assert out.tolist() == [
        "buy",
        "hold",  # add
        "hold",  # reduce
        "hold",  # takeprofit
        "hold",
        "exit",
        "stoploss",
        "hold",  # none
    ]


def test_binarize_preserves_index():
    """Index alignment matters for downstream pd.concat with prices."""
    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    actions = pd.Series(["buy", "add", "exit", "hold"], index=idx)
    out = _binarize_actions(actions)
    pd.testing.assert_index_equal(out.index, idx)
