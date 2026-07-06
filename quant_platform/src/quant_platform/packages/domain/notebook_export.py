"""Open-in-notebook export — build a ``.ipynb`` dict from a run record (pure).

Turns a runs-ledger record into a minimal, self-contained Jupyter notebook the
operator opens in the repo venv (``uv run jupyter lab``) to poke at a run
*directly* — importing ``quant_platform`` and reading the JSONL ledger + series
sidecar, NOT round-tripping through the REST API. The notebook is prefilled with:

  1. a markdown header (run identity + window + gate verdict),
  2. a load cell (record from ``runs_store`` + equity/trades from
     ``run_series_store``, repo-relative paths),
  3. a quick-look plot cell (equity + drawdown, matplotlib — kept minimal),
  4. a blank "your analysis" cell.

Pure: no IO, no nbformat dependency — it emits the nbformat 4.5 JSON shape
directly so the router just serializes it as an attachment. ``build_notebook``
takes only the record; the load cell re-reads the stores at *notebook* run time so
the export stays a thin template, not a data dump.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: nbformat version this template targets (4.5 → cells carry stable ``id``s).
NBFORMAT = 4
NBFORMAT_MINOR = 5


def _lines(text: str) -> list[str]:
    """Split a cell body into nbformat ``source`` lines (each keeps its newline
    except the last), matching how Jupyter serializes multi-line cells."""
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


def _markdown(cell_id: str, text: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "id": cell_id, "metadata": {}, "source": _lines(text)}


def _code(cell_id: str, text: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "id": cell_id,
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": _lines(text),
    }


def _run_window(record: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Extract ``(is_start, is_end)`` handling both record shapes: the harness
    ``window: [start, end]`` and the flat ``is_start`` / ``is_end`` projection."""
    window = record.get("window")
    if isinstance(window, (list, tuple)) and len(window) == 2:
        return (window[0], window[1])
    return (record.get("is_start"), record.get("is_end"))


def build_notebook(record: Mapping[str, Any]) -> dict[str, Any]:
    """Build the nbformat 4.5 notebook dict for one run record.

    ``record`` is a runs-ledger record (identity + metadata + gate verdict). The
    returned dict is JSON-serializable as a ``.ipynb`` and validates against the
    nbformat 4.x schema (top-level ``nbformat`` / ``nbformat_minor`` / ``metadata`` /
    ``cells``; every cell has ``cell_type`` / ``id`` / ``metadata`` / ``source`` and
    code cells add ``outputs`` / ``execution_count``).
    """
    run_id = str(record.get("run_id", ""))
    strategy = record.get("strategy") or "?"
    hypothesis = record.get("hypothesis") or "—"
    gate_status = record.get("gate_status") or "?"
    start, end = _run_window(record)

    header = _markdown(
        "md-title",
        f"# Run Report — `{run_id}`\n"
        f"\n"
        f"- **策略 (strategy)**: `{strategy}`\n"
        f"- **假設 (hypothesis)**: {hypothesis}\n"
        f"- **IS 窗口 (window)**: `{start}` → `{end}`\n"
        f"- **審判庭判決 (gate_status)**: **{gate_status}**\n"
        f"\n"
        f"此 notebook 在 repo venv 直接讀 ledger + series sidecar（不繞 REST）。"
        f"先 `uv run jupyter lab`，再逐格執行。",
    )

    load = _code(
        "code-load",
        "# 直接 import 平台，載入這個 run 的 record 與 equity/trades sidecar\n"
        "from quant_platform.packages.adapters.runs_store import read_runs\n"
        "from quant_platform.packages.adapters import run_series_store\n"
        "\n"
        f'RUN_ID = "{run_id}"\n'
        "\n"
        "record = next(\n"
        '    (r for r in read_runs() if str(r.get("run_id")) == RUN_ID), None\n'
        ")\n"
        'assert record is not None, f"run {RUN_ID} 不在 ledger (reports/runs.jsonl)"\n'
        "\n"
        "series = run_series_store.read_series(RUN_ID) or {}\n"
        'equity = series.get("equity", [])\n'
        'drawdown = series.get("drawdown", [])\n'
        'trades = series.get("trades", [])\n'
        'print("gate:", record.get("gate_status"), "| bars:", len(equity), "| trades:", len(trades))\n'
        'record.get("metrics")',
    )

    plot = _code(
        "code-plot",
        "# 快速圖：equity 曲線 + drawdown（matplotlib，保持極簡）\n"
        "import matplotlib.pyplot as plt\n"
        "\n"
        "fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)\n"
        'ax1.plot(equity, color="steelblue")\n'
        'ax1.set_title(f"Equity — {RUN_ID}")\n'
        "ax2.fill_between(range(len(drawdown)), drawdown, 0, color=\"crimson\", alpha=0.4)\n"
        'ax2.set_title("Drawdown")\n'
        "plt.tight_layout()\n"
        "plt.show()",
    )

    analysis = _code(
        "code-analysis",
        "# 你的分析 (your analysis)\n",
    )

    return {
        "cells": [header, load, plot, analysis],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": NBFORMAT,
        "nbformat_minor": NBFORMAT_MINOR,
    }
