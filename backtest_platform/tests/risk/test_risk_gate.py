"""Unit tests for the ex-ante risk gate (24_risk_management_spec.md §2.1/§2.2).

Strategy-agnostic. All state is injected (synthetic ``Order`` / ``AccountState``
/ ``RiskGateConfig``); no DB, network, or broker dependency. Each test pins one
EX rule's pass/reject behaviour plus boundary, then a block asserts the §2.2
evaluation order when several rules trip simultaneously.
"""
from __future__ import annotations

import dataclasses

import pytest

from backtest_platform.risk.risk_gate import (
    AccountState,
    BreakerState,
    Order,
    Position,
    RiskGate,
    RiskGateConfig,
    RiskGateResult,
)

# --------------------------------------------------------------------------- #
# Builders — minimal "happy path" objects that pass every rule, so each test   #
# perturbs exactly one dimension.                                              #
# --------------------------------------------------------------------------- #


def _order(**overrides) -> Order:
    base = dict(
        stock_id="2330",
        side="buy",
        qty=1000,
        price=100.0,
        industry="semiconductor",
        stop_loss=96.0,        # 4% below price → passes EX-008
        prev_close=100.0,      # limit within ±10% → passes EX-006
        avg_volume_20d=1_000_000,  # qty 1000 << 20% → passes EX-010
    )
    base.update(overrides)
    return Order(**base)


def _account(**overrides) -> AccountState:
    base = dict(
        equity=10_000_000.0,
        cash=5_000_000.0,        # 50% cash → passes EX-005
        positions=(),            # 0 holdings → passes EX-007 & EX-002 & EX-003
        breaker_state=BreakerState.NORMAL,  # passes EX-012
        orders_last_minute=0,    # passes EX-009
        blacklist=frozenset(),   # passes EX-011
    )
    base.update(overrides)
    return AccountState(**base)


def _pos(**overrides) -> Position:
    base = dict(
        stock_id="1101",
        qty=1000,
        entry=50.0,
        stop_loss=47.5,
        market_value=50_000.0,
        industry="cement",
    )
    base.update(overrides)
    return Position(**base)


@pytest.fixture
def gate() -> RiskGate:
    return RiskGate(RiskGateConfig())


# --------------------------------------------------------------------------- #
# Happy path: a clean order passes the whole gate.                             #
# --------------------------------------------------------------------------- #


def test_clean_order_passes(gate: RiskGate) -> None:
    result = gate.check(_order(), _account())
    assert isinstance(result, RiskGateResult)
    assert result.allowed is True
    assert result.rejections == []


def test_result_is_frozen(gate: RiskGate) -> None:
    result = gate.check(_order(), _account())
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.allowed = False  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# EX-012 — circuit breaker HALTED rejects everything.                          #
# --------------------------------------------------------------------------- #


def test_ex012_halted_rejects_buy(gate: RiskGate) -> None:
    result = gate.check(_order(side="buy"), _account(breaker_state=BreakerState.HALTED))
    assert result.allowed is False
    assert "EX-012" in {r[0] for r in result.rejections}


def test_ex012_halted_rejects_even_sell(gate: RiskGate) -> None:
    # HALTED locks the gate for *all* orders (spec §2.1: "reject all").
    result = gate.check(_order(side="sell"), _account(breaker_state=BreakerState.HALTED))
    assert result.allowed is False
    assert "EX-012" in {r[0] for r in result.rejections}


def test_ex012_normal_passes(gate: RiskGate) -> None:
    result = gate.check(_order(), _account(breaker_state=BreakerState.NORMAL))
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-009 — order frequency cap (< 30 / minute).                                #
# --------------------------------------------------------------------------- #


def test_ex009_over_frequency_rejects(gate: RiskGate) -> None:
    result = gate.check(_order(), _account(orders_last_minute=30))
    assert result.allowed is False
    assert "EX-009" in {r[0] for r in result.rejections}


