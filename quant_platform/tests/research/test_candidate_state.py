"""research.candidate_state — deterministic transition machine (rebuild Goal 4)."""
from __future__ import annotations

import pytest

from quant_platform.packages.domain.candidate_state import (
    ACTIONS,
    DECISION_ACTIONS,
    IllegalTransitionError,
    next_state,
    reason_required,
)


@pytest.mark.parametrize(
    "current,action,target,expected",
    [
        ("draft", "auto_label", None, "triaged"),
        ("draft", "mark_data_issue", None, "data_issue"),
        ("triaged", "mark_data_issue", None, "data_issue"),
        ("triaged", "keep", "promising", "promising"),
        ("triaged", "keep", "weak", "weak"),
        ("triaged", "keep", "negative", "negative"),
        ("promising", "keep", "weak", "weak"),
        ("triaged", "rerun", None, "triaged"),
        ("weak", "rerun", None, "triaged"),
        ("data_issue", "rerun", None, "triaged"),
        ("promising", "select_live_oos", None, "live_oos_selected"),
        ("weak", "select_live_oos", None, "live_oos_selected"),
        ("negative", "override_select", None, "live_oos_selected"),
        ("triaged", "archive", None, "archived"),
        ("negative", "archive", None, "archived"),
        ("live_oos_selected", "archive", None, "archived"),
        ("archived", "unarchive", None, "triaged"),
    ],
)
def test_legal_transitions(current, action, target, expected):
    assert next_state(current, action, target_label=target) == expected


def test_all_actions_covered_by_parametrize():
    # every declared action appears in the legal-transition matrix above
    tested = {"auto_label", "mark_data_issue", "keep", "rerun",
              "select_live_oos", "override_select", "archive", "unarchive"}
    assert tested == ACTIONS


def test_keep_requires_valid_label():
    with pytest.raises(IllegalTransitionError, match="target_label"):
        next_state("triaged", "keep")
    with pytest.raises(IllegalTransitionError, match="target_label"):
        next_state("triaged", "keep", target_label="banana")


def test_illegal_source_state():
    with pytest.raises(IllegalTransitionError, match="cannot"):
        next_state("draft", "keep", target_label="weak")
    with pytest.raises(IllegalTransitionError, match="cannot"):
        next_state("archived", "keep", target_label="weak")


def test_unknown_action():
    with pytest.raises(IllegalTransitionError, match="unknown action"):
        next_state("triaged", "explode")


def test_select_from_negative_needs_override_not_plain_select():
    with pytest.raises(IllegalTransitionError):
        next_state("negative", "select_live_oos")


def test_reason_required_matrix():
    assert reason_required("archive") is True
    assert reason_required("override_select") is True
    assert reason_required("keep") is False
    assert reason_required("rerun") is False
    assert reason_required("select_live_oos", recommendation="eligible") is False
    assert reason_required("select_live_oos", recommendation="not_recommended") is True
    assert reason_required("select_live_oos", recommendation="blocked") is True


def test_decision_actions_are_subset():
    assert DECISION_ACTIONS <= ACTIONS
    assert "select_live_oos" not in DECISION_ACTIONS  # goes via select-live-oos endpoint
