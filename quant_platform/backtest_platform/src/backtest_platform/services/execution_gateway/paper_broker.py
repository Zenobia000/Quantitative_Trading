"""Strategy-agnostic simulated broker for paper trading (WBS 7.A.1 / 7.A.2).

``PaperBroker`` is the in-process matching engine used by the M4 paper-trading
daemon (``python -m backtest_platform.adapters.brokers.paper_broker`` in the
deployment topology, dev_docs/23 §3.3) and by any monitoring / risk caller that
needs a deterministic portfolio model without touching a real brokerage.

Design contract:
  * Matching is simplified — a market/limit order fills *entirely* at the
    supplied ``price``. There is no order book, partial fill, or latency model;
    the caller decides the execution price.
  * Costs come from ``StrategyConfig`` so the platform has a single source of
    truth for the cost model:
        fee  = notional × fee_rate × fee_discount   (both buy and sell)
        tax  = notional × tax_stock_rate            (sell side only — Taiwan
                                                      securities-transaction tax)
    Slippage is intentionally *not* applied here: the caller passes the already
    slipped execution price, keeping this class a pure book-keeper.
  * No naked shorting — selling more than the held quantity is rejected.
  * ``portfolio_snapshot`` exposes positions / cash / equity / heat for the
    ex-post monitor and the EX-004 heat circuit-breaker (dev_docs/24 §EX-004):
        Heat = Σ_i qty_i · |entry_i − stop_i| / equity
    Stop levels are strategy-specific, so they are injected per call; with no
    stops known the heat contribution is 0 (strategy-agnostic default).

The class holds no DB / network handles; persistence (``INSERT fills``) is the
caller's concern. This keeps it unit-testable with synthetic inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig


class OrderSide(str, Enum):
    """Order direction. Inherits ``str`` so ``OrderSide('buy')`` and plain
    string comparisons / JSON serialization work for CLI and snapshot output."""

    BUY = "buy"
    SELL = "sell"

    @classmethod
    def coerce(cls, value: OrderSide | str) -> OrderSide:
        """Accept an ``OrderSide`` or a case-insensitive 'buy'/'sell' string."""
        if isinstance(value, OrderSide):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            raise ValueError(
                f"invalid order side {value!r}; expected 'buy' or 'sell'"
            ) from None


class InsufficientPositionError(Exception):
    """Raised when a sell exceeds the held quantity (no naked shorting)."""


@dataclass(frozen=True, slots=True)
class Fill:
    """An executed trade. Immutable record appended to the trade log."""

    stock_id: str
    side: OrderSide
    qty: int
    price: float
    fee: float
    tax: float

    @property
    def notional(self) -> float:
        """Gross trade value before costs."""
        return self.qty * self.price

    @property
    def cash_flow(self) -> float:
        """Signed effect on cash: negative for a buy, positive for a sell."""
        if self.side is OrderSide.BUY:
            return -(self.notional + self.fee + self.tax)
        return self.notional - self.fee - self.tax


@dataclass(slots=True)
class Position:
    """A long holding with weighted-average cost basis (per share)."""

    qty: int
    cost_basis: float


@dataclass(slots=True)
class PaperBroker:
    """In-process simulated broker with a Taiwan-equity cost model.

    Parameters
    ----------
    initial_cash:
        Starting account cash; must be > 0.
    config:
        Cost-model source (fees / tax). Defaults to the platform-wide
        ``DEFAULT_CONFIG`` so callers need not wire it explicitly.
    """

    initial_cash: float
    config: StrategyConfig = field(default_factory=StrategyConfig)
    cash: float = field(init=False)
    _positions: dict[str, Position] = field(init=False, default_factory=dict)
    _trade_log: list[Fill] = field(init=False, default_factory=list)
    _last_price: dict[str, float] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(
                f"initial_cash must be > 0, got {self.initial_cash!r}"
            )
        self.cash = float(self.initial_cash)

    # ------------------------------------------------------------------ #
    # Restore — rehydrate a book persisted by a previous session
    # ------------------------------------------------------------------ #
    @classmethod
    def from_seed(
        cls,
        cash: float,
        positions: Mapping[str, tuple[int, float]],
        *,
        config: StrategyConfig | None = None,
    ) -> PaperBroker:
        """Build a broker pre-loaded with restored ``cash`` + ``positions``.

        ``positions`` maps ``stock_id -> (qty, cost_basis)`` (the shape
        ``data.db_reader.load_broker_state`` reconstructs from persisted fills).
        This is the cross-day restore path for the after-close daemon: without it
        the portfolio risk gates (EX-002 / EX-004 / EX-007) would run from an empty
        book every session. A fresh object is built (never mutating a shared one);
        seeded holdings are pre-existing state, so they are *not* logged as
        this-session fills, and each name's last price defaults to its cost basis
        so ``equity()`` can mark-to-cost with no explicit prices.
        """
        broker = cls(initial_cash=cash, config=config or StrategyConfig())
        for stock_id, (qty, cost_basis) in positions.items():
            broker._positions[stock_id] = Position(qty=int(qty), cost_basis=float(cost_basis))
            broker._last_price[stock_id] = float(cost_basis)
        return broker

    # ------------------------------------------------------------------ #
    # Read-only views (return copies so callers cannot mutate internals)
    # ------------------------------------------------------------------ #
    @property
    def positions(self) -> dict[str, Position]:
        """Snapshot copy of current holdings, keyed by stock id."""
        return {sid: Position(p.qty, p.cost_basis) for sid, p in self._positions.items()}

    @property
    def trade_log(self) -> list[Fill]:
        """Copy of all fills in execution order (``Fill`` is immutable)."""
        return list(self._trade_log)

    # ------------------------------------------------------------------ #
    # Cost model
    # ------------------------------------------------------------------ #
    def _fee(self, notional: float) -> float:
        return notional * self.config.fee_rate * self.config.fee_discount

    def _tax(self, notional: float, side: OrderSide) -> float:
        # Taiwan securities-transaction tax is charged on the sell side only.
        if side is OrderSide.SELL:
            return notional * self.config.tax_stock_rate
        return 0.0

    # ------------------------------------------------------------------ #
    # Order entry
    # ------------------------------------------------------------------ #
    def submit_order(
        self,
        stock_id: str,
        side: OrderSide | str,
        qty: int,
        price: float,
    ) -> Fill:
        """Match an order fully at ``price`` and update the book.

        Returns the resulting :class:`Fill`. Raises ``ValueError`` on invalid
        input or insufficient cash, and :class:`InsufficientPositionError` on an
        oversell. On any rejection the book is left unchanged (nothing logged).
        """
        side = OrderSide.coerce(side)
        if qty <= 0:
            raise ValueError(f"qty must be > 0, got {qty!r}")
        if price <= 0:
            raise ValueError(f"price must be > 0, got {price!r}")

        notional = qty * price
        fee = self._fee(notional)
        tax = self._tax(notional, side)

        if side is OrderSide.BUY:
            self._apply_buy(stock_id, qty, price, notional, fee)
        else:
            self._apply_sell(stock_id, qty, notional, fee, tax)

        self._last_price[stock_id] = float(price)
        fill = Fill(
            stock_id=stock_id, side=side, qty=qty, price=float(price), fee=fee, tax=tax
        )
        self._trade_log.append(fill)
        return fill

    def _apply_buy(
        self, stock_id: str, qty: int, price: float, notional: float, fee: float
    ) -> None:
        total_cost = notional + fee
        if total_cost > self.cash:
            raise ValueError(
                f"insufficient cash: need {total_cost:.2f}, have {self.cash:.2f}"
            )
        self.cash -= total_cost
        existing = self._positions.get(stock_id)
        if existing is None:
            self._positions[stock_id] = Position(qty=qty, cost_basis=float(price))
        else:
            new_qty = existing.qty + qty
            # Weighted-average cost basis on price only (fees excluded so the
            # basis stays a clean per-share price for P&L / heat reporting).
            new_basis = (existing.cost_basis * existing.qty + price * qty) / new_qty
            existing.qty = new_qty
            existing.cost_basis = new_basis

    def _apply_sell(
        self, stock_id: str, qty: int, notional: float, fee: float, tax: float
    ) -> None:
        existing = self._positions.get(stock_id)
        held = existing.qty if existing is not None else 0
        if qty > held:
            raise InsufficientPositionError(
                f"cannot sell {qty} of {stock_id!r}: only {held} held (no shorting)"
            )
        # `existing` is non-None here because held >= qty > 0.
        assert existing is not None
        self.cash += notional - fee - tax
        remaining = existing.qty - qty
        if remaining == 0:
            del self._positions[stock_id]
        else:
            existing.qty = remaining  # cost_basis unchanged on a partial sell

    # ------------------------------------------------------------------ #
    # Valuation
    # ------------------------------------------------------------------ #
    def _mark(self, stock_id: str, marks: Mapping[str, float] | None) -> float:
        """Resolve the mark price: explicit mark first, else last fill price."""
        if marks is not None and stock_id in marks:
            return float(marks[stock_id])
        return self._last_price[stock_id]

    def market_value(self, marks: Mapping[str, float] | None = None) -> float:
        """Mark-to-market value of all holdings."""
        return sum(
            pos.qty * self._mark(sid, marks) for sid, pos in self._positions.items()
        )

    def equity(self, marks: Mapping[str, float] | None = None) -> float:
        """Total account value = cash + mark-to-market holdings.

        ``marks`` maps stock id → latest price. Symbols absent from ``marks``
        fall back to their most recent fill price.
        """
        return self.cash + self.market_value(marks)

    # ------------------------------------------------------------------ #
    # Monitoring / risk
    # ------------------------------------------------------------------ #
    def portfolio_snapshot(
        self,
        marks: Mapping[str, float] | None = None,
        stop_prices: Mapping[str, float] | None = None,
    ) -> dict[str, Any]:
        """Serializable portfolio state for the monitor / risk gate.

        Returns ``{positions, cash, equity, heat}`` where ``heat`` follows the
        EX-004 formula (dev_docs/24 §EX-004)::

            Heat = Σ_i qty_i · |cost_basis_i − stop_i| / equity

        ``stop_prices`` is injected because stop levels are strategy-specific;
        absent a stop for a symbol its heat contribution is 0, keeping this
        broker strategy-agnostic.
        """
        eq = self.equity(marks)
        positions = {
            sid: {"qty": pos.qty, "cost_basis": pos.cost_basis}
            for sid, pos in self._positions.items()
        }
        heat = self._compute_heat(eq, stop_prices)
        return {
            "positions": positions,
            "cash": self.cash,
            "equity": eq,
            "heat": heat,
        }

    def _compute_heat(
        self, equity: float, stop_prices: Mapping[str, float] | None
    ) -> float:
        if stop_prices is None or equity <= 0:
            return 0.0
        total_risk = 0.0
        for sid, pos in self._positions.items():
            stop = stop_prices.get(sid)
            if stop is None:
                continue
            total_risk += pos.qty * abs(pos.cost_basis - float(stop))
        return total_risk / equity


__all__ = [
    "Fill",
    "InsufficientPositionError",
    "OrderSide",
    "PaperBroker",
    "Position",
]
