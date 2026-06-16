# Strategy Dispatch & Contract — Design Spec (Sub-project ①)

> **Status:** Draft for review · **Date:** 2026-06-16 · **Author:** Sunny + Claude
> **Workflow:** sunnydata-design Phase 1 (Brainstorm) output

**Goal:** Make every strategy a first-class, self-describing citizen the platform can
dispatch *by name with arbitrary params* — so an AI-authored strategy module that
follows one contract can be validated, run, and reported on without touching the
engine, gate, or CLI. This is the foundation that later enables the MLflow-style
"write code → register → backtest → view in UI" loop.

---

## 1. Context & Motivation

The platform already has the spine of an MLflow-shaped system:

| MLflow concept | Existing piece | Status |
| :--- | :--- | :--- |
| You write model code (a flavor) | `strategies/<name>/` + `StrategyRun` contract (ADR-027) | ✅ |
| `log_metric` / `log_model` | `StrategyRun.metrics` + `append_run()` | ✅ |
| Tracking store | `reports/runs.jsonl` + TimescaleDB `runs` table | ✅ |
| Tracking UI | React `frontend/` (RunsTable / RunReport) | ✅ |
| Model registry + promotion | `@register_strategy` + gate + `PromotePage` | ✅ |
| **`mlflow.run(model_name)` dispatch** | `_run_is_core` hardwired to `FourLayerRunner` | ❌ |
| **model signature / schema** | Config is Pydantic but schema not exposed | ❌ |
| **artifact conformance check** | only four_layer-specific tests | ❌ |

This sub-project closes the three ❌ rows. It is **sub-project ① of three**:

- **① (this spec)** — dispatch + self-describing contract + conformance gate (Python core + HTTP contract surface).
- **②** — dynamic DB-backed registry + sandboxed runtime loading of AI-authored modules. *Depends on ①'s conformance gate as its load-time safety gate.*
- **③** — React frontend wiring (strategy picker, schema-driven param form) + the markdown→strategy authoring skill.

The conformance gate built here (§5) is intentionally the same checker ② will reuse
before trusting a dynamically-loaded module — that is why ① must land first.

---

## 2. Scope

### In scope (①)
1. Replace the `preset` run-contract with `strategy` + `params` (方案 1).
2. Add a `config_model` attribute to the strategy contract so dispatch can validate params and expose schema.
3. A generic **conformance gate** (`check_strategy`) + pytest (over the whole registry) + `validate-strategy` CLI.
4. HTTP contract surface: `POST /runs` accepts `strategy`+`params`; new `GET /strategies` exposes name/title/description/JSON-schema.
5. **Full removal of `preset`** across the Python core + HTTP layer (no back-compat — decision Y).
6. **Relocate four_layer's `StrategyConfig`** from `config/strategy_config.py` into `strategies/four_layer_resonance/` and repoint all importers — de-privileging four_layer so its config lives with it like momentum/inst_flow.

### Out of scope (deferred)
- **②** dynamic registry, code-string loading, subprocess sandbox.
- **③** React frontend changes + markdown→strategy authoring skill. The existing
  frontend's preset pages **will break** until ③ rewires them — accepted (decision Y).
- Named/saved parameter presets as a *feature* (the old `PRESETS` bundles are removed; if "saved configs per strategy" is wanted later, it returns as a ③/UI concern, not a core run-contract field).
- Zipline-engine config decoupling beyond the mechanical import-path move.

---

## 3. Locked Design Decisions

| # | Decision | Rationale |
| :--- | :--- | :--- |
| D1 | Run carries `strategy: str` + `params: dict`; params validated at dispatch against the strategy's own `config_model` | AI-friendly (`{"strategy": x, "params": {...}}`); keeps `RunConfig` decoupled from concrete strategy configs (no upward import — ADR-027); validation still strict via `frozen`+`extra="forbid"`. |
| D2 | `StrategyRunner` Protocol gains `config_model: ClassVar[type[BaseModel]]` (+ optional `title`) | One place to resolve name→Config for validation, schema (`GET /strategies`), and conformance default-config. |
| D3 | Conformance gate validates any registered strategy on synthetic data | Same checker is ②'s load-time safety gate. Required keys = the gate's universal edge set. |
| D4 | `POST /runs` dispatches by `strategy`; `GET /strategies` exposes schema | ① must be end-to-end demonstrable via curl/Postman; React is just a consumer (③). |
| D5 | `preset` fully removed (no back-compat) | four_layer is just a citizen; `preset` was a pre-contract privileged path. Mixed-state deprecated aliases rejected. |
| D6 | four_layer `StrategyConfig` relocated into its strategy folder | The central-config coupling is the disease; relocate now rather than defer. Pure import-path migration, no logic change. |