def test_ex009_boundary_29_passes(gate: RiskGate) -> None:
    # 29 already placed → this is the 30th; spec threshold is "< 30 orders".
    result = gate.check(_order(), _account(orders_last_minute=29))
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-011 — blacklist.                                                          #
# --------------------------------------------------------------------------- #


def test_ex011_blacklisted_rejects(gate: RiskGate) -> None:
    result = gate.check(_order(stock_id="0050"), _account(blacklist=frozenset({"0050"})))
    assert result.allowed is False
    assert "EX-011" in {r[0] for r in result.rejections}


def test_ex011_not_blacklisted_passes(gate: RiskGate) -> None:
    result = gate.check(_order(stock_id="2330"), _account(blacklist=frozenset({"0050"})))
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-001 — single order notional cap (< NT$500k AND < 5% equity).              #
# --------------------------------------------------------------------------- #


def test_ex001_over_absolute_cap_rejects(gate: RiskGate) -> None:
    # 6000 * 100 = 600,000 > 500,000 absolute cap.
    result = gate.check(_order(qty=6000, price=100.0), _account(equity=100_000_000.0))
    assert result.allowed is False
    assert "EX-001" in {r[0] for r in result.rejections}


def test_ex001_over_equity_pct_rejects(gate: RiskGate) -> None:
    # notional 400,000 < 500k abs cap, but equity is tiny → > 5% equity.
    result = gate.check(_order(qty=4000, price=100.0), _account(equity=1_000_000.0))
    assert result.allowed is False
    assert "EX-001" in {r[0] for r in result.rejections}


def test_ex001_within_caps_passes(gate: RiskGate) -> None:
    result = gate.check(_order(qty=1000, price=100.0), _account(equity=10_000_000.0))
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-002 — single-name position cap (< 8% equity, incl. new order).            #
# --------------------------------------------------------------------------- #


def test_ex002_over_single_name_rejects(gate: RiskGate) -> None:
    # Existing 700k in 2330 + new 200k = 900k = 9% of 10M > 8%.
    existing = _pos(stock_id="2330", market_value=700_000.0, industry="semiconductor")
    result = gate.check(
        _order(stock_id="2330", qty=2000, price=100.0),  # +200k
        _account(equity=10_000_000.0, positions=(existing,)),
    )
    assert result.allowed is False
    assert "EX-002" in {r[0] for r in result.rejections}


def test_ex002_at_boundary_passes(gate: RiskGate) -> None:
    # Existing 500k + new 200k = 700k = 7% < 8%.
    existing = _pos(stock_id="2330", market_value=500_000.0, industry="semiconductor")
    result = gate.check(
        _order(stock_id="2330", qty=2000, price=100.0),
        _account(equity=10_000_000.0, positions=(existing,)),
    )
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-003 — industry concentration cap (< 35% equity).                         #
# --------------------------------------------------------------------------- #


def test_ex003_over_industry_rejects(gate: RiskGate) -> None:
    # 3.3M existing semiconductor + 200k new = 3.5M = 35% — not < 35% → reject.
    existing = _pos(stock_id="2454", market_value=3_300_000.0, industry="semiconductor")
    result = gate.check(
        _order(stock_id="2330", qty=2000, price=100.0, industry="semiconductor"),
        _account(equity=10_000_000.0, positions=(existing,)),
    )
    assert result.allowed is False
    assert "EX-003" in {r[0] for r in result.rejections}


def test_ex003_other_industry_passes(gate: RiskGate) -> None:
    existing = _pos(stock_id="2454", market_value=3_300_000.0, industry="semiconductor")
    result = gate.check(
        _order(stock_id="1101", qty=2000, price=100.0, industry="cement"),
        _account(equity=10_000_000.0, positions=(existing,)),
    )
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-004 — portfolio heat cap (< 6%).                                         #
# --------------------------------------------------------------------------- #


