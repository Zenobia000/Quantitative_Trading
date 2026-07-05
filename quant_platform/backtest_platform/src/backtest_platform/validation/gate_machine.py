"""gate_machine — IS→WFA→OOS irreversible workflow gate + OOS sealed vault.

8.G.3-full. Upgrades the v0.1 read-only ``gate_state`` judge into a *stateful,
enforcing* workflow gate. A run must clear each phase in order:

    PENDING → IS_PASS → WFA_PASS → OOS_PASS → APPROVED

The machine enforces three properties that a passive judge cannot:

1. **No gate-skipping** — ``submit_wfa`` requires ``IS_PASS``, ``submit_oos``
   requires ``WFA_PASS``, ``approve`` requires ``OOS_PASS``. Calling out of
   order raises ``ValueError``.
2. **Irreversibility** — you can never transition to a *lower*-ordinal state
   through the normal methods (no re-running IS to "refresh" a passed gate).
   The only way back is ``reset()``, which returns to ``PENDING`` and is
   counted in ``n_resets`` (so a strategy that keeps resetting to retry is
   visible, not silent — anti-overfit accountability).
3. **OOS sealed vault** — ``read_oos(loader)`` refuses to call ``loader`` until
   IS *and* WFA have passed (state ``>= WFA_PASS``). Premature reads raise
   ``OOSSealedError`` and bump ``n_oos_blocked``; legitimate reads bump
   ``n_oos_access``. This closes the classic look-ahead leak where a researcher
   peeks at the out-of-sample data and turns it into in-sample.

The IS verdict is *not* re-derived here: ``submit_is`` delegates to
``validation.gate_state.evaluate_gate`` so the single '審判庭' threshold source
(``DEFAULT_GATE``) stays authoritative. An INCOMPLETE gate (missing metric) is
treated as a non-pass — you cannot APPROVE a gate you cannot fully evaluate.

No IO. ``read_oos`` takes an injected ``loader`` callable so the vault logic is
testable without touching parquet / bundles.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import Enum
from typing import TypeVar

from backtest_platform.validation.gate_state import (
    DEFAULT_GATE,
    Criterion,
    GateResult,
    GateStatus,
    evaluate_gate,
)

T = TypeVar("T")


class GateState(str, Enum):
    """Ordered workflow states. Ordinal = position in the IS→WFA→OOS pipeline.

    ``FAILED`` is the dead-end any gate failure drops into; it is *not* on the
    forward path and carries no ordinal (you cannot advance out of it — only
    ``reset()`` escapes it).
    """

    PENDING = "PENDING"
    IS_PASS = "IS_PASS"
    WFA_PASS = "WFA_PASS"
    OOS_PASS = "OOS_PASS"
    APPROVED = "APPROVED"
    FAILED = "FAILED"


# Forward-progress ordering. FAILED is deliberately absent (off-path sink).
_ORDER: dict[GateState, int] = {
    GateState.PENDING: 0,
    GateState.IS_PASS: 1,
    GateState.WFA_PASS: 2,
    GateState.OOS_PASS: 3,
    GateState.APPROVED: 4,
}


# --------------------------------------------------------------------------- #
# Canonical IS-status vocabulary bridge (code-audit 2026-06-10)
# --------------------------------------------------------------------------- #
# Two layers talk about "did IS pass": the persisted ``validation_status``
# (lowercase verdict vocab written by promotion_service / the API) and the
# workflow ``GateState``. These maps are the SINGLE place the vocabularies meet,
# kept inverse-consistent so the CLI (reads) and promotion_service (writes) can
# never drift into the silent mismatch the audit found — the CLI was parsing a
# persisted ``"is_pass"`` string as ``GateState(raw)`` and falling through on
# every value, ignoring the recorded verdict.

#: IS gate verdict → persisted validation_status string (promotion / API vocab).
IS_VERDICT_TO_STATUS: dict[GateStatus, str] = {
    GateStatus.PASS: "is_pass",
    GateStatus.FAIL: "is_fail",
    GateStatus.INCOMPLETE: "incomplete",
}

#: Persisted validation_status (verdict OR later-phase vocab) → workflow GateState.
#: INCOMPLETE collapses to FAILED — a gate you cannot fully evaluate is not a pass.
_STATUS_TO_STATE: dict[str, GateState] = {
    "is_pass": GateState.IS_PASS,
    "is_fail": GateState.FAILED,
    "incomplete": GateState.FAILED,
    "wfa_pass": GateState.WFA_PASS,
    "oos_pass": GateState.OOS_PASS,
    "approved": GateState.APPROVED,
}


def _is_state_from_result(result: GateResult) -> GateState:
    """The one IS-verdict rule: gate PASS → IS_PASS, else (FAIL/INCOMPLETE) FAILED."""
    return GateState.IS_PASS if result.passed else GateState.FAILED


def derive_is_state(
    metrics: Mapping[str, float], gate: tuple[Criterion, ...] = DEFAULT_GATE
) -> GateState:
    """Stateless IS derivation from metrics — the same rule ``submit_is`` applies,
    for callers (e.g. the CLI) that need the verdict without a stateful machine."""
    return _is_state_from_result(evaluate_gate(metrics, gate))


def coerce_gate_state(raw: str | None) -> GateState | None:
    """Map a persisted ``validation_status`` to a ``GateState``, accepting BOTH the
    GateState enum form (``IS_PASS`` …) and the persisted verdict form
    (``is_pass`` / ``is_fail`` / ``incomplete`` …). Unknown / empty → ``None`` so
    the caller re-derives from metrics rather than guessing past the record."""
    if not raw:
        return None
    try:
        return GateState(raw)
    except ValueError:
        return _STATUS_TO_STATE.get(raw.lower())


class OOSSealedError(RuntimeError):
    """Raised when OOS data is read before the IS+WFA gates have cleared.

    Subclasses ``RuntimeError`` because peeking at sealed out-of-sample data is
    a workflow-integrity violation (look-ahead leak), not a bad-argument error.
    """


class ValidationGate:
    """Mutable IS→WFA→OOS state machine with a sealed OOS vault.

    Single-run scope: one ``ValidationGate`` tracks one strategy/run candidate
    through the validation pipeline. Construct, then drive it with
    ``submit_is`` / ``submit_wfa`` / ``submit_oos`` / ``approve`` in order.
    """

    def __init__(self, gate: tuple[Criterion, ...] = DEFAULT_GATE) -> None:
        self._gate = gate
        self._state: GateState = GateState.PENDING
        self._last_is_result: GateResult | None = None
        self.n_resets: int = 0
        self.n_oos_blocked: int = 0
        self.n_oos_access: int = 0

    # ------------------------------------------------------------------ #
    # read-only views
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> GateState:
        return self._state

    @property
    def last_is_result(self) -> GateResult | None:
        """The ``GateResult`` from the most recent ``submit_is`` (None after reset)."""
        return self._last_is_result

    @property
    def oos_unsealed(self) -> bool:
        """True once IS+WFA have cleared (state ordinal >= WFA_PASS)."""
        return _ORDER.get(self._state, -1) >= _ORDER[GateState.WFA_PASS]

    # ------------------------------------------------------------------ #
    # forward transitions
    # ------------------------------------------------------------------ #
    def submit_is(self, metrics: Mapping[str, float]) -> GateState:
        """Judge IS metrics via ``evaluate_gate``. PASS → IS_PASS, else FAILED.

        Legal only from PENDING (cannot re-run a gate that already advanced —
        irreversibility). INCOMPLETE (missing gated metric) counts as non-pass.
        """
        self._require(GateState.PENDING, "submit_is")
        result = evaluate_gate(metrics, self._gate)
        self._last_is_result = result
        self._state = _is_state_from_result(result)
        return self._state

    def submit_wfa(self, passed: bool) -> GateState:
        """Record the walk-forward verdict. Requires current state IS_PASS."""
        self._require(GateState.IS_PASS, "submit_wfa")
        self._state = GateState.WFA_PASS if passed else GateState.FAILED
        return self._state

    def submit_oos(self, passed: bool) -> GateState:
        """Record the out-of-sample verdict. Requires current state WFA_PASS."""
        self._require(GateState.WFA_PASS, "submit_oos")
        self._state = GateState.OOS_PASS if passed else GateState.FAILED
        return self._state

    def approve(self) -> GateState:
        """Final human/automation sign-off. Requires current state OOS_PASS."""
        self._require(GateState.OOS_PASS, "approve")
        self._state = GateState.APPROVED
        return self._state

    # ------------------------------------------------------------------ #
    # reset — the only legal way back to PENDING
    # ------------------------------------------------------------------ #
    def reset(self) -> GateState:
        """Return to PENDING and clear the IS result. Counts toward ``n_resets``.

        Resets also re-seal the OOS vault (state drops below WFA_PASS). The
        access/block tallies persist across resets so the full audit trail of a
        candidate's lifecycle survives a retry.
        """
        self._state = GateState.PENDING
        self._last_is_result = None
        self.n_resets += 1
        return self._state

    # ------------------------------------------------------------------ #
    # OOS sealed vault
    # ------------------------------------------------------------------ #
    def read_oos(self, loader: Callable[[], T]) -> T:
        """Read OOS data via ``loader``, but only once IS+WFA have cleared.

        Sealed (state < WFA_PASS): raise ``OOSSealedError`` *without* calling
        ``loader`` (no leak path) and bump ``n_oos_blocked``.
        Unsealed (state >= WFA_PASS): call ``loader``, bump ``n_oos_access``,
        return its result.
        """
        if not self.oos_unsealed:
            self.n_oos_blocked += 1
            raise OOSSealedError(
                f"OOS vault is sealed in state {self._state.value}; "
                f"IS and WFA must pass (state >= WFA_PASS) before reading OOS data."
            )
        self.n_oos_access += 1
        return loader()

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _require(self, expected: GateState, action: str) -> None:
        if self._state is not expected:
            raise ValueError(
                f"{action} requires state {expected.value}, "
                f"but gate is in {self._state.value} (gate-skip / out-of-order / "
                f"irreversible-regress blocked)."
            )
