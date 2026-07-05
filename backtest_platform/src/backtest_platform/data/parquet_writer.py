"""Atomic parquet writer for FinMind ETL bundles (W5.2c-2).

Extracted from ``data.finmind_etl`` so the parquet write path carries **zero DB
dependency**. This matters for the architecture fitness wall: research reaches
``finlab_source`` (module-level) → ``write_parquet`` only for parquet output;
routing that through ``finmind_etl`` (which lazy-imports ``db_writer``) created a
second ``research → db_writer`` chain that would break contract 1 once
``db_writer`` re-exports the extracted service writers (W5.2d/e). Keeping the
parquet writer pure (pandas / pathlib / stdlib + ETLBundle) severs research from
the DB write path honestly, with no import-linter exemption.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pandas as pd

from backtest_platform.data.schemas import ETLBundle


def _atomic_to_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write ``df`` to ``path`` atomically: write a temp sibling then os.replace.

    A crash mid-write leaves the previous parquet intact rather than a truncated
    file. ``os.replace`` is atomic on POSIX when src/dst share a directory, so the
    temp file is created alongside the target (not in the system temp dir).
    """
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        df.to_parquet(tmp, index=False)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_parquet(bundle: ETLBundle, root: Path) -> dict[str, Path]:
    """Write three parquet files atomically; returns paths keyed by table name.

    Each file is written to a temp sibling and renamed into place, so a partial
    write never corrupts an existing cache (see ``_atomic_to_parquet``).
    """
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "daily_bars": root / f"daily_bars__{bundle.stock_id}.parquet",
        "institutional": root / f"institutional__{bundle.stock_id}.parquet",
        "broker_chips": root / f"broker_chips__{bundle.stock_id}.parquet",
    }
    _atomic_to_parquet(bundle.daily_bars, paths["daily_bars"])
    _atomic_to_parquet(bundle.institutional, paths["institutional"])
    _atomic_to_parquet(bundle.broker_chips, paths["broker_chips"])
    return paths
