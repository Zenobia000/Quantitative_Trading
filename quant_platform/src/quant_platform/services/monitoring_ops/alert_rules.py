"""Discord three-tier alert rule engine — the *decision* layer.

This module decides **whether** an alert should fire and **at what level**; it
does NOT touch Discord. Actual delivery is the job of ``discord_notifier`` /
``alerter.py``. Keeping decision separate from delivery makes the rule logic
unit-testable with zero network and a fully injected clock.

Spec: ``dev_docs/20_dashboard_specification.md`` §4
  - §4.1 levels: Critical / High / Info
  - §4.2 trigger table: CRIT-001..004, HIGH-001..004, INFO-001..002
  - §4.4 dedup (same rule_id once / 30 min) + silent window (22:00–08:00 only Critical)

Design notes
------------
- Rules are declarative *data* (``RULES`` list of :class:`Rule`), mirroring the
  ``DEFAULT_GATE`` pattern in ``validation/gate_state.py``: a predicate over a
  plain metrics ``Mapping`` plus a message builder. Adding a rule is data, not
  control flow.
- Time enters through one seam: the ``clock`` callable injected into
  :class:`AlertRouter`. Tests pin it; production defaults to ``datetime.now(UTC)``.
- Strategy-agnostic: the engine knows nothing about any particular strategy. It
  only reads a metrics dict whose keys come from the §4.2 source columns.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Any

# §4.4 — same rule_id within this window fires once.
DEDUPE_WINDOW: timedelta = timedelta(minutes=30)

# §4.4 — silent window [SILENT_START, SILENT_END) in *local* wall-clock time.
# Inside it only Critical alerts are emitted.
SILENT_START: time = time(22, 0)  # 22:00 inclusive → silent
SILENT_END: time = time(8, 0)  # 08:00 exclusive → active again

Metrics = Mapping[str, Any]
Clock = Callable[[], datetime]


class AlertLevel(str, Enum):
    """Severity tiers per §4.1. ``str`` mixin → JSON/log friendly."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    INFO = "INFO"


@dataclass(frozen=True, slots=True)
class Alert:
    """A fired alert. Immutable so a router result can't be mutated downstream."""

    rule_id: str
    level: AlertLevel
    title: str
    message: str


@dataclass(frozen=True, slots=True)
class Rule:
    """One row of the §4.2 trigger table, as data.

    ``predicate`` reads the metrics mapping and returns True when the rule
    should fire. ``build_message`` renders the human-facing body from the same
    mapping (so context values land in the message).
    """

    rule_id: str
    level: AlertLevel
    title: str
    predicate: Callable[[Metrics], bool]
    build_message: Callable[[Metrics], str] = field(
        default=lambda _m: ""
    )


def silent_hours(now: datetime) -> bool:
    """True if ``now`` falls in the 22:00–08:00 silent window (local wall time).

    The window wraps midnight, so we test ``hour >= 22 OR hour < 08``. 22:00 is
    silent; 08:00 is active again (half-open ``[22:00, 08:00)``).
    """
    t = now.timetz().replace(tzinfo=None) if now.tzinfo else now.time()
    return t >= SILENT_START or t < SILENT_END


# ---------------------------------------------------------------------------
# Small predicate helpers — keep the rule table readable and total.
# ---------------------------------------------------------------------------


def _num(metrics: Metrics, key: str) -> float | None:
    val = metrics.get(key)
    if isinstance(val, bool):  # bool is an int subclass — treat separately
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _ge(metrics: Metrics, key: str, threshold: float) -> bool:
    v = _num(metrics, key)
    return v is not None and v >= threshold


def _gt(metrics: Metrics, key: str, threshold: float) -> bool:
    v = _num(metrics, key)
    return v is not None and v > threshold


def _lt(metrics: Metrics, key: str, threshold: float) -> bool:
    v = _num(metrics, key)
    return v is not None and v < threshold


def _eq_str(metrics: Metrics, key: str, *values: str) -> bool:
    return str(metrics.get(key, "")) in values