def test_ex004_over_heat_rejects(gate: RiskGate) -> None:
    # Isolate EX-004: large equity so notional/cash/single-name rules pass,
    # but an existing position whose stop-risk alone exceeds 6% of equity.
    # risk = qty * |entry - stop| = 700_000 * |50 - 47.5| = 1,750,000.
    # equity 20M → heat = 8.75% >= 6%. Use collect_all to see EX-004 even if a
    # later detail rule were also to trip (none should here).
    existing = _pos(stock_id="1101", qty=700_000, entry=50.0, stop_loss=47.5,
                    market_value=1_000_000.0, industry="cement")
    result = gate.check(
        _order(stock_id="2330", qty=1000, price=100.0, stop_loss=96.0),  # tiny new risk
        _account(equity=20_000_000.0, cash=19_000_000.0, positions=(existing,)),
        collect_all=True,
    )
    assert result.allowed is False
    assert "EX-004" in {r[0] for r in result.rejections}


def test_ex004_within_heat_passes(gate: RiskGate) -> None:
    existing = _pos(stock_id="1101", qty=1000, entry=50.0, stop_loss=47.5,
                    market_value=50_000.0, industry="cement")
    # existing heat = 1000*2.5 = 2500 / 10M tiny; new order risk small → < 6%.
    result = gate.check(
        _order(stock_id="2330", qty=1000, price=100.0, stop_loss=96.0),
        _account(equity=10_000_000.0, positions=(existing,)),
    )
    assert result.allowed is True


def test_ex004_sell_skips_heat(gate: RiskGate) -> None:
    # A reduce/exit order lowers heat — it must not be rejected by EX-004.
    existing = _pos(stock_id="1101", qty=200_000, entry=50.0, stop_loss=47.5,
                    market_value=10_000_000.0, industry="cement")
    result = gate.check(
        _order(stock_id="1101", side="sell", qty=1000, price=50.0, stop_loss=0.0),
        _account(equity=1_000_000.0, positions=(existing,)),
    )
    assert "EX-004" not in {r[0] for r in result.rejections}


# --------------------------------------------------------------------------- #
# EX-005 — cash reserve floor (> 10% equity after a buy).                      #
# --------------------------------------------------------------------------- #


def test_ex005_buy_drains_cash_rejects(gate: RiskGate) -> None:
    # cash 1.2M, equity 10M → floor 1.0M. Buy 300k would leave 900k < floor.
    result = gate.check(
        _order(side="buy", qty=3000, price=100.0),  # 300k
        _account(equity=10_000_000.0, cash=1_200_000.0),
    )
    assert result.allowed is False
    assert "EX-005" in {r[0] for r in result.rejections}


def test_ex005_sell_exempt(gate: RiskGate) -> None:
    # Sells add cash; EX-005 only guards buy/add.
    result = gate.check(
        _order(side="sell", qty=3000, price=100.0),
        _account(equity=10_000_000.0, cash=1_050_000.0),
    )
    assert "EX-005" not in {r[0] for r in result.rejections}


def test_ex005_buy_with_buffer_passes(gate: RiskGate) -> None:
    result = gate.check(
        _order(side="buy", qty=1000, price=100.0),  # 100k
        _account(equity=10_000_000.0, cash=5_000_000.0),
    )
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-007 — max concurrent holdings (≤ 15, only blocks *new* names on buy).     #
# --------------------------------------------------------------------------- #


def test_ex007_new_name_at_limit_rejects(gate: RiskGate) -> None:
    # Equity sized so the small order clears EX-001/002/005; collect_all keeps
    # EX-007 visible regardless of evaluation order.
    positions = tuple(_pos(stock_id=f"S{i:04d}") for i in range(15))
    result = gate.check(
        _order(stock_id="9999", side="buy"),  # 16th distinct name
        _account(equity=10_000_000.0, cash=9_000_000.0, positions=positions),
        collect_all=True,
    )
    assert result.allowed is False
    assert "EX-007" in {r[0] for r in result.rejections}


def test_ex007_add_to_existing_at_limit_passes(gate: RiskGate) -> None:
    # Adding to a name already held does not increase the holdings count.
    positions = tuple(_pos(stock_id=f"S{i:04d}") for i in range(15))
    result = gate.check(
        _order(stock_id="S0000", side="buy"),
        _account(equity=10_000_000.0, cash=9_000_000.0, positions=positions),
        collect_all=True,
    )
    assert "EX-007" not in {r[0] for r in result.rejections}


