"""Live-OOS queue consumer (rebuild Goal 10) — the queue drives paper/live OOS.

The queue (``live_oos_queue``) is the human-selection layer; this consumer is the
bridge that turns a *selected* item into real work, and NOTHING else runs. Per the
Goal 10 acceptance, an unselected candidate never auto-runs paper replay — the only
trigger is a queue item a human put there.

Two kinds, two backing modules (contract README §7):

  * ``paper_watch_berth`` / ``after_close`` → ``watch_registry.enroll`` (ADR-033: the DSR
    band + ≤ 2 berths + 90-day window remain enforced by the registry, unchanged). A
    successful enroll advances the item ``queued → running``; the after-close
    scheduler's berth gate then admits exactly these strategies. A full cabin leaves
    the item ``queued`` (it waits for a berth next tick).
  * ``paper_replay`` → ``workflows.paper_replay`` once, on consumption; the queue owns
    the lifecycle ``queued → completed`` (carrying the run's ``run_id`` / ``gate_status``).
    A failed replay stays ``queued`` (retryable) and never crashes the tick.

State sync (each tick): a ``running`` / ``paused`` berth item is re-folded from the
registry — ``active→running``, ``paused→paused``, ``expired→expired``, ``exited→completed``
— so expired / paused / completed become visible on ``GET /research/live-oos/queue``
without a second store. Every side-effectful seam (enroll / status read / replay run)
is injected, so the whole decision path is unit-testable with no JSONL, no calendar
and no network.

Compatibility (ADR-040): berth enrollment is now *queue-driven*. The manual
``watch enroll`` CLI still works for ops / testing, but the primary path is
select-live-oos → consume. ``run_after_close``'s berth gate is unchanged — this
consumer only changes *how berths come to exist* (from the queue), not how the daily
session is gated. The two together give the Goal 10 guarantee: no berth without a
queued selection, and no selection auto-runs a session.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from backtest_platform.governance import live_oos_queue
from backtest_platform.governance.live_oos_queue import DEFAULT_QUEUE_PATH
from backtest_platform.governance.watch_registry import (
    AlreadyActiveError,
    CabinFullError,
    WatchRegistryError,
)

#: Queue kinds that map onto an ADR-033 observation berth (both consumed via enroll).
BERTH_KINDS: frozenset[str] = frozenset({"paper_watch_berth", "after_close"})
#: Folded ``WatchStatus.state`` → queue state (contract README §7).
_REGISTRY_TO_QUEUE: dict[str, str] = {
    "active": "running",
    "paused": "paused",
    "expired": "expired",
    "exited": "completed",
}

_TWT = timezone(timedelta(hours=8))

#: A live-OOS enroll seam: (strategy, verdict_dsr, as_of) → folded ``WatchStatus``.
EnrollFn = Callable[[str, float, date], Any]
#: A berth-status read seam: (strategy, as_of) → ``WatchStatus`` | None.
WatchStatusFn = Callable[[str, date], Any]
#: A paper-replay run seam: (strategy, as_of) → a result carrying ``run_id`` / ``gate_status``.
RunPaperReplayFn = Callable[[str, date], Any]


def _now_iso() -> str:
    return datetime.now(_TWT).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ConsumeReport:
    """Immutable digest of one consume tick — what changed, and what was left waiting."""

    enrolled: tuple[str, ...] = ()          # queue_ids that became ``running`` via enroll
    replayed: tuple[str, ...] = ()          # queue_ids that ran a paper replay (→ completed)
    synced: tuple[tuple[str, str], ...] = ()   # (queue_id, new_state) from a berth re-fold
    skipped: tuple[tuple[str, str], ...] = ()  # (queue_id, reason) left in place (cabin full, …)


# --------------------------------------------------------------------------- #
# default production seams (all overridable per call for testing)             #
# --------------------------------------------------------------------------- #
def default_enroll(strategy: str, verdict_dsr: float, as_of: date) -> Any:
    """Production enroll — admit a berth via the real ADR-033 registry (band / cap enforced)."""
    from backtest_platform.governance.watch_registry import enroll

    return enroll(strategy, verdict_dsr, as_of)


def default_watch_status(strategy: str, as_of: date) -> Any:
    """Production berth read — fold the strategy's current ``WatchStatus`` (or None)."""
    from backtest_platform.governance.watch_registry import status

    return status(strategy, as_of=as_of)


def default_run_paper_replay(strategy: str, as_of: date) -> Any:
    """Best-effort production replay: build a config from the strategy's registered
    defaults + the env universe (``AFTER_CLOSE_UNIVERSE``) and run one paper replay.

    A strategy whose ``config_model`` needs required fields (no default) or a missing
    universe raises — the consumer degrades that into a retryable ``skipped`` entry
    rather than crashing the tick. The heavy dispatch/gate imports are lazy so merely
    importing this module (e.g. for the CLI) stays cheap.
    """
    from backtest_platform.research.workflows.config import PaperReplayConfig
    from backtest_platform.research.workflows.paper_replay import run_paper_replay_workflow
    from backtest_platform.strategies.protocol import get_strategy

    raw = os.environ.get("AFTER_CLOSE_UNIVERSE", "")
    symbols = [s.strip() for s in raw.split(",") if s.strip()]
    if not symbols:
        raise ValueError(
            "no universe configured for paper_replay consumption — set AFTER_CLOSE_UNIVERSE"
        )
    runner = get_strategy(strategy)
    cfg = PaperReplayConfig(
        strategy=strategy, fixed_config=runner.config_model(), symbols=symbols, as_of=as_of
    )
    return run_paper_replay_workflow(cfg)