# ---------------------------------------------------------------------------
# §4.2 trigger table — the single source of which rules exist.
# ---------------------------------------------------------------------------

RULES: tuple[Rule, ...] = (
    # CRIT-001 — fills.status='REJECTED' 連續 3 筆
    Rule(
        rule_id="CRIT-001",
        level=AlertLevel.CRITICAL,
        title="連續委託遭拒",
        predicate=lambda m: _ge(m, "fills_rejected_streak", 3),
        build_message=lambda m: (
            f"連續 {int(_num(m, 'fills_rejected_streak') or 0)} 筆委託遭券商拒絕，"
            "下單通道可能異常。"
        ),
    ),
    # CRIT-002 — shioaji connected=0 持續 60s
    Rule(
        rule_id="CRIT-002",
        level=AlertLevel.CRITICAL,
        title="Shioaji 斷線",
        predicate=lambda m: (
            _num(m, "shioaji_connected") == 0.0
            and _ge(m, "shioaji_disconnect_secs", 60)
        ),
        build_message=lambda m: (
            f"Shioaji 已斷線 {int(_num(m, 'shioaji_disconnect_secs') or 0)}s，"
            "即時報價中斷、無法下新單。"
        ),
    ),
    # CRIT-003 — risk_metrics.event_type in {L2_CUT, L3_HALT}
    Rule(
        rule_id="CRIT-003",
        level=AlertLevel.CRITICAL,
        title="熔斷觸發",
        predicate=lambda m: _eq_str(m, "risk_event_type", "L2_CUT", "L3_HALT"),
        build_message=lambda m: (
            f"風控熔斷 {m.get('risk_event_type')} 觸發，倉位將依規則處置。"
        ),
    ),
    # CRIT-004 — container restart_count > 0
    Rule(
        rule_id="CRIT-004",
        level=AlertLevel.CRITICAL,
        title="容器重啟",
        predicate=lambda m: _gt(m, "container_restart_count", 0),
        build_message=lambda m: (
            f"偵測到容器重啟 {int(_num(m, 'container_restart_count') or 0)} 次。"
        ),
    ),
    # HIGH-001 — etl_run.status='FAIL'
    Rule(
        rule_id="HIGH-001",
        level=AlertLevel.HIGH,
        title="ETL 失敗",
        predicate=lambda m: _eq_str(m, "etl_status", "FAIL"),
        build_message=lambda m: (
            f"ETL 來源 {m.get('etl_source', '未知')} 拉取失敗，今日盤前資料可能延遲。"
        ),
    ),
    # HIGH-002 — 14:30 訊號數 = 0（預期 > 0）
    Rule(
        rule_id="HIGH-002",
        level=AlertLevel.HIGH,
        title="訊號缺漏",
        predicate=lambda m: _num(m, "signal_count_1430") == 0.0,
        build_message=lambda _m: "14:30 訊號數為 0（預期 > 0），策略可能未正常產出訊號。",
    ),
    # HIGH-003 — |qty_actual - qty_expected| / qty_expected > 5%
    Rule(
        rule_id="HIGH-003",
        level=AlertLevel.HIGH,
        title="部位偏離",
        predicate=lambda m: _gt(m, "max_position_drift_pct", 0.05),
        build_message=lambda m: (
            f"最大部位偏離 {(_num(m, 'max_position_drift_pct') or 0) * 100:.1f}% > 5%。"
        ),
    ),
    # HIGH-004 — api_quota.finlab.remaining_mb < 500
    Rule(
        rule_id="HIGH-004",
        level=AlertLevel.HIGH,
        title="FinLab 流量偏低",
        predicate=lambda m: _lt(m, "finlab_remaining_mb", 500),
        build_message=lambda m: (
            f"FinLab 剩餘流量 {int(_num(m, 'finlab_remaining_mb') or 0)}MB < 500MB。"
        ),
    ),
    # INFO-001 — 每日 14:35 digest（績效 + 訊號摘要）
    Rule(
        rule_id="INFO-001",
        level=AlertLevel.INFO,
        title="每日績效摘要",
        predicate=lambda m: bool(m.get("daily_digest")),
        build_message=lambda m: str(m.get("digest_text", "每日績效與訊號摘要。")),
    ),
    # INFO-002 — 每筆 buy/sell 成交
    Rule(
        rule_id="INFO-002",
        level=AlertLevel.INFO,
        title="成交回報",
        predicate=lambda m: isinstance(m.get("trade_fill"), Mapping),
        build_message=lambda m: (
            f"{(m.get('trade_fill') or {}).get('action', '?')} "
            f"{(m.get('trade_fill') or {}).get('symbol', '?')} 成交。"
        ),
    ),
)