def test_ex007_below_limit_passes(gate: RiskGate) -> None:
    positions = tuple(_pos(stock_id=f"S{i:04d}") for i in range(14))
    result = gate.check(
        _order(stock_id="9999", side="buy"),
        _account(equity=10_000_000.0, cash=9_000_000.0, positions=positions),
    )
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# EX-006 — price-limit (±10% from prev_close) for limit orders.               #
# --------------------------------------------------------------------------- #


def test_ex006_over_limit_up_rejects(gate: RiskGate) -> None:
    result = gate.check(
        _order(price=111.0, prev_close=100.0),  # +11% > +10%
        _account(),
    )
    assert result.allowed is False
    assert "EX-006" in {r[0] for r in result.rejections}


def test_ex006_under_limit_down_rejects(gate: RiskGate) -> None:
    result = gate.check(
        _order(price=89.0, prev_close=100.0, stop_loss=85.0),  # -11% < -10%
        _account(),
    )
    assert result.allowed is False
    assert "EX-006" in {r[0] for r in result.rejections}


def test_ex006_within_band_passes(gate: RiskGate) -> None:
    # stop_loss must stay within 5% of the (raised) price to also clear EX-008.
    result = gate.check(
        _order(price=109.0, prev_close=100.0, stop_loss=105.0), _account()
    )
    assert result.allowed is True


def test_ex006_market_order_exempt(gate: RiskGate) -> None:
    # order_type "market" has no limit price → EX-006 does not apply.
    result = gate.check(
        _order(price=130.0, prev_close=100.0, order_type="market"),
        _account(),
    )
    assert "EX-006" not in {r[0] for r in result.rejections}


# --------------------------------------------------------------------------- #
# EX-008 — minimum stop distance (stop_loss >= entry * 0.95).                   #
# --------------------------------------------------------------------------- #


def test_ex008_stop_too_far_rejects(gate: RiskGate) -> None:
    # stop 90 < 100*0.95=95 → too far → reject.
    result = gate.check(_order(side="buy", price=100.0, stop_loss=90.0), _account())
    assert result.allowed is False
    assert "EX-008" in {r[0] for r in result.rejections}


def test_ex008_stop_at_boundary_passes(gate: RiskGate) -> None:
    result = gate.check(_order(side="buy", price=100.0, stop_loss=95.0), _account())
    assert result.allowed is True


def test_ex008_sell_exempt(gate: RiskGate) -> None:
    # Stop distance only meaningful for entries; sells carry no stop.
    result = gate.check(_order(side="sell", price=100.0, stop_loss=0.0), _account())
    assert "EX-008" not in {r[0] for r in result.rejections}


# --------------------------------------------------------------------------- #
# EX-010 — liquidity (qty ≤ 20% of 20D avg volume).                           #
# --------------------------------------------------------------------------- #


def test_ex010_over_liquidity_rejects(gate: RiskGate) -> None:
    # 20D avg 1000 → 20% = 200. qty 500 > 200 → reject.
    result = gate.check(_order(qty=500, avg_volume_20d=1000), _account())
    assert result.allowed is False
    assert "EX-010" in {r[0] for r in result.rejections}


def test_ex010_at_boundary_passes(gate: RiskGate) -> None:
    # qty 200 == 20% of 1000 → "≤" so passes.
    result = gate.check(_order(qty=200, avg_volume_20d=1000), _account())
    assert result.allowed is True


# --------------------------------------------------------------------------- #
# Config-driven thresholds (strategy-agnostic, no hardcoded numbers).          #
# --------------------------------------------------------------------------- #