---

## 4. Architecture & Components

Each unit below states **what it does / its interface / its dependencies**.

### 4.1 `RunConfig` (new shape) — `research/run_config.py`
- **Does:** Value object for one IS run, now keyed on strategy name + free-form params.
- **Interface (target):**
  ```python
  class RunConfig(BaseModel):
      model_config = {"frozen": True, "extra": "forbid"}
      hypothesis: str = Field(..., min_length=1)
      strategy:   str = Field(...)                              # registered strategy name
      params:     dict[str, Any] = Field(default_factory=dict)  # validated at dispatch
      stocks:     tuple[str, ...] = Field(..., min_length=1)
      is_start:   date
      is_end:     date
      engine:     str = "sim"                                   # sim | zipline

      @property
      def run_id(self) -> str:
          key = "|".join([
              self.strategy,
              json.dumps(self.params, sort_keys=True, default=str),
              self.engine, ",".join(self.stocks),
              self.is_start.isoformat(), self.is_end.isoformat(),
          ])
          return hashlib.sha1(key.encode()).hexdigest()[:12]
  ```
- **Deps:** none on `strategies` (stays a dumb data holder — strategy-name + params validity is enforced at dispatch, §4.4, to preserve layering). Removes `from ...config.strategy_config import PRESETS` and the `_preset_known` validator.

### 4.2 Strategy contract additions — `strategies/protocol.py`
- **Does:** Extends the existing `StrategyRunner` Protocol so each runner declares its Config type and a human label.
- **Interface (target additions):**
  ```python
  @runtime_checkable
  class StrategyRunner(Protocol):
      config_model: ClassVar[type[BaseModel]]   # NEW — the strategy's own config class
      title: ClassVar[str]                       # NEW — short human label (optional default = name)
      def run(self, symbols, start, end, config, loader) -> StrategyRun: ...
  ```
- Each `runner.py` adds e.g. `config_model = MomentumConfig` (momentum), `InstFlowConfig` (inst_flow), `StrategyConfig` (four_layer), `TemplateConfig` (template).
- **Deps:** unchanged registry (`_REGISTRY`, `register_strategy`, `get_strategy`, `list_strategies`).

### 4.3 Registry description — `strategies/protocol.py`
- **Does:** Turns the registry into a self-describing catalog for the API and conformance.
- **Interface (target):**
  ```python
  @dataclass(frozen=True)
  class StrategyInfo:
      name: str
      title: str
      description: str          # from runner class docstring
      config_schema: dict       # config_model.model_json_schema()

  def describe_strategies() -> list[StrategyInfo]: ...
  def describe_strategy(name: str) -> StrategyInfo: ...
  ```
- **Deps:** `get_strategy`, `list_strategies`.

### 4.4 Dispatch — `research/is_harness.py`
- **Does:** Resolve strategy by name, validate params → config, run.
- **Interface (target `_run_is_core`):**
  ```python
  def _run_is_core(cfg, loader=load_merged_parquet):
      runner = get_strategy(cfg.strategy)          # raises ValueError on unknown
      sconf  = runner.config_model(**cfg.params)   # raises ValidationError on bad params
      run    = runner.run(list(cfg.stocks), cfg.is_start, cfg.is_end, sconf, loader)
      return run.metrics, run.returns, run.trades
  ```
- Removes the `get_preset(cfg.preset)` + hardwired `FourLayerRunner()` lines.
- **Deps:** `strategies.protocol` (registry). Must ensure all runners are imported/registered first (via the existing `research/runners.py` aggregator import).