def rules_spec() -> list[dict[str, Any]]:
    """Read-only projection of the built-in §4.2 alert rules (id / level / title).

    Backs ``GET /system/alerts/rules``. Rule *definitions* are config, not live
    telemetry, so they ship now — derived from the ``RULES`` table so the API
    cannot drift from the engine. Alert *history* (actual firings) stays pending
    on the M4 producer; the predicates/message builders are runtime-only and not
    projected.
    """
    return [{"rule_id": r.rule_id, "level": r.level.value, "title": r.title} for r in RULES]


def _default_clock() -> datetime:
    # Taiwan time (UTC+8, no DST) so the 22:00-08:00 silent window is correct by
    # default. Fixed offset avoids a tzdata dependency; callers may inject any clock.
    return datetime.now(timezone(timedelta(hours=8)))


class AlertRouter:
    """Evaluate metrics against the §4.2 rule table into a list of :class:`Alert`.

    Side effect: an in-memory dedup ledger (``rule_id -> last fired at``) so the
    same rule fires at most once per :data:`DEDUPE_WINDOW`. This mirrors §4.4's
    "in-memory dict" option; swap for Redis at the call site if multi-process
    dedup is ever required (the engine itself stays pure-Python).

    Parameters
    ----------
    clock:
        Zero-arg callable returning the current :class:`datetime`. Injected so
        tests pin time; defaults to ``datetime.now(UTC)``. The clock is the sole
        time source — dedup windows and silent-hour checks both read it.
    """

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock: Clock = clock or _default_clock
        self._last_fired: dict[str, datetime] = {}

    def evaluate(self, metrics: Metrics) -> list[Alert]:
        """Return alerts that should be sent right now for ``metrics``.

        Order of checks per alert:
          1. predicate matches (§4.2)
          2. not silenced (§4.4 — non-Critical dropped inside 22:00–08:00)
          3. not deduped (§4.4 — same rule within 30 min)

        Only alerts that pass all three are returned *and* recorded in the
        dedup ledger. A rule suppressed by silent hours is NOT recorded, so it
        can still fire once the active window returns.
        """
        if not isinstance(metrics, Mapping):
            raise TypeError(f"metrics must be a Mapping, got {type(metrics).__name__}")

        now = self._clock()
        muted = silent_hours(now)
        fired: list[Alert] = []

        for rule in RULES:
            if not rule.predicate(metrics):
                continue
            if muted and rule.level is not AlertLevel.CRITICAL:
                continue  # §4.4 silent window — drop, do NOT record
            if self._is_deduped(rule.rule_id, now):
                continue
            fired.append(
                Alert(
                    rule_id=rule.rule_id,
                    level=rule.level,
                    title=rule.title,
                    message=rule.build_message(metrics),
                )
            )
            self._last_fired[rule.rule_id] = now

        return fired

    def _is_deduped(self, rule_id: str, now: datetime) -> bool:
        last = self._last_fired.get(rule_id)
        if last is None:
            return False
        # Window is inclusive of the boundary: "30 分鐘內只發一次" means a repeat
        # at exactly +30:00 is still within the window and suppressed. Only
        # strictly past 30 min releases the rule.
        return (now - last) <= DEDUPE_WINDOW

    def reset(self) -> None:
        """Clear the dedup ledger (e.g. on daemon restart)."""
        self._last_fired.clear()
