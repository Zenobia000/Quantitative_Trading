"""3-level circuit breaker state machine (24_risk_management_spec §4).

Strategy-agnostic ex-post risk control. Given a stream of immutable
``RiskMetrics`` snapshots (one per fill / per 5-min tick / per close, see
spec §1.2), the breaker decides a ``BreakerState`` and exposes cheap query
helpers (``should_halt`` / ``should_reduce`` / ``should_block_new_entries``)
for the order layer to consult before submitting — this is the runtime side of
ex-ante rule ``EX-012`` (spec §2.1).

State machine (spec §4.1)::

    NORMAL --DD>=1.0x | losses>=5----------------> L1
    L1     --DD<0.7x sustained l1_recovery_days---> NORMAL
    L1     --DD>=1.5x | losses>=8 | daily_dd>10%--> L2
    L2     --DD<1.0x sustained l2_recovery_days---> L1
    L2     --DD>=2.0x | broker/recon/exception----> L3 (-> HALTED, latched)
    HALTED --manual reset() only------------------> NORMAL

Design rules honoured:

* **Escalation is immediate** — the worst matching trigger applies at once.
* **Recovery is gradual** — de-escalation needs the recovery condition held
  for N consecutive snapshots, and steps down one level at a time
  (L2 -> L1 -> NORMAL), never skipping.
* **L3 latches to HALTED** — once halted the breaker will not auto-recover on a
  clean snapshot; only an explicit operator ``reset()`` clears it (spec §4.2
  "人工 reset only").
* **Protective signals always allowed** — stoploss/exit/reduce are never
  blocked (spec §5.1); only buy/add are intercepted.

Thresholds default to spec §10 (``dd_limit=0.15`` → L1@15% / L2@22.5% /
L3@30%). The breaker is config-injected, so any strategy can wire its own
``CircuitBreakerConfig`` without touching this logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

# Canonical BreakerState lives in risk.types so risk_gate.check_ex012 and this
# breaker share one enum (a HALTED breaker must block all orders — see types.py).
from backtest_platform.risk.types import BreakerState


@dataclass(frozen=True)
class RiskMetrics:
    """Immutable snapshot of the live risk indicators the breaker consumes.

    Mirrors the subset of ``21_data_contract §4.8 risk_metrics`` plus the
    operational counters from spec §4.3. ``current_dd`` / ``daily_dd`` are
    fractions (0.15 == 15%); sign is ignored (drawdown magnitude is used).
    """

    current_dd: float = 0.0
    daily_dd: float = 0.0
    consecutive_losses: int = 0
    shioaji_errors: int = 0
    reconciliation_failed: bool = False
    exceptions_last_hour: int = 0


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Breaker thresholds. Defaults reproduce 24_risk_management_spec §10.

    Kept independent of ``config.risk_config.RiskConfig`` so the breaker is
    importable and testable without the full Pydantic risk config; a caller may
    build this from a ``RiskConfig`` at the integration boundary.
    """

    dd_limit: float = 0.15
    l1_dd_multiplier: float = 1.0
    l2_dd_multiplier: float = 1.5
    l3_dd_multiplier: float = 2.0
    l1_recovery_dd: float = 0.7  # fraction of dd_limit
    l1_recovery_days: int = 3
    l2_recovery_days: int = 5
    consecutive_loss_l1: int = 5
    consecutive_loss_l2: int = 8
    daily_dd_l2: float = 0.10
    shioaji_errors_l3: int = 5
    exceptions_per_hour_l3: int = 10

    def __post_init__(self) -> None:
        if self.dd_limit <= 0:
            raise ValueError("dd_limit must be > 0")
        if not (self.l1_dd_multiplier < self.l2_dd_multiplier < self.l3_dd_multiplier):
            raise ValueError(
                "dd multipliers must strictly increase: "
                f"l1={self.l1_dd_multiplier} l2={self.l2_dd_multiplier} "
                f"l3={self.l3_dd_multiplier}"
            )
        if self.l1_recovery_days < 1 or self.l2_recovery_days < 1:
            raise ValueError("recovery days must be >= 1")
        if not (0 < self.l1_recovery_dd < self.l1_dd_multiplier):
            raise ValueError("l1_recovery_dd must be in (0, l1_dd_multiplier)")