def test_config_overrides_single_name_cap() -> None:
    # Loosen single-name cap to 10% → an order that fails at 8% now passes.
    loose = RiskGate(RiskGateConfig(single_name_max_pct=0.10))
    existing = _pos(stock_id="2330", market_value=700_000.0, industry="semiconductor")
    res = loose.check(
        _order(stock_id="2330", qty=2000, price=100.0),  # +200k → 9%
        _account(equity=10_000_000.0, positions=(existing,)),
    )
    assert res.allowed is True


def test_config_defaults_match_spec() -> None:
    cfg = RiskGateConfig()
    assert cfg.single_order_max_notional == 500_000
    assert cfg.single_order_max_equity_pct == 0.05
    assert cfg.single_name_max_pct == 0.08
    assert cfg.industry_max_pct == 0.35
    assert cfg.portfolio_heat_max == 0.06
    assert cfg.cash_floor_pct == 0.10
    assert cfg.max_positions == 15
    assert cfg.min_stop_pct == 0.05
    assert cfg.order_rate_max_per_min == 30
    assert cfg.price_limit_pct == 0.10
    assert cfg.liquidity_max_pct == 0.20


# --------------------------------------------------------------------------- #
# §2.2 evaluation order — when several rules trip, the gate reports the        #
# first-failing rule per RULES_IN_ORDER, and (by design) collects *all*        #
# rejections so the audit trail is complete.                                   #
# --------------------------------------------------------------------------- #


def test_rules_in_order_matches_spec() -> None:
    assert RiskGate.RULES_IN_ORDER == [
        "EX-012",
        "EX-009",
        "EX-011",
        "EX-001",
        "EX-002",
        "EX-003",
        "EX-005",
        "EX-007",
        "EX-004",
        "EX-006",
        "EX-008",
        "EX-010",
    ]


def test_halted_short_circuits_first_rejection() -> None:
    # HALTED + blacklist + over-frequency all trip; EX-012 must be reported
    # first (and, with fail-fast semantics, be the *only* rejection).
    gate = RiskGate(RiskGateConfig())
    res = gate.check(
        _order(stock_id="0050", price=200.0),  # also breaks EX-006 etc.
        _account(
            breaker_state=BreakerState.HALTED,
            blacklist=frozenset({"0050"}),
            orders_last_minute=99,
        ),
    )
    assert res.allowed is False
    assert res.rejections[0][0] == "EX-012"


def test_first_failing_is_highest_priority() -> None:
    # Not halted, but over-frequency (EX-009) AND blacklisted (EX-011).
    # EX-009 precedes EX-011 in RULES_IN_ORDER → reported first.
    gate = RiskGate(RiskGateConfig())
    res = gate.check(
        _order(stock_id="0050"),
        _account(blacklist=frozenset({"0050"}), orders_last_minute=50),
    )
    assert res.allowed is False
    assert res.rejections[0][0] == "EX-009"


def test_collect_all_reports_every_violation() -> None:
    # collect_all=True → audit trail contains both violations, still ordered.
    gate = RiskGate(RiskGateConfig())
    res = gate.check(
        _order(stock_id="0050"),
        _account(blacklist=frozenset({"0050"}), orders_last_minute=50),
        collect_all=True,
    )
    rule_ids = [r[0] for r in res.rejections]
    assert rule_ids == ["EX-009", "EX-011"]
    assert res.allowed is False


def test_rejection_reason_is_human_readable() -> None:
    gate = RiskGate(RiskGateConfig())
    res = gate.check(_order(), _account(breaker_state=BreakerState.HALTED))
    rule_id, reason = res.rejections[0]
    assert rule_id == "EX-012"
    assert isinstance(reason, str) and reason  # non-empty explanation


# --------------------------------------------------------------------------- #
# Input validation at the boundary.                                            #
# --------------------------------------------------------------------------- #


def test_unknown_side_raises() -> None:
    gate = RiskGate(RiskGateConfig())
    with pytest.raises(ValueError):
        gate.check(_order(side="hold"), _account())


def test_negative_qty_raises() -> None:
    gate = RiskGate(RiskGateConfig())
    with pytest.raises(ValueError):
        gate.check(_order(qty=-1), _account())