### 4.5 Conformance gate — `strategies/conformance.py` (new)
- **Does:** Proves any registered strategy satisfies the contract on synthetic data — used by CI (§7) and reused as ②'s load-time gate.
- **Interface (target):**
  ```python
  REQUIRED_METRIC_KEYS: frozenset[str] = frozenset(
      {"cagr", "sharpe", "slippage_sharpe", "maxdd", "trades", "bars"}
  )

  @dataclass(frozen=True)
  class ConformanceReport:
      name: str
      ok: bool
      errors: list[str]

  def synthetic_loader(n_bars: int = 400, seed: int = 0) -> Loader:
      """A Loader returning a merged frame with every canonical column:
      trade_date, stock_id, open/high/low/close/volume, adj_factor,
      foreign_buy/trust_buy/dealer_buy, top_broker_buy/key_broker_buy/
      gov_broker_buy/geo_broker_buy/day_trade_volume/margin_offset_volume."""

  def check_strategy(name: str, *, n_symbols: int = 6, n_bars: int = 400) -> ConformanceReport:
      """Resolve → build default config → run on synthetic_loader → assert:
      returns a StrategyRun; metrics is a dict ⊇ REQUIRED_METRIC_KEYS;
      returns is a pd.Series; trades is a list; no exception."""
  ```
- **Required-keys rationale:** the gate's *edge* criteria (`cagr`, `sharpe`,
  `slippage_sharpe`) are shared by every gate variant (`DEFAULT_GATE`,
  `MOMENTUM_GATE`), plus `maxdd`/`trades`/`bars` for the run record. The *health*
  keys differ per strategy family (`struct1_pct`/`churn_pct`/`avg_hold` vs
  `avg_holdings`) so they are **not** required by conformance.
- **Deps:** `strategies.protocol`, the canonical merged schema (data contract doc 21).

### 4.6 CLI — `research/cli.py`
- **Does:** `validate-strategy <name>` runs `check_strategy` and prints the report (exit non-zero on failure) so an author/AI can self-check one strategy. `run-is` switches `--preset` → `--strategy` + `--params` (JSON).
- **Deps:** `strategies.conformance`, `research.run_config`.

### 4.7 HTTP surface — `api/`
- **`RunCreateRequest`** (`api/schemas.py`): replace `preset: str` with `strategy: str` + `params: dict = {}`.
- **`POST /runs` / `/runs/async`** (`api/routers/runs.py`): build the new `RunConfig`; dispatch unchanged downstream.
- **`GET /strategies`** (new `api/routers/strategies.py`): `Envelope[list[StrategyInfo]]` from `describe_strategies()`.
- **Remove** `api/routers/presets.py` (`GET /presets`) and its registration in `app.py`; repoint any FE-facing needs to `GET /strategies` (FE itself is ③).
- **Deps:** existing envelope/deps wiring.

---

## 5. Data Flow

```
POST /runs {hypothesis, strategy, params, stocks, is_start, is_end, engine}
   → RunCreateRequest → RunConfig (run_id = hash of the above)
      → run_and_judge_persist(cfg)
         → _run_is_core: get_strategy(strategy) → config_model(**params) → runner.run(...)
            → StrategyRun{metrics, returns, trades}
         → evaluate_gate(metrics) → gate_status/summary
         → persist: runs.jsonl + TimescaleDB runs/equity_snapshots
   → Envelope[RunRecord]  (run_id, metrics, gate_status, ...)

GET /strategies → describe_strategies() → [{name, title, description, config_schema}]
```

---

## 6. Error Handling

| Failure | Where | Behavior |
| :--- | :--- | :--- |
| Unknown strategy name | `get_strategy` (dispatch) | `ValueError` → API 400 with `choose from [...]`. |
| Invalid params (typo/range) | `config_model(**params)` | Pydantic `ValidationError` → API 422, field-level detail. |
| Strategy violates contract | `check_strategy` (CI/load-time) | `ConformanceReport.ok = False`, errors listed; CI red; ②'s loader refuses to register. |
| Empty/zero-data window | runner returns `StrategyRun({"trades":0,"bars":0})` | run completes, gate marks INCOMPLETE (unchanged). |

