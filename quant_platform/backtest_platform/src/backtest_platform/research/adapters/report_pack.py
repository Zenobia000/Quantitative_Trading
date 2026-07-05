"""Report-pack writer (rebuild Goal 3) — the Report Viewer's on-disk source.

Writes one evaluation's report pack under ``reports/research_runs/<run_id>/`` and a
``manifest.json`` matching ``dev_docs/contracts/report_pack_manifest.example.json``.
The four Goal-3-required files are always produced: ``summary.json`` (verdict +
recommendation + headline, superset-compatible with ``GET /runs/{id}/report``),
``metrics.json`` (flat metric dict), ``scorecards.json`` (the five scorecards) and
``report.md`` (the human narrative entrypoint). ``gate_results.json`` is written
when the profile ran severity-graded gates.

Honesty (spec §8 #6): the v1 series sidecar is JSON, not parquet, so the manifest
lists ``series.json`` as the real ``available`` series file and marks the contract's
``equity.parquet`` / ``trades.parquet`` (and ``simulations.json`` / ``figures/*``)
``not_available`` with a reason — never a placeholder claimed as present.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_PACK_ROOT = Path("reports") / "research_runs"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    path.write_text(text, encoding="utf-8")
    return _sha256(text)


def _render_markdown(result: dict[str, Any]) -> str:
    """Human-readable narrative report (the operator entrypoint)."""
    v = result["verdict"]
    rec = v.get("recommendation", {})
    h = result.get("headline_metrics", {})
    lines: list[str] = [
        f"# Evaluation — {result['strategy']} · {result['profile']}",
        "",
        f"- **Evaluation id:** `{result['evaluation_id']}`",
        f"- **Run id (config hash):** `{result['run_id']}`",
        f"- **Created:** {result['created_at']}",
        f"- **Verdict:** {v.get('label')} (truth_verdict={v.get('truth_verdict')})",
        f"- **Recommendation:** {rec.get('action')} (confidence={rec.get('confidence')})",
        "",
        "## Headline metrics",
        "",
        "| Metric | Value |",
        "| :--- | ---: |",
    ]
    for key in ("cagr", "total_return", "sharpe", "sortino", "calmar", "max_drawdown",
                "volatility", "oos_holdout_sharpe", "slippage_sharpe", "dsr",
                "wfa_oos_positive_frac", "trades", "avg_holdings", "avg_turnover"):
        if key in h and h[key] is not None:
            lines.append(f"| {key} | {h[key]} |")
    lines += ["", "## Scorecards", "", "| Scorecard | Status |", "| :--- | :--- |"]
    for sc in result.get("scorecards", []):
        lines.append(f"| {sc['category']} | {sc['status']} |")
    reasons = rec.get("reasons", [])
    if reasons:
        lines += ["", "## Why", ""]
        lines += [f"- {r}" for r in reasons]
    gaps = result.get("data_gaps", [])
    if gaps:
        lines += ["", "## Data gaps (rule #6 — reported, not fabricated)", ""]
        lines += [f"- `{g['field']}` — {g['reason']}" for g in gaps]
    lines.append("")
    return "\n".join(lines)


def write_report_pack(
    result: dict[str, Any],
    series: dict[str, Any] | None = None,
    *,
    root: Path | str = DEFAULT_PACK_ROOT,
) -> dict[str, Any]:
    """Write the report pack for ``result`` and return its ReportPackManifest.

    ``series`` is ``{equity, drawdown, trades}`` (may be None / empty). Returns the
    manifest dict; ``manifest['root_dir']`` + ``result['report_pack_ref']`` point at
    the written ``manifest.json``.
    """
    run_id = result["run_id"]
    pack_dir = Path(root) / run_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []

    def _add(name: str, kind: str, media: str, payload: Any, description: str) -> None:
        sha = _write_json(pack_dir / name, payload)
        files.append({"name": name, "kind": kind, "path": name, "media_type": media,
                      "status": "available", "sha256": sha, "description": description})

    _add("summary.json", "summary", "application/json", {
        "run_id": run_id,
        "evaluation_id": result["evaluation_id"],
        "strategy": result["strategy"],
        "profile": result["profile"],
        "window": result.get("window"),
        "universe": result.get("universe"),
        "verdict": result["verdict"],
        "headline_metrics": result.get("headline_metrics", {}),
        "sizing": result.get("sizing"),
    }, "Headline verdict + recommendation + headline metrics. Superset-compatible with GET /runs/{id}/report verdict block.")

    _add("metrics.json", "metrics", "application/json", result.get("headline_metrics", {}),
         "Flat metric dict from validation.metrics + workflows.truth_gate.")

    _add("scorecards.json", "scorecards", "application/json", result.get("scorecards", []),
         "The five FinLab-style scorecards with per-metric pass/warn/fail/not_available.")

    checks = result.get("checks", [])
    if checks:
        _add("gate_results.json", "gate_results", "application/json",
             {"truth_verdict": result["verdict"].get("truth_verdict"), "checks": checks},
             "Severity-graded gate checks + TruthVerdict (validation.two_stage_gate).")
    else:
        files.append({"name": "gate_results.json", "kind": "gate_results", "path": "gate_results.json",
                      "media_type": "application/json", "status": "not_available",
                      "reason": "This profile ran no severity-graded gates (e.g. quick_triage single_run)."})

    md = _render_markdown(result)
    (pack_dir / "report.md").write_text(md, encoding="utf-8")
    files.append({"name": "report.md", "kind": "report_md", "path": "report.md",
                  "media_type": "text/markdown", "status": "available", "sha256": _sha256(md),
                  "description": "Human-readable narrative report (the operator entrypoint)."})

    equity = (series or {}).get("equity") or []
    if equity:
        _add("series.json", "series", "application/json",
             {"equity": equity, "drawdown": (series or {}).get("drawdown") or [], "trades": (series or {}).get("trades") or []},
             "Equity + drawdown + per-rebalance trade rows (v1 JSON sidecar, from research.run_series_store).")
    else:
        files.append({"name": "series.json", "kind": "series", "path": "series.json",
                      "media_type": "application/json", "status": "not_available",
                      "reason": "Run produced no equity series (empty / data-issue window)."})

    # Contract lists parquet series + simulations + figures; honestly not produced yet.
    files += [
        {"name": "equity.parquet", "kind": "series", "path": "equity.parquet",
         "media_type": "application/vnd.apache.parquet", "status": "not_available",
         "reason": "v1 series sidecar is JSON (series.json), not parquet; a parquet writer is a later add."},
        {"name": "trades.parquet", "kind": "series", "path": "trades.parquet",
         "media_type": "application/vnd.apache.parquet", "status": "not_available",
         "reason": "Panel trades carry no per-trade pnl/entry/exit columns (rule #6); parquet writer deferred."},
        {"name": "simulations.json", "kind": "simulations", "path": "simulations.json",
         "media_type": "application/json", "status": "not_available",
         "reason": "Interactive stop-loss/take-profit/cost/capacity sweeps are Goal 8."},
        {"name": "figures/equity.png", "kind": "figure", "path": "figures/equity.png",
         "media_type": "image/png", "status": "not_available",
         "reason": "Figure rendering deferred; JSON/series are the GUI source (client-side charts)."},
    ]

    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "evaluation_id": result["evaluation_id"],
        "strategy": result["strategy"],
        "profile": result["profile"],
        "profile_version": result.get("profile_version"),
        "report_pack": result.get("report_pack"),
        "created_at": result["created_at"],
        "root_dir": str(pack_dir).replace("\\", "/"),
        "human_entrypoint": "report.md",
        "gui_entrypoint": "summary.json",
        "files": files,
        "lineage": result.get("lineage", {}),
        "compat": {
            "runs_report_endpoint": "GET /runs/{run_id}/report",
            "relationship": "Superset of RunReportData; adds scorecards.json / metrics.json / "
                            "gate_results.json + a file-level manifest with sha256.",
        },
    }
    _write_json(pack_dir / "manifest.json", manifest)
    return manifest
