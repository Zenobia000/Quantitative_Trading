"""FinMind ETL for v2.md Part 4.1 data needs.

CLI usage::

    python -m backtest_platform.data.finmind_etl \\
        --stock-id 2330 --start 2024-01-01 --end 2024-12-31 \\
        --output data/parquet

Without ``--output``, writes nothing — useful for dry-run + schema validation.
Use ``--db`` to additionally upsert into TimescaleDB.

This module intentionally avoids a heavy DataLoader dependency at import time;
``DataLoader`` is constructed lazily inside ``fetch_bundle`` so unit tests can
mock it without installing the package.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

import click
import pandas as pd
from loguru import logger

from backtest_platform.data.schemas import ETLBundle


class FinMindLike(Protocol):
    """Subset of FinMind ``DataLoader`` interface we depend on.

    Real ``FinMind.data.DataLoader`` satisfies this. Tests can inject a stub.
    """

    def taiwan_stock_daily(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame: ...
    def taiwan_stock_institutional_investors(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame: ...
    def taiwan_stock_day_trading(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame: ...
    def taiwan_stock_dividend(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame: ...


@dataclass(slots=True, frozen=True)
class ETLConfig:
    rate_limit_seconds: float = 0.6  # FinMind free tier: ~600 req/hour
    rename_map_daily: dict[str, str] = None  # type: ignore[assignment]
    rename_map_inst: dict[str, str] = None  # type: ignore[assignment]


_DEFAULT_DAILY_RENAME = {
    "date": "trade_date",
    "Trading_Volume": "volume",
    "open": "open",
    "max": "high",
    "min": "low",
    "close": "close",
}

_DEFAULT_INST_RENAME = {
    "date": "trade_date",
    "Foreign_Investor": "foreign_buy",
    "Investment_Trust": "trust_buy",
    "Dealer_self": "dealer_buy",
}


def _build_loader(token: str | None) -> FinMindLike:
    """Lazy import to keep test env light."""
    from FinMind.data import DataLoader  # type: ignore[import-not-found]

    dl = DataLoader()
    if token:
        dl.login_by_token(api_token=token)
    return dl


def fetch_bundle(
    stock_id: str,
    start: date,
    end: date,
    loader: FinMindLike | None = None,
    token: str | None = None,
    rate_limit_seconds: float = 0.6,
    apply_adjustment: bool = True,
) -> ETLBundle:
    """Pull OHLCV + institutional + day-trading frames for one stock.

    Broker chip data (top10 / gov / geo) is not in FinMind's free tier;
    columns are returned as zero placeholders so downstream scoring still
    runs. M2 will add a backfill path (TWSE / paid source) for those.

    When ``apply_adjustment`` is True (default), forward-adjusts OHLC from
    cash dividends; raw values preserved in ``raw_*`` columns and
    ``adj_factor`` column added.
    """
    from backtest_platform.data.adjustment import (
        apply_adjustment as _apply_adj,
        compute_adj_factor,
    )

    loader = loader or _build_loader(token or os.environ.get("FINMIND_TOKEN"))
    s, e = start.isoformat(), end.isoformat()

    logger.info("fetch daily bars stock={} {}..{}", stock_id, s, e)
    daily_raw = loader.taiwan_stock_daily(stock_id=stock_id, start_date=s, end_date=e)
    time.sleep(rate_limit_seconds)

    logger.info("fetch institutional flows stock={} {}..{}", stock_id, s, e)
    inst_raw = loader.taiwan_stock_institutional_investors(
        stock_id=stock_id, start_date=s, end_date=e
    )
    time.sleep(rate_limit_seconds)

    logger.info("fetch day trading stock={} {}..{}", stock_id, s, e)
    dt_raw = loader.taiwan_stock_day_trading(stock_id=stock_id, start_date=s, end_date=e)

    daily = _normalize_daily(daily_raw, stock_id)

    if apply_adjustment and not daily.empty:
        time.sleep(rate_limit_seconds)
        logger.info("fetch dividends stock={} {}..{}", stock_id, s, e)
        try:
            div_raw = loader.taiwan_stock_dividend(stock_id=stock_id, start_date=s, end_date=e)
            adj_factor = compute_adj_factor(daily, div_raw)
            daily = _apply_adj(daily, adj_factor)
            distinct_factors = adj_factor.round(6).nunique()
            n_adjusted_bars = int((adj_factor < 1.0).sum())
            logger.info(
                "applied adjustment: {} distinct factor levels, {} bars adjusted",
                distinct_factors,
                n_adjusted_bars,
            )
        except Exception as exc:  # noqa: BLE001 — adjustment is best-effort
            logger.warning("adjustment skipped due to error: {}", exc)

    institutional = _normalize_institutional(inst_raw, stock_id)
    broker_chips = _normalize_day_trading(dt_raw, stock_id)
    return ETLBundle(
        stock_id=stock_id,
        start_date=start,
        end_date=end,
        daily_bars=daily,
        institutional=institutional,
        broker_chips=broker_chips,
    )


def _normalize_daily(raw: pd.DataFrame, stock_id: str) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(
            columns=["stock_id", "trade_date", "open", "high", "low", "close", "volume", "adj_factor"]
        )
    df = raw.rename(columns=_DEFAULT_DAILY_RENAME).copy()
    df["stock_id"] = stock_id
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df["adj_factor"] = 1.0
    return df[["stock_id", "trade_date", "open", "high", "low", "close", "volume", "adj_factor"]]


def _normalize_institutional(raw: pd.DataFrame, stock_id: str) -> pd.DataFrame:
    """Pivot FinMind long-format institutional table to wide.

    FinMind name buckets observed (2024 schema):
        Foreign_Investor, Foreign_Dealer_Self, Investment_Trust,
        Dealer_self, Dealer_Hedging

    v2.md treats "外資" as Foreign_Investor + Foreign_Dealer_Self,
    "自營商" as Dealer_self + Dealer_Hedging (both proprietary trading desks).
    """
    cols_out = ["stock_id", "trade_date", "foreign_buy", "trust_buy", "dealer_buy"]
    if raw.empty:
        return pd.DataFrame(columns=cols_out)

    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["net"] = df["buy"].fillna(0) - df["sell"].fillna(0)
    net = df.pivot_table(
        index="date", columns="name", values="net", aggfunc="sum", fill_value=0
    ).reset_index()

    out = pd.DataFrame({"trade_date": net["date"]})
    out["stock_id"] = stock_id
    out["foreign_buy"] = (
        _col_or_zero(net, "Foreign_Investor") + _col_or_zero(net, "Foreign_Dealer_Self")
    ).astype("int64")
    out["trust_buy"] = _col_or_zero(net, "Investment_Trust").astype("int64")
    out["dealer_buy"] = (
        _col_or_zero(net, "Dealer_self") + _col_or_zero(net, "Dealer_Hedging")
    ).astype("int64")
    return out[cols_out]


def _normalize_day_trading(raw: pd.DataFrame, stock_id: str) -> pd.DataFrame:
    """FinMind TaiwanStockDayTrading schema (2024):
        date, stock_id, BuyAfterSale, Volume, BuyAmount, SellAmount

    The ``Volume`` column is the day-trade share count we want.
    Broker chip subgroups (top10/gov/geo) and margin_offset are not in
    FinMind free tier — left as zeros for M1, backfill in M2.
    """
    cols_out = [
        "stock_id",
        "trade_date",
        "top_broker_buy",
        "key_broker_buy",
        "gov_broker_buy",
        "geo_broker_buy",
        "day_trade_volume",
        "margin_offset_volume",
    ]
    if raw.empty:
        return pd.DataFrame(columns=cols_out)
    df = raw.rename(columns={"date": "trade_date"}).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df["stock_id"] = stock_id
    df["day_trade_volume"] = _col_or_zero(df, "Volume").astype("int64")
    for col in (
        "top_broker_buy",
        "key_broker_buy",
        "gov_broker_buy",
        "geo_broker_buy",
        "margin_offset_volume",
    ):
        df[col] = 0
    return df[cols_out]


def _col_or_zero(df: pd.DataFrame, name: str) -> pd.Series:
    """Return the column as numeric Series, or a same-length zero Series if absent."""
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").fillna(0)
    return pd.Series(0, index=df.index, dtype="int64")


def write_parquet(bundle: ETLBundle, root: Path) -> dict[str, Path]:
    """Write three parquet files; returns paths keyed by table name."""
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "daily_bars": root / f"daily_bars__{bundle.stock_id}.parquet",
        "institutional": root / f"institutional__{bundle.stock_id}.parquet",
        "broker_chips": root / f"broker_chips__{bundle.stock_id}.parquet",
    }
    bundle.daily_bars.to_parquet(paths["daily_bars"], index=False)
    bundle.institutional.to_parquet(paths["institutional"], index=False)
    bundle.broker_chips.to_parquet(paths["broker_chips"], index=False)
    return paths


@click.command()
@click.option("--stock-id", required=True, help="e.g. 2330")
@click.option("--start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory to write parquet files. Omit to skip parquet output.",
)
@click.option(
    "--db / --no-db",
    default=False,
    help="Also upsert into TimescaleDB (uses POSTGRES_* env vars).",
)
@click.option(
    "--token",
    envvar="FINMIND_TOKEN",
    default=None,
    help="FinMind API token (or set FINMIND_TOKEN env var).",
)
def main(
    stock_id: str,
    start: datetime,
    end: datetime,
    output: Path | None,
    db: bool,
    token: str | None,
) -> None:
    """Pull one stock's OHLCV + chip data via FinMind."""
    bundle = fetch_bundle(stock_id, start.date(), end.date(), token=token)
    logger.info(
        "fetched stock={} rows daily={} inst={} chips={}",
        stock_id,
        len(bundle.daily_bars),
        len(bundle.institutional),
        len(bundle.broker_chips),
    )
    if output:
        paths = write_parquet(bundle, output)
        for table, path in paths.items():
            logger.info("wrote {} -> {}", table, path)
    if db:
        from backtest_platform.data.db_writer import upsert_bundle

        upsert_bundle(bundle)
    if not output and not db:
        logger.info("dry-run complete (no --output or --db specified)")


if __name__ == "__main__":
    main()
