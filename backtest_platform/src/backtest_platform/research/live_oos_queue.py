"""Live-OOS selection queue (rebuild Goal 4; Goal 10 will consume it).

The **human-selection layer**: any candidate a human picks for zero-capital live OOS
lands here as an append-only ``LiveOOSQueueItem`` carrying the selection audit
(``selected_by`` / ``selection_reason`` / ``override``) that ``watch_registry`` does
not model. This wave only PERSISTS + QUERIES the queue; Goal 10 wires the
``paper_watch_berth`` items to ``watch_registry`` and the ``paper_replay`` items to
``workflows.paper_replay``, folding the observation clock. Until then a queued item's
berth fields (``enrolled_on`` / ``expiry_date`` / ``days_remaining`` …) are honestly
``null`` — matching the contract's ``paper_replay`` fixture (README §7).

Append-only JSONL, same philosophy as ``watch_registry`` / ``runs_store``; current
state for a ``queue_id`` is the latest record carrying it. ``position_size`` is always
``0.0`` (zero-capital observation; ``evaluate_two_stage`` never sizes a non-REAL verdict).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest_platform.validation.report import dsr_band

DEFAULT_QUEUE_PATH = Path("reports") / "live_oos_queue.jsonl"
OBSERVATION_KINDS: frozenset[str] = frozenset({"paper_watch_berth", "paper_replay", "after_close"})

_TWT = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_TWT).isoformat(timespec="seconds")


def _read(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _append(item: dict[str, Any], path: Path | str) -> dict[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
    return item


def enqueue(
    candidate_id: str,
    strategy: str,
    evaluation_id: str,
    *,
    selected_by: str = "operator",
    selection_reason: str | None,
    recommendation_at_selection: str,
    override: bool = False,
    override_reason: str | None = None,
    observation_kind: str = "paper_replay",
    report_pack_ref: str | None = None,
    dsr: float | None = None,
    path: Path | str = DEFAULT_QUEUE_PATH,
    at: str | None = None,
) -> dict[str, Any]:
    """Append one live-OOS queue item (state ``queued``) and return it.

    Berth fields stay ``null`` (Goal 10 folds them from ``watch_registry``); only a
    ``paper_watch_berth`` selection carries a computed ``dsr_band`` for the UI.
    """
    if observation_kind not in OBSERVATION_KINDS:
        raise ValueError(f"unknown observation_kind {observation_kind!r}; choose from {sorted(OBSERVATION_KINDS)}")
    ts = at or _now_iso()
    queue_id = f"loq_{strategy}_{ts.replace(':', '').replace('-', '').replace('+', '')[:16]}"
    band = dsr_band(dsr) if observation_kind == "paper_watch_berth" else None
    item = {
        "queue_id": queue_id,
        "candidate_id": candidate_id,
        "strategy": strategy,
        "evaluation_id": evaluation_id,
        "selected_at": ts,
        "selected_by": selected_by,
        "selection_reason": selection_reason,
        "recommendation_at_selection": recommendation_at_selection,
        "override": override,
        "override_reason": override_reason,
        "state": "queued",
        "observation": {
            "kind": observation_kind,
            "watch_registry_ref": strategy if observation_kind == "paper_watch_berth" else None,
            "dsr_band": band.lower() if isinstance(band, str) else None,
            "enrolled_on": None,
            "expiry_date": None,
            "observation_days": None,
            "observed_trading_days": None,
            "days_remaining": None,
            "position_size": 0.0,
        },
        "report_pack_ref": report_pack_ref,
        "links": {
            "report": f"GET /research/evaluations/{evaluation_id}/report",
            "candidate": f"GET /research/candidates/{candidate_id}",
            "strategy_asset": f"GET /research/strategies/{strategy}",
        },
    }
    return _append(item, path)


def list_queue(
    *, state: str | None = None, path: Path | str = DEFAULT_QUEUE_PATH
) -> list[dict[str, Any]]:
    """Latest queue item per ``queue_id`` (newest first), optionally filtered by state."""
    folded: dict[str, dict[str, Any]] = {}
    for rec in _read(path):
        folded[rec["queue_id"]] = rec
    items = sorted(folded.values(), key=lambda r: r.get("selected_at", ""), reverse=True)
    if state is not None:
        items = [i for i in items if i.get("state") == state]
    return items


def get_queue_item(queue_id: str, *, path: Path | str = DEFAULT_QUEUE_PATH) -> dict[str, Any] | None:
    """The latest record for ``queue_id`` (``None`` if never enqueued)."""
    match: dict[str, Any] | None = None
    for rec in _read(path):
        if rec.get("queue_id") == queue_id:
            match = rec
    return match
