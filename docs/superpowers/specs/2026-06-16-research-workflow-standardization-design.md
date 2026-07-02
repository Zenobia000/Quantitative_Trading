# Research Workflow Standardization — Design Spec (Sub-project ①.5)

> **Status:** Shipped (ADR-029) · **Date:** 2026-06-16 · **Author:** Sunny + Claude
> **Workflow:** sunnydata-design Phase 1 (Brainstorm) output

**Goal:** Turn the seven one-off `scripts/inst_flow_*.py` research scripts into a
standardized platform service: generic workflows in `research/workflows/`, per-strategy
research configuration in `strategies/<name>/research_config.py`, accessible via CLI
and HTTP API — so adding a new strategy requires zero additional scripts and all
research workflows go through the ADR-028 dispatch layer.

**Positions in the sub-project sequence:**
- ① Strategy dispatch contract (ADR-028) — DONE (PR #132)
- **①.5 Research workflow standardization — this spec**
- ② Dynamic DB registry + sandbox
- ③ React frontend + authoring skill

---

## 1. Context & Motivation

### Current pain

`backtest_platform/scripts/` contains 7 files, all named `inst_flow_*.py`:

| Script | What it does | Problem |
| :--- | :--- | :--- |
| `inst_flow_doe.py` | Parameter grid scan (DOE first read) | Calls `backtest_inst_flow()` directly, bypasses dispatch |
| `inst_flow_go_gates.py` | WFA + PBO over wide universe | Hardwired to inst_flow, `get_preset`/`DEFAULT_CONFIG` (broken post ADR-028) |
| `inst_flow_survivorship.py` | WFA + PBO with delisted stocks | Same |
| `inst_flow_truth_gate.py` | ADR-025 two-stage gate | Same |
| `inst_flow_revalidate_finlab.py` | FinLab re-validation | Same |
| `inst_flow_paper_replay.py` | Paper replay (single session) | Same |
| `inst_flow_daemon_replay.py` | Multi-session daemon replay | Same |

**Root cause:** Each script is both a workflow definition AND a strategy-specific runner.
Adding `multi_factor` would require copying all 7 scripts and editing each.
Post ADR-028 they are all broken (`get_preset`/`DEFAULT_CONFIG` removed).

### Target state

```
研究工作流 = 平台通用邏輯(research/workflows/) + 策略宣告配置(strategies/<name>/research_config.py)
```

Any registered strategy can run DOE / GO gates / truth gate / paper replay by:
1. Declaring `research_config.py` in its folder.
2. Calling `research.cli doe --strategy <name>` or `POST /research/workflows/doe`.

Zero per-strategy workflow code needed.

---

## 2. Scope

### In scope (①.5)
1. `research/workflows/` package: `config.py` + `doe.py` + `go_gates.py` + `truth_gate.py` + `paper_replay.py` + `loader.py`.
2. Per-strategy `research_config.py` in: `strategies/inst_flow/`, `strategies/momentum/`, `strategies/_template/`.
3. CLI extensions in `research/cli.py`: `doe`, `go-gates`, `truth-gate`, `paper-replay` commands.
4. New HTTP router `api/routers/research_workflows.py`: `POST /research/workflows/{workflow}` + `GET /research/workflows/{strategy}`.
5. **Delete** `backtest_platform/scripts/` (all 7 files).
6. Doc sync: `08_project_structure_guide.md`, ADR-029, `16_wbs.md`, `06_api_design_specification.md`.

### Out of scope (deferred)
- `inst_flow_revalidate_finlab.py` logic (FinLab survivorship universe building is complex; handled separately).
- `inst_flow_daemon_replay.py` forward live scheduling (needs real calendar time, belongs to 8.H.8).
- Frontend UI triggering research workflows (sub-project ③).
- WFA and PBO implementations (already exist in `validation/`; workflows just call them).

---

## 3. Architecture

### 3.1 `research/workflows/config.py` — Pydantic models (the declaration contract)

```python
@dataclass  # or Pydantic BaseModel frozen=True
class DOEConfig:
    strategy: str
    grid: dict[str, list]          # param name → list of values to try
    symbols: list[str]             # universe for this DOE run
    is_start: date
    is_end: date
    hypothesis_prefix: str = "DOE" # prepended to auto-generated hypothesis

class GOGatesConfig:
    strategy: str
    fixed_config: BaseModel        # the single pre-registered config to test
    symbols: list[str]             # wide universe (incl. delisted)
    is_start: date
    is_end: date
    n_wfa_folds: int = 5
    pbo_n_iter: int = 1000

class TruthGateConfig:
    strategy: str
    fixed_config: BaseModel        # pre-registered, never re-selected
    symbols: list[str]
    is_start: date                 # full span start (includes OOS)
    oos_start: date                # OOS boundary
    is_end: date
    n_trials: int                  # landscape size for DSR deflation
    pre_registered: bool = True
    slippage_stress: float = 0.003

class PaperReplayConfig:
    strategy: str
    fixed_config: BaseModel
    symbols: list[str]
    as_of: date                    # single rebalance as-of date
    initial_cash: float = 10_000_000.0
    run_id_prefix: str = "paper_replay"
```

### 3.2 `strategies/<name>/research_config.py` — Per-strategy declaration

Each strategy declares its own instances of the above models.
The platform reads them via `loader.load_research_config(strategy_name)`.

Example (`strategies/inst_flow/research_config.py`):
```python
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig
from backtest_platform.research.workflows.config import DOEConfig, GOGatesConfig, TruthGateConfig, PaperReplayConfig

SYMBOLS_WIDE = ['2330','2317','2454', ...40 names..., *DELISTED]

DOE = DOEConfig(
    strategy="inst_flow",
    grid={
        "rebalance":         ["monthly", "quarterly"],
        "lookback_days":     [20, 60],
        "flow_source":       ["foreign", "foreign_trust"],
        "vol_target_annual": [None, 0.15],
    },
    symbols=list(DEFAULT_UNIVERSE),
    is_start=date(2016, 1, 1),
    is_end=date(2020, 12, 31),
)

GO_GATES = GOGatesConfig(
    strategy="inst_flow",
    fixed_config=InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign"),
    symbols=SYMBOLS_WIDE,
    is_start=date(2015, 1, 1),
    is_end=date(2024, 12, 31),
)

TRUTH_GATE = TruthGateConfig(
    strategy="inst_flow",
    fixed_config=InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign"),
    symbols=SYMBOLS_WIDE,
    is_start=date(2015, 1, 1),
    oos_start=date(2021, 1, 1),
    is_end=date(2024, 12, 31),
    n_trials=24,
    slippage_stress=0.003,
)

PAPER_REPLAY = PaperReplayConfig(
    strategy="inst_flow",
    fixed_config=InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign"),
    symbols=list(DEFAULT_UNIVERSE),
    as_of=date(2023, 1, 3),
    initial_cash=10_000_000.0,
)
```

### 3.3 `research/workflows/loader.py`

```python
def load_research_config(strategy_name: str):
    """Dynamically import strategies/<name>/research_config.py."""
    module_path = f"backtest_platform.strategies.{strategy_name}.research_config"
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError:
        raise ValueError(
            f"strategy {strategy_name!r} has no research_config.py — "
            f"copy from strategies/_template/research_config.py"
        )

def get_doe_config(strategy_name: str) -> DOEConfig:
    return load_research_config(strategy_name).DOE

def get_go_gates_config(strategy_name: str) -> GOGatesConfig:
    return load_research_config(strategy_name).GO_GATES

def get_truth_gate_config(strategy_name: str) -> TruthGateConfig:
    return load_research_config(strategy_name).TRUTH_GATE

def get_paper_replay_config(strategy_name: str) -> PaperReplayConfig:
    return load_research_config(strategy_name).PAPER_REPLAY
```

### 3.4 `research/workflows/{workflow}.py` — Generic implementations

All call `get_strategy(cfg.strategy).run(...)` — never call backtest functions directly.

```
doe.py         → run_doe(cfg: DOEConfig, loader=...) → DOEResult
go_gates.py    → run_go_gates(cfg: GOGatesConfig, loader=...) → GOGatesResult
truth_gate.py  → run_truth_gate(cfg: TruthGateConfig, loader=...) → TruthGateResult
paper_replay.py→ run_paper_replay(cfg: PaperReplayConfig) → PaperReplayResult
```

Result dataclasses (all frozen, serializable):
```python
@dataclass(frozen=True)
class DOEResult:
    strategy: str
    runs: list[dict]        # [{param_k: v, ..., cagr: x, sharpe: y, ...}]
    n_configs: int
    is_start: date
    is_end: date

@dataclass(frozen=True)
class GOGatesResult:
    strategy: str
    wfa_oos_positive_frac: float
    pbo: float
    verdict: str            # "PASS" | "FAIL"
    details: dict

@dataclass(frozen=True)
class TruthGateResult:
    strategy: str
    verdict: str            # "REAL" | "REJECTED"
    dsr: float
    slippage_sharpe: float
    wfa_oos_positive_frac: float
    details: dict

@dataclass(frozen=True)
class PaperReplayResult:
    strategy: str
    run_id: str
    gate_status: str
    metrics: dict
```

### 3.5 CLI — Extensions to `research/cli.py`

```bash
uv run python -m backtest_platform.research.cli doe --strategy inst_flow
uv run python -m backtest_platform.research.cli doe --strategy inst_flow \
    --is-start 2018-01-01 --is-end 2022-12-31   # override subset

uv run python -m backtest_platform.research.cli go-gates   --strategy inst_flow
uv run python -m backtest_platform.research.cli truth-gate --strategy inst_flow
uv run python -m backtest_platform.research.cli paper-replay --strategy inst_flow
```

Each command:
1. `load_research_config(strategy)` → get the relevant `*Config`
2. Apply any CLI overrides (date range, symbols)
3. Call `run_*(cfg)` from `research/workflows/`
4. Print result + optionally write to runs ledger / CSV

### 3.6 HTTP API — `api/routers/research_workflows.py`

```
POST /research/workflows/doe           { strategy, overrides? }  → 202 {job_id}
POST /research/workflows/go-gates      { strategy, overrides? }  → 202 {job_id}
POST /research/workflows/truth-gate    { strategy, overrides? }  → 202 {job_id}
POST /research/workflows/paper-replay  { strategy, overrides? }  → 202 {job_id}

GET  /research/workflows/{strategy}    → list available configs (which workflows declared)
```

All heavy workflows go async (reuse 8.H.6 `jobs/` infrastructure).
Poll `GET /runs/{job_id}/log` for result.

### 3.7 Dispatch call chain (invariant)

```
CLI doe --strategy inst_flow
  OR POST /research/workflows/doe {"strategy": "inst_flow"}
    → load_research_config("inst_flow").DOE          # load declaration
    → run_doe(DOEConfig)
       → for params in expand_grid(cfg.grid):
           runner = get_strategy(cfg.strategy)        # ADR-028 registry
           sconf  = runner.config_model(**params)     # validated config
           run    = runner.run(symbols, start, end, sconf, loader)
           # collect run.metrics
    → DOEResult → ledger / HTTP response
```

---

## 4. Data Flow & Error Handling

| Failure | Where | Behavior |
| :--- | :--- | :--- |
| Strategy has no `research_config.py` | `loader.load_research_config` | `ValueError` → CLI error / API 400 |
| `research_config.py` missing a constant (e.g. `DOE`) | `loader.get_doe_config` | `AttributeError` → clear error message with template path |
| Unknown strategy name | `get_strategy` (inside workflow) | `ValueError` → CLI error / API 400 |
| Invalid param override | `runner.config_model(**params)` | `ValidationError` → CLI error / API 422 |
| Workflow takes too long | jobs/ infrastructure | Timeout → job status `failed` with error |

---

## 5. New Directory Structure (after ①.5)

```
backtest_platform/src/backtest_platform/
  research/
    workflows/            ← NEW
      __init__.py
      config.py           ← workflow config models
      loader.py           ← load_research_config()
      doe.py              ← run_doe()
      go_gates.py         ← run_go_gates()
      truth_gate.py       ← run_truth_gate()
      paper_replay.py     ← run_paper_replay()
    cli.py                ← EXTEND: add 4 new commands
    ...existing modules...

  strategies/
    _template/
      research_config.py  ← NEW (skeleton all-None/example, AI copies this)
    inst_flow/
      research_config.py  ← NEW (migrated from scripts/)
    momentum/
      research_config.py  ← NEW (basic DOE declaration)
    four_layer_resonance/
      research_config.py  ← NEW (optional, minimal skeleton)

  api/routers/
    research_workflows.py ← NEW: POST /research/workflows/*

backtest_platform/scripts/  ← DELETED (all 7 files removed)
```

---

## 6. Testing Strategy

1. **`research_config.py` loading:** `load_research_config("inst_flow")` returns module with `DOE`/`GO_GATES`/`TRUTH_GATE`/`PAPER_REPLAY`; unknown strategy raises `ValueError`; missing constant raises `AttributeError` with clear message.
2. **Workflow unit tests (synthetic data):** `run_doe(doe_cfg, loader=synthetic_loader)` returns `DOEResult` with `n_configs == len(expand_grid(grid))` rows; each row has required metric keys.
3. **CLI integration:** `CliRunner.invoke(cli, ["doe", "--strategy", "momentum"])` exits 0 and prints a result.
4. **API shape:** `POST /research/workflows/doe` returns 202 with `job_id`; `GET /research/workflows/inst_flow` lists declared workflows.
5. **Dispatch invariant:** `run_doe` never imports `backtest_inst_flow` or `backtest_momentum` directly — verified by `grep` in CI.

---

## 7. Doc Sync (code-doc-sync.md triggers)

| Trigger | Docs to update |
| :--- | :--- |
| New `research/workflows/` package | `08_project_structure_guide.md` §backend structure |
| New CLI commands | `06_api_design_specification.md` §CLI table |
| New API endpoints | `06_api_design_specification.md` §HTTP routes; `25_fe_be_rest_contract.md` |
| Delete `scripts/` | `08_project_structure_guide.md` (remove scripts/ section) |
| New ADR-029 | ADR index |
| Milestone | `16_wbs.md` |

---

## 8. Success Criteria

- `backtest_platform/scripts/` directory does not exist.
- `uv run python -m backtest_platform.research.cli doe --strategy inst_flow` runs end-to-end on real parquet data and prints a DOE result table.
- `uv run python -m backtest_platform.research.cli doe --strategy momentum` runs (demonstrates strategy-agnostic generic workflow).
- `POST /research/workflows/doe {"strategy": "inst_flow"}` → 202 job queued.
- `GET /research/workflows/inst_flow` → lists `["doe", "go_gates", "truth_gate", "paper_replay"]`.
- Adding a new strategy requires ONLY `strategies/<name>/research_config.py` to participate in all workflows — zero new script files.
- All existing 987 tests remain green.

---

## 9. Open Questions (resolve in Phase 2 plan)

1. **`overrides` schema in HTTP body** — allow partial override of any `*Config` field? Or only date range + symbols? Keep minimal (date + symbols only) to avoid re-creating the preset problem.
2. **`four_layer_resonance/research_config.py`** — four_layer was deemed value-destructive (ADR-023). Should it have a research_config at all, or only `_template` as skeleton? Recommendation: include minimal skeleton for completeness (it's a registered strategy), but `GO_GATES`/`TRUTH_GATE` may document the known verdict.
3. **DOE result persistence** — write to `reports/runs.jsonl` (same as `run-is`) or a separate `reports/doe_results/` CSV? Recommendation: CSV per DOE run (same as existing `sweep` command output), plus optional append to runs ledger.
4. **`run_truth_gate` WFA integration** — the existing `validation/wfa.py` and `validation/two_stage_gate.py` need to be called. Verify they accept `loader: Callable` (not hardwired to parquet) before Phase 2 plan.
