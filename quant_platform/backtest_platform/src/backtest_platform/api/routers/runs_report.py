"""``/runs/{id}/report`` (aggregate) + ``/runs/{id}/notebook`` (Open-in-notebook).

The Run-Report page needs many things at once — the审判庭 verdict, the sealed-window
boundaries, a month×year return heat-map, a drawdown-event table, and the cost-
sensitivity Sharpe pair. Rather than make the frontend fan out to a dozen calls,
``GET /runs/{id}/report`` assembles them in one uniform envelope. Every field it
cannot source honestly comes back ``null`` (the #169 in-flight-null convention — a
missing verdict input is never fabricated).

Data sources, per block:
  * **verdict**   — the record's ``gate_status`` / ``gate_summary`` (#164) + the
    strategy's declared gate criteria (``get_strategy_gate``) + the latest folded
    validation state (``validation_store``) + the觀察艙 berth if the strategy is
    enrolled (``watch_registry`` — the only *persisted* truth-gate evidence; the
    truth-gate workflow itself computes on demand and is not persisted). The DSR
    band position is derived from the berth's enrollment DSR (``report.dsr_band``).
  * **segments**  — the run's own window + the strategy's ``TRUTH_GATE`` sealed
    boundary (``oos_start`` / ``is_end``) when its ``research_config`` declares one.
  * **monthly_returns / drawdown_events** — computed from the series sidecar via the
    pure ``validation.report`` functions; ``null`` (+ a note) when the sidecar is
    absent. Dates are reconstructed as business days across the run window (the v1
    sidecar persists no date index) — disclosed via ``monthly_returns.basis``.
  * **cost_sensitivity** — the ``sharpe`` vs ``slippage_sharpe`` pair the panel
    runner already emits into ``metrics``.

``GET /runs/{id}/notebook`` returns a prefilled ``.ipynb`` attachment (the template
lives in ``research.notebook_export``); the route stays thin.

Path depth (/runs/{id}/report) is more specific than runs.py's /{run_id}, so route
resolution is unambiguous regardless of include order.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from backtest_platform.api.deps import (
    get_runs_path,
    get_validation_events_path,
    get_watch_registry_path,
)
from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.api.response_models import RunReportData
from backtest_platform.governance.watch_registry import status as watch_status
from backtest_platform.research import notebook_export, run_series_store, validation_store
from backtest_platform.research.runs_store import read_runs
from backtest_platform.validation.report import drawdown_events, dsr_band, monthly_returns_matrix

router = APIRouter(prefix="/runs", tags=["runs"])

_NO_SERIES_NOTE = (
    "series sidecar not persisted for this run (predates the sidecar, or the window "
    "yielded no tradable data) — monthly matrix / drawdown events unavailable"
)
_NO_WINDOW_NOTE = (
    "run record carries no IS window — cannot reconstruct a date index for the "
    "monthly matrix"
)
#: Disclosure: the v1 series sidecar persists no date index, so the month buckets
#: key off a business-day index reconstructed from the run's is_start (approximate).
_MONTHLY_BASIS = "reconstructed_business_days_from_is_start"


def _find_run(run_id: str, runs_path: Path) -> dict[str, Any] | None:
    """Latest ledger record for ``run_id`` (last append wins), or ``None``."""
    match: dict[str, Any] | None = None
    for record in read_runs(runs_path):
        if str(record.get("run_id")) == run_id:
            match = record
    return match


def _run_window(record: dict[str, Any]) -> tuple[str | None, str | None]:
    """``(is_start, is_end)`` handling both the harness ``window: [s, e]`` shape and
    the flat ``is_start`` / ``is_end`` projection."""
    window = record.get("window")
    if isinstance(window, (list, tuple)) and len(window) == 2:
        return (window[0], window[1])
    return (record.get("is_start"), record.get("is_end"))


def _gate_criteria(strategy: str | None) -> list[dict[str, Any]] | None:
    """The strategy's declared gate criteria, or ``None`` if the strategy is unknown
    or declares no gate (honest null — never another strategy's ruler)."""
    if not strategy:
        return None
    try:
        from backtest_platform.research import runners as _runners  # noqa: F401 — register
        from backtest_platform.strategies.protocol import get_strategy_gate

        gate = get_strategy_gate(strategy)
    except ValueError:
        return None
    return [
        {"key": c.key, "op": c.op, "threshold": c.threshold, "kind": c.kind, "label": c.label}
        for c in gate
    ]


def _watch_berth(strategy: str | None, reg_path: Path) -> dict[str, Any] | None:
    """The觀察艙 berth for ``strategy`` (the persisted truth-gate/DSR evidence), or
    ``None`` if the strategy never enrolled. Band position is derived from the
    enrollment DSR; other truth-gate outputs (WFA/holdout) are computed on demand and
    not persisted, so they are honestly omitted rather than invented."""
    if not strategy:
        return None
    try:
        st = watch_status(strategy, path=reg_path)
    except Exception:
        return None
    if st is None:
        return None
    return {
        "verdict_dsr": st.verdict_dsr,
        "band": dsr_band(st.verdict_dsr),
        "state": st.state,
        "enrolled_on": st.enrolled_on.isoformat(),
        "expiry_date": st.expiry_date.isoformat(),
        "days_remaining": st.days_remaining,
        "observed_trading_days": st.observed_trading_days,
        "source": "watch_registry",
    }


def _build_verdict(
    record: dict[str, Any], strategy: str | None, run_id: str, val_path: Path, reg_path: Path
) -> dict[str, Any]:
    """Assemble the verdict block from the record + the three persisted stores."""
    return {
        "gate_status": record.get("gate_status"),
        "gate_summary": record.get("gate_summary"),
        "criteria": _gate_criteria(strategy),
        "validation": validation_store.current(run_id, path=val_path),
        "truth_gate": _watch_berth(strategy, reg_path),
    }


def _truth_gate_window(strategy: str | None) -> dict[str, Any] | None:
    """The strategy's ``TRUTH_GATE`` sealed boundary (is_start / oos_start / is_end)
    for the front-end's sealed-window line, or ``None`` when it declares none."""
    if not strategy:
        return None
    try:
        from backtest_platform.research.workflows.loader import get_truth_gate_config

        tg = get_truth_gate_config(strategy)
    except Exception:
        return None
    return {
        "is_start": tg.is_start.isoformat(),
        "oos_start": tg.oos_start.isoformat(),
        "is_end": tg.is_end.isoformat(),
    }


def _reconstruct_dates(is_start: str, n: int) -> list[str]:
    """A length-``n`` business-day ISO index anchored at ``is_start`` (the v1 sidecar
    persists no dates — see module docstring / ``_MONTHLY_BASIS``)."""
    idx = pd.date_range(start=is_start, periods=n, freq="B")
    return [d.date().isoformat() for d in idx]


def _returns_from_equity(equity: list[float]) -> list[float]:
    """Per-bar simple returns from an equity curve (``eq[i]/eq[i-1] - 1``)."""
    out: list[float] = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        out.append(equity[i] / prev - 1.0 if prev else 0.0)
    return out


def _series_blocks(
    record: dict[str, Any], run_id: str
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]] | None]:
    """Compute ``(monthly_returns, monthly_note, drawdown_events)`` from the sidecar.

    Sidecar absent → both null with a note. Window absent → monthly null with a note,
    but drawdown events still compute (by bar index, dateless).
    """
    series = run_series_store.read_series(run_id)
    equity = list(series.get("equity", [])) if series else []
    if not equity:
        return None, _NO_SERIES_NOTE, None

    is_start, _ = _run_window(record)
    if is_start is None:
        # Dateless: drawdown events still work (bar indices); monthly needs a calendar.
        return None, _NO_WINDOW_NOTE, drawdown_events(equity, dates=None, top_n=5)

    dates = _reconstruct_dates(is_start, len(equity))
    returns = _returns_from_equity(equity)
    monthly = monthly_returns_matrix(pd.Series(returns, index=pd.to_datetime(dates[1:])))
    monthly["basis"] = _MONTHLY_BASIS
    return monthly, None, drawdown_events(equity, dates=dates, top_n=5)


