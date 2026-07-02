"""Parquet cache reader for FinMind ETL bundles (M1 既有 write_parquet 的反向).

The bundle ingester reads from parquet first, only hitting FinMind API when
cache miss. This is the main mitigation for FinMind 600 req/hr rate limit
(plan v3.0 R2): 100 stocks × 7 years would need 2100 API calls if naive;
with parquet cache + day-incremental, drops to ~7 calls/day.

Layout (matches `data/finmind_etl.py:write_parquet`):
    data/parquet/
        daily_bars__<stock_id>.parquet
        institutional__<stock_id>.parquet
        broker_chips__<stock_id>.parquet
        manifest.json        <- bundle lineage (coverage / stock_count / hash)
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from backtest_platform.data.schemas import ETLBundle

# Lineage sidecar written next to the parquet files. `runs.bundle_ref` can point
# at this file (or its aggregate data_hash) to record which data a run consumed.
MANIFEST_NAME = "manifest.json"


@dataclass(slots=True, frozen=True)
class ParquetCache:
    """Read-side companion to `data/finmind_etl.write_parquet`."""

    root: Path

    def exists(self, stock_id: str) -> bool:
        """All three tables must be present to consider cache valid."""
        return all(
            (self.root / f"{table}__{stock_id}.parquet").exists()
            for table in ("daily_bars", "institutional", "broker_chips")
        )

    def load(self, stock_id: str) -> ETLBundle:
        """Read three parquet files into an ETLBundle.

        Caller must check `exists()` first; missing files raise FileNotFoundError.
        Date range is inferred from the daily_bars frame, not the filename.
        """
        daily = pd.read_parquet(self.root / f"daily_bars__{stock_id}.parquet")
        inst = pd.read_parquet(self.root / f"institutional__{stock_id}.parquet")
        chips = pd.read_parquet(self.root / f"broker_chips__{stock_id}.parquet")

        if daily.empty:
            raise ValueError(f"daily_bars__{stock_id}.parquet is empty")

        start = pd.to_datetime(daily["trade_date"].min()).date()
        end = pd.to_datetime(daily["trade_date"].max()).date()
        return ETLBundle(
            stock_id=stock_id,
            start_date=start,
            end_date=end,
            daily_bars=daily,
            institutional=inst,
            broker_chips=chips,
        )

    def load_or_none(self, stock_id: str) -> ETLBundle | None:
        """Convenience: return None on cache miss instead of raising."""
        return self.load(stock_id) if self.exists(stock_id) else None


def _gap_ranges(
    cached: ETLBundle | None, start: date, end: date
) -> list[tuple[date, date]]:
    """Ranges that must be fetched to cover [start, end] given the cache.

    Returns the missing head and/or tail slices only — never the whole span —
    so an ingest that extends coverage does NOT re-fetch (and thus never risks
    overwriting) data already on disk. Gaps are strictly outside the cached span
    (`±1 day`), so the fetched data does not overlap the cache.
    """
    if cached is None:
        return [(start, end)]
    ranges: list[tuple[date, date]] = []
    if start < cached.start_date:
        ranges.append((start, cached.start_date - timedelta(days=1)))
    if end > cached.end_date:
        ranges.append((cached.end_date + timedelta(days=1), end))
    return ranges


def _merge_frame(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concat frames, de-duplicate on (stock_id, trade_date), sort by date.

    ``keep='last'`` lets a freshly fetched row win over a stale cached one on any
    incidental boundary overlap (e.g. re-computed adjustment factors)."""
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        # keep the column schema of the first frame for an empty result
        return frames[0].iloc[0:0].reset_index(drop=True)
    combined = pd.concat(non_empty, ignore_index=True)
    key = [c for c in ("stock_id", "trade_date") if c in combined.columns]
    if key:
        combined = combined.drop_duplicates(subset=key, keep="last")
    if "trade_date" in combined.columns:
        combined = combined.sort_values("trade_date")
    return combined.reset_index(drop=True)


