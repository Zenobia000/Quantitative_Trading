"""Ex-ante risk gate — the 12 pre-trade checks (EX-001..EX-012).

Implements ``dev_docs/24_risk_management_spec.md`` §2.1 (rule table) and §2.2
(evaluation order). Strategy-agnostic: the gate knows nothing about any specific
strategy. It receives a single proposed :class:`Order` plus an injected
:class:`AccountState` snapshot and a :class:`RiskGateConfig` of thresholds, and
returns a :class:`RiskGateResult` describing whether the order may proceed.

Design principles (spec §1):

* **保守優先** — when in doubt, reject.
* **可追溯** — every rejection carries ``(rule_id, reason)`` for the audit trail.

Each rule is a small pure function ``check_<exNNN>(order, account, config) ->
str | None`` returning ``None`` on pass or a human-readable reason on reject.
:class:`RiskGate` wires them together in the spec's priority order. By default it
fails fast (returns on the first violation, matching the spec's reference
``evaluate`` loop); pass ``collect_all=True`` for a full audit sweep.

No DB, network, or broker dependency — all state is injected, so the module is
trivially unit-testable and reusable across backtest / paper / live runners.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar

# Canonical BreakerState shared with risk.circuit_breaker (see risk/types.py):
# the breaker latches to HALTED, so EX-012 must reject on HALTED (and L3).
from quant_platform.services.risk_gate.types import BreakerState

# --------------------------------------------------------------------------- #
# Value objects (frozen — never mutate inputs, per coding-style §不可變性).     #
# --------------------------------------------------------------------------- #

_BUY_SIDES = frozenset({"buy", "add"})
_SELL_SIDES = frozenset({"sell", "reduce", "exit", "stoploss"})
_VALID_SIDES = _BUY_SIDES | _SELL_SIDES


@dataclass(frozen=True)
class Position:
    """A currently-held position used to evaluate portfolio-level limits."""

    stock_id: str
    qty: float
    entry: float
    stop_loss: float
    market_value: float
    industry: str = ""

    @property
    def risk_amount(self) -> float:
        """Loss if this position hits its stop (heat numerator term)."""
        return abs(self.qty) * abs(self.entry - self.stop_loss)


@dataclass(frozen=True)
class Order:
    """A proposed pre-trade order. All fields needed by EX-001..EX-012.

    ``order_type`` distinguishes ``"limit"`` (price-checked by EX-006) from
    ``"market"`` (exempt). ``stop_loss`` / ``prev_close`` / ``avg_volume_20d``
    are only consulted by the rules that need them.
    """

    stock_id: str
    side: str
    qty: float
    price: float
    industry: str = ""
    stop_loss: float = 0.0
    prev_close: float = 0.0
    avg_volume_20d: float = 0.0
    order_type: str = "limit"

    @property
    def notional(self) -> float:
        return abs(self.qty) * self.price

    @property
    def is_buy(self) -> bool:
        return self.side in _BUY_SIDES


@dataclass(frozen=True)
class AccountState:
    """Injected account snapshot. Strategy-agnostic context for the gate."""

    equity: float
    cash: float
    positions: tuple[Position, ...] = ()
    breaker_state: BreakerState = BreakerState.NORMAL
    orders_last_minute: int = 0
    blacklist: frozenset[str] = field(default_factory=frozenset)

    def position(self, stock_id: str) -> Position | None:
        for pos in self.positions:
            if pos.stock_id == stock_id:
                return pos
        return None


@dataclass(frozen=True)
class RiskGateConfig:
    """Thresholds for the 12 rules. Defaults reproduce spec §2.1 numbers.

    All limits live here (no hardcoded magic numbers inside the rule functions)
    so a strategy/account can tune them without touching logic.
    """

    single_order_max_notional: float = 500_000.0   # EX-001 absolute (NT$)
    single_order_max_equity_pct: float = 0.05       # EX-001 relative
    single_name_max_pct: float = 0.08               # EX-002
    industry_max_pct: float = 0.35                  # EX-003
    portfolio_heat_max: float = 0.06                # EX-004
    cash_floor_pct: float = 0.10                    # EX-005
    max_positions: int = 15                         # EX-007
    min_stop_pct: float = 0.05                      # EX-008 (stop within 5%)
    order_rate_max_per_min: int = 30                # EX-009 (must be < this)
    price_limit_pct: float = 0.10                   # EX-006 (±10%)
    liquidity_max_pct: float = 0.20                 # EX-010 (≤20% of ADV20)


@dataclass(frozen=True)
class RiskGateResult:
    """Outcome of a gate evaluation.

    ``allowed`` is ``True`` only when ``rejections`` is empty. ``rejections`` is
    an ordered list of ``(rule_id, reason)`` tuples for the audit trail.
    """

    allowed: bool
    rejections: list[tuple[str, str]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Rule functions — pure: (order, account, config) -> reason | None.            #
# Returning None means "passed"; a string means "rejected, here's why".        #
# --------------------------------------------------------------------------- #


def check_ex001(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-001 — single order notional under both the absolute and %-equity cap."""
    if order.notional >= cfg.single_order_max_notional:
        return (
            f"order notional {order.notional:,.0f} >= cap "
            f"{cfg.single_order_max_notional:,.0f}"
        )
    if account.equity > 0:
        pct = order.notional / account.equity
        if pct >= cfg.single_order_max_equity_pct:
            return (
                f"order is {pct:.2%} of equity >= "
                f"{cfg.single_order_max_equity_pct:.0%}"
            )
    return None


