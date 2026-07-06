#!/usr/bin/env python3
"""Seed deterministic local demo data for the FastAPI/React operator console.

The seed is intentionally derived from ``packages/contracts/examples``. It gives a
fresh local TimescaleDB plus the JSONL ledgers enough real-shaped data to exercise
the happy path without inventing another fixture universe.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKTEST_ROOT = REPO_ROOT / "quant_platform"
SRC_ROOT = BACKTEST_ROOT / "src"
CONTRACT_EXAMPLES = REPO_ROOT / "packages" / "contracts" / "examples"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


RUN_IDS = {
    "inst_flow": "a1b9c3d4e5f6",
    "momentum": "b2c8d9e0f1a2",
    "four_layer_resonance": "c3d9e0f1a2b3",
    "reversal": "d4e0f1a2b3c4",
    "long_short": "e5f1a2b3c4d5",
}
TWT = timezone(timedelta(hours=8))


def _load_example(name: str) -> dict[str, Any]:
    return json.loads((CONTRACT_EXAMPLES / name).read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def _run_id_from_report_ref(ref: str | None, strategy: str) -> str:
    if ref:
        parts = Path(ref).parts
        if len(parts) >= 3:
            return parts[-2]
    return RUN_IDS.get(strategy, f"seed_{strategy}")[:12]


def _recommendation_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    rec = candidate.get("live_oos_recommendation")
    if rec == "eligible":
        return {
            "action": "eligible_for_live_oos",
            "confidence": "medium",
            "reasons": [candidate.get("next_action") or "Eligible for zero-capital live OOS."],
        }
    if rec == "blocked":
        return {
            "action": "blocked",
            "confidence": "high",
            "reasons": [candidate.get("next_action") or "Blocked by the latest evaluation."],
        }
    return {
        "action": "research_follow_up",
        "confidence": "medium",
        "reasons": [candidate.get("next_action") or "Run a deeper evaluation profile."],
    }


def _evaluation_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Build a compact EvaluationResult-compatible row for non-primary fixtures."""
    strategy = candidate["strategy"]
    run_id = _run_id_from_report_ref(candidate.get("report_pack_ref"), strategy)
    label = candidate.get("latest_label")
    truth = candidate.get("latest_truth_verdict")
    scorecards = [
        {"category": key, "status": status, "metrics": []}
        for key, status in (candidate.get("scorecard_summary") or {}).items()
    ]
    verdict = {
        "label": label,
        "truth_verdict": truth,
        "live_oos_recommendation": candidate.get("live_oos_recommendation"),
        "recommendation": _recommendation_from_candidate(candidate),
    }
    return {
        "schema_version": "1.0",
        "evaluation_id": candidate["latest_evaluation_id"],
        "run_id": run_id,
        "strategy": strategy,
        "profile": candidate.get("latest_profile") or "quick_triage",
        "profile_version": "1.0",
        "created_at": candidate["created_at"],
        "window": {
            "is_start": "2018-01-01",
            "oos_start": "2023-01-01",
            "is_end": "2024-12-31",
        },
        "universe": {
            "symbols_count": 3,
            "bundle_ref": "data/parquet_finlab_universe",
            "survivorship_clean": bool((candidate.get("headline") or {}).get("survivorship_clean")),
        },
        "verdict": verdict,
        "headline_metrics": candidate.get("headline") or {},
        "scorecards": scorecards,
        "checks": [],
        "sizing": {"position_size": 0.0, "reason": "Seeded demo row; not deployable capital."},
        "lineage": {
            "config_hash": run_id,
            "params": {},
            "engine": "sim",
            "bundle_ref": "data/parquet_finlab_universe",
            "n_trials": None,
            "git_sha": None,
        },
        "report_pack_ref": f"reports/research_runs/{run_id}/manifest.json",
        "data_gaps": [],
    }


