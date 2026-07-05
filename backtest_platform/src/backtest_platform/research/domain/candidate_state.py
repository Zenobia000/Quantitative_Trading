"""Candidate pool state machine (rebuild Goal 4).

The deterministic transition function behind every ``CandidateDecision``, matching
``dev_docs/contracts/candidate_pool.example.json`` §6.2. Pure (no IO) so every
transition is unit-testable; ``candidate_store`` appends the events, this module
decides which transitions are legal and which demand an audit ``reason``.

The eight contract actions (``auto_label`` / ``keep`` / ``archive`` / ``rerun`` /
``select_live_oos`` / ``mark_data_issue`` / ``unarchive`` / ``override_select``)
drive the research-triage subset of the lifecycle. The later
``live_oos_running`` / ``live_oos_done`` / ``deploy_blocked`` / ``deployable`` states
are queue-driven (Goal 10) and are NOT reached by a human decision here.
"""
from __future__ import annotations

#: Every state in the contract enum (§6.1).
STATES: frozenset[str] = frozenset({
    "draft", "triaged", "promising", "weak", "negative", "data_issue",
    "live_oos_selected", "live_oos_running", "live_oos_done",
    "deploy_blocked", "deployable", "archived",
})

#: The three human "keep" target labels.
KEEP_LABELS: frozenset[str] = frozenset({"promising", "weak", "negative"})

#: States a decision may still act on (archived is a discoverable terminal).
_NON_TERMINAL: frozenset[str] = frozenset({
    "draft", "triaged", "promising", "weak", "negative", "data_issue", "live_oos_selected",
})

#: action → (allowed-from states, fixed to-state | None when the target is dynamic).
_TRANSITIONS: dict[str, tuple[frozenset[str], str | None]] = {
    "auto_label": (frozenset({"draft"}), "triaged"),
    "mark_data_issue": (frozenset({"draft", "triaged"}), "data_issue"),
    "keep": (frozenset({"triaged", "promising", "weak", "negative"}), None),
    "rerun": (frozenset({"triaged", "promising", "weak", "negative", "data_issue"}), "triaged"),
    "select_live_oos": (frozenset({"triaged", "promising", "weak"}), "live_oos_selected"),
    "override_select": (frozenset({"triaged", "promising", "weak", "negative"}), "live_oos_selected"),
    "archive": (_NON_TERMINAL, "archived"),
    "unarchive": (frozenset({"archived"}), "triaged"),
}

ACTIONS: frozenset[str] = frozenset(_TRANSITIONS)

#: Actions callable from the decision endpoint (select/override go via select-live-oos).
DECISION_ACTIONS: frozenset[str] = frozenset({"keep", "archive", "rerun", "mark_data_issue", "unarchive"})


class IllegalTransitionError(ValueError):
    """A (state, action) pair the machine forbids (→ API 400 with a hint)."""


def next_state(current: str, action: str, *, target_label: str | None = None) -> str:
    """Resolve the deterministic to-state for ``(current, action)`` or raise.

    ``keep`` requires an explicit ``target_label`` ∈ {promising, weak, negative}; every
    other action has a fixed target. An unknown action or an illegal source state
    raises :class:`IllegalTransitionError`.
    """
    if action not in _TRANSITIONS:
        raise IllegalTransitionError(f"unknown action {action!r}; choose from {sorted(ACTIONS)}")
    allowed_from, to_state = _TRANSITIONS[action]
    if current not in allowed_from:
        raise IllegalTransitionError(
            f"cannot {action!r} from state {current!r}; allowed from {sorted(allowed_from)}"
        )
    if action == "keep":
        if target_label not in KEEP_LABELS:
            raise IllegalTransitionError(
                f"keep requires target_label ∈ {sorted(KEEP_LABELS)}, got {target_label!r}"
            )
        return target_label
    assert to_state is not None
    return to_state


def reason_required(action: str, *, recommendation: str | None = None) -> bool:
    """Whether an action must carry a non-empty audit reason (research plan §8.4).

    ``archive`` and ``override_select`` always require a reason; ``select_live_oos``
    requires one only when the candidate's live-OOS recommendation is not ``eligible``
    (selecting a not-recommended / blocked candidate is an override).
    """
    if action in ("archive", "override_select"):
        return True
    if action == "select_live_oos":
        return recommendation != "eligible"
    return False
