"""FinMind universe batch-ingest helper (data layer).

Resolves a universe of Taiwan-stock ids (env override or default top-10),
then fetches each stock's ``ETLBundle`` through the parquet cache
(``cached_or_fetch`` short-circuits the FinMind API when local parquet already
covers the requested range), isolating per-symbol failures so one bad stock
never aborts the whole batch.

This is the ingest primitive consumed by ``orchestration/collaborators.py``'s
FinMind ingest path. It is DATA-LAYER only — the zipline bundle-writer callback
(``finmind_to_bundle`` / ``ensure_registered`` / the daily-frame normalizers)
was removed with the engines/ tree (ADR-037; sim is the only engine). Re-adding
an event engine later would introduce a fresh adapter, not resurrect this module.

Universe selection (priority order):
    1. UNIVERSE_FINMIND env var (comma-separated stock_ids, e.g. "2330,2454")
    2. UNIVERSE_FILE env var (path to text file, one stock_id per line)
    3. Default top-10 台股 (constant ``DEFAULT_UNIVERSE``)

Daily bars sourced from FinMind ``taiwan_stock_daily``, already
cash-dividend-adjusted by ``data/adjustment.py``.

Cache strategy: ``ParquetCache`` short-circuits FinMind API hits when local
parquet covers the requested date range. First-time backfill of 100 stocks
× 7 years takes ~2 hours (rate-limited by FinMind 600 req/hr × 4 endpoints);
subsequent ingests with cache are <30 seconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from loguru import logger

from quant_platform.packages.infrastructure.config.universe import DEFAULT_UNIVERSE  # re-export (back-compat)
from quant_platform.services.data_platform.parquet_cache import (
    ParquetCache,
    cached_or_fetch,
)
from quant_platform.services.data_platform.schemas import ETLBundle

__all__ = [
    "DEFAULT_CACHE_DIR",
    "DEFAULT_UNIVERSE",
    "UniverseIngestResult",
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

    Used by scripts / orchestration that need ``ETLBundle`` dicts. The
    single-stock failure path is the critical contract: one bad symbol must not
    abort the whole batch (FinMind transient 5xx is common).

    Raises ``RuntimeError`` only when *every* symbol fails — silently returning
    an empty result is worse, because downstream consumers would treat an empty
    universe as a successful (but useless) ingest.
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
        except Exception as exc:
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