def _series_for(run_id: str, *, points: int = 24, start: float = 10_000_000.0) -> dict[str, Any]:
    equity: list[float] = []
    peak = start
    drawdown: list[float] = []
    for i in range(points):
        value = start * (1 + 0.008 * i + 0.018 * ((i % 5) - 2) / 10)
        equity.append(round(value, 2))
        peak = max(peak, value)
        drawdown.append(round((value / peak) - 1, 6))
    trades = [
        {"at": "2026-07-03", "stock_id": "2330", "side": "Buy", "qty": 2000, "price": 998.0},
        {"at": "2026-07-03", "stock_id": "2317", "side": "Buy", "qty": 5000, "price": 214.5},
        {"at": "2026-07-03", "stock_id": "2454", "side": "Buy", "qty": 1000, "price": 1560.0},
    ]
    return {"run_id": run_id, "equity": equity, "drawdown": drawdown, "trades": trades}


def _seed_ledgers(reports_root: Path) -> dict[str, int]:
    from quant_platform.services.governance_release.live_oos_queue import DEFAULT_QUEUE_PATH
    from quant_platform.services.governance_release.promotion_store import DEFAULT_PROMOTION_PATH
    from quant_platform.services.governance_release.watch_registry import DEFAULT_WATCH_PATH
    from quant_platform.services.strategy_runtime.after_close import DEFAULT_MARKER_PATH
    from quant_platform.services.research_validation.evaluation.report_pack import write_report_pack
    from quant_platform.services.research_validation.evaluation.store import DEFAULT_EVALUATIONS_PATH
    from quant_platform.packages.adapters.run_series_store import write_series
    from quant_platform.packages.adapters.runs_store import DEFAULT_RUNS_PATH
    from quant_platform.packages.adapters.validation_store import DEFAULT_VALIDATION_PATH

    evaluation = _load_example("evaluation_result.example.json")
    candidate_payload = _load_example("candidate_pool.example.json")
    queue_payload = _load_example("live_oos_queue.example.json")

    main_eval = copy.deepcopy(evaluation)
    main_eval.setdefault("verdict", {})["live_oos_recommendation"] = "eligible"
    candidates = []
    decisions = []
    evaluations = [main_eval]
    for candidate in candidate_payload["data"]:
        snap = {k: v for k, v in candidate.items() if k != "decisions"}
        candidates.append(snap)
        decisions.extend(candidate.get("decisions") or [])
        if candidate["latest_evaluation_id"] != main_eval["evaluation_id"]:
            evaluations.append(_evaluation_from_candidate(candidate))

    _write_jsonl(reports_root / DEFAULT_EVALUATIONS_PATH.name, evaluations)
    _write_jsonl(reports_root / "candidates.jsonl", candidates)
    _write_jsonl(reports_root / "candidate_decisions.jsonl", decisions)
    _write_jsonl(reports_root / DEFAULT_QUEUE_PATH.name, queue_payload["data"])

    run_rows = [_run_row(ev, candidates) for ev in evaluations]
    _write_jsonl(reports_root / DEFAULT_RUNS_PATH.name, run_rows)

    series_counts = 0
    for ev in evaluations:
        run_id = ev["run_id"]
        series = _series_for(run_id, points=24 if ev["strategy"] == "inst_flow" else 10)
        write_series(
            run_id,
            series["equity"],
            series["drawdown"],
            series["trades"],
            series_dir=reports_root / "series",
        )
        write_report_pack(ev, series, root=reports_root / "research_runs")
        series_counts += 1

    _write_jsonl(
        reports_root / DEFAULT_VALIDATION_PATH.name,
        [
            {
                "run_id": main_eval["run_id"],
                "validation_status": "paper_watch",
                "stage": "deployment_strict",
                "note": "DSR 0.908: eligible for zero-capital live OOS, blocked for capital deployment.",
                "at": "2026-07-02T18:45:00+08:00",
            }
        ],
    )
    _write_jsonl(
        reports_root / DEFAULT_PROMOTION_PATH.name,
        [
            {
                "strategy_id": "inst_flow",
                "stage": "paper",
                "note": "Seeded Paper-Watch berth after deployment_strict evaluation.",
                "actor": "operator",
                "at": "2026-07-02T19:10:00+08:00",
            }
        ],
    )
    _write_jsonl(
        reports_root / DEFAULT_WATCH_PATH.name,
        [
            {
                "strategy": "inst_flow",
                "event": "enroll",
                "verdict_dsr": 0.908,
                "enrolled_on": "2026-07-02",
                "re_enroll_evidence": None,
                "at": "2026-07-02T19:10:00+08:00",
            }
        ],
    )
    _write_jsonl(
        reports_root / DEFAULT_MARKER_PATH.name,
        [
            {
                "key": "inst_flow@2026-07-03",
                "strategy": "inst_flow",
                "date": "2026-07-03",
                "ok": True,
                "detail": "Seeded after-close paper session.",
                "recorded_at": "2026-07-03T14:45:00+08:00",
            }
        ],
    )
    return {
        "evaluations": len(evaluations),
        "candidates": len(candidates),
        "candidate_decisions": len(decisions),
        "live_oos_queue": len(queue_payload["data"]),
        "runs": len(run_rows),
        "series": series_counts,
    }


