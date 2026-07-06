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

from quant_platform.services.data_platform import finlab_source
from quant_platform.services.data_platform.finlab_source import Getter, ingest_universe_finlab
from quant_platform.packages.adapters.finlab_universe import select_survivorship_universe
from quant_platform.services.research_validation.workflows.config import UniverseConfig


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
    getter = getter or _finlab_getter(exchange=cfg.exchange)

    mv = getter(finlab_source._MARKET_VALUE)
    close = getter(finlab_source._ADJ["close"])
    turnover = getter(finlab_source._TURNOVER)

    # Eligibility (ADR-007 Slice 3): fetch the 全額交割/處置/注意 status frames only when
    # asked — the time-varying exclusion mask is opt-in (default off = unchanged).
    exclude_frames = _eligibility_frames(getter) if cfg.exclude_flagged else ()

    rebalance_dates = _quarterly_rebalance_dates(cfg.span_start, cfg.span_end)
    universe = select_survivorship_universe(
        mv, close, turnover, rebalance_dates,
        top_n=cfg.top_n, min_turnover=cfg.min_turnover,
        exclude_frames=exclude_frames,
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


#: FinLab status-frame keys for the eligibility mask (verified live 2026-07-05):
#: 變更交易 includes 全額交割; 處置/注意 are the ESB attention-disposal windows.
_ELIGIBILITY_KEYS: tuple[str, ...] = (
    "change_transaction:變更交易",
    "esb_attention_disposal:處置有價證券",
    "esb_attention_disposal:注意有價證券",
)


def _finlab_getter(exchange: str | None = None) -> Getter:
    """Authenticate FinLab and return its real getter (lazy — imports finlab).

    When ``exchange`` is given, apply the static board filter via finlab's native
    ``data.set_universe`` (ADR-007 Slice 3 — we reuse finlab's eligibility layer, we
    do NOT rebuild board/sector/asset-type filtering ourselves) before returning the
    getter, so every subsequent ``data.get`` is scoped to that board."""
    finlab_source.login()
    if exchange:
        from finlab import data as _fdata

        _fdata.set_universe(exchange=exchange)
    return finlab_source._default_getter()


def _eligibility_frames(getter: Getter) -> tuple[pd.DataFrame, ...]:
    """Fetch the 全額交割/處置/注意 status frames via ``getter`` (defensive).

    A frame that errors (key drift / entitlement) is skipped rather than aborting the
    build — a partial mask still excludes what it can, and the missing status is
    simply not applied."""
    frames: list[pd.DataFrame] = []
    for key in _ELIGIBILITY_KEYS:
        try:
            frames.append(getter(key))
        except Exception:  # key drift / entitlement — skip this status, never abort
            continue
    return tuple(frames)


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
