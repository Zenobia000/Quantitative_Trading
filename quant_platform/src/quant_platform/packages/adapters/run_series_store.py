"""Per-run series sidecar store (equity / drawdown / trades).

The append-only runs ledger (``runs_store``) stays lean — list/compare read the
whole file, so embedding multi-year equity arrays there would bloat every line.
Instead each run's heavy series live in a per-run JSON sidecar under
``reports/series/{run_id}.json``, loaded only when a specific run's detail is
requested (``GET /runs/{id}/equity`` · ``/trades``). Dependency-free JSON keeps it
diffable and matches the ``runs_store`` JSONL philosophy.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

DEFAULT_SERIES_DIR = Path("reports") / "series"


def series_path(run_id: str, series_dir: Path | str = DEFAULT_SERIES_DIR) -> Path:
    """Sidecar path for one run's series."""
    return Path(series_dir) / f"{run_id}.json"


def write_series(
    run_id: str,
    equity: Sequence[float],
    drawdown: Sequence[float],
    trades: Sequence[dict[str, Any]],
    series_dir: Path | str = DEFAULT_SERIES_DIR,
) -> Path:
    """Write a run's equity / drawdown / trades sidecar (creates parent dirs)."""
    p = series_path(run_id, series_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "equity": [float(x) for x in equity],
        "drawdown": [float(x) for x in drawdown],
        "trades": [dict(t) for t in trades],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    return p


def read_series(
    run_id: str, series_dir: Path | str = DEFAULT_SERIES_DIR
) -> dict[str, Any] | None:
    """Read a run's series sidecar; ``None`` if it was never persisted."""
    p = series_path(run_id, series_dir)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
