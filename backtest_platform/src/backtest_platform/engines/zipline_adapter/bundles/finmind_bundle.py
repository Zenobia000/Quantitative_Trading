"""FinMind → zipline-reloaded bundle ingester (ADR-013 + ADR-014, plan v3.0 §4.1).

Pulls Taiwan-stock OHLCV via FinMind API (M1 既有 ETL), normalizes to
zipline daily-bar format, and writes to zipline's bcolz-backed bundle
storage. Subsequent `zipline run -b finmind` reads directly from the
bundle without re-hitting FinMind.

Universe selection (priority order):
    1. UNIVERSE_FINMIND env var (comma-separated stock_ids, e.g. "2330,2454")
    2. UNIVERSE_FILE env var (path to text file, one stock_id per line)
    3. Default top-10 台股 (constant `DEFAULT_UNIVERSE`)

Daily bars sourced from FinMind `taiwan_stock_daily`, already
cash-dividend-adjusted by `data/adjustment.py`. We write the adjusted OHLC
into zipline's bundle and leave `adjustment_writer` empty (no
double-adjustment).

Institutional + chip data is NOT written to the bundle — zipline's bundle
schema only stores OHLCV. Strategy `handle_data` will pull chip data from
the parquet cache separately via `enrich_with_chips()` helper (M2 Sprint 2).

Cache strategy: `ParquetCache` short-circuits FinMind API hits when local
parquet covers the requested date range. First-time backfill of 100 stocks
× 7 years takes ~2 hours (rate-limited by FinMind 600 req/hr × 4 endpoints);
subsequent ingests with cache are <30 seconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
from loguru import logger

from backtest_platform.config.universe import DEFAULT_UNIVERSE  # re-export (back-compat)
from backtest_platform.data.schemas import ETLBundle
from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
    ParquetCache,
    cached_or_fetch,
)

__all__ = [
    "DEFAULT_CACHE_DIR",
    "DEFAULT_UNIVERSE",
    "UniverseIngestResult",
    "ensure_registered",
    "finmind_to_bundle",
    "ingest_universe",
]


@dataclass(slots=True, frozen=True)
class UniverseIngestResult:
    """Outcome of a batch ingest run.

    ``bundles`` keeps successful symbols only; failing symbols are recorded
    in ``failed_symbols`` so the caller can decide whether to retry, log, or
    fall through to a partial-universe backtest.
    """

    bundles: dict[str, ETLBundle] = field(default_factory=dict)
    failed_symbols: list[str] = field(default_factory=list)


# ``DEFAULT_UNIVERSE`` now lives in ``config.universe`` (a zero-dep leaf module) and
# is imported above; it is re-exported here so existing importers keep working.

# Default parquet cache directory (relative to repo root).
DEFAULT_CACHE_DIR = Path("data/parquet")


def _resolve_universe(environ: dict) -> list[str]:
    """Resolve stock_id list from env (CLI override path), else default."""
    if "UNIVERSE_FINMIND" in environ:
        return [s.strip() for s in environ["UNIVERSE_FINMIND"].split(",") if s.strip()]
    if "UNIVERSE_FILE" in environ:
        path = Path(environ["UNIVERSE_FILE"])
        return [
            line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
    return list(DEFAULT_UNIVERSE)


def _resolve_cache_dir(environ: dict) -> Path:
    if "FINMIND_PARQUET_CACHE" in environ:
        return Path(environ["FINMIND_PARQUET_CACHE"])
    return DEFAULT_CACHE_DIR


def ingest_universe(
    universe: list[str] | tuple[str, ...] | None = None,
    *,
    start: date,
    end: date,
    cache_dir: Path | None = None,
) -> UniverseIngestResult:
    """Batch-ingest a universe of symbols, isolating per-symbol failures.

    Used by ``finmind_to_bundle`` (zipline callback) and by direct scripts
    that need ETLBundle dicts without going through the zipline writer
    pipeline. The single-stock failure path is the critical contract: one
    bad symbol must not abort the whole batch (FinMind transient 5xx is
    common).

    Raises ``RuntimeError`` only when *every* symbol fails — silently
    returning an empty result is worse, because downstream zipline would
    write an empty bundle file that confuses later runs.
    """
    symbols = list(universe) if universe is not None else list(DEFAULT_UNIVERSE)
    cache_root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    cache = ParquetCache(root=cache_root)

    bundles: dict[str, ETLBundle] = {}
    failed: list[str] = []
    for symbol in symbols:
        try:
            bundles[symbol] = cached_or_fetch(symbol, start, end, cache)
        except Exception as exc:  # noqa: BLE001 — per-symbol isolation is the point
            logger.error("ingest failed stock={} error={}", symbol, exc)
            failed.append(symbol)

    if not bundles:
        raise RuntimeError(
            f"no stocks ingested — every symbol in universe failed (failed={failed})"
        )

    logger.info(
        "universe ingest done: ok={} failed={}", len(bundles), len(failed)
    )
    return UniverseIngestResult(bundles=bundles, failed_symbols=failed)


def _to_zipline_daily_frame(bundle: ETLBundle, calendar) -> pd.DataFrame:
    """Convert ETLBundle.daily_bars → zipline daily-bar format.

    zipline expects:
        index = DatetimeIndex covering EVERY XTAI session in [start, end]
                (timezone-naive, UTC normalized)
        columns = ['open', 'high', 'low', 'close', 'volume']
        all floats except volume (int64)

    Critical: zipline's `BcolzDailyBarWriter._write_internal` asserts
    `len(df) == len(sessions_in_range)`. FinMind 偶有缺失 sessions（停止
    交易整股、單檔暫停等），我們必須補齊：
    - Forward-fill OHLC (假設停止交易日價格不變)
    - Volume = 0 (沒成交)

    Filtering vs reindexing:
    - 落在 XTAI 不認的日子 → drop
    - 在 XTAI session 但 FinMind 沒給 → ffill + volume=0
    """
    df = bundle.daily_bars.copy()
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    df = df[["open", "high", "low", "close", "volume"]]

    # Strip timezone from session index to match df index
    sessions_in_range = calendar.sessions_in_range(df.index.min(), df.index.max())
    sessions_naive = pd.DatetimeIndex(
        [s.tz_localize(None) if s.tz else s for s in sessions_in_range]
    )

    # Drop rows on non-session dates (FinMind 偶見資料溢出 calendar)
    df = df.loc[df.index.isin(sessions_naive)]

    # Reindex to ALL sessions in range; forward-fill OHLC, volume=0 for missing
    df = df.reindex(sessions_naive)
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce").ffill()
    df["volume"] = df["volume"].fillna(0).astype("int64")

    # Edge case: leading NaN（最早幾天 FinMind 沒給）→ drop
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df


def _build_asset_metadata(
    sid_map: dict[str, int], bundles: dict[str, ETLBundle]
) -> pd.DataFrame:
    """Construct asset_db_writer-compatible equities frame.

    Required columns (zipline-reloaded 3.x):
        symbol, asset_name, start_date, end_date, first_traded,
        auto_close_date, exchange
    """
    rows = []
    for symbol, sid in sid_map.items():
        b = bundles[symbol]
        start_ts = pd.Timestamp(b.start_date)
        end_ts = pd.Timestamp(b.end_date)
        rows.append(
            {
                "sid": sid,
                "symbol": symbol,
                "asset_name": symbol,  # M2 ok; M3 enrich with company names
                "start_date": start_ts,
                "end_date": end_ts,
                "first_traded": start_ts,
                "auto_close_date": end_ts + pd.Timedelta(days=1),
                "exchange": "XTAI",
            }
        )
    df = pd.DataFrame(rows).set_index("sid")
    return df


def _iter_daily_bars(
    sid_map: dict[str, int], frames: dict[str, pd.DataFrame]
):
    """Generator yielding (sid, daily_frame) tuples for daily_bar_writer.

    Empty frames skipped — zipline writer raises on empty data.
    """
    for symbol, sid in sid_map.items():
        df = frames[symbol]
        if df.empty:
            logger.warning("skipping {} (empty frame after normalization)", symbol)
            continue
        yield sid, df


def finmind_to_bundle(
    environ,
    asset_db_writer,
    minute_bar_writer,
    daily_bar_writer,
    adjustment_writer,
    calendar,
    start_session,
    end_session,
    cache,
    show_progress,
    output_dir,
):
    """zipline bundle ingest callback (registered as 'finmind' below).

    Called by `zipline ingest -b finmind`. Receives writers from zipline
    that persist to bcolz/sqlite under ZIPLINE_ROOT/data/finmind/.

    Parameters reflect zipline-reloaded 3.0.4's bundle protocol. We do not
    use `cache` (zipline's request cache), `minute_bar_writer` (no minute
    data in M2), or `output_dir` (writers handle paths).
    """
    universe = _resolve_universe(environ)
    cache_dir = _resolve_cache_dir(environ)

    # zipline passes pandas-friendly date objects; M1 ETL wants `datetime.date`.
    start_date = start_session.date() if hasattr(start_session, "date") else date.fromisoformat(
        str(start_session)[:10]
    )
    end_date = end_session.date() if hasattr(end_session, "date") else date.fromisoformat(
        str(end_session)[:10]
    )

    logger.info(
        "finmind bundle ingest: universe={} range={}..{}",
        universe,
        start_date,
        end_date,
    )

    # Phase 1 — fetch (or read from cache) every stock's bundle; delegate
    # to ingest_universe so error-isolation logic stays single-sourced.
    result = ingest_universe(
        universe, start=start_date, end=end_date, cache_dir=cache_dir
    )
    bundles = result.bundles
    if result.failed_symbols:
        logger.warning(
            "bundle ingest skipped {} symbol(s): {}",
            len(result.failed_symbols),
            result.failed_symbols,
        )

    # Phase 2 — normalize to zipline daily-bar format
    frames: dict[str, pd.DataFrame] = {
        sym: _to_zipline_daily_frame(b, calendar) for sym, b in bundles.items()
    }
    sid_map = {symbol: idx for idx, symbol in enumerate(bundles.keys())}

    # Phase 3 — write asset metadata
    metadata = _build_asset_metadata(sid_map, bundles)
    exchanges = pd.DataFrame(
        [{"exchange": "XTAI", "canonical_name": "XTAI", "country_code": "TW"}]
    )
    asset_db_writer.write(equities=metadata, exchanges=exchanges)
    logger.info("wrote asset metadata: {} symbols", len(metadata))

    # Phase 4 — write daily bars
    daily_bar_writer.write(
        _iter_daily_bars(sid_map, frames), show_progress=show_progress
    )
    logger.info(
        "wrote daily bars: total_rows={}",
        sum(len(f) for f in frames.values()),
    )

    # Phase 5 — write adjustments (no splits/dividends: OHLC already
    # cash-dividend-adjusted in M1 ETL → zipline would double-adjust).
    # Passing None lets zipline write an empty bcolz adjustments file.
    adjustment_writer.write(splits=None, dividends=None)
    logger.info("wrote adjustments (empty — pre-adjusted in M1 ETL)")


def ensure_registered() -> None:
    """Register the ``finmind`` bundle with zipline's process-global registry.

    Registration is an EXPLICIT call rather than an import-time side-effect
    (dependency-untangle refactor). This keeps the module importable for its pure
    helpers — ``DEFAULT_UNIVERSE`` / ``ingest_universe`` / the frame-normalization
    functions — WITHOUT mutating zipline's global registry and without requiring
    zipline to be importable at all (zipline is imported lazily, only here).

    Idempotent: re-registering the same name is a no-op, so callers may invoke it
    freely. Call it at every zipline entry point (``cli.py`` before
    ``run_algorithm``, ``list-bundles``). The ``calendar_name`` must match an
    ``exchange_calendars`` calendar; XTAI is the Taiwan Stock Exchange.
    """
    from zipline.data.bundles import bundles as _registry
    from zipline.data.bundles import register

    if "finmind" in _registry:
        return
    register("finmind", finmind_to_bundle, calendar_name="XTAI")
