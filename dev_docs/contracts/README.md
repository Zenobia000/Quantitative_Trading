# Evaluation / Candidate / Live-OOS Contracts

> **Status:** draft contract (docs + fixtures only, zero backend code) · **Created:** 2026-07-03
> **Scope:** rebuild Goal 2 — "Backend Evaluation / Candidate Contracts"
> **Source spec:** `rebuild_goal_spec_ai_requirements_2026-07-03.md` §3.1 / §4.3 / Goal 2 / §6 / §8
> **Product rationale:** `product_repositioning_research_plan_2026-07-03.md`

These contracts let the frontend and backend develop independently. The frontend
implements against the fixtures here first, then switches to real endpoints when
the Goal 3/4/10 orchestrator lands. **Every field below is producible by an
existing backend module** — the per-contract mapping tables (§10) are the Goal 2
hard requirement. Fields that cannot be produced today are marked
`not_available` with a reason (rule #6), never fabricated.

This is a **documentation + fixtures** deliverable only: no backend code, no
`openapi.json` / `api.gen.ts` changes, no DB migration. It intentionally avoids the
contract-drift gate (doc 25 §9) so it can land in parallel with other work.

---

## 1. File inventory

| File | What it is | Envelope? |
| :--- | :--- | :--- |
| `README.md` | This overview: endpoints, errors, state machine, module mapping. | — |
| `evaluation_profile.schema.json` | JSON Schema (draft-07) for `EvaluationProfile`; the four built-in profiles are embedded in `examples` and self-validate. | data payload |
| `evaluation_result.example.json` | One `EvaluationResult` (`data` payload of `GET /research/evaluations/{id}`) — the real inst_flow `deployment_strict` verdict. | data payload |
| `report_pack_manifest.example.json` | One `ReportPackManifest` (`data` payload of `GET /research/evaluations/{id}/report`). | data payload |
| `candidate_pool.example.json` | `GET /research/candidates` — full envelope (list + `page_meta`). | full envelope |
| `live_oos_queue.example.json` | `GET /research/live-oos/queue` — full envelope. | full envelope |

The two list fixtures (`candidate_pool`, `live_oos_queue`) are **full envelopes**
(directly usable as fixtures). The two singleton fixtures (`evaluation_result`,
`report_pack_manifest`) are the **`data` payloads** their `GET` endpoints wrap in
`ok(data, meta)` — the endpoint drafts in §9 show the wrapping.

---

## 2. Conventions (reuse doc 25, `api/envelope.py`)

All new endpoints reuse the existing contract, not a new one:

- **Envelope** `{ success, data, error, meta }` (`api/envelope.py::Envelope`). Success = `ok(data, meta)`, error = `fail(message, code, detail)`.
- **Error object** `{ code, message, detail }` with the doc 25 §2 code enum. 404 `detail = {resource, id}`; 400 `detail = {hint}`; 409 `detail = {resource_id, state}`; 422 `detail = [{loc, msg}]`.
- **Pagination** (doc 25 §3, standardized #176): `?page=<int ge 1, default 1>&limit=<int 1..500, default 50>`; `meta = page_meta(total, page, limit)`.
- **`meta.data_source`** must be an existing `DataSource` enum member (doc 25 §5.4). These contracts reuse `ledger` (candidate/evaluation projections over the append-only JSONL store) and `watch_registry` (live-OOS queue folded from the event-sourced berth log). No new token is minted here (that would touch `envelope.py`).
- **Types**: percentages as decimals (`0.162` = 16.2%); `stock_id` as TEXT; `NaN`/`Inf` → `null`; dates ISO-8601 with offset.
- **TTL**: research/batch products `meta.ttl = 300` (doc 25 §5.1).

---

## 3. The four built-in EvaluationProfiles

A profile is a **high-level recipe above** the ADR-029 primitives — it never
replaces them. `deployment_strict` **wraps** the truth gate; it is not the only
evaluation path (§6 Non-Goal).

| Profile | One-line definition |
| :--- | :--- |
| **`quick_triage`** | One single-config backtest + the five scorecards; no PBO/DSR/full-WFA/paper — "is this worth researching?" (seconds). |
| **`fixed_hypothesis_oos`** | Pre-registered locked hypothesis: IS/OOS split + WFA-lite OOS breadth + OOS holdout + cost stress; PBO disabled, DSR optional (minutes). |
| **`grid_search_selection`** | DOE parameter landscape + heatmap/plateau + landscape PBO + trials-deflated DSR + top-N compare (tens of minutes). |
| **`deployment_strict`** | The existing ADR-025/030 truth gate unchanged (survivorship + WFA breadth + DSR + OOS holdout + K3 slippage + sizing), exposed as a deployment-level profile (tens of minutes). |

Each profile declares `wraps_primitives`, `scorecards`, severity-graded `gates`,
`report_pack`, `live_oos_policy`, `runtime_magnitude`, and `source_modules`. See
`evaluation_profile.schema.json` `examples[]` for the full definitions.

`severity` replaces a single binary verdict: `info` (display) → `warn` (poolable
note) → `block_live_oos` (don't spend live OOS without override) → `block_deploy`
(never allocate capital).

---

## 4. EvaluationResult

`GET /research/evaluations/{id}` → `Envelope[EvaluationResult]`. See
`evaluation_result.example.json`.

Top-level shape: `evaluation_id`, `run_id`, `strategy`, `profile(+version)`,
`window`, `universe`, `verdict{label, truth_verdict, recommendation}`,
`headline_metrics`, `scorecards[5]`, `checks[]`, `sizing`, `lineage`,
`report_pack_ref`, `data_gaps[]`.

**Failed/weak/negative strategies are fully persisted** (global acceptance #5).
The example is inst_flow `deployment_strict`: `truth_verdict = PAPER_WATCH`,
`recommendation.action = eligible_for_live_oos` — a REJECTED-for-deploy strategy
that is still a research asset and a Paper-Watch candidate.

### 4.1 The five scorecards (per-metric pass/warn/fail/not_available)

| Scorecard | Available today (source module) | `not_available` today (reason) |
| :--- | :--- | :--- |
| **Profitability** | `cagr`, `total_return` (`validation.metrics`), `avg_holdings` (`panel_metrics`) | `alpha`, `beta` (no benchmark series joined), `max_holdings` (only avg tracked) |
| **Risk** | `max_drawdown`, `ulcer_index` (`validation.metrics`), `avg_drawdown`, `recovery_days` (`validation.report.drawdown_events`) | `var_95`, `cvar_95` (not implemented in `metrics.py`) |
| **Risk-Adjusted** | `sharpe`, `sortino`, `calmar` (`validation.metrics`), `oos_holdout_sharpe` (`truth_gate`) | `profit_factor` (panel `trades` is a count, no per-trade pnl), `tail_ratio` (not implemented) |
| **Win Rate** | *(partial for `four_layer_resonance`, which emits per-trade dicts)* | Entire card for panel strategies: `trade_win_rate`, `payoff_ratio`, `expectancy`, `rolling_12m_win_rate`, `mae`, `mfe` — the trades schema carries no per-trade pnl/entry/exit/excursion (**P1 blocker**) |
| **Liquidity** | `avg_turnover` (`panel_metrics`), `cost_sensitivity` (`sharpe` vs `slippage_sharpe`) | `volume_bucket_distribution`, `safe_trade_fraction`, `capacity_proxy` (need per-trade notional + per-bar ADV join) |

Each scorecard metric object: `{ id, label, value|null, unit, threshold|null, op|null, status, severity, source_module, reason? }` where `status ∈ pass|warn|fail|missing|not_applicable|not_available`.

---

## 5. ReportPackManifest

`GET /research/evaluations/{id}/report` → `Envelope[ReportPackManifest]`. See
`report_pack_manifest.example.json`.

Lists the report-pack files under `reports/research_runs/<run_id>/`
(`summary.json`, `metrics.json`, `scorecards.json`, `report.md` required per Goal 3;
`gate_results.json`, `equity.parquet`, `trades.parquet` where available;
`simulations.json` / `figures/*` marked `not_available` until Goal 8 / Phase 9),
plus `lineage` (`config_hash` = `RunConfig.run_id`, `bundle_ref`, `params`,
`n_trials`, `survivorship_clean`; `git_sha` = `not_available`).

**Compatibility with `GET /runs/{id}/report`:** the pack is a **superset** of the
existing `RunReportData` (`api/routers/runs_report.py`). `summary.json`'s
verdict/segments/cost_sensitivity blocks are field-compatible with `RunReportData`;
the pack **adds** `scorecards.json`, `metrics.json`, `gate_results.json` and the
file-level manifest (with `sha256` for caching/lineage) that the endpoint aggregate
does not carry. See `compat` in the fixture for the exact differences (e.g. the
monthly-returns reconstructed business-day index is inherited).

---

## 6. Candidate pool & the state machine

`GET /research/candidates` → paginated list of `Candidate`. Each candidate carries
its `state`, latest evaluation summary, five-scorecard status, headline metrics,
`live_oos_recommendation`, and an **append-only** `decisions[]` trail. See
`candidate_pool.example.json` (5 candidates spanning every state).

### 6.1 Candidate states

| State | Meaning |
| :--- | :--- |
| `draft` | Asset created, no evaluation yet. |
| `triaged` | Evaluated + report exists, auto-labelled, no human decision yet. |
| `promising` | Human kept it — worth further research. |
| `weak` | Kept as a research asset; not deployable (near-miss / thin edge). |
| `negative` | Negative / failure control (kept as an avoidance rule). |
| `data_issue` | Data quality insufficient (e.g. empty series). |
| `live_oos_selected` | Human selected for live OOS → an item exists in the queue. |
| `live_oos_running` | Queue item is consuming paper replay / Paper-Watch berth. |
| `live_oos_done` | Observation window complete, awaiting re-evaluation. |
| `deploy_blocked` | Ran `deployment_strict`, blocked from capital. |
| `deployable` | Cleared `deployment_strict` (`TruthVerdict.REAL`). |
| `archived` | Terminal but still discoverable (never deleted). |

### 6.2 Transition diagram (text)

```
draft ──auto_label──▶ triaged
                        │
        ┌───────────────┼───────────────┬───────────────┐
     keep            keep            keep         mark_data_issue
        ▼               ▼               ▼               ▼
   promising         weak          negative        data_issue
        │               │
        │           select_live_oos (override_requires_reason when
        │               │            recommendation != eligible)
        └──────┬────────┘
               ▼
      live_oos_selected ──(queue consumes)──▶ live_oos_running
                                                    │
                                              (window closes)
                                                    ▼
                                             live_oos_done
                                                    │
                                          rerun deployment_strict
                                            ┌───────┴────────┐
                                            ▼                ▼
                                      deployable       deploy_blocked

any non-terminal ──archive──▶ archived ──unarchive──▶ triaged
```

### 6.3 CandidateDecision (append-only event)

`POST /research/candidates/{id}/decision` appends one immutable event (same
philosophy as `promotion_store` / `watch_registry` JSONL). Shape:

```jsonc
{
  "decision_id": "dec_0002",
  "candidate_id": "cand_inst_flow",
  "at": "2026-07-02T18:45:00+08:00",
  "actor": "operator",                 // "system" for auto_label / mark_data_issue
  "action": "keep",                    // auto_label|keep|archive|rerun|select_live_oos|mark_data_issue|unarchive|override_select
  "from_state": "triaged",
  "to_state": "weak",
  "reason": "…",                       // REQUIRED for archive / override_select / any non-eligible select_live_oos; else nullable
  "evaluation_ref": "eval_…",          // which evaluation this decision was made against
  "queue_ref": "loq_…"                 // present when action created a live-OOS queue item
}
```

**Override rule (research plan §8.4):** selecting a candidate whose
`live_oos_recommendation` is `not_recommended` or `blocked` requires
`action = override_select` + a non-empty `reason`. A missing reason is a
`422 VALIDATION_ERROR`; a `blocked` candidate without override authority is a
`409` (see §9).

---

## 7. LiveOOSQueueItem & its relationship to `watch_registry`

`GET /research/live-oos/queue` → list of `LiveOOSQueueItem`. See
`live_oos_queue.example.json`.

The queue is the **human-selection layer**; `watch_registry.py` is the **ADR-033
enforcement layer**. They are related by wrapping, not duplication:

- The **queue** holds *any* human-selected candidate awaiting/undergoing live OOS,
  carrying the selection audit (`candidate_id`, `selected_by`, `selection_reason`,
  `override`) that `watch_registry` does not model.
- The **watch_registry** enforces the narrower ADR-033 Paper-Watch berth: DSR ∈
  [0.90, 0.95), at most 2 berths, 90-day window, one-shot re-entry bar.

Mapping via `observation.kind`:

| `observation.kind` | `watch_registry_ref` | Backing module |
| :--- | :--- | :--- |
| `paper_watch_berth` | the strategy name (a real berth) | `watch_registry.status(strategy)` folds `enrolled_on` / `expiry_date` / `observed_trading_days` / `days_remaining` / `state` |
| `paper_replay` | `null` (not a DSR-band berth) | `workflows.paper_replay` triggered on selection; queue owns the lifecycle |
| `after_close` | `null` | `runtime.after_close` scheduler (consumes the queue instead of auto-running) |

So the queue **wraps and generalizes** `watch_registry`: a `paper_watch_berth`
item mirrors a berth 1:1 (state derived from the folded `WatchStatus`), while a
`paper_replay` item is a plain observation the registry never knew about. Queue
`state` values (`queued|running|paused|completed|expired|cancelled`) map onto the
registry's folded states (`active`→`running`, `paused`→`paused`, `expired`→`expired`,
`exited`→`completed`) plus two queue-only pre/terminal states (`queued`, `cancelled`).

`position_size` is always `0.0` for live-OOS items (zero-capital observation;
`evaluate_two_stage` never sizes a non-REAL verdict).

---

## 8. Non-goals honoured (spec §6)

- Does not rewrite the strategy runner contract (`strategies/protocol.py` untouched).
- Does not delete or modify the low-level workflows (`doe/go_gates/truth_gate/paper_replay`).
- Does not reposition or loosen the strict truth gate — `deployment_strict` **wraps** it; the ADR-025/030 thresholds are cited verbatim, not relaxed.
- No DB migration; JSONL/fixtures only.

---

## 9. Endpoint drafts

Paths, methods, request/response (envelope-wrapped), and error semantics. Shapes
follow the fixtures; error codes follow doc 25 §2 (#176 standardization).

### 9.1 Profiles

| Method | Path | Response `data` | Errors |
| :--- | :--- | :--- | :--- |
| `GET` | `/research/profiles` | `EvaluationProfile[]` (the four built-ins + user profiles) | — |
| `GET` | `/research/profiles/{name}` | `EvaluationProfile` | `404 {resource:"profile", id}` |

### 9.2 Evaluate (async job, doc 25 §5.2)

```
POST /research/evaluate
  req:  { "strategy": "inst_flow", "profile": "deployment_strict", "overrides": { ... } }
  resp: 202  ok({ "evaluation_id": "eval_…", "run_id": "…", "status": "queued" })
  errors:
    404 {resource:"strategy"|"profile", id}   unknown strategy or profile
    422 [{loc, msg}]                            bad overrides (re-validated at the boundary,
                                                like research/workflows/config.revalidate_with_overrides)
```

```
GET  /research/evaluate/{evaluation_id}/status
  resp: ok({ status: "queued|running|done|failed", progress?, error? })   // meta.ttl 2–5s
GET  /research/evaluations/{evaluation_id}
  resp: ok(EvaluationResult)                                              // meta.ttl 300
  errors: 404 {resource:"evaluation", id}
GET  /research/evaluations/{evaluation_id}/report
  resp: ok(ReportPackManifest)                                           // meta.ttl 300
  errors: 404 {resource:"evaluation", id}
```

### 9.3 Candidates

```
GET  /research/candidates?page=1&limit=50&state=&strategy=
  resp: ok(Candidate[], meta=page_meta + data_source:"ledger")            // see candidate_pool fixture
GET  /research/candidates/{candidate_id}
  resp: ok(Candidate)                                                     // includes full decisions[]
  errors: 404 {resource:"candidate", id}

POST /research/candidates/{candidate_id}/decision
  req:  { "action": "keep|archive|rerun|mark_data_issue|unarchive", "reason": "…", "profile": "…"? }
  resp: 201 ok(CandidateDecision)                                         // the appended event
  errors:
    404 {resource:"candidate", id}
    400 {hint}                     illegal transition for current state (state machine ValueError)
    422 [{loc, msg}]               archive without reason, unknown action

POST /research/candidates/{candidate_id}/select-live-oos
  req:  { "reason": "…"?, "override": false, "observation_kind": "paper_watch_berth|paper_replay" }
  resp: 201 ok(LiveOOSQueueItem)                                          // the created queue item
  errors:
    404 {resource:"candidate", id}
    409 {resource_id, state}        recommendation "blocked" without override authority,
                                    or Paper-Watch berth cap reached (watch_registry CabinFullError)
    422 [{loc, msg}]               recommendation != "eligible" and override reason missing
```

### 9.4 Live-OOS queue

```
GET  /research/live-oos/queue?page=1&limit=50&state=
  resp: ok(LiveOOSQueueItem[], meta=page_meta + data_source:"watch_registry")
```

Error-code source: `404 NOT_FOUND`, `400 BAD_REQUEST`, `409` (`IS_GATE_NOT_PASSED`
is the doc 25 §2 backstop for a gate/cap-blocked advance — reused here for
`select-live-oos` blocked/cap), `422 VALIDATION_ERROR`. All localhost-only, no
auth (ADR-031).

---

## 10. Module → contract-field mapping (Goal 2 hard requirement)

Every contract states which **current** backend module produces its fields.

### 10.1 EvaluationProfile → modules

| Profile field | Produced by |
| :--- | :--- |
| `wraps_primitives` | `research/workflows/{doe,go_gates,truth_gate,paper_replay}.py` + `single_run` = `strategies.protocol.get_strategy().run()` dispatch (ADR-028) |
| `metrics[].source_module` | declared per metric (see below) |
| `gates[].threshold` | the ADR-025 constants in `validation/two_stage_gate.py` (`PBO_MAX`, `WFA_OOS_POSITIVE_MIN`, `DSR_MIN`, `PAPER_WATCH_DSR_MIN`, `SLIPPAGE_SHARPE_MIN`, `OOS_HOLDOUT_SHARPE_MIN`) + `gate_state` criteria |
| `scorecards` | composed from `validation/metrics.py` + `validation/report.py` |

### 10.2 EvaluationResult → modules

| Result field | Produced by |
| :--- | :--- |
| `run_id` / `lineage.config_hash` | `research/run_config.py::RunConfig.run_id` (deterministic sha1 over strategy\|params\|engine\|stocks\|window) |
| `headline_metrics.{cagr,total_return,sharpe,sortino,calmar,max_drawdown,ulcer_index,volatility}` | `validation/metrics.py` (pure functions on `StrategyRun.returns`) |
| `headline_metrics.{trades,avg_holdings,avg_turnover,slippage_sharpe}` | `strategies/common/panel.py::panel_metrics` |
| `headline_metrics.{dsr,wfa_oos_positive_frac,oos_holdout_sharpe}` | `research/workflows/truth_gate.py::run_truth_gate` (+ `validation/dsr.py`, `validation/wfa.py`) |
| `verdict.truth_verdict` | `validation/two_stage_gate.py::evaluate_truth_gate` (`REAL/PAPER_WATCH/REJECTED/INCOMPLETE`) |
| `verdict.recommendation` | derived from `TruthGateResult` + gate severities (new orchestration, Goal 3) |
| `scorecards[]` | `validation/metrics.py` + `validation/report.py` + `panel_metrics`; per-metric `source_module` inlined |
| `checks[]` | `validation/two_stage_gate.py` (`TruthGateInput` → reasons) + `validation/gate_state.py::Criterion` |
| `sizing.position_size` | `validation/two_stage_gate.py::compute_position_size` |
| `report_pack_ref` | new report_pack writer (Goal 3) over `research/run_series_store.py` |

### 10.3 ReportPackManifest → modules

| File | Produced by |
| :--- | :--- |
| `summary.json` | new writer; verdict block field-compatible with `api/routers/runs_report.py::RunReportData` |
| `metrics.json` | `validation/metrics.py` + `panel_metrics` |
| `scorecards.json` | mirrors `EvaluationResult.scorecards` |
| `gate_results.json` | `validation/two_stage_gate.py` / `validation/gate_state.py` |
| `equity.parquet` / `trades.parquet` | `research/run_series_store.py` (equity/drawdown/trades sidecar) |
| `report.md` | new markdown writer (Goal 3); notebook variant already exists in `research/notebook_export.py` |
| `lineage.*` | `research/run_config.py` + `TruthGateConfig.parquet_dir` (`bundle_ref`) |

### 10.4 Candidate / CandidateDecision → modules

| Field | Produced by |
| :--- | :--- |
| `Candidate.*` projection | new `candidate_store.py` (Goal 4) — JSONL, mirrors `runs_store` philosophy; auto-label derived from `EvaluationResult.verdict` |
| `Candidate.decisions[]` | new append-only `candidate_decisions.jsonl` — same pattern as `promotion_store.py::record`/`audit` (append-only event log, folded state) |
| `Candidate.headline` / `scorecard_summary` | folded from the latest `EvaluationResult` |
| `Candidate.report_pack_ref` | `ReportPackManifest.root_dir` |

### 10.5 LiveOOSQueueItem → modules

| Field | Produced by |
| :--- | :--- |
| `observation` (berth: `enrolled_on`/`expiry_date`/`observed_trading_days`/`days_remaining`/`state`) | `research/watch_registry.py::status` folded `WatchStatus` (event-sourced JSONL) |
| `observation.kind = paper_replay` | `research/workflows/paper_replay.py` triggered on selection |
| `dsr_band` | `validation/report.py::dsr_band` / `two_stage_gate._classify_dsr` |
| `selection_reason` / `override` / `selected_by` | new queue store (Goal 10) — the human-selection audit `watch_registry` does not model |
| `position_size` | always `0.0` (`evaluate_two_stage` sizes only REAL) |

---

## 11. `not_available` register (rule #6)

12 field families are marked `not_available` in the fixtures, each with a reason:

| # | Field | Reason (missing capability) |
| :-: | :--- | :--- |
| 1 | `profitability.alpha` | no benchmark return series joined in the run/series stores |
| 2 | `profitability.beta` | same benchmark gap |
| 3 | `profitability.max_holdings` | `panel_metrics` tracks `avg_holdings` only |
| 4 | `risk.var_95` | VaR not implemented in `validation/metrics.py` |
| 5 | `risk.cvar_95` | CVaR not implemented in `validation/metrics.py` |
| 6 | `risk_adjusted.profit_factor` | panel `trades` is a rebalance count, no per-trade `pnl` |
| 7 | `risk_adjusted.tail_ratio` | not implemented in `validation/metrics.py` |
| 8 | `win_rate.*` (6 metrics) | trades schema lacks per-trade pnl/entry/exit/excursion — **P1 blocker** |
| 9 | `liquidity.volume_bucket_distribution` | no per-trade notional + per-bar ADV join |
| 10 | `liquidity.safe_trade_fraction` | no per-trade notional vs ADV cap |
| 11 | `liquidity.capacity_proxy` | no ADV + position-size join |
| 12 | `lineage.git_sha` | run ledger carries no source-tree SHA today (`run_id` is a config hash) |

The **Win-Rate trade schema** (#6, #8, and the MAE/MFE excursion metrics) is the
single most impactful gap: adding per-trade `{pnl, entry_price, exit_price,
hold_days, mae, mfe, notional}` to the trades sidecar unblocks the whole Win-Rate
card, `profit_factor`, and most Liquidity metrics at once.

---

## 12. Self-validation

```bash
# 1. every fixture is legal JSON
cd dev_docs/contracts
for f in *.json; do python3 -m json.tool "$f" >/dev/null && echo "OK $f"; done

# 2. the schema is valid draft-07 and its four built-in profiles validate
python3 - <<'PY'
import json
from jsonschema import Draft7Validator
s = json.load(open("evaluation_profile.schema.json"))
Draft7Validator.check_schema(s)
v = Draft7Validator(s)
for ex in s["examples"]:
    assert not list(v.iter_errors(ex)), ex["name"]
    print("OK", ex["name"])
PY
```

Both pass as of 2026-07-03 (`jsonschema` 4.26.0).