@router.get("/{run_id}/report", response_model=Envelope[RunReportData])
def run_report(
    run_id: str,
    runs_path: Path = Depends(get_runs_path),
    val_path: Path = Depends(get_validation_events_path),
    reg_path: Path = Depends(get_watch_registry_path),
) -> Envelope:
    """One-shot aggregate for the Run-Report page (verdict / segments / monthly /
    drawdown events / cost sensitivity). 404 if the run is unknown; every
    unsourceable field is ``null`` (never fabricated)."""
    record = _find_run(run_id, runs_path)
    if record is None:
        raise HTTPException(status_code=404, detail={"resource": "run", "id": run_id})

    strategy = record.get("strategy")
    metrics = record.get("metrics") or {}
    is_start, is_end = _run_window(record)
    monthly, monthly_note, dd_events = _series_blocks(record, run_id)

    return ok(
        {
            "run_id": run_id,
            "verdict": _build_verdict(record, strategy, run_id, val_path, reg_path),
            "segments": {
                "run_window": {"is_start": is_start, "is_end": is_end},
                "truth_gate_window": _truth_gate_window(strategy),
            },
            "monthly_returns": monthly,
            "monthly_returns_note": monthly_note,
            "drawdown_events": dd_events,
            "cost_sensitivity": {
                "sharpe": metrics.get("sharpe"),
                "slippage_sharpe": metrics.get("slippage_sharpe"),
            },
        }
    )


@router.get("/{run_id}/notebook")
def run_notebook(run_id: str, runs_path: Path = Depends(get_runs_path)) -> JSONResponse:
    """Download a prefilled ``.ipynb`` for one run (Open-in-notebook). 404 if unknown.

    Returns the notebook JSON with a ``Content-Disposition: attachment`` header so a
    browser saves ``run_<id>.ipynb``; the template loads the run from the repo stores
    (not the REST API) when the operator runs it in the repo venv Jupyter.
    """
    record = _find_run(run_id, runs_path)
    if record is None:
        raise HTTPException(status_code=404, detail={"resource": "run", "id": run_id})
    notebook = notebook_export.build_notebook(record)
    return JSONResponse(
        content=notebook,
        headers={"Content-Disposition": f'attachment; filename="run_{run_id}.ipynb"'},
    )
