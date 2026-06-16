"""FinLab primary data source (ADR-006 realized).

Sources Taiwan market data from **FinLab** into the *same* parquet schema the
FinMind bundle writes (:class:`data.schemas.ETLBundle` → :func:`write_parquet`),
so every downstream consumer (``load_merged_parquet`` / validation / replay /
``signal_fn``) is unchanged. FinMind stays the fallback source.

FinLab returns **wide** frames (date x stock_id): one ``data.get`` returns every
stock, so a universe ingest is a few batch fetches — not a per-symbol loop —
which is far gentler on the API quota than the FinMind path.

Dataset keys verified live 2026-06-15 (paid token: full history 2007→present,
2753 stocks incl. delisted). ``getter`` is injected so the suite mocks
``finlab.data.get`` and never makes a live call.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from backtest_platform.config.settings import get_settings
from backtest_platform.data.finmind_etl import write_parquet
from backtest_platform.data.schemas import ETLBundle

#: A ``finlab.data.get``-like callable: dataset key -> wide DataFrame (date x stock).
Getter = Callable[[str], pd.DataFrame]

# --- FinLab dataset keys (verified live 2026-06-15) ------------------------- #
_ADJ = {
    "open": "etl:adj_open",
    "high": "etl:adj_high",
    "low": "etl:adj_low",
    "close": "etl:adj_close",
}
_VOLUME = "price:成交股數"
_TURNOVER = "price:成交金額"
_MARKET_VALUE = "etl:market_value"

_INST = "institutional_investors_trading_summary"
#: net-buy (買賣超) share series summed into the FinMind bucket convention
#: (foreign = 外資 + 外資自營商; dealer = 自營商自行 + 避險) — see finmind_etl._normalize_institutional.
_FOREIGN = (f"{_INST}:外陸資買賣超股數(不含外資自營商)", f"{_INST}:外資自營商買賣超股數")
_TRUST = (f"{_INST}:投信買賣超股數",)
_DEALER = (f"{_INST}:自營商買賣超股數(自行買賣)", f"{_INST}:自營商買賣超股數(避險)")

#: broker-chip columns the FinMind schema carries; FinLab day-trading chips are
#: out of scope for the data-layer sub-project → zero-filled (matches FinMind M1).
_BROKER_CHIP_COLS = (
    "top_broker_buy", "key_broker_buy", "gov_broker_buy",
    "geo_broker_buy", "day_trade_volume", "margin_offset_volume",
)

_DEFAULT_CACHE_DIR = Path("data/parquet")


def login() -> None:
    """Authenticate FinLab from ``FINLAB_API_TOKEN`` (headless, daemon-friendly).

    NOTE: ``finlab.login(api_token=...)`` is deprecated after 2026/08/01 in
    finlab 2.x (new flow: ``python -m finlab login``). Migrating off token auth
    is tracked as a follow-up; token auth is kept for headless automation.
    """
    token = get_settings().finlab_api_token
    if not token:
        raise RuntimeError("FINLAB_API_TOKEN not set — required for the FinLab source (ADR-006)")
    import finlab

    finlab.login(api_token=token)


def _default_getter() -> Getter:
    from finlab import data

    return data.get  # type: ignore[no-any-return]


@dataclass(frozen=True)
class FinlabIngestResult:
    """Batch-ingest outcome; ``failed_symbols`` mirrors ``UniverseIngestResult``
    so :func:`orchestration.collaborators.make_ingest` consumes it unchanged."""

    ok_symbols: tuple[str, ...] = ()
    failed_symbols: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# ingest — FinLab wide frames → FinMind-parity ETLBundle parquet               #
# --------------------------------------------------------------------------- #
def _sum_wide(getter: Getter, keys: Sequence[str]) -> pd.DataFrame:
    """Element-wise sum of several wide net-buy frames (NaN treated as 0)."""
    total: pd.DataFrame | None = None
    for k in keys:
        frame = getter(k)
        total = frame.copy() if total is None else total.add(frame, fill_value=0)
    assert total is not None  # keys is never empty
    return total.sort_index()


def _series(wide: pd.DataFrame, sid: str, start: date, end: date) -> pd.Series:
    """Column ``sid`` over ``[start, end]`` as a date-indexed Series (empty if absent)."""
    if sid not in wide.columns:
        return pd.Series(dtype="float64")
    s = wide.sort_index().loc[str(start):str(end), sid]
    return s


def _bundle_for(sid: str, start: date, end: date, frames: dict[str, pd.DataFrame]) -> ETLBundle | None:
    """Assemble one stock's :class:`ETLBundle` aligned to its adjusted-close dates.

    Returns ``None`` when the symbol has no price data in range (→ failed).
    """
    close = _series(frames["close"], sid, start, end).dropna()
    if close.empty:
        return None
    idx = close.index

    def aligned(name: str) -> pd.Series:
        return _series(frames[name], sid, start, end).reindex(idx)

    trade_dates = [ts.date() for ts in idx]
    daily_bars = pd.DataFrame({
        "stock_id": sid,
        "trade_date": trade_dates,
        "open": aligned("open").to_numpy(),
        "high": aligned("high").to_numpy(),
        "low": aligned("low").to_numpy(),
        "close": close.to_numpy(),
        "volume": aligned("volume").fillna(0).to_numpy(),
        "adj_factor": 1.0,
    })

    def flow(name: str) -> pd.Series:
        return aligned(name).fillna(0).round().astype("int64")

    institutional = pd.DataFrame({
        "stock_id": sid,
        "trade_date": trade_dates,
        "foreign_buy": flow("foreign").to_numpy(),
        "trust_buy": flow("trust").to_numpy(),
        "dealer_buy": flow("dealer").to_numpy(),
    })

    broker_chips = pd.DataFrame({
        "stock_id": sid,
        "trade_date": trade_dates,
        **{c: 0 for c in _BROKER_CHIP_COLS},
    })

    return ETLBundle(
        stock_id=sid, start_date=start, end_date=end,
        daily_bars=daily_bars, institutional=institutional, broker_chips=broker_chips,
    )


def ingest_universe_finlab(
    symbols: Sequence[str],
    start: date,
    end: date,
    *,
    cache_dir: Path | str | None = None,
    getter: Getter | None = None,
) -> FinlabIngestResult:
    """Batch-ingest ``symbols`` from FinLab → FinMind-parity parquet cache.

    Fetches each wide dataset **once**, then slices per symbol. Symbols with no
    price data in range are recorded in ``failed_symbols`` (never abort the batch).
    """
    getter = getter or _default_getter()
    root = Path(cache_dir) if cache_dir is not None else _DEFAULT_CACHE_DIR

    frames = {
        "open": getter(_ADJ["open"]),
        "high": getter(_ADJ["high"]),
        "low": getter(_ADJ["low"]),
        "close": getter(_ADJ["close"]),
        "volume": getter(_VOLUME),
        "foreign": _sum_wide(getter, _FOREIGN),
        "trust": _sum_wide(getter, _TRUST),
        "dealer": _sum_wide(getter, _DEALER),
    }

    ok: list[str] = []
    failed: list[str] = []
    for sid in symbols:
        bundle = _bundle_for(sid, start, end, frames)
        if bundle is None:
            failed.append(sid)
            continue
        write_parquet(bundle, root)
        ok.append(sid)
    return FinlabIngestResult(tuple(ok), tuple(failed))


# --------------------------------------------------------------------------- #
# survivorship-clean universe — FinLab attribute panel → universe_builder      #
# --------------------------------------------------------------------------- #
def _asof_value(wide: pd.DataFrame, sid: str, ts: pd.Timestamp) -> float:
    """Last value on/before ``ts`` for ``sid`` (NaN if none) — strictly no look-ahead."""
    if sid not in wide.columns:
        return float("nan")
    col = wide.sort_index().loc[:ts, sid].dropna()
    return float(col.iloc[-1]) if not col.empty else float("nan")


def build_survivorship_universe(
    rebalance_dates: Sequence[date],
    *,
    top_n: int,
    min_turnover: float,
    getter: Getter | None = None,
) -> pd.DataFrame:
    """Build a point-in-time, survivorship-clean membership ledger from FinLab.

    ``delisted_date`` = each stock's last valid adjusted-close date; ``listed_date``
    = first valid. Market cap / turnout are read as-of each rebalance date (no
    look-ahead), then handed to :func:`universe_builder.assign_membership`.
    """
    from backtest_platform.data.universe_builder import (
        SmallCapUniverseConfig,
        assign_membership,
    )

    getter = getter or _default_getter()
    mv = getter(_MARKET_VALUE).sort_index()
    amt20 = getter(_TURNOVER).sort_index().rolling(20, min_periods=1).mean()
    close = getter(_ADJ["close"]).sort_index()

    first_valid = {c: close[c].first_valid_index() for c in close.columns}
    last_valid = {c: close[c].last_valid_index() for c in close.columns}

    rows: list[dict] = []
    for d in rebalance_dates:
        ts = pd.Timestamp(d)
        for sid in mv.columns:
            rows.append({
                "stock_id": sid,
                "rebalance_date": d,
                "market_cap": _asof_value(mv, sid, ts),
                "avg_amount_20": _asof_value(amt20, sid, ts),
                "listed_date": first_valid.get(sid, pd.NaT),
                "delisted_date": last_valid.get(sid, pd.NaT),
            })
    panel = pd.DataFrame(rows)

    config = SmallCapUniverseConfig(top_exclude_rank=0, max_rank=top_n, min_avg_amount=min_turnover)
    return assign_membership(panel, config)
