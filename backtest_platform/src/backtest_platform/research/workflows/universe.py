"""build_universe workflow — survivorship-clean FinLab universe as a platform service.

Rebuilds the inst_flow re-validation universe that used to live in the deleted
``scripts/inst_flow_revalidate_finlab.py`` as an ADR-029-shaped workflow: a strategy
declares a :class:`UniverseConfig`, this workflow executes it. The steps mirror the
old driver exactly (only the data is honest):

  1. fetch the FinLab wide frames (market cap / adj-close / turnover) via the getter;
  2. select the point-in-time, survivorship-clean union across quarterly rebalances
     (``research.finlab_universe.select_survivorship_universe`` — delisted names are
     retained for the quarters they were live);
  3. batch-ingest that universe into a dedicated parquet cache
     (``data.finlab_source.ingest_universe_finlab``);
  4. write a ``universe_manifest.json`` recording params, symbols, alive/delisted and
     the ingest ok/failed counts — the manifest is the reproducible provenance record.

FinLab is imported lazily and ONLY when ``getter`` is None, so the module (and the
test suite) never depends on finlab. Ingest failures are surfaced in the result and
the manifest, never swallowed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pandas as pd

from backtest_platform.data import finlab_source
from backtest_platform.data.finlab_source import Getter, ingest_universe_finlab
from backtest_platform.research.finlab_universe import select_survivorship_universe
from backtest_platform.research.workflows.config import UniverseConfig


@dataclass(frozen=True)
class UniverseBuildResult:
    """Outcome of a survivorship-clean universe build (immutable)."""

    strategy: str
    universe: tuple[str, ...]
    n_alive: int
    n_delisted: int
    n_ingested_ok: int
    n_ingested_failed: int
    manifest_path: str


def run_build_universe(cfg: UniverseConfig, getter: Getter | None = None) -> UniverseBuildResult:
    """Build + ingest the survivorship-clean universe declared by ``cfg``.

    ``getter`` is a ``finlab.data.get``-like callable (dataset key → wide frame); when
    None the workflow authenticates and uses FinLab's real getter (the only path that
    imports finlab). The selected universe is the union of per-quarter liquid large
    names alive on each rebalance date — so delisted names survive in the union.
    """
    getter = getter or _finlab_getter()

    mv = getter(finlab_source._MARKET_VALUE)
    close = getter(finlab_source._ADJ["close"])
    turnover = getter(finlab_source._TURNOVER)

    rebalance_dates = _quarterly_rebalance_dates(cfg.span_start, cfg.span_end)
    universe = select_survivorship_universe(
        mv, close, turnover, rebalance_dates,
        top_n=cfg.top_n, min_turnover=cfg.min_turnover,
    )
    n_alive, n_delisted = _alive_delisted_counts(close, universe)

    ingest = ingest_universe_finlab(
        universe, cfg.span_start, cfg.span_end, cache_dir=cfg.cache_dir, getter=getter,
    )

    manifest_path = _write_manifest(
        cfg, universe, n_alive, n_delisted, ingest, len(rebalance_dates),
    )
    return UniverseBuildResult(
        strategy=cfg.strategy,
        universe=tuple(universe),
        n_alive=n_alive,
        n_delisted=n_delisted,
        n_ingested_ok=len(ingest.ok_symbols),
        n_ingested_failed=len(ingest.failed_symbols),
        manifest_path=manifest_path,
    )


def _finlab_getter() -> Getter:
    """Authenticate FinLab and return its real getter (lazy — imports finlab)."""
    finlab_source.login()
    return finlab_source._default_getter()


def _quarterly_rebalance_dates(start: date, end: date) -> list[date]:
    """Quarter-end rebalance dates across ``[start, end]`` (pandas ``QE``)."""
    return [ts.date() for ts in pd.date_range(start, end, freq="QE")]


def _alive_delisted_counts(close: pd.DataFrame, universe: list[str]) -> tuple[int, int]:
    """Split the universe into alive-at-span-end vs delisted by last adj-close row."""
    if not universe:
        return 0, 0
    last_row = close.sort_index()[list(universe)].iloc[-1]
    n_alive = int(last_row.notna().sum())
    return n_alive, len(universe) - n_alive


def _write_manifest(cfg, universe, n_alive, n_delisted, ingest, n_rebalances) -> str:
    """Write ``universe_manifest.json`` into the cache dir; return its path."""
    from pathlib import Path

    root = Path(cfg.cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "universe_manifest.json"
    manifest = {
        "strategy": cfg.strategy,
        "params": {
            "span_start": cfg.span_start.isoformat(),
            "span_end": cfg.span_end.isoformat(),
            "top_n": cfg.top_n,
            "min_turnover": cfg.min_turnover,
            "rebalance": "quarterly",
            "n_rebalances": n_rebalances,
            "cache_dir": str(cfg.cache_dir),
        },
        "symbols": list(universe),
        "n_symbols": len(universe),
        "n_alive": n_alive,
        "n_delisted": n_delisted,
        "ingest": {
            "ok": len(ingest.ok_symbols),
            "failed": len(ingest.failed_symbols),
            "failed_symbols": list(ingest.failed_symbols),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
