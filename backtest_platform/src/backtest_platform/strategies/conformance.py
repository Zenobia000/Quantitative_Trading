"""Strategy conformance gate — proves any registered runner satisfies the contract.

Used by:
- CI: parametrized pytest over list_strategies() (tests/strategies/test_conformance.py)
- CLI: ``validate-strategy <name>`` (research/cli.py, T6)
- Sub-project ②: load-time gate before dynamic module registration
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.strategies.protocol import Loader, get_strategy, get_strategy_gate

# Universal edge keys every strategy must return — aligns with gate_state.py
# DEFAULT_GATE + MOMENTUM_GATE common keys. Health keys are family-specific (excluded).
REQUIRED_METRIC_KEYS: frozenset[str] = frozenset(
    {"cagr", "sharpe", "slippage_sharpe", "maxdd", "trades", "bars"}
)

# Canonical merged-parquet columns (data contract doc 21)
_CANONICAL_COLS = [
    "stock_id", "trade_date",
    "open", "high", "low", "close", "volume", "adj_factor",
    "foreign_buy", "trust_buy", "dealer_buy",
    "top_broker_buy", "key_broker_buy", "gov_broker_buy",
    "geo_broker_buy", "day_trade_volume", "margin_offset_volume",
]


@dataclass(frozen=True)
class ConformanceReport:
    name: str
    ok: bool
    errors: list[str] = field(default_factory=list)


def synthetic_loader(n_bars: int = 400, seed: int = 0) -> Loader:
    """Return a Loader generating a synthetic merged DataFrame per stock.

    Prices follow a geometric random walk; institutional/chip columns are
    random integers — sufficient for contract checks, not signal quality.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n_bars, freq="B")
    base = 100.0

    def _loader(sid: str) -> pd.DataFrame:
        log_ret = rng.normal(0, 0.01, n_bars)
        close = base * np.exp(np.cumsum(log_ret))
        data: dict = {
            "stock_id": sid,
            "trade_date": dates,
            "open":  close * rng.uniform(0.98, 1.00, n_bars),
            "high":  close * rng.uniform(1.00, 1.02, n_bars),
            "low":   close * rng.uniform(0.97, 0.99, n_bars),
            "close": close,
            "volume": rng.integers(1_000_000, 10_000_000, n_bars),
            "adj_factor": np.ones(n_bars),
            "foreign_buy":  rng.integers(-500_000, 500_000, n_bars),
            "trust_buy":    rng.integers(-200_000, 200_000, n_bars),
            "dealer_buy":   rng.integers(-100_000, 100_000, n_bars),
            "top_broker_buy":    rng.integers(0, 100_000, n_bars),
            "key_broker_buy":    rng.integers(0, 50_000, n_bars),
            "gov_broker_buy":    rng.integers(0, 30_000, n_bars),
            "geo_broker_buy":    rng.integers(0, 20_000, n_bars),
            "day_trade_volume":  rng.integers(0, 500_000, n_bars),
            "margin_offset_volume": rng.integers(0, 200_000, n_bars),
        }
        return pd.DataFrame(data)

    return _loader


def check_strategy(
    name: str,
    *,
    n_symbols: int = 6,
    n_bars: int = 400,
) -> ConformanceReport:
    """Run ``name`` over synthetic data and verify the contract.

    Checks:
    1. Strategy resolves in the registry.
    2. config_model attribute exists and builds a default config.
    3. runner.run() completes without exception.
    4. Return is a StrategyRun with metrics ⊇ REQUIRED_METRIC_KEYS,
       returns is pd.Series, trades is list.
    5. The strategy declares a validation gate whose every criterion key ⊆ the
       metrics it actually produces — otherwise the gate references a metric the
       strategy never emits and every run is judged INCOMPLETE (審查缺陷 #8).
    """
    errors: list[str] = []

    # 1. Resolve
    try:
        runner = get_strategy(name)
    except ValueError as exc:
        return ConformanceReport(name=name, ok=False, errors=[str(exc)])

    # 2. Build default config
    if not hasattr(runner, "config_model"):
        errors.append("runner missing config_model attribute")
        return ConformanceReport(name=name, ok=False, errors=errors)
    try:
        cfg = runner.config_model()
    except Exception as exc:
        errors.append(f"config_model() raised: {exc}")
        return ConformanceReport(name=name, ok=False, errors=errors)

    # 3. Run on synthetic data
    symbols = [f"SYN{i:04d}" for i in range(n_symbols)]
    loader = synthetic_loader(n_bars=n_bars)
    start = date(2019, 1, 1)
    end   = date(2020, 12, 31)
    try:
        result = runner.run(symbols, start, end, cfg, loader)
    except Exception as exc:
        errors.append(f"runner.run() raised: {exc!r}")
        return ConformanceReport(name=name, ok=False, errors=errors)

    # 4. Validate output
    produced_keys: frozenset[str] = frozenset()
    if not isinstance(result.metrics, dict):
        errors.append("StrategyRun.metrics is not a dict")
    else:
        produced_keys = frozenset(result.metrics.keys())
        missing = REQUIRED_METRIC_KEYS - produced_keys
        if missing:
            errors.append(f"metrics missing required keys: {sorted(missing)}")

    if not isinstance(result.returns, pd.Series):
        errors.append("StrategyRun.returns is not a pd.Series")

    if not isinstance(result.trades, list):
        errors.append("StrategyRun.trades is not a list")

    # 5. Gate declared + every gate key ⊆ produced metrics
    try:
        gate = get_strategy_gate(name)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        gate_keys = {c.key for c in gate}
        unbacked = gate_keys - produced_keys
        if unbacked:
            errors.append(
                f"gate references metrics the strategy never produces: {sorted(unbacked)}"
            )

    return ConformanceReport(name=name, ok=len(errors) == 0, errors=errors)
