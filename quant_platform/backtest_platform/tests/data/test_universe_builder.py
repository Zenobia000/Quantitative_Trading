"""Point-in-time small/mid-cap universe builder tests — Candidate D.

Maps design spec ``2026-06-03-candidate-d-smallcap-universe-design.md`` §2.1
(selection rules) and §2.2 (anti-survivorship three iron rules). All fixtures
are synthetic — the builder is hermetic, so correctness is pinned here without
any real data (the real point-in-time data is gated on the §3 spike).

Small configs (top_exclude_rank=2, max_rank=4) keep the rank arithmetic obvious;
one realistic 350-stock case sanity-checks the 51-300 band.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backtest_platform.data.universe_builder import (
    SmallCapUniverseConfig,
    assign_membership,
    quarter_label,
    selected_universe,
    write_membership_ledger,
)

# Band = ranks (2, 4] = {3, 4}; mega = {1, 2}; below_band = {5, ...}.
SMALL = SmallCapUniverseConfig(top_exclude_rank=2, max_rank=4, min_avg_amount=2e7)


def _panel_row(rebalance_date: date, stock_id: str, market_cap: float, **overrides) -> dict:
    """One point-in-time panel row that is alive + liquid by default."""
    base = {
        "rebalance_date": rebalance_date,
        "stock_id": stock_id,
        "market_cap": market_cap,
        "avg_amount_20": 5e7,  # liquid (> 2,000萬 floor)
        "listed_date": date(2010, 1, 1),
        "delisted_date": pd.NaT,
    }
    base.update(overrides)
    return base


def _caps(rebalance_date: date, caps: dict[str, float], **overrides) -> list[dict]:
    return [_panel_row(rebalance_date, sid, c, **overrides) for sid, c in caps.items()]


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _reasons(membership: pd.DataFrame) -> dict[str, str]:
    return dict(zip(membership["stock_id"], membership["excluded_reason"]))


# --- §2.1 rule 1+2: market-cap rank band 51-300 (mega excluded, below-band excluded)


def test_market_cap_band_selects_middle_ranks() -> None:
    panel = _frame(_caps(date(2020, 1, 1), {"A": 60e9, "B": 50e9, "C": 40e9, "D": 30e9, "E": 20e9}))
    m = assign_membership(panel, SMALL)
    assert selected_universe(m)[pd.Timestamp(2020, 1, 1)] == ["C", "D"]
    assert _reasons(m) == {
        "A": "mega_cap",
        "B": "mega_cap",
        "C": "",
        "D": "",
        "E": "below_band",
    }


def test_realistic_51_to_300_band() -> None:
    # 350 stocks, strictly decreasing caps → rank == index; band 51-300 = 250 names.
    rows = [
        _panel_row(date(2020, 1, 1), f"S{i:03d}", market_cap=1e12 - i * 1e9)
        for i in range(1, 351)
    ]
    m = assign_membership(_frame(rows))  # default config: 51-300
    members = selected_universe(m)[pd.Timestamp(2020, 1, 1)]
    assert members == [f"S{i:03d}" for i in range(51, 301)]
    assert len(members) == 250


def test_market_cap_tie_broken_by_stock_id() -> None:
    cfg = SmallCapUniverseConfig(top_exclude_rank=1, max_rank=2, min_avg_amount=2e7)
    panel = _frame(_caps(date(2020, 1, 1), {"Z": 50e9, "A": 50e9, "M": 40e9}))
    m = assign_membership(panel, cfg)
    # Tie at 50e9 → smaller stock_id 'A' gets rank 1 (mega), 'Z' rank 2 (band), 'M' rank 3 (below).
    assert selected_universe(m)[pd.Timestamp(2020, 1, 1)] == ["Z"]
    assert _reasons(m)["A"] == "mega_cap"


# --- §2.1 rule 3: liquidity floor applied AFTER the rank band (count may shrink)


def test_illiquid_in_band_rejected() -> None:
    panel = _frame(_caps(date(2020, 1, 1), {"A": 60e9, "B": 50e9, "C": 40e9, "D": 30e9}))
    panel.loc[panel["stock_id"] == "C", "avg_amount_20"] = 1e7  # below 2,000萬
    m = assign_membership(panel, SMALL)
    assert selected_universe(m)[pd.Timestamp(2020, 1, 1)] == ["D"]
    assert _reasons(m)["C"] == "illiquid"


def test_illiquid_mega_cap_keeps_mega_reason() -> None:
    # First reason wins: a mega cap that is also illiquid is reported as mega_cap.
    panel = _frame(_caps(date(2020, 1, 1), {"A": 60e9, "B": 50e9, "C": 40e9, "D": 30e9}))
    panel.loc[panel["stock_id"] == "A", "avg_amount_20"] = 1e7
    m = assign_membership(panel, SMALL)
    assert _reasons(m)["A"] == "mega_cap"


# --- §2.2 rule 1+2: anti-survivorship + point-in-time (delisted/not-listed)


def test_delisted_stock_included_before_excluded_after() -> None:
    def market(d: date) -> list[dict]:
        rows = _caps(d, {"A": 60e9, "B": 50e9, "C": 40e9})
        rows.append(_panel_row(d, "DEL", 35e9, delisted_date=date(2020, 8, 1)))
        return rows

    q3 = market(date(2020, 7, 1))  # before delist
    q4 = market(date(2020, 10, 1))  # after delist
    m = assign_membership(_frame(q3 + q4), SMALL)
    uni = selected_universe(m)
    # Q3 ranks A1 B2 C3 DEL4 → band {3,4} = C, DEL → DEL is a valid member.
    assert "DEL" in uni[pd.Timestamp(2020, 7, 1)]
    # Q4: DEL delisted (2020-08-01 ≤ 2020-10-01) → not a member, reason 'delisted'.
    assert "DEL" not in uni[pd.Timestamp(2020, 10, 1)]
    q4_del = m[(m["stock_id"] == "DEL") & (m["rebalance_date"] == pd.Timestamp(2020, 10, 1))]
    assert q4_del["excluded_reason"].iloc[0] == "delisted"


def test_not_listed_before_listing_date_excluded() -> None:
    rows = _caps(date(2020, 1, 1), {"A": 60e9, "B": 50e9, "C": 40e9})
    rows.append(_panel_row(date(2020, 1, 1), "NEW", 35e9, listed_date=date(2020, 6, 1)))
    m = assign_membership(_frame(rows), SMALL)
    assert _reasons(m)["NEW"] == "not_listed"
    assert "NEW" not in selected_universe(m)[pd.Timestamp(2020, 1, 1)]


def test_no_future_leak_across_dates() -> None:
    # 2020Q1 membership must not change when 2020Q2 rows are added to the panel.
    q1 = _caps(date(2020, 1, 1), {"A": 60e9, "B": 50e9, "C": 40e9, "D": 30e9})
    q2 = _caps(date(2020, 4, 1), {"A": 10e9, "B": 20e9, "C": 30e9, "D": 40e9})
    only_q1 = selected_universe(assign_membership(_frame(q1), SMALL))
    both = selected_universe(assign_membership(_frame(q1 + q2), SMALL))
    assert only_q1[pd.Timestamp(2020, 1, 1)] == both[pd.Timestamp(2020, 1, 1)]


# --- §2.1 rule 5: quarterly rebalance — membership tracks as-of market cap


def test_membership_changes_across_quarters() -> None:
    # 'MOVER' is mega in Q1 (rank 1) and falls into the band in Q2 (rank 3).
    q1 = _caps(date(2020, 1, 1), {"MOVER": 99e9, "A": 60e9, "B": 50e9, "C": 40e9})
    q2 = _caps(date(2020, 4, 1), {"A": 60e9, "B": 50e9, "MOVER": 40e9, "C": 30e9})
    m = assign_membership(_frame(q1 + q2), SMALL)
    uni = selected_universe(m)
    assert "MOVER" not in uni[pd.Timestamp(2020, 1, 1)]  # mega in Q1
    assert "MOVER" in uni[pd.Timestamp(2020, 4, 1)]  # band in Q2


# --- §2.1 rule 4: optional momentum top-N (off by default in v0.1)


def test_momentum_top_n_restricts_band() -> None:
    cfg = SmallCapUniverseConfig(top_exclude_rank=0, max_rank=4, min_avg_amount=2e7, momentum_top_n=2)
    rows = [
        _panel_row(date(2020, 1, 1), sid, cap, momentum=mom)
        for sid, cap, mom in [("A", 60e9, 0.1), ("B", 50e9, 0.5), ("C", 40e9, 0.3), ("D", 30e9, 0.2)]
    ]
    m = assign_membership(_frame(rows), cfg)
    # Band = all 4; momentum top-2 = B(0.5), C(0.3).
    assert selected_universe(m)[pd.Timestamp(2020, 1, 1)] == ["B", "C"]
    reasons = _reasons(m)
    assert reasons["A"] == "below_momentum"
    assert reasons["D"] == "below_momentum"


def test_momentum_requires_column() -> None:
    cfg = SmallCapUniverseConfig(momentum_top_n=2)
    panel = _frame(_caps(date(2020, 1, 1), {"A": 60e9, "B": 50e9}))
    with pytest.raises(ValueError, match="missing columns"):
        assign_membership(panel, cfg)


# --- §2.2 rule 3: membership ledger persisted per quarter


def test_membership_ledger_written(tmp_path) -> None:
    panel = _frame(
        _caps(date(2020, 1, 1), {"A": 60e9, "B": 50e9, "C": 40e9, "D": 30e9})
        + _caps(date(2020, 4, 1), {"A": 60e9, "B": 50e9, "C": 40e9, "D": 30e9})
    )
    m = assign_membership(panel, SMALL)
    paths = write_membership_ledger(m, tmp_path)
    assert sorted(p.name for p in paths) == [
        "universe_membership__2020Q1.csv",
        "universe_membership__2020Q2.csv",
    ]
    df = pd.read_csv(tmp_path / "universe_membership__2020Q1.csv")
    assert sorted(df["stock_id"].astype(str)) == ["C", "D"]
    assert "market_cap_rank" in df.columns


# --- validation + helpers


def test_missing_columns_raises() -> None:
    bad = pd.DataFrame({"stock_id": ["S1"]})
    with pytest.raises(ValueError, match="missing columns"):
        assign_membership(bad)


def test_quarter_label() -> None:
    assert quarter_label(date(2020, 1, 1)) == "2020Q1"
    assert quarter_label(date(2020, 4, 1)) == "2020Q2"
    assert quarter_label(date(2020, 7, 1)) == "2020Q3"
    assert quarter_label(date(2020, 12, 31)) == "2020Q4"