No silent swallowing — surface at the boundary with actionable messages (project error-handling rule).

---

## 7. Testing Strategy (TDD, 80%+)

1. **Conformance (the headline test):** a pytest parametrized over `list_strategies()` calling `check_strategy(name)` — every built-in strategy must conform. New strategies are covered automatically.
2. **Dispatch unit:** `_run_is_core` resolves a named strategy, validates params, rejects unknown name + bad params.
3. **RunConfig:** `run_id` determinism over (strategy, params, window); `extra="forbid"`; window-order validator.
4. **describe_strategies:** returns one entry per registered strategy with a non-empty `config_schema`.
5. **API:** `POST /runs` with `strategy`+`params` (happy path + unknown strategy 400 + bad params 422); `GET /strategies` shape.
6. **Equivalence guard:** a four_layer run via `strategy="four_layer", params={...}` reproduces the legacy four_layer metrics (locks the relocation + dispatch change against regression).

---

## 8. Blast Radius & Migration

### 8.1 `preset` removal (decision Y) — Python core + HTTP (≈ src files)
`api/{app,response_models,schemas}.py`, `api/routers/{home,presets,research,research_registry,runs}.py`,
`config/strategy_config.py` (drop `PRESETS`/`get_preset`), `data/db_writer.py` (runs record: `preset` column → `strategy`+`params`),
`engines/protocol.py`, `engines/zipline_adapter/{algorithms/four_layer_resonance,cli}.py`,
`research/{cli,is_harness,run_config,run_tags_store,saved_views_store,sweep}.py`,
`strategies/{protocol, four_layer_resonance/sim}.py`. Plus **17 test files**.
Frontend (5 files) is **③, out of scope** and will break until then.

### 8.2 `StrategyConfig` relocation (decision D6) — 27 importers
Move `config/strategy_config.py::StrategyConfig` → `strategies/four_layer_resonance/config.py`, update imports in:
`adapters/brokers/paper_broker.py`, `api/{response_models,schemas}.py`, `config/__init__.py`,
`engines/protocol.py`, `engines/zipline_adapter/{algorithms/four_layer_resonance,cli,controls/taiwan_stock_rules,validation/*}`,
`pipeline.py`, `research/{cli,is_harness,run_config,sweep}.py`, `strategies/{protocol, momentum/strategy, four_layer_resonance/*}`.
Pure import-path change, no logic edits.

### 8.3 Doc sync (project `code-doc-sync.md` triggers)
- ADR: new **ADR-028 strategy-dispatch-contract** (records D1–D6; supersedes the preset/`get_preset` path).
- Doc 06 (API design): `POST /runs` body change, new `GET /strategies`, removed `GET /presets`.
- Doc 21 (data contract): `runs` record `preset`→`strategy`+`params`.
- Doc 16 WBS: progress entry for sub-project ①.

---

## 9. Open Questions / Risks (resolve in Phase 2 plan)

1. **`momentum/strategy.py` imports `StrategyConfig`** — why? (shared slippage constant? base?) Confirm the relocation doesn't create a strategy→strategy coupling; if it's only a constant, lift it to `strategies/common`.
2. **`db_writer` runs schema** — changing `preset`→`strategy`/`params` (JSONB) touches DDL + upsert + any reader. Confirm no migration of existing rows is required (single-operator, reports are reproducible).
3. **Zipline engine coupling** — `engines/zipline_adapter` consumes `StrategyConfig` directly. The relocation is mechanical, but verify the zipline four_layer algorithm still imports cleanly.
4. **Registration ordering** — dispatch validating a strategy name requires all runners imported first; confirm `research/runners.py` is the single import that guarantees registration, and that the API imports it at startup.

---

## 10. Success Criteria

- A new strategy authored by copying `_template/` (config + backtest + runner, `config_model` declared) is: (a) auto-covered by the conformance pytest, (b) runnable via `POST /runs {strategy, params}` and `validate-strategy`, (c) self-described by `GET /strategies` with a usable JSON-schema.
- four_layer runs through the identical path as any other strategy; no `preset`/`get_preset`/`PRESETS` remain in the Python core or HTTP layer.
- All tests green; coverage ≥ 80% on changed modules.