# --------------------------------------------------------------------------- #
# consume                                                                     #
# --------------------------------------------------------------------------- #
def consume_queue(
    as_of: date,
    *,
    queue_path: Path | str = DEFAULT_QUEUE_PATH,
    enroll_fn: EnrollFn = default_enroll,
    watch_status_fn: WatchStatusFn = default_watch_status,
    run_paper_replay_fn: RunPaperReplayFn = default_run_paper_replay,
) -> ConsumeReport:
    """Consume the live-OOS queue for ``as_of`` and return a :class:`ConsumeReport`.

    For each ``queued`` item: a berth kind is enrolled (→ ``running``); a ``paper_replay``
    is run once (→ ``completed``). For each ``running`` / ``paused`` berth item: its state
    is re-folded from the registry so a matured / paused / exited berth surfaces. Items
    of any other state are left untouched — nothing outside the queue ever runs.
    """
    enrolled: list[str] = []
    replayed: list[str] = []
    synced: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []

    for item in live_oos_queue.list_queue(path=queue_path):
        qid = item["queue_id"]
        kind = item.get("observation", {}).get("kind")
        state = item.get("state")
        if state == "queued":
            if kind in BERTH_KINDS:
                _consume_berth(item, as_of, enroll_fn, watch_status_fn, queue_path, enrolled, skipped)
            elif kind == "paper_replay":
                _consume_replay(item, as_of, run_paper_replay_fn, queue_path, replayed, skipped)
            else:
                skipped.append((qid, f"unknown observation kind {kind!r}"))
        elif state in ("running", "paused") and kind in BERTH_KINDS:
            _sync_berth(item, as_of, watch_status_fn, queue_path, synced)

    return ConsumeReport(
        enrolled=tuple(enrolled), replayed=tuple(replayed),
        synced=tuple(synced), skipped=tuple(skipped),
    )


def _consume_berth(
    item: dict[str, Any],
    as_of: date,
    enroll_fn: EnrollFn,
    watch_status_fn: WatchStatusFn,
    queue_path: Path | str,
    enrolled: list[str],
    skipped: list[tuple[str, str]],
) -> None:
    """Enroll a queued berth item; a full cabin / band refusal leaves it ``queued``."""
    qid = item["queue_id"]
    strategy = item["strategy"]
    dsr = item.get("observation", {}).get("verdict_dsr")
    if dsr is None:
        skipped.append((qid, "no verdict_dsr recorded for berth enrollment"))
        return
    try:
        st = enroll_fn(strategy, float(dsr), as_of)
    except AlreadyActiveError:
        st = watch_status_fn(strategy, as_of)  # already holds a berth → fold the current one
    except CabinFullError:
        skipped.append((qid, "cabin_full"))  # legitimate wait — retried next tick
        return
    except WatchRegistryError as exc:  # band / one-shot refusal — not a berth candidate
        skipped.append((qid, f"enroll_refused: {exc}"))
        return
    if st is None:
        skipped.append((qid, "enrolled_but_status_none"))
        return
    live_oos_queue.advance(qid, to_state="running", observation_patch=_berth_patch(st), path=queue_path)
    enrolled.append(qid)


def _consume_replay(
    item: dict[str, Any],
    as_of: date,
    run_paper_replay_fn: RunPaperReplayFn,
    queue_path: Path | str,
    replayed: list[str],
    skipped: list[tuple[str, str]],
) -> None:
    """Run one paper replay for a queued item; a failure leaves it ``queued`` (retryable)."""
    qid = item["queue_id"]
    strategy = item["strategy"]
    try:
        result = run_paper_replay_fn(strategy, as_of)
    except Exception as exc:
        logger.warning("live-oos consume: paper_replay {} failed (stays queued): {}", qid, exc)
        skipped.append((qid, f"replay_failed: {type(exc).__name__}: {exc}"))
        return
    run_block = {
        "run_id": getattr(result, "run_id", None),
        "gate_status": getattr(result, "gate_status", None),
        "ran_at": _now_iso(),
    }
    live_oos_queue.advance(qid, to_state="completed", run=run_block, path=queue_path)
    replayed.append(qid)


def _sync_berth(
    item: dict[str, Any],
    as_of: date,
    watch_status_fn: WatchStatusFn,
    queue_path: Path | str,
    synced: list[tuple[str, str]],
) -> None:
    """Re-fold a running / paused berth item from the registry; append only when it moved."""
    qid = item["queue_id"]
    st = watch_status_fn(item["strategy"], as_of)
    if st is None:
        return
    desired = _REGISTRY_TO_QUEUE.get(st.state)
    if desired is None:
        return
    obs = item.get("observation", {})
    state_changed = desired != item.get("state")
    clock_moved = (
        obs.get("observed_trading_days") != st.observed_trading_days
        or obs.get("days_remaining") != st.days_remaining
    )
    if state_changed or clock_moved:
        live_oos_queue.advance(qid, to_state=desired, observation_patch=_berth_patch(st), path=queue_path)
        if state_changed:
            synced.append((qid, desired))


def _berth_patch(st: Any) -> dict[str, Any]:
    """The observation fields folded from a ``WatchStatus`` onto a berth queue item."""
    from backtest_platform.governance.watch_registry import OBSERVATION_DAYS

    return {
        "watch_registry_ref": st.strategy,
        "enrolled_on": st.enrolled_on.isoformat(),
        "expiry_date": st.expiry_date.isoformat(),
        "observation_days": OBSERVATION_DAYS,
        "observed_trading_days": st.observed_trading_days,
        "days_remaining": st.days_remaining,
        "verdict_dsr": st.verdict_dsr,
    }