def _run_row(evaluation: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    strategy = evaluation["strategy"]
    candidate = next((c for c in candidates if c.get("strategy") == strategy), {})
    window = evaluation.get("window") or {}
    headline = evaluation.get("headline_metrics") or {}
    status = "done"
    verdict = evaluation.get("verdict") or {}
    truth = verdict.get("truth_verdict")
    gate_status = "PASS" if truth == "REAL" else "FAIL" if truth in {"REJECTED", "PAPER_WATCH"} else "INCOMPLETE"
    return {
        "run_id": evaluation["run_id"],
        "hypothesis": candidate.get("hypothesis") or f"{strategy} seeded demo run",
        "strategy": strategy,
        "engine": (evaluation.get("lineage") or {}).get("engine") or "sim",
        "stocks": ["2330", "2317", "2454"],
        "is_start": window.get("is_start", "2018-01-01"),
        "is_end": window.get("is_end", "2024-12-31"),
        "git_sha": None,
        "bundle_ref": (evaluation.get("lineage") or {}).get("bundle_ref") or "data/parquet_finlab_universe",
        "cost_assumptions": {"commission_bps": 14.25, "tax_bps": 30, "slippage_bps": 10},
        "params": (evaluation.get("lineage") or {}).get("params") or {},
        "metrics": headline,
        "gate_status": gate_status,
        "gate_summary": verdict.get("recommendation", {}).get("action"),
        "status": status,
        "trials_count": int(headline.get("n_trials") or 0),
    }


def _seed_data_cache(data_root: Path) -> dict[str, int]:
    cache = data_root / "parquet"
    universe = data_root / "parquet_finlab_universe"
    cache.mkdir(parents=True, exist_ok=True)
    universe.mkdir(parents=True, exist_ok=True)

    symbols = ["2330", "2317", "2454"]
    days = pd.date_range("2026-06-29", periods=5, freq="B")
    for idx, symbol in enumerate(symbols):
        base = 900 + idx * 200
        daily = pd.DataFrame(
            {
                "stock_id": symbol,
                "trade_date": days,
                "open": [base + i * 3 for i in range(len(days))],
                "high": [base + i * 3 + 8 for i in range(len(days))],
                "low": [base + i * 3 - 5 for i in range(len(days))],
                "close": [base + i * 4 for i in range(len(days))],
                "volume": [12_000_000 + idx * 1_000_000 + i * 200_000 for i in range(len(days))],
                "adj_factor": 1.0,
            }
        )
        inst = pd.DataFrame(
            {
                "stock_id": symbol,
                "trade_date": days,
                "foreign_buy": [800_000 + i * 25_000 for i in range(len(days))],
                "trust_buy": [120_000 + i * 10_000 for i in range(len(days))],
                "dealer_buy": [50_000 + i * 5_000 for i in range(len(days))],
            }
        )
        chips = pd.DataFrame(
            {
                "stock_id": symbol,
                "trade_date": days,
                "top_broker_buy": [300_000 + i * 20_000 for i in range(len(days))],
                "key_broker_buy": [180_000 + i * 12_000 for i in range(len(days))],
                "gov_broker_buy": [30_000 + i * 3_000 for i in range(len(days))],
                "geo_broker_buy": [40_000 + i * 4_000 for i in range(len(days))],
                "day_trade_volume": [900_000 + i * 20_000 for i in range(len(days))],
                "margin_offset_volume": [120_000 + i * 8_000 for i in range(len(days))],
            }
        )
        daily.to_parquet(cache / f"daily_bars__{symbol}.parquet", index=False)
        inst.to_parquet(cache / f"institutional__{symbol}.parquet", index=False)
        chips.to_parquet(cache / f"broker_chips__{symbol}.parquet", index=False)

    manifest = {
        "schema_version": 1,
        "stocks": {
            symbol: {
                "start": "2026-06-29",
                "end": "2026-07-03",
                "rows": len(days),
                "data_hash": f"seed-{symbol}",
            }
            for symbol in symbols
        },
        "stock_count": len(symbols),
        "coverage": {"start": "2026-06-29", "end": "2026-07-03"},
        "data_hash": "seed-demo-bundle",
        "generated_at": "2026-07-05T00:00:00+08:00",
    }
    (cache / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    universe_manifest = {
        "strategy": "inst_flow",
        "params": {
            "span_start": "2010-01-01",
            "span_end": "2024-12-31",
            "top_n": 200,
            "min_turnover": 50_000_000.0,
        },
        "symbols": symbols,
        "n_symbols": len(symbols),
        "n_alive": 3,
        "n_delisted": 0,
        "ingest": {"ok": 3, "failed": 0, "failed_symbols": []},
        "generated_at": "2026-07-02T00:00:00+08:00",
    }
    (universe / "universe_manifest.json").write_text(
        json.dumps(universe_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"symbols": len(symbols), "trading_days": len(days), "manifests": 2}


def _seed_db() -> dict[str, int]:
    from quant_platform.packages.infrastructure.db_kernel import DBConfig, _connection
    from quant_platform.services.monitoring_ops.telemetry_writer import upsert_equity_snapshots, upsert_fills, upsert_signals
    from quant_platform.packages.infrastructure.runs_writer import upsert_runs

    cfg = DBConfig.from_env()
    run_ids = list(RUN_IDS.values())
    strategies = ["inst_flow", "momentum", "four_layer_resonance", "reversal", "long_short"]
    with _connection(cfg) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM signals WHERE run_id = ANY(%s) OR strategy_id = ANY(%s)", (run_ids, strategies))
        cur.execute("DELETE FROM fills WHERE strategy_id = ANY(%s)", (strategies,))
        cur.execute("DELETE FROM equity_snapshots WHERE run_id = ANY(%s) OR strategy_id = ANY(%s)", (run_ids, strategies))
        cur.execute("DELETE FROM runs WHERE run_id = ANY(%s)", (run_ids,))

    evaluations = _load_example("candidate_pool.example.json")["data"]
    rows = [_db_run_row(candidate) for candidate in evaluations]
    run_count = upsert_runs(rows, cfg=cfg)

    equity_rows = []
    start = datetime(2026, 7, 1, 14, 30, tzinfo=TWT)
    for i in range(8):
        equity = 10_000_000 + i * 42_500
        equity_rows.append(
            {
                "snapshot_time": (start + timedelta(days=i)).isoformat(),
                "strategy_id": "inst_flow",
                "mode": "paper",
                "run_id": RUN_IDS["inst_flow"],
                "equity": equity,
                "cash": 4_850_000 - i * 20_000,
                "positions_value": equity - (4_850_000 - i * 20_000),
                "open_positions": 3,
                "portfolio_heat": 0.41,
                "drawdown": -0.006 if i == 2 else 0.0,
                "daily_return": 0.004 if i else 0.0,
                "cumulative_return": (equity / 10_000_000) - 1,
            }
        )
    equity_count = upsert_equity_snapshots(equity_rows, cfg=cfg)

    signal_rows = [
        {
            "signal_time": "2026-07-03T09:00:00+08:00",
            "strategy_id": "inst_flow",
            "run_id": RUN_IDS["inst_flow"],
            "stock_id": "2330",
            "action": "buy",
            "priority": 3,
            "reason_json": {"factor": "foreign_flow", "target_weight": 0.15},
            "submitted": True,
            "submitted_at": "2026-07-03T09:01:00+08:00",
        },
        {
            "signal_time": "2026-07-03T09:00:30+08:00",
            "strategy_id": "inst_flow",
            "run_id": RUN_IDS["inst_flow"],
            "stock_id": "2317",
            "action": "buy",
            "priority": 4,
            "reason_json": {"factor": "foreign_flow", "target_weight": 0.1},
            "submitted": True,
            "submitted_at": "2026-07-03T09:01:30+08:00",
        },
        {
            "signal_time": "2026-07-03T09:02:00+08:00",
            "strategy_id": "inst_flow",
            "run_id": RUN_IDS["inst_flow"],
            "stock_id": "2603",
            "action": "exit",
            "priority": 2,
            "reason_json": {"risk": "factor_score_drop"},
            "submitted": True,
            "submitted_at": "2026-07-03T09:03:00+08:00",
        },
    ]
    signal_count = upsert_signals(signal_rows, cfg=cfg)

    fill_rows = [
        {
            "filled_at": "2026-07-03T09:05:00+08:00",
            "order_id": "11111111-1111-4111-8111-111111111111",
            "strategy_id": "inst_flow",
            "stock_id": "2330",
            "side": "Buy",
            "qty": 2000,
            "price": 998.0,
            "commission": 284.43,
            "tax": 0.0,
            "slippage_bps": 2.1,
            "broker": "paper",
            "broker_trade_id": "seed-fill-2330",
        },
        {
            "filled_at": "2026-07-03T09:08:00+08:00",
            "order_id": "22222222-2222-4222-8222-222222222222",
            "strategy_id": "inst_flow",
            "stock_id": "2317",
            "side": "Buy",
            "qty": 5000,
            "price": 214.5,
            "commission": 152.87,
            "tax": 0.0,
            "slippage_bps": 1.4,
            "broker": "paper",
            "broker_trade_id": "seed-fill-2317",
        },
    ]
    fill_count = upsert_fills(fill_rows, cfg=cfg)
    return {"runs": run_count, "equity_snapshots": equity_count, "signals": signal_count, "fills": fill_count}


def _db_run_row(candidate: dict[str, Any]) -> dict[str, Any]:
    strategy = candidate["strategy"]
    run_id = _run_id_from_report_ref(candidate.get("report_pack_ref"), strategy)
    headline = candidate.get("headline") or {}
    truth = candidate.get("latest_truth_verdict")
    gate_status = "PASS" if truth == "REAL" else "FAIL" if truth in {"REJECTED", "PAPER_WATCH"} else "INCOMPLETE"
    return {
        "run_id": run_id,
        "hypothesis": candidate.get("hypothesis") or f"{strategy} seeded run",
        "strategy": strategy,
        "engine": "sim",
        "stocks": ["2330", "2317", "2454"],
        "is_start": "2018-01-01",
        "is_end": "2024-12-31",
        "git_sha": None,
        "bundle_ref": "data/parquet_finlab_universe",
        "cost_assumptions": {"commission_bps": 14.25, "tax_bps": 30, "slippage_bps": 10},
        "params": {},
        "metrics": headline,
        "gate_status": gate_status,
        "gate_summary": candidate.get("next_action"),
        "status": "done",
        "trials_count": int(headline.get("n_trials") or 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-root", type=Path, default=BACKTEST_ROOT / "reports")
    parser.add_argument("--data-root", type=Path, default=BACKTEST_ROOT / "data")
    parser.add_argument("--skip-db", action="store_true", help="Only seed local files/ledgers.")
    args = parser.parse_args()

    ledger_counts = _seed_ledgers(args.reports_root)
    data_counts = _seed_data_cache(args.data_root)
    db_counts = {} if args.skip_db else _seed_db()

    print(
        json.dumps(
            {
                "reports_root": str(args.reports_root),
                "data_root": str(args.data_root),
                "ledgers": ledger_counts,
                "data_cache": data_counts,
                "db": db_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
