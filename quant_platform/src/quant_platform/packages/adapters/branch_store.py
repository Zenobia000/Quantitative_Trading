"""Branch-experiment store (rebuild Goal 9) — explicit strategy iteration lineage.

A *branch* is an alternative config of an already-evaluated strategy, forked from a
parent ``EvaluationResult`` with an explicit ``config_delta``. It exists so a
researcher can iterate ("what if lookback were 90 not 60?") with **provable lineage**
and a **side-by-side comparison** against the parent — never a silent in-place edit
(spec Goal 9 acceptance: every branch links its parent, compare shows delta metrics +
a decision, no branch overwrites the parent).

Same append-only, dependency-free, folded-projection philosophy as ``runs_store`` /
``evaluation.store`` / ``candidate_store``: ``branch_experiments.jsonl`` collects one
record per state change; the current state of a ``branch_id`` is the LATEST record
carrying that id (``create`` appends a ``draft``; ``evaluate`` appends an ``evaluated``
record with the backfilled ``evaluation_id`` — the draft line is never mutated).

Immutability is the whole point (Goal 9 acceptance #3):

* ``create_branch`` reads the parent evaluation and applies the delta to a **new**
  config dict — the parent's evaluation/run/candidate records are never touched.
* ``evaluate_branch`` runs the orchestrator with the branch config as a *param
  override*; because at least one config key differs, the branch gets a **distinct**
  ``run_id`` (config hash) and therefore a distinct ``evaluation_id`` — it can never
  fold over the parent's evaluation ledger record.

Two delta-key vocabularies (validated at ``create`` → 422 on an unknown key):

* **config keys** — real ``config_model`` fields of the strategy (``lookback_days`` …).
  These are applied to the re-run and produce a genuinely different backtest.
* **execution-overlay knobs** — the fixed simulation vocabulary
  (``cost_multiplier`` / ``slippage_bps`` / ``capacity_scale`` / ``stop_loss_pct`` /
  ``take_profit_pct``, from ``research.simulation``). A ``simulation``-origin fork
  records these as lineage, but the current runners do not *consume* them (the
  contract §11 P1 blocker the simulation module already discloses), so an
  overlay-only branch is honestly ``applies_to_rerun = false`` and refuses to
  evaluate rather than fabricate a re-run identical to the parent.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from quant_platform.services.research_validation.evaluation.store import (
    DEFAULT_EVALUATIONS_PATH,
    get_evaluation,
)
from quant_platform.services.research_validation.strategies.protocol import describe_strategy, get_strategy

DEFAULT_BRANCHES_PATH = Path("reports") / "branch_experiments.jsonl"

#: The fixed execution-overlay vocabulary a ``simulation`` fork may carry (mirrors
#: ``research.simulation._branch_suggestion``). Recognised as legal delta keys but
#: NOT applied to the re-run — the runners do not consume them (contract §11).
EXECUTION_OVERLAY_KNOBS = frozenset(
    {"cost_multiplier", "slippage_bps", "capacity_scale", "stop_loss_pct", "take_profit_pct"}
)

#: The valid ``origin`` values (where a branch suggestion came from — never an LLM).
BRANCH_ORIGINS = frozenset({"simulation", "manual", "report_finding"})

_TWT = timezone(timedelta(hours=8))


class ParentNotFoundError(ValueError):
    """No parent evaluation for the given id (→ API 404)."""


class IllegalDeltaError(ValueError):
    """A config_delta key is neither a strategy config field nor an overlay knob,
    or a resolved config value fails the strategy's config_model bounds (→ API 422)."""


class BranchNotFoundError(ValueError):
    """No branch for the id (→ API 404)."""


class BranchNotEvaluableError(ValueError):
    """A branch whose delta changes only execution-overlay knobs (no config-key
    change) cannot be re-run — doing so would reproduce the parent (→ API 409)."""