@dataclass(frozen=True)
class Transition:
    """Audit record of a single state change (immutable, append-only log)."""

    from_state: BreakerState
    to_state: BreakerState
    reason: str | None
    metrics_snapshot: RiskMetrics
    manual: bool = False
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CircuitBreaker:
    """Stateful 3-level breaker driven by injected metric snapshots.

    Not thread-safe by design — callers serialise the ex-post evaluation loop
    (one snapshot at a time per spec §1.2). Construct once per trading session,
    feed every snapshot through :meth:`evaluate`, and gate orders via the query
    helpers.
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._state: BreakerState = BreakerState.NORMAL
        self._recovery_streak: int = 0
        self._transitions: list[Transition] = []

    # --- read-only properties ---------------------------------------------

    @property
    def state(self) -> BreakerState:
        return self._state

    @property
    def config(self) -> CircuitBreakerConfig:
        return self._config

    @property
    def transitions(self) -> list[Transition]:
        """Append-only audit trail (returns a copy; cannot mutate internals)."""
        return list(self._transitions)

    # --- core evaluation ---------------------------------------------------

    def evaluate(self, metrics: RiskMetrics) -> BreakerState:
        """Fold one metric snapshot into the machine; return the new state.

        Escalates immediately to the worst triggered level. De-escalates only
        when the recovery condition for the *current* level has held for the
        configured number of consecutive snapshots, stepping down one level.
        ``HALTED`` is terminal until :meth:`reset`.
        """
        if self._state is BreakerState.HALTED:
            # Latched — no automatic recovery. Record the snapshot's intent
            # only by leaving state untouched; manual reset is the sole exit.
            return self._state

        triggered = self._classify(metrics)
        if triggered.severity > self._state.severity:
            return self._escalate(triggered, metrics)

        # No new escalation: consider gradual recovery for the current level.
        return self._maybe_recover(metrics)

    def reset(self, reason: str | None = None) -> BreakerState:
        """Operator clears a halted (or any) breaker back to NORMAL.

        No-op (and no transition logged) if already NORMAL, so an idempotent
        "all clear" call from a runbook does not pollute the audit trail.
        """
        if self._state is BreakerState.NORMAL:
            return self._state
        self._record(
            from_state=self._state,
            to_state=BreakerState.NORMAL,
            reason=reason or "manual reset",
            metrics=RiskMetrics(),
            manual=True,
        )
        self._state = BreakerState.NORMAL
        self._recovery_streak = 0
        return self._state

    # --- order-layer query helpers (EX-012 hook) --------------------------

    def should_halt(self) -> bool:
        """True iff trading is fully halted (HALTED). Gates EX-012 reject-all."""
        return self._state is BreakerState.HALTED

    def should_reduce(self) -> bool:
        """True at L2 and above — forced position reduction is in effect."""
        return self._state.severity >= BreakerState.L2.severity

    def should_block_new_entries(self) -> bool:
        """True at any non-NORMAL state — buy/add are intercepted (spec §5.1)."""
        return self._state is not BreakerState.NORMAL

    def allows_protective_exit(self) -> bool:
        """Protective signals (stoploss/exit/reduce) are never blocked (§5.1)."""
        return True

    # --- internals ---------------------------------------------------------

    def _classify(self, m: RiskMetrics) -> BreakerState:
        """Pure mapping: worst breaker level implied by a snapshot alone."""
        cfg = self._config
        dd_ratio = abs(m.current_dd) / cfg.dd_limit

        if (
            dd_ratio >= cfg.l3_dd_multiplier
            or m.shioaji_errors >= cfg.shioaji_errors_l3
            or m.reconciliation_failed
            or m.exceptions_last_hour >= cfg.exceptions_per_hour_l3
        ):
            return BreakerState.L3
        if (
            dd_ratio >= cfg.l2_dd_multiplier
            or m.consecutive_losses >= cfg.consecutive_loss_l2
            or abs(m.daily_dd) > cfg.daily_dd_l2
        ):
            return BreakerState.L2
        if dd_ratio >= cfg.l1_dd_multiplier or m.consecutive_losses >= cfg.consecutive_loss_l1:
            return BreakerState.L1
        return BreakerState.NORMAL

    def _escalate(self, triggered: BreakerState, m: RiskMetrics) -> BreakerState:
        target = BreakerState.HALTED if triggered is BreakerState.L3 else triggered
        self._record(
            from_state=self._state,
            to_state=target,
            reason=self._describe_trigger(triggered, m),
            metrics=m,
        )
        self._state = target
        self._recovery_streak = 0
        return self._state

    def _maybe_recover(self, m: RiskMetrics) -> BreakerState:
        """Advance / reset the recovery streak for the current level."""
        cfg = self._config
        dd_ratio = abs(m.current_dd) / cfg.dd_limit

        if self._state is BreakerState.L1:
            recovered = dd_ratio < cfg.l1_recovery_dd
            need = cfg.l1_recovery_days
            step_to = BreakerState.NORMAL
        elif self._state is BreakerState.L2:
            recovered = dd_ratio < cfg.l1_dd_multiplier
            need = cfg.l2_recovery_days
            step_to = BreakerState.L1
        else:  # NORMAL — nothing to recover from
            self._recovery_streak = 0
            return self._state

        if not recovered:
            self._recovery_streak = 0
            return self._state

        self._recovery_streak += 1
        if self._recovery_streak >= need:
            self._record(
                from_state=self._state,
                to_state=step_to,
                reason=(
                    f"recovery: DD held below threshold for {need} snapshots"
                ),
                metrics=m,
            )
            self._state = step_to
            self._recovery_streak = 0
        return self._state

    def _record(
        self,
        *,
        from_state: BreakerState,
        to_state: BreakerState,
        reason: str | None,
        metrics: RiskMetrics,
        manual: bool = False,
    ) -> None:
        self._transitions.append(
            Transition(
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                metrics_snapshot=replace(metrics),
                manual=manual,
            )
        )

    @staticmethod
    def _describe_trigger(level: BreakerState, m: RiskMetrics) -> str:
        bits: list[str] = []
        if level is BreakerState.L3:
            if m.reconciliation_failed:
                bits.append("reconciliation failed")
            if m.shioaji_errors:
                bits.append(f"shioaji_errors={m.shioaji_errors}")
            if m.exceptions_last_hour:
                bits.append(f"exceptions/hr={m.exceptions_last_hour}")
        if m.consecutive_losses:
            bits.append(f"consecutive_losses={m.consecutive_losses}")
        if m.daily_dd:
            bits.append(f"daily_dd={m.daily_dd:.3f}")
        bits.append(f"current_dd={m.current_dd:.3f}")
        return f"{level.name}: " + ", ".join(bits)