def _merge_bundles(stock_id: str, parts: list[ETLBundle]) -> ETLBundle:
    """Merge cached + freshly fetched bundle parts into one contiguous bundle.

    The resulting date span is derived from the merged daily_bars, so a partial
    ingest keeps the full historical range rather than shrinking to the fetched
    slice (the HIGH-severity cache-clobber bug this guards against).
    """
    daily = _merge_frame([p.daily_bars for p in parts])
    inst = _merge_frame([p.institutional for p in parts])
    chips = _merge_frame([p.broker_chips for p in parts])
    if daily.empty:
        raise ValueError(f"merged daily_bars for {stock_id} is empty")
    start = pd.to_datetime(daily["trade_date"].min()).date()
    end = pd.to_datetime(daily["trade_date"].max()).date()
    return ETLBundle(
        stock_id=stock_id,
        start_date=start,
        end_date=end,
        daily_bars=daily,
        institutional=inst,
        broker_chips=chips,
    )


def _frame_digest(df: pd.DataFrame) -> bytes:
    """Order-independent content digest of a frame (sorted by its natural key)."""
    if df.empty:
        return b""
    key = [c for c in ("stock_id", "trade_date") if c in df.columns]
    ordered = df.sort_values(key).reset_index(drop=True) if key else df
    return hashlib.sha256(
        pd.util.hash_pandas_object(ordered, index=False).values.tobytes()
    ).digest()


def _bundle_hash(bundle: ETLBundle) -> str:
    """Stable 16-hex digest over a bundle's three frames (data lineage id)."""
    h = hashlib.sha256()
    for df in (bundle.daily_bars, bundle.institutional, bundle.broker_chips):
        h.update(_frame_digest(df))
    return h.hexdigest()[:16]


def write_manifest(cache_root: Path, bundle: ETLBundle) -> Path:
    """Upsert ``bundle``'s lineage entry into ``<cache_root>/manifest.json``.

    Read-modify-write so a universe ingest (finmind_bundle loops symbols one at a
    time) accumulates every stock into one manifest. Recomputes the aggregate
    coverage window, stock count and combined data hash on each call. Written
    atomically (temp + os.replace). Safe on a corrupt/empty existing file.
    """
    path = Path(cache_root) / MANIFEST_NAME
    manifest: dict = {"schema_version": 1, "stocks": {}}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                manifest = loaded
        except (json.JSONDecodeError, OSError):
            pass

    stocks = manifest.setdefault("stocks", {})
    stocks[bundle.stock_id] = {
        "start": bundle.start_date.isoformat(),
        "end": bundle.end_date.isoformat(),
        "rows": len(bundle.daily_bars),
        "data_hash": _bundle_hash(bundle),
    }

    # aggregate rollup — ISO date strings sort lexicographically
    starts = [v["start"] for v in stocks.values()]
    ends = [v["end"] for v in stocks.values()]
    agg = hashlib.sha256()
    for sid in sorted(stocks):
        agg.update(stocks[sid]["data_hash"].encode())

    manifest.update(
        {
            "schema_version": 1,
            "stock_count": len(stocks),
            "coverage": {"start": min(starts), "end": max(ends)},
            "data_hash": agg.hexdigest()[:16],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    Path(cache_root).mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path


def cached_or_fetch(
    stock_id: str,
    start: date,
    end: date,
    cache: ParquetCache,
    fetch_fn=None,  # callable matching `fetch_bundle` signature; default = M1 ETL
) -> ETLBundle:
    """Return a bundle covering [start, end], fetching only what the cache lacks.

    Range check is inclusive on both ends; a full cache hit requires
    `cached.start_date <= start <= end <= cached.end_date`. On a partial hit only
    the missing head/tail gap is fetched, then merged with the cached data and
    written back atomically — so extending coverage never destroys existing
    (possibly paid) history. Every call refreshes the lineage manifest.
    """
    cached = cache.load_or_none(stock_id)
    if cached and cached.start_date <= start and end <= cached.end_date:
        write_manifest(cache.root, cached)
        return cached

    if fetch_fn is None:
        from backtest_platform.data.finmind_etl import fetch_bundle as fetch_fn

    fetched = [fetch_fn(stock_id, gap_start, gap_end)
               for gap_start, gap_end in _gap_ranges(cached, start, end)]
    parts = ([cached] if cached else []) + fetched
    merged = _merge_bundles(stock_id, parts)

    from backtest_platform.data.finmind_etl import write_parquet

    write_parquet(merged, cache.root)
    write_manifest(cache.root, merged)
    return merged