def _now_iso() -> str:
    return datetime.now(_TWT).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# pure functions (unit-testable, never touch disk or the parent record)        #
# --------------------------------------------------------------------------- #
def config_keys(config_schema: Mapping[str, Any] | None) -> set[str]:
    """The strategy's declared config_model field names (JSON-schema properties)."""
    props = (config_schema or {}).get("properties")
    return set(props.keys()) if isinstance(props, dict) else set()


def classify_delta(
    config_delta: list[dict[str, Any]], config_schema: Mapping[str, Any] | None
) -> tuple[list[str], list[str], list[str]]:
    """Split delta keys into ``(config_keys, overlay_knobs, illegal)`` for a strategy.

    A key is a *config* key if it is a real ``config_model`` field, an *overlay* knob
    if it is in :data:`EXECUTION_OVERLAY_KNOBS`, otherwise *illegal*. Pure — the
    single source of truth for the create-time 422 guard.
    """
    valid = config_keys(config_schema)
    cfg, overlay, illegal = [], [], []
    for d in config_delta:
        key = d["key"]
        if key in valid:
            cfg.append(key)
        elif key in EXECUTION_OVERLAY_KNOBS:
            overlay.append(key)
        else:
            illegal.append(key)
    return cfg, overlay, illegal


def apply_config_delta(
    parent_config: Mapping[str, Any], config_delta: list[dict[str, Any]], config_schema: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Apply the *config-key* subset of ``config_delta`` onto ``parent_config``.

    Returns a **new** dict (immutability — the parent config is never mutated).
    Overlay knobs are ignored here: the runner never reads them, so injecting one
    into the re-run params would be fabricating an effect the backtest cannot honour.
    """
    valid = config_keys(config_schema)
    branch = dict(parent_config)  # new object — parent untouched
    for d in config_delta:
        if d["key"] in valid:
            branch[d["key"]] = d["to"]
    return branch


def _normalize_delta(
    config_delta: list[dict[str, Any]], parent_config: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Canonicalise each ``{key, to, from?}`` — resolve the authoritative ``from``
    from the parent config (client-sent ``from`` is advisory only)."""
    out: list[dict[str, Any]] = []
    for d in config_delta:
        key = d["key"]
        frm = parent_config.get(key, d.get("from"))
        out.append({"key": key, "from": frm, "to": d["to"]})
    return out


def _branch_id(strategy: str, parent_run_id: str, config_delta: list[dict[str, Any]], created_at: str) -> str:
    """A short, collision-resistant branch id: ``branch_<strategy>_<hash10>``."""
    payload = json.dumps([parent_run_id, config_delta, created_at], sort_keys=True, default=str)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"branch_{strategy}_{digest}"


# --------------------------------------------------------------------------- #
# store primitives                                                             #
# --------------------------------------------------------------------------- #
def _read(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _append(record: dict[str, Any], path: Path | str) -> dict[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def get_branch(branch_id: str, *, branches_path: Path | str = DEFAULT_BRANCHES_PATH) -> dict[str, Any] | None:
    """The latest record for ``branch_id`` (a re-evaluation folds to its last append)."""
    match: dict[str, Any] | None = None
    for rec in _read(branches_path):
        if rec.get("branch_id") == branch_id:
            match = rec
    return match


def list_branches(
    *,
    strategy: str | None = None,
    parent_evaluation_id: str | None = None,
    parent_run_id: str | None = None,
    branches_path: Path | str = DEFAULT_BRANCHES_PATH,
) -> list[dict[str, Any]]:
    """All branches (newest-created first), optionally filtered by strategy / parent."""
    ids = {rec["branch_id"] for rec in _read(branches_path)}
    branches = [b for bid in ids if (b := get_branch(bid, branches_path=branches_path)) is not None]
    if strategy is not None:
        branches = [b for b in branches if b.get("strategy") == strategy]
    if parent_evaluation_id is not None:
        branches = [b for b in branches if b.get("parent_evaluation_id") == parent_evaluation_id]
    if parent_run_id is not None:
        branches = [b for b in branches if b.get("parent_run_id") == parent_run_id]
    return sorted(branches, key=lambda b: b.get("created_at", ""), reverse=True)


# --------------------------------------------------------------------------- #
# create                                                                       #
# --------------------------------------------------------------------------- #
def create_branch(
    parent_evaluation_id: str,
    config_delta: list[dict[str, Any]],
    *,
    origin: str = "manual",
    note: str | None = None,
    profile: str = "quick_triage",
    branches_path: Path | str = DEFAULT_BRANCHES_PATH,
    evaluations_path: Path | str = DEFAULT_EVALUATIONS_PATH,
    clock: Any = _now_iso,
) -> dict[str, Any]:
    """Fork a branch from ``parent_evaluation_id`` with ``config_delta`` → a draft record.

    Validates the parent exists (:class:`ParentNotFoundError` → 404) and that every
    delta key is a strategy config field or an overlay knob and any resolved config
    value passes the strategy's ``config_model`` bounds (:class:`IllegalDeltaError` →
    422). Applies the config-key subset to a **new** config dict — the parent's
    records are never touched — and appends a ``draft`` branch. ``config_delta`` must
    be non-empty. ``evaluation_id`` is ``None`` until :func:`evaluate_branch` runs.
    """
    parent = get_evaluation(parent_evaluation_id, evaluations_path)
    if parent is None:
        raise ParentNotFoundError(f"no parent evaluation {parent_evaluation_id!r}")
    if not config_delta:
        raise IllegalDeltaError("config_delta must contain at least one {key, to} change")
    if origin not in BRANCH_ORIGINS:
        raise IllegalDeltaError(f"origin must be one of {sorted(BRANCH_ORIGINS)}")

    strategy = parent["strategy"]
    parent_config = dict((parent.get("lineage") or {}).get("params") or {})
    parent_run_id = parent["run_id"]
    try:
        schema = describe_strategy(strategy).config_schema
    except ValueError as exc:  # strategy no longer registered
        raise IllegalDeltaError(str(exc)) from None

    cfg_keys, overlay_keys, illegal = classify_delta(config_delta, schema)
    if illegal:
        allowed = sorted(config_keys(schema) | EXECUTION_OVERLAY_KNOBS)
        raise IllegalDeltaError(
            f"illegal config_delta key(s) {illegal} for strategy {strategy!r}; "
            f"allowed keys: {allowed}"
        )

    branch_config = apply_config_delta(parent_config, config_delta, schema)
    # Eagerly reject config values that violate the strategy's own field bounds.
    if cfg_keys:
        try:
            get_strategy(strategy).config_model(**branch_config)
        except Exception as exc:  # pydantic ValidationError (or unknown extra)
            raise IllegalDeltaError(f"branch config rejected by {strategy!r} config_model: {exc}") from None

    # A branch that changes at least one *config* value away from the parent re-runs
    # to a distinct config hash; an overlay-only branch does not (honest flag).
    applies_to_rerun = any(
        parent_config.get(d["key"]) != d["to"] for d in config_delta if d["key"] in set(cfg_keys)
    )

    created_at = clock()
    normalized = _normalize_delta(config_delta, parent_config)
    branch_id = _branch_id(strategy, parent_run_id, normalized, created_at)
    record = {
        "branch_id": branch_id,
        "parent_evaluation_id": parent_evaluation_id,
        "parent_run_id": parent_run_id,
        "strategy": strategy,
        "profile": profile,
        "origin": origin,
        "note": note,
        "config_delta": normalized,
        "branch_config": branch_config,
        "applies_to_rerun": applies_to_rerun,
        "created_at": created_at,
        "evaluation_id": None,
        "status": "draft",
    }
    return _append(record, branches_path)


# --------------------------------------------------------------------------- #
# evaluate                                                                      #
# --------------------------------------------------------------------------- #
def evaluate_branch(
    branch_id: str,
    *,
    loader: Any = None,
    data_dir: str | None = None,
    branches_path: Path | str = DEFAULT_BRANCHES_PATH,
    evaluations_path: Path | str = DEFAULT_EVALUATIONS_PATH,
    pack_root: Any = None,
    ingest: bool = True,
    candidates_path: Path | str | None = None,
    decisions_path: Path | str | None = None,
    evaluate_fn: Any = None,
    ingest_fn: Any = None,
    clock: Any = _now_iso,
) -> dict[str, Any]:
    """Run the branch config through the evaluation orchestrator; backfill its id.

    Runs the branch's own ``profile`` (default ``quick_triage``) with the config-key
    deltas as a param override — a genuinely different backtest → distinct
    ``run_id`` / ``evaluation_id`` (never folds over the parent). The produced
    ``EvaluationResult`` is tagged with its branch lineage (``result["branch"]``) and,
    by default, ingested into the candidate pool carrying that branch origin. Appends
    an ``evaluated`` branch record; the draft line is left intact (append-only).

    Raises :class:`BranchNotFoundError` (unknown id → 404) or
    :class:`BranchNotEvaluableError` (overlay-only branch → 409).
    """
    from quant_platform.services.research_validation.evaluation.orchestrator import evaluate as _default_evaluate
    from quant_platform.services.research_validation.evaluation.report_pack import DEFAULT_PACK_ROOT

    branch = get_branch(branch_id, branches_path=branches_path)
    if branch is None:
        raise BranchNotFoundError(f"no branch {branch_id!r}")
    if not branch.get("applies_to_rerun"):
        raise BranchNotEvaluableError(
            f"branch {branch_id!r} changes only execution-overlay knobs the runner "
            f"does not consume (contract §11 P1 blocker) — no config-key change to re-run"
        )

    run = evaluate_fn or _default_evaluate
    schema_keys = config_keys(describe_strategy(branch["strategy"]).config_schema)
    param_overrides = {d["key"]: d["to"] for d in branch["config_delta"] if d["key"] in schema_keys}
    branch_lineage = {
        "branch_id": branch_id,
        "parent_evaluation_id": branch["parent_evaluation_id"],
        "parent_run_id": branch["parent_run_id"],
        "origin": branch["origin"],
    }

    result = run(
        branch["strategy"],
        branch.get("profile", "quick_triage"),
        loader=loader,
        data_dir=data_dir,
        param_overrides=param_overrides,
        branch_lineage=branch_lineage,
        evaluations_path=evaluations_path,
        pack_root=pack_root if pack_root is not None else DEFAULT_PACK_ROOT,
    )

    if ingest:
        from quant_platform.packages.adapters import candidate_store
        do_ingest = ingest_fn or candidate_store.ingest_evaluation
        kw: dict[str, Any] = {}
        if candidates_path is not None:
            kw["candidates_path"] = candidates_path
        if decisions_path is not None:
            kw["decisions_path"] = decisions_path
        do_ingest(result, **kw)

    evaluated = {
        **branch,
        "evaluation_id": result["evaluation_id"],
        "status": "evaluated",
        "evaluated_at": clock(),
    }
    _append(evaluated, branches_path)
    return {"branch": evaluated, "evaluation": result}


# --------------------------------------------------------------------------- #
# compare                                                                       #
# --------------------------------------------------------------------------- #
#: Headline metrics diffed in the compare table, in display order. ``lower_is_better``
#: flips the "improved" sense (a *smaller* drawdown / volatility is better).
_COMPARE_METRICS: tuple[tuple[str, bool], ...] = (
    ("cagr", False),
    ("total_return", False),
    ("sharpe", False),
    ("sortino", False),
    ("calmar", False),
    ("max_drawdown", True),
    ("volatility", True),
    ("oos_holdout_sharpe", False),
    ("dsr", False),
    ("trades", False),
)


def _num(x: Any) -> float | None:
    if isinstance(x, bool) or x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # drop NaN


def _decision(rows: list[dict[str, Any]], parent_label: str | None, branch_label: str | None) -> dict[str, Any]:
    """A deterministic branch-vs-parent verdict driven by the Sharpe delta.

    Sharpe is the single tie-breaker (risk-adjusted edge); the reasons list the
    Sharpe / CAGR / max-drawdown deltas so the call is hand-checkable. ``inconclusive``
    when Sharpe is missing on either side or the delta is zero.
    """
    by_metric = {r["metric"]: r for r in rows}
    sharpe = by_metric.get("sharpe", {})
    ds = sharpe.get("delta")
    if ds is None or ds == 0:
        verdict = "inconclusive"
    elif ds > 0:
        verdict = "branch_better"
    else:
        verdict = "parent_better"
    reasons: list[str] = []
    for m in ("sharpe", "cagr", "max_drawdown"):
        row = by_metric.get(m)
        if row and row.get("delta") is not None:
            reasons.append(f"{m} Δ {row['delta']:+.4f} ({row['change']})")
    return {
        "verdict": verdict,
        "parent_label": parent_label,
        "branch_label": branch_label,
        "reasons": reasons,
    }


def compare_branch(
    branch_id: str,
    *,
    branches_path: Path | str = DEFAULT_BRANCHES_PATH,
    evaluations_path: Path | str = DEFAULT_EVALUATIONS_PATH,
) -> dict[str, Any]:
    """Build the branch-vs-parent headline-metric delta table (+ a decision).

    Reuses both sides' persisted ``EvaluationResult`` headline metrics (no re-run).
    When the branch has not been evaluated yet (``evaluation_id is None``) the table
    still lists the parent column with ``branch``/``delta`` = ``null`` and
    ``branch_evaluated = false`` so the UI can prompt "evaluate first" rather than
    error. Raises :class:`BranchNotFoundError` for an unknown branch (→ 404).
    """
    branch = get_branch(branch_id, branches_path=branches_path)
    if branch is None:
        raise BranchNotFoundError(f"no branch {branch_id!r}")

    parent = get_evaluation(branch["parent_evaluation_id"], evaluations_path)
    parent_h = (parent or {}).get("headline_metrics", {})
    branch_eval = get_evaluation(branch["evaluation_id"], evaluations_path) if branch.get("evaluation_id") else None
    branch_h = (branch_eval or {}).get("headline_metrics", {})
    evaluated = branch_eval is not None

    rows: list[dict[str, Any]] = []
    for metric, lower_better in _COMPARE_METRICS:
        pv, bv = _num(parent_h.get(metric)), _num(branch_h.get(metric))
        delta = (bv - pv) if (evaluated and pv is not None and bv is not None) else None
        if delta is None or delta == 0:
            change = "flat"
        else:
            improved = (delta < 0) if lower_better else (delta > 0)
            change = "improved" if improved else "worsened"
        rows.append(
            {"metric": metric, "lower_is_better": lower_better,
             "parent": pv, "branch": bv, "delta": delta, "change": change}
        )

    parent_label = (parent or {}).get("verdict", {}).get("label")
    branch_label = (branch_eval or {}).get("verdict", {}).get("label")
    return {
        "branch_id": branch_id,
        "strategy": branch["strategy"],
        "parent_evaluation_id": branch["parent_evaluation_id"],
        "parent_run_id": branch["parent_run_id"],
        "branch_evaluation_id": branch.get("evaluation_id"),
        "branch_run_id": (branch_eval or {}).get("run_id"),
        "config_delta": branch["config_delta"],
        "branch_evaluated": evaluated,
        "metrics": rows,
        "decision": _decision(rows, parent_label, branch_label) if evaluated else None,
    }
