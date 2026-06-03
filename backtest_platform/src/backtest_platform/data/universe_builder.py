"""Point-in-time small/mid-cap universe builder — Candidate D.

Design spec ``2026-06-03-candidate-d-smallcap-universe-design.md`` §2 / §8 and
[ADR-020]. The four-layer-resonance mechanism is FROZEN; Candidate D only swaps
the *scanned universe* from large caps to a point-in-time small/mid-cap pool.
This module is that swap: it turns a point-in-time attribute panel (one row per
``(rebalance_date, stock_id)`` carrying as-of market cap, trailing turnover and
listing status) into the per-quarter membership list — the core data structure
of Candidate D.

Anti-survivorship is structural (spec §2.2): the caller supplies *every* stock
that existed at each rebalance date, including those later delisted. Membership
for a date is decided using only that date's as-of values plus the stock's
listed/delisted dates; the builder never reads across dates, so future
information cannot leak into a past quarter's pool.

Selection rules (spec §2.1), applied per rebalance date in order:
  1. keep only stocks alive at the date (listed and not yet delisted);
  2. rank survivors by market cap (desc, ties broken by stock_id for
     determinism), drop ranks 1..``top_exclude_rank`` (mega caps);
  3. keep ranks (``top_exclude_rank``, ``max_rank``] — the small/mid band;
  4. drop band members below the liquidity floor (count may shrink — no backfill);
  5. optional momentum top-N (off in v0.1 to avoid in-sample tuning).

Hermetic: pure functions over an in-memory DataFrame, no I/O except the
explicit ledger writer. Real point-in-time data is gated on the §3 spike;
correctness is pinned with synthetic fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

PANEL_COLUMNS: tuple[str, ...] = (
    "rebalance_date",  # date — quarter-start scan date
    "stock_id",
    "market_cap",  # NTD, as-of rebalance_date
    "avg_amount_20",  # NTD, trailing 20-day avg daily turnover as-of rebalance_date
    "listed_date",  # date
    "delisted_date",  # date or NaT (still listed)
)

MOMENTUM_COLUMN = "momentum"  # trailing return as-of rebalance_date; required only when momentum_top_n is set

LEDGER_COLUMNS: tuple[str, ...] = ("stock_id", "market_cap", "market_cap_rank", "avg_amount_20")


@dataclass(frozen=True, slots=True)
class SmallCapUniverseConfig:
    """Candidate D universe rules — frozen for v0.1 (design spec §2.1)."""

    top_exclude_rank: int = 50  # drop market-cap rank 1..50 (mega caps)
    max_rank: int = 300  # keep ranks (top_exclude_rank, max_rank]
    min_avg_amount: float = 2e7  # 2,000萬 TWD trailing-20d avg turnover floor
    momentum_top_n: int | None = None  # v0.1: None = take whole band (no in-sample tuning)

    @classmethod
    def default(cls) -> "SmallCapUniverseConfig":
        return cls()


def quarter_label(d: date | pd.Timestamp) -> str:
    """``2020Q1`` style label for the membership-ledger filename."""
    ts = pd.Timestamp(d)
    return f"{ts.year}Q{(ts.month - 1) // 3 + 1}"


def assign_membership(
    panel: pd.DataFrame,
    config: SmallCapUniverseConfig | None = None,
) -> pd.DataFrame:
    """Return ``panel`` with ``market_cap_rank`` / ``excluded_reason`` / ``selected``.

    First reason wins (mirrors :func:`universe.apply_filters`), so a stock that
    fails several gates is reported by the first one that killed it.
    """
    config = config or SmallCapUniverseConfig.default()
    _validate_panel(panel, config)

    out = panel.copy()
    out["rebalance_date"] = pd.to_datetime(out["rebalance_date"])
    out["excluded_reason"] = ""
    out["market_cap_rank"] = pd.NA

    listed = pd.to_datetime(out["listed_date"])
    delisted = pd.to_datetime(out["delisted_date"])

    for d, idx in out.groupby("rebalance_date").groups.items():
        not_listed = listed.loc[idx] > d
        delisted_now = delisted.loc[idx].notna() & (delisted.loc[idx] <= d)
        alive = ~(not_listed | delisted_now)

        # Rank alive survivors by market cap; tie-break by stock_id for determinism.
        alive_idx = pd.Index(idx)[alive.to_numpy()]
        ranked = out.loc[alive_idx, ["market_cap", "stock_id"]].sort_values(
            ["market_cap", "stock_id"], ascending=[False, True]
        )
        ranks = pd.Series(range(1, len(ranked) + 1), index=ranked.index)
        out.loc[ranks.index, "market_cap_rank"] = ranks.to_numpy()

        _set_reason(out, pd.Index(idx)[not_listed.to_numpy()], "not_listed")
        _set_reason(out, pd.Index(idx)[delisted_now.to_numpy()], "delisted")
        _set_reason(out, ranks.index[ranks <= config.top_exclude_rank], "mega_cap")
        _set_reason(out, ranks.index[ranks > config.max_rank], "below_band")

        band = ranks.index[(ranks > config.top_exclude_rank) & (ranks <= config.max_rank)]
        illiquid = [i for i in band if out.at[i, "avg_amount_20"] < config.min_avg_amount]
        _set_reason(out, illiquid, "illiquid")

        if config.momentum_top_n is not None:
            keep = [i for i in band if out.at[i, "excluded_reason"] == ""]
            by_mom = out.loc[keep, [MOMENTUM_COLUMN, "stock_id"]].sort_values(
                [MOMENTUM_COLUMN, "stock_id"], ascending=[False, True]
            )
            _set_reason(out, by_mom.index[config.momentum_top_n :], "below_momentum")

    out["market_cap_rank"] = out["market_cap_rank"].astype("Int64")
    out["selected"] = out["excluded_reason"] == ""
    return out


def selected_universe(membership: pd.DataFrame) -> dict[pd.Timestamp, list[str]]:
    """``{rebalance_date: [stock_id, ...]}`` for selected rows, ids sorted."""
    chosen = membership[membership["selected"]]
    return {
        d: sorted(group["stock_id"].astype(str))
        for d, group in chosen.groupby("rebalance_date")
    }


def write_membership_ledger(membership: pd.DataFrame, out_dir: Path | str) -> list[Path]:
    """Write one ``universe_membership__{YYYYQ}.csv`` per quarter (spec §2.2 rule 3)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chosen = membership[membership["selected"]]
    paths: list[Path] = []
    for d, group in chosen.groupby("rebalance_date"):
        path = out_dir / f"universe_membership__{quarter_label(d)}.csv"
        group.sort_values("stock_id")[list(LEDGER_COLUMNS)].to_csv(path, index=False)
        paths.append(path)
    return sorted(paths)


def _set_reason(out: pd.DataFrame, index, reason: str) -> None:
    index = pd.Index(index)
    if len(index) == 0:
        return
    empty = out.loc[index, "excluded_reason"] == ""
    out.loc[empty[empty].index, "excluded_reason"] = reason


def _validate_panel(df: pd.DataFrame, config: SmallCapUniverseConfig) -> None:
    required = list(PANEL_COLUMNS)
    if config.momentum_top_n is not None:
        required.append(MOMENTUM_COLUMN)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"universe panel missing columns: {missing}")
