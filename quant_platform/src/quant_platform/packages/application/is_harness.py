"""IS harness — `run_is(RunConfig) → metrics`, the productized form of the
one-off scripts/v3_double_window_is.py read.

Reuses the same offline close-to-close portfolio sim. `run_is` takes an injectable
`loader` so logic is unit-testable without the parquet cache (the default loader
reads data/parquet). `run_and_judge` wires it to the gate_state審判庭 so a run
yields an objective PASS/FAIL/INCOMPLETE in one call — turning '手寫 script 半天'
into 'run_is(cfg) → gate 逐條綠紅'.

NOTE: the sim is a lightweight close-to-close approximation (not zipline). The
v3 verdict was calibrated against the real engine (gate review §6); use the
relative read + health checks, not absolute CAGR.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

import pandas as pd

from quant_platform.services.research_validation import runners as _runners  # noqa: F401 — registers all strategies
from quant_platform.packages.domain.run_config import RunConfig
from quant_platform.services.research_validation.strategies.four_layer_resonance import sim as _fl_sim
from quant_platform.services.research_validation.strategies.protocol import get_strategy, get_strategy_gate
from quant_platform.services.research_validation.validation.gate_state import GateResult, evaluate_gate


def _utc_now() -> datetime:
    """Default clock: timezone-aware UTC now. Injectable so records are testable
    (a naive ``datetime.now()`` produced ambiguous, non-comparable timestamps)."""
    return datetime.now(timezone.utc)

# Back-compat re-exports (ADR-027): the four-layer sim helpers used to be defined
# in this module; ``research.sweep`` still imports these private names from here.
# Alias via assignment (not `import ... as`) so the linter cannot strip them as
# "unused re-exports".
TRADING_DAYS = _fl_sim.TRADING_DAYS
_SLIP_STRESS = _fl_sim._SLIP_STRESS
_signaled_window = _fl_sim.signaled_window
_daily_returns = _fl_sim.daily_returns
_trades = _fl_sim.trades
_sharpe = _fl_sim.sharpe
_metrics = _fl_sim.metrics

PARQUET_DIR = "data/parquet"
_FLOW_COLS = [
    "foreign_buy", "trust_buy", "dealer_buy", "top_broker_buy", "key_broker_buy",
    "gov_broker_buy", "geo_broker_buy", "day_trade_volume", "margin_offset_volume",
]


def load_merged_parquet(sid: str, parquet_dir: str = PARQUET_DIR) -> pd.DataFrame:
    """Default loader: read + merge the 3 parquet for one stock (ETLBundle.merged)."""
    db = pd.read_parquet(f"{parquet_dir}/daily_bars__{sid}.parquet")
    inst = pd.read_parquet(f"{parquet_dir}/institutional__{sid}.parquet")
    chips = pd.read_parquet(f"{parquet_dir}/broker_chips__{sid}.parquet")
    m = db.merge(inst, on=["stock_id", "trade_date"], how="left").merge(
        chips, on=["stock_id", "trade_date"], how="left"
    )
    for c in _FLOW_COLS:
        if c in m.columns:
            m[c] = m[c].fillna(0).astype("int64")
    return m


def _run_is_core(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> tuple[dict, pd.Series, list[dict]]:
    """The IS portfolio sim. Returns ``(metrics, daily-returns series, trades)``.

    Dispatches to the registered strategy by name, validates params through
    config_model(**params), and delegates to runner.run(). Unknown strategy name
    raises ValueError (→ API 400); invalid params raise ValidationError (→ API 422).
    """
    runner = get_strategy(cfg.strategy)           # ValueError on unknown name
    sconf  = runner.config_model(**cfg.params)    # ValidationError on bad params
    run    = runner.run(list(cfg.stocks), cfg.is_start, cfg.is_end, sconf, loader)
    return run.metrics, run.returns, run.trades


def run_is(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> dict:
    """Run the IS portfolio sim for a RunConfig. Returns a metrics dict."""
    return _run_is_core(cfg, loader)[0]


def run_is_returns(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> pd.Series:
    """Portfolio daily-returns series for a RunConfig (for tear sheets / plots).

    The same series the IS metrics are derived from; an empty Series when the
    window yields no tradable data. Pair with
    ``validation.tearsheet.write_tearsheet``.
    """
    return _run_is_core(cfg, loader)[1]


def run_is_trades(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
) -> list[dict]:
    """Per-trade list ({ret, hold, entry_structure}) for a RunConfig.

    The same trades the E (trade-quality) metrics are derived from; an empty
    list when the window yields no closed trades.
    """
    return _run_is_core(cfg, loader)[2]


def run_and_judge(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
    gate=None,
    clock: Callable[[], datetime] = _utc_now,
) -> dict:
    """run_is → evaluate_gate → a complete, ledger-ready run record."""
    return run_and_judge_with_returns(cfg, loader, gate, clock)[0]


def run_and_judge_with_returns(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
    gate=None,
    clock: Callable[[], datetime] = _utc_now,
) -> tuple[dict, pd.Series]:
    """One sim pass → ``(ledger-ready run record, portfolio daily returns)``.

    The record is identical to ``run_and_judge``'s; returning the returns series
    alongside it lets a caller that wants both (e.g. ``run-is --tearsheet``) avoid
    running the sim twice.

    When ``gate`` is omitted the审判庭 criteria are dispatched from the run's own
    strategy (``get_strategy_gate``) — NOT a shared four-layer default — so a panel
    strategy is judged by its own gate and reaches a real verdict (審查缺陷 #8).
    An explicit ``gate`` always wins (back-compat).
    """
    metrics, returns, _trades_list = _run_is_core(cfg, loader)
    resolved_gate = gate if gate is not None else get_strategy_gate(cfg.strategy)
    result: GateResult = evaluate_gate(metrics, resolved_gate)
    record = {
        "run_id": cfg.run_id,
        "created_at": clock().isoformat(timespec="seconds"),
        "hypothesis": cfg.hypothesis,
        "strategy": cfg.strategy,
        "params": cfg.params,
        "engine": cfg.engine,
        "stocks": list(cfg.stocks),
        "window": [cfg.is_start.isoformat(), cfg.is_end.isoformat()],
        "metrics": metrics,
        "gate_status": result.status.value,
        "gate_summary": result.summary(),
    }
    return record, returns


def equity_drawdown(returns: pd.Series) -> tuple[list[float], list[float]]:
    """Cumulative equity + running drawdown from a daily-returns series.

    ``equity[i] = prod(1 + returns[:i+1])`` (starts near 1.0); ``drawdown[i]``
    is the signed fraction below the running peak (<= 0). Empty in → empty out.
    """
    if returns is None or len(returns) == 0:
        return [], []
    eq = (1.0 + returns.astype(float)).cumprod()
    dd = eq / eq.cummax() - 1.0
    return [float(x) for x in eq], [float(x) for x in dd]


def run_and_judge_persist(
    cfg: RunConfig,
    loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
    gate=None,
    series_dir=None,
    clock: Callable[[], datetime] = _utc_now,
) -> dict:
    """run_and_judge + persist the per-run equity/drawdown/trades sidecar.

    The API run-executor (``deps.get_run_executor``) so a triggered run also
    populates ``run_series_store`` for ``GET /runs/{id}/equity`` · ``/trades``
    without a second sim pass. Returns the ledger record (same shape as
    ``run_and_judge``); the heavy series go to the sidecar, not the ledger line.

    Like ``run_and_judge``, an omitted ``gate`` is dispatched from the run's own
    strategy so an API/GUI-triggered panel run is no longer stuck at INCOMPLETE
    (審查缺陷 #8). An explicit ``gate`` still wins.
    """
    from quant_platform.packages.adapters import run_series_store

    metrics, returns, trades = _run_is_core(cfg, loader)
    resolved_gate = gate if gate is not None else get_strategy_gate(cfg.strategy)
    result: GateResult = evaluate_gate(metrics, resolved_gate)
    record = {
        "run_id": cfg.run_id,
        "created_at": clock().isoformat(timespec="seconds"),
        "hypothesis": cfg.hypothesis,
        "strategy": cfg.strategy,
        "params": cfg.params,
        "engine": cfg.engine,
        "stocks": list(cfg.stocks),
        "window": [cfg.is_start.isoformat(), cfg.is_end.isoformat()],
        "metrics": metrics,
        "gate_status": result.status.value,
        "gate_summary": result.summary(),
    }
    equity, drawdown = equity_drawdown(returns)
    kwargs = {} if series_dir is None else {"series_dir": series_dir}
    run_series_store.write_series(cfg.run_id, equity, drawdown, trades, **kwargs)
    return record
