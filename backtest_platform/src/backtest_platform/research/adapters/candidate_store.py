"""Candidate pool store (rebuild Goal 4) — append-only, folded projection.

Stores every evaluation outcome as a candidate (draft → triaged → …) and every
human decision as an immutable event, matching
``dev_docs/contracts/candidate_pool.example.json``. Two append-only JSONL logs, same
philosophy as ``runs_store`` / ``promotion_store`` / ``watch_registry``:

- ``candidates.jsonl``          — candidate metadata + latest-evaluation snapshot
  (an upsert appends a fresh snapshot; the fold takes the latest per candidate_id).
- ``candidate_decisions.jsonl`` — the append-only ``CandidateDecision`` audit trail;
  current ``state`` is folded from the last decision's ``to_state``.

Every evaluation — including weak / negative / data-issue — creates or updates a
candidate (global acceptance #5). A candidate is keyed 1:1 to its strategy
(``cand_<strategy>``), matching the contract fixtures.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest_platform.research.candidate_state import (
    next_state,
    reason_required,
)

#: Live-OOS enqueue port (W1.3, ADR-R02). The candidate store (Layer-2 research)
#: *produces* into the live-OOS queue but must not import the queue module, which
#: is Layer-3 governance-bound (live_oos_queue moves to governance/ in W2.1b).
#: The concrete `live_oos_queue.enqueue` is injected by the composition root
#: (API router / orchestration), keeping the research → governance direction
#: one-way and the import-linter contract green.
EnqueuePort = Callable[..., dict[str, Any]]

DEFAULT_CANDIDATES_PATH = Path("reports") / "candidates.jsonl"
DEFAULT_DECISIONS_PATH = Path("reports") / "candidate_decisions.jsonl"

_TWT = timezone(timedelta(hours=8))


class CandidateNotFoundError(ValueError):
    """No candidate for the id (→ API 404)."""


class MissingReasonError(ValueError):
    """An override / archive decision lacked a required reason (→ API 422)."""


class BlockedSelectionError(ValueError):
    """A ``blocked`` candidate was selected without override authority (→ API 409)."""


def _now_iso() -> str:
    return datetime.now(_TWT).isoformat(timespec="seconds")


def candidate_id_for(strategy: str) -> str:
    """Deterministic candidate id for a strategy (``cand_<strategy>``)."""
    return f"cand_{strategy}"


# --------------------------------------------------------------------------- #
# store primitives                                                            #
# --------------------------------------------------------------------------- #
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


def _append(record: dict[str, Any], path: Path | str) -> dict[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def _latest_snapshot(candidate_id: str, path: Path | str) -> dict[str, Any] | None:
    match: dict[str, Any] | None = None
    for rec in _read(path):
        if rec.get("candidate_id") == candidate_id:
            match = rec
    return match


def _decisions_for(candidate_id: str, path: Path | str) -> list[dict[str, Any]]:
    return [d for d in _read(path) if d.get("candidate_id") == candidate_id]


# --------------------------------------------------------------------------- #
# reads (folded)                                                              #
# --------------------------------------------------------------------------- #
def get_candidate(
    candidate_id: str,
    *,
    candidates_path: Path | str = DEFAULT_CANDIDATES_PATH,
    decisions_path: Path | str = DEFAULT_DECISIONS_PATH,
) -> dict[str, Any] | None:
    """The folded candidate (latest snapshot + folded state + full decisions[]) or None."""
    snap = _latest_snapshot(candidate_id, candidates_path)
    if snap is None:
        return None
    decisions = _decisions_for(candidate_id, decisions_path)
    state = decisions[-1]["to_state"] if decisions else "draft"
    return {**snap, "state": state, "decisions": decisions}


def list_candidates(
    *,
    state: str | None = None,
    strategy: str | None = None,
    candidates_path: Path | str = DEFAULT_CANDIDATES_PATH,
    decisions_path: Path | str = DEFAULT_DECISIONS_PATH,
) -> list[dict[str, Any]]:
    """All candidates (newest-created first), optionally filtered by state / strategy."""
    ids = {rec["candidate_id"] for rec in _read(candidates_path)}
    cands = [
        c for cid in ids
        if (c := get_candidate(cid, candidates_path=candidates_path, decisions_path=decisions_path)) is not None
    ]
    if state is not None:
        cands = [c for c in cands if c.get("state") == state]
    if strategy is not None:
        cands = [c for c in cands if c.get("strategy") == strategy]
    return sorted(cands, key=lambda c: c.get("created_at", ""), reverse=True)


# --------------------------------------------------------------------------- #
# writes                                                                       #
# --------------------------------------------------------------------------- #
def _next_decision_id(candidate_id: str, decisions_path: Path | str) -> str:
    seq = len(_decisions_for(candidate_id, decisions_path)) + 1
    return f"dec_{candidate_id}_{seq:04d}"


def record_decision(
    candidate_id: str,
    action: str,
    *,
    actor: str = "operator",
    reason: str | None = None,
    target_label: str | None = None,
    evaluation_ref: str | None = None,
    queue_ref: str | None = None,
    recommendation: str | None = None,
    candidates_path: Path | str = DEFAULT_CANDIDATES_PATH,
    decisions_path: Path | str = DEFAULT_DECISIONS_PATH,
    at: str | None = None,
) -> dict[str, Any]:
    """Validate + append one immutable ``CandidateDecision`` event; return it.

    Raises :class:`CandidateNotFoundError` (unknown id), :class:`IllegalTransitionError`
    (forbidden state/action) or :class:`MissingReasonError` (an override/archive without a
    reason). The transition target is deterministic (``candidate_state.next_state``).
    """
    cand = get_candidate(candidate_id, candidates_path=candidates_path, decisions_path=decisions_path)
    if cand is None:
        raise CandidateNotFoundError(f"no candidate {candidate_id!r}")
    current = cand["state"]
    to_state = next_state(current, action, target_label=target_label)  # IllegalTransitionError on bad move
    if reason_required(action, recommendation=recommendation) and not (reason and reason.strip()):
        raise MissingReasonError(
            f"action {action!r} requires a non-empty reason (override/archive audit, research plan §8.4)"
        )
    event = {
        "decision_id": _next_decision_id(candidate_id, decisions_path),
        "candidate_id": candidate_id,
        "at": at or _now_iso(),
        "actor": actor,
        "action": action,
        "from_state": current,
        "to_state": to_state,
        "reason": reason,
        "evaluation_ref": evaluation_ref or cand.get("latest_evaluation_id"),
    }
    if queue_ref is not None:
        event["queue_ref"] = queue_ref
    return _append(event, decisions_path)


def _next_action_hint(recommendation: str, data_issue: bool) -> str:
    if data_issue:
        return "Ingest the required bundle; the run yielded no tradable bars (empty series sidecar)."
    return {
        "eligible": "Eligible for live OOS — select from the candidate pool to collect zero-capital observation.",
        "not_recommended": "Run a deeper profile (fixed_hypothesis_oos / deployment_strict) before spending live OOS.",
        "blocked": "Blocked for live OOS; keep as a research / negative control asset.",
    }.get(recommendation, "Review the report and decide next action.")


def ingest_evaluation(
    result: dict[str, Any],
    *,
    hypothesis: str | None = None,
    candidates_path: Path | str = DEFAULT_CANDIDATES_PATH,
    decisions_path: Path | str = DEFAULT_DECISIONS_PATH,
    clock: Any = _now_iso,
) -> dict[str, Any]:
    """Create or update the candidate for an ``EvaluationResult`` and return it.

    First evaluation → the candidate is created and auto-labelled: ``draft → triaged``
    (or ``draft → data_issue`` when the run produced no bars). A re-evaluation only
    refreshes the snapshot; the human-decided state is preserved.
    """
    strategy = result["strategy"]
    cid = candidate_id_for(strategy)
    existing = get_candidate(cid, candidates_path=candidates_path, decisions_path=decisions_path)
    verdict = result["verdict"]
    data_issue = verdict.get("label") == "Data Issue"
    recommendation = verdict.get("live_oos_recommendation", "not_recommended")
    h = result.get("headline_metrics", {})

    if hypothesis is None and existing is None:
        try:
            from backtest_platform.strategies.protocol import describe_strategy
            hypothesis = describe_strategy(strategy).description
        except Exception:
            hypothesis = None

    snapshot = {
        "candidate_id": cid,
        "strategy": strategy,
        "hypothesis": (existing or {}).get("hypothesis") if existing else hypothesis,
        "created_at": (existing or {}).get("created_at") if existing else clock(),
        "latest_evaluation_id": result["evaluation_id"],
        "latest_profile": result["profile"],
        "latest_label": verdict.get("label"),
        "latest_truth_verdict": verdict.get("truth_verdict"),
        "live_oos_recommendation": recommendation,
        "scorecard_summary": {sc["category"]: sc["status"] for sc in result.get("scorecards", [])},
        "headline": {
            "sharpe": h.get("sharpe"),
            "oos_holdout_sharpe": h.get("oos_holdout_sharpe"),
            "cagr": h.get("cagr"),
            "max_drawdown": h.get("max_drawdown"),
            "dsr": h.get("dsr"),
            "trades": h.get("trades"),
            "avg_turnover": h.get("avg_turnover"),
            "survivorship_clean": result.get("universe", {}).get("survivorship_clean"),
        },
        "report_pack_ref": result.get("report_pack_ref"),
        "next_action": _next_action_hint(recommendation, data_issue),
        # When the latest evaluation was produced by a branch experiment (Goal 9), the
        # candidate carries its branch lineage so the pool can badge the branch origin.
        "branch_origin": result.get("branch"),
    }
    _append(snapshot, candidates_path)

    if existing is None:
        if data_issue:
            record_decision(
                cid, "mark_data_issue", actor="system",
                reason="Empty equity series — the window yielded no tradable data.",
                evaluation_ref=result["evaluation_id"],
                candidates_path=candidates_path, decisions_path=decisions_path,
            )
        else:
            record_decision(
                cid, "auto_label", actor="system", evaluation_ref=result["evaluation_id"],
                candidates_path=candidates_path, decisions_path=decisions_path,
            )
    return get_candidate(cid, candidates_path=candidates_path, decisions_path=decisions_path)


def select_live_oos(
    candidate_id: str,
    *,
    reason: str | None = None,
    override: bool = False,
    observation_kind: str = "paper_replay",
    actor: str = "operator",
    candidates_path: Path | str = DEFAULT_CANDIDATES_PATH,
    decisions_path: Path | str = DEFAULT_DECISIONS_PATH,
    queue_path: Path | str,
    enqueue: EnqueuePort,
) -> dict[str, Any]:
    """Select a candidate for live OOS: enqueue a queue item + append the decision.

    ``enqueue`` is the injected live-OOS queue port (W1.3): callers pass the
    concrete ``live_oos_queue.enqueue`` so research never imports the governance-
    bound queue module. ``queue_path`` is the queue's storage path.

    Returns ``{"decision": …, "queue_item": …}``. A ``blocked`` candidate without
    ``override`` raises :class:`BlockedSelectionError` (→ 409); a not-eligible selection
    without a reason raises :class:`MissingReasonError` (→ 422); an illegal transition
    raises :class:`IllegalTransitionError` (→ 400).
    """
    cand = get_candidate(candidate_id, candidates_path=candidates_path, decisions_path=decisions_path)
    if cand is None:
        raise CandidateNotFoundError(f"no candidate {candidate_id!r}")
    reco = cand.get("live_oos_recommendation", "not_recommended")
    if reco == "blocked" and not override:
        raise BlockedSelectionError(
            f"candidate {candidate_id!r} recommendation is 'blocked'; pass override=True with a reason"
        )
    action = "override_select" if (override or reco != "eligible") else "select_live_oos"
    # Pre-validate the move + reason before writing the queue item (no orphan on failure).
    next_state(cand["state"], action)
    if reason_required(action, recommendation=reco) and not (reason and reason.strip()):
        raise MissingReasonError(f"selecting a {reco!r} candidate requires a non-empty reason")

    queue_item = enqueue(
        candidate_id, cand["strategy"], cand.get("latest_evaluation_id"),
        selected_by=actor, selection_reason=reason, recommendation_at_selection=reco,
        override=(action == "override_select"), override_reason=reason if override else None,
        observation_kind=observation_kind, report_pack_ref=cand.get("report_pack_ref"),
        dsr=(cand.get("headline") or {}).get("dsr"), path=queue_path,
    )
    decision = record_decision(
        candidate_id, action, actor=actor, reason=reason, recommendation=reco,
        evaluation_ref=cand.get("latest_evaluation_id"), queue_ref=queue_item["queue_id"],
        candidates_path=candidates_path, decisions_path=decisions_path,
    )
    return {"decision": decision, "queue_item": queue_item}