def check_ex002(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-002 — resulting single-name exposure under 8% equity (buys only)."""
    if not order.is_buy or account.equity <= 0:
        return None
    held = account.position(order.stock_id)
    held_mv = held.market_value if held else 0.0
    projected = held_mv + order.notional
    pct = projected / account.equity
    if pct >= cfg.single_name_max_pct:
        return (
            f"{order.stock_id} would be {pct:.2%} of equity >= "
            f"{cfg.single_name_max_pct:.0%}"
        )
    return None


def check_ex003(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-003 — resulting industry concentration under 35% equity (buys only)."""
    if not order.is_buy or account.equity <= 0 or not order.industry:
        return None
    industry_mv = sum(
        p.market_value for p in account.positions if p.industry == order.industry
    )
    projected = industry_mv + order.notional
    pct = projected / account.equity
    if pct >= cfg.industry_max_pct:
        return (
            f"industry '{order.industry}' would be {pct:.2%} of equity >= "
            f"{cfg.industry_max_pct:.0%}"
        )
    return None


def check_ex004(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-004 — portfolio heat under 6% (buys add risk; sells reduce it)."""
    if not order.is_buy or account.equity <= 0:
        return None
    existing_risk = sum(p.risk_amount for p in account.positions)
    new_risk = abs(order.qty) * abs(order.price - order.stop_loss)
    heat = (existing_risk + new_risk) / account.equity
    if heat >= cfg.portfolio_heat_max:
        return f"portfolio heat {heat:.2%} >= {cfg.portfolio_heat_max:.0%}"
    return None


def check_ex005(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-005 — cash after a buy must stay above 10% of equity."""
    if not order.is_buy or account.equity <= 0:
        return None
    cash_after = account.cash - order.notional
    floor = cfg.cash_floor_pct * account.equity
    if cash_after < floor:
        return (
            f"cash after buy {cash_after:,.0f} < floor {floor:,.0f} "
            f"({cfg.cash_floor_pct:.0%} equity)"
        )
    return None


def check_ex006(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-006 — limit price within ±10% of prev_close (market orders exempt)."""
    if order.order_type != "limit" or order.prev_close <= 0:
        return None
    move = (order.price - order.prev_close) / order.prev_close
    if abs(move) > cfg.price_limit_pct:
        return (
            f"limit price {order.price} is {move:+.2%} vs prev_close "
            f"{order.prev_close} (>|{cfg.price_limit_pct:.0%}|)"
        )
    return None


def check_ex007(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-007 — opening a *new* name must not exceed max concurrent holdings."""
    if not order.is_buy:
        return None
    if account.position(order.stock_id) is not None:
        return None  # adding to an existing name does not raise the count
    if len(account.positions) >= cfg.max_positions:
        return (
            f"opening {order.stock_id} would exceed max positions "
            f"{cfg.max_positions} (held {len(account.positions)})"
        )
    return None


def check_ex008(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-008 — entry stop no further than 5% below price (buys only)."""
    if not order.is_buy or order.price <= 0:
        return None
    min_stop = order.price * (1.0 - cfg.min_stop_pct)
    if order.stop_loss < min_stop:
        return (
            f"stop_loss {order.stop_loss} < min {min_stop:.2f} "
            f"(entry {order.price} x {1 - cfg.min_stop_pct:.2f})"
        )
    return None


def check_ex009(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-009 — order-rate guard: fewer than N orders in the trailing minute."""
    if account.orders_last_minute >= cfg.order_rate_max_per_min:
        return (
            f"{account.orders_last_minute} orders in last minute >= "
            f"{cfg.order_rate_max_per_min}/min (possible runaway)"
        )
    return None


def check_ex010(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-010 — order qty within 20% of 20-day average volume."""
    if order.avg_volume_20d <= 0:
        return None
    cap = cfg.liquidity_max_pct * order.avg_volume_20d
    if abs(order.qty) > cap:
        return (
            f"qty {abs(order.qty):,.0f} > {cfg.liquidity_max_pct:.0%} of ADV20 "
            f"({cap:,.0f})"
        )
    return None


def check_ex011(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-011 — stock must not be on the runtime blacklist."""
    if order.stock_id in account.blacklist:
        return f"{order.stock_id} is blacklisted"
    return None


def check_ex012(order: Order, account: AccountState, cfg: RiskGateConfig) -> str | None:
    """EX-012 — circuit breaker must not be tripped (reject all orders).

    The breaker latches L3 → HALTED (terminal); both are a full stop, so reject
    on either — a divergent enum previously let HALTED-state orders slip through.
    """
    if account.breaker_state in (BreakerState.L3, BreakerState.HALTED):
        return "circuit breaker tripped (L3/HALTED) — all orders rejected"
    return None


# --------------------------------------------------------------------------- #
# The gate.                                                                    #
# --------------------------------------------------------------------------- #


# Rule registry keyed by id. Module-level so it is built once.
_RULES = {
    "EX-001": check_ex001,
    "EX-002": check_ex002,
    "EX-003": check_ex003,
    "EX-004": check_ex004,
    "EX-005": check_ex005,
    "EX-006": check_ex006,
    "EX-007": check_ex007,
    "EX-008": check_ex008,
    "EX-009": check_ex009,
    "EX-010": check_ex010,
    "EX-011": check_ex011,
    "EX-012": check_ex012,
}


class RiskGate:
    """Evaluates the 12 ex-ante rules in spec §2.2 priority order.

    >>> gate = RiskGate(RiskGateConfig())
    >>> result = gate.check(order, account_state)
    >>> if result.allowed: broker.submit(order)
    """

    # §2.2: HALT first, then frequency/blacklist, then quota rules, heat last
    # (most expensive), then order-detail checks.
    RULES_IN_ORDER: ClassVar[list[str]] = [
        "EX-012",  # circuit breaker
        "EX-009",  # order frequency
        "EX-011",  # blacklist
        "EX-001",  # single-order notional
        "EX-002",  # single-name exposure
        "EX-003",  # industry concentration
        "EX-005",  # cash floor
        "EX-007",  # max positions
        "EX-004",  # portfolio heat
        "EX-006",  # price limit
        "EX-008",  # stop distance
        "EX-010",  # liquidity
    ]

    def __init__(self, config: RiskGateConfig | None = None) -> None:
        self._config = config if config is not None else RiskGateConfig()

    @property
    def config(self) -> RiskGateConfig:
        return self._config

    def check(
        self,
        order: Order,
        account_state: AccountState,
        *,
        collect_all: bool = False,
    ) -> RiskGateResult:
        """Run the gate.

        Args:
            order: the proposed pre-trade order.
            account_state: injected account / portfolio snapshot.
            collect_all: when ``False`` (default) return on the first failing
                rule (fail-fast, matching the spec reference loop). When
                ``True`` evaluate every rule and report all violations,
                preserving §2.2 order — useful for a complete audit trail.

        Returns:
            :class:`RiskGateResult` with ``allowed`` and ordered ``rejections``.

        Raises:
            ValueError: on malformed input (unknown side, negative qty).
        """
        self._validate(order, account_state)

        rejections: list[tuple[str, str]] = []
        for rule_id in self.RULES_IN_ORDER:
            reason = _RULES[rule_id](order, account_state, self._config)
            if reason is not None:
                rejections.append((rule_id, reason))
                if not collect_all:
                    break

        return RiskGateResult(allowed=not rejections, rejections=rejections)

    @staticmethod
    def _validate(order: Order, account_state: AccountState) -> None:
        if order.side not in _VALID_SIDES:
            raise ValueError(
                f"unknown order side {order.side!r}; expected one of "
                f"{sorted(_VALID_SIDES)}"
            )
        if order.qty < 0:
            raise ValueError(f"order qty must be non-negative, got {order.qty}")
        if account_state.equity < 0:
            raise ValueError(
                f"account equity must be non-negative, got {account_state.equity}"
            )


def risk_spec(config: RiskGateConfig | None = None) -> dict[str, Any]:
    """Structured, read-only description of the 12 ex-ante rules in evaluation
    order plus the active thresholds.

    Pure projection — no evaluation. Derived from the rule registry and
    ``RiskGate.RULES_IN_ORDER`` so "what the gate checks" cannot drift from the
    logic that enforces it. Backs ``GET /system/risk/spec`` (config, not live
    telemetry — available without the M4 producer) and the CLI risk-spec view.
    """
    cfg = config or RiskGateConfig()
    rules = [
        {
            "id": rid,
            "order": i,
            "description": (_RULES[rid].__doc__ or rid).strip().splitlines()[0],
        }
        for i, rid in enumerate(RiskGate.RULES_IN_ORDER, start=1)
    ]
    return {"rules": rules, "thresholds": asdict(cfg)}


__all__ = [
    "AccountState",
    "BreakerState",
    "Order",
    "Position",
    "RiskGate",
    "RiskGateConfig",
    "RiskGateResult",
    "check_ex001",
    "check_ex002",
    "check_ex003",
    "check_ex004",
    "check_ex005",
    "check_ex006",
    "check_ex007",
    "check_ex008",
    "check_ex009",
    "check_ex010",
    "check_ex011",
    "check_ex012",
    "risk_spec",
]
