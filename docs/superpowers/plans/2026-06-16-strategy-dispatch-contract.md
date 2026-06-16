# Strategy Dispatch & Contract — Implementation Plan (Sub-project ①)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> or the Execute Plan phase of superpowers:sunnydata-design to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `preset`-hardwired dispatch with `strategy`+`params`, add
`config_model` self-description to every runner, build a generic conformance gate,
and expose `GET /strategies` + updated `POST /runs` — so any AI-authored strategy
module that follows the contract can be validated, run, and reported on.

**Architecture:** Spec §4 (four-layer components: RunConfig → _run_is_core dispatch
→ conformance gate → HTTP surface). Preset fully removed (decision Y).
four_layer StrategyConfig relocated from `config/` into its strategy folder (D6).

**Tech Stack:** Python 3.10+, Pydantic v2, FastAPI, pytest, existing registry
(`strategies/protocol.py`).

**Worktree:** All work happens in `../Quantitative_Trading--strategy-dispatch/`
(branch `feat/strategy-dispatch-contract`). Do NOT touch the main worktree.

---

## File Structure Map

| Action | Path |
| :--- | :--- |
| **Move** | `config/strategy_config.py` → `strategies/four_layer_resonance/config.py` |
| **Modify** | `strategies/protocol.py` — add `config_model`, `StrategyInfo`, `describe_strategies` |
| **Modify** | `strategies/_template/runner.py` — add `config_model = TemplateConfig` |
| **Modify** | `strategies/momentum/runner.py` — add `config_model = MomentumConfig` |
| **Modify** | `strategies/inst_flow/runner.py` — add `config_model = InstFlowConfig` |
| **Modify** | `strategies/four_layer_resonance/runner.py` — add `config_model = StrategyConfig` |
| **Create** | `strategies/conformance.py` — `synthetic_loader`, `check_strategy`, `ConformanceReport` |
| **Modify** | `research/run_config.py` — replace `preset` with `strategy`+`params` |
| **Modify** | `research/is_harness.py` — `_run_is_core` dispatches via registry |
| **Modify** | `research/runners.py` — no logic change; verify import list |
| **Modify** | `research/cli.py` — `run-is` → `--strategy`/`--params`; add `validate-strategy` |
| **Modify** | `research/sweep.py` — replace `preset` with `strategy`+`params` |
| **Modify** | `research/run_tags_store.py` — replace `preset` references |
| **Modify** | `research/saved_views_store.py` — replace `preset` references |
| **Modify** | `data/db_writer.py` — `_RUNS_COLS`: `"preset"` → `"strategy"` |
| **Modify** | `api/schemas.py` — `RunCreateRequest`: `preset` → `strategy`+`params` |
| **Modify** | `api/response_models.py` — run record: `preset` → `strategy`+`params` |
| **Create** | `api/routers/strategies.py` — `GET /strategies` |
| **Modify** | `api/routers/runs.py` — build new `RunConfig`; remove preset logic |
| **Modify** | `api/routers/presets.py` — **delete** (or gut and redirect) |
| **Modify** | `api/routers/research.py`, `api/routers/research_registry.py` — remove preset refs |
| **Modify** | `api/routers/home.py` — remove preset refs |
| **Modify** | `api/app.py` — remove preset router; register strategies router; fix startup import |
| **Modify** | `api/__init__.py` — remove preset exports if any |
| **Modify** | `config/__init__.py` — remove StrategyConfig/PRESETS re-exports |
| **Modify** | `config/strategy_config.py` — **delete** after relocation |
| **Modify** | `engines/protocol.py` — update StrategyConfig import path |
| **Modify** | `engines/zipline_adapter/algorithms/four_layer_resonance.py` — update import |
| **Modify** | `engines/zipline_adapter/cli.py` — remove preset; update import |
| **Modify** | `engines/zipline_adapter/controls/taiwan_stock_rules.py` — update import |
| **Modify** | `engines/zipline_adapter/validation/cross_check_vectorbt.py` — update import |
| **Modify** | `engines/zipline_adapter/validation/regression_vs_m1.py` — update import |
| **Modify** | `engines/zipline_adapter/validation/vectorized_pnl_check.py` — update import |
| **Modify** | `adapters/brokers/paper_broker.py` — update StrategyConfig import |
| **Modify** | `pipeline.py` — update StrategyConfig import; remove preset |
| **Modify** | `strategies/four_layer_resonance/sim.py` — update import |
| **Modify** | `strategies/four_layer_resonance/scoring.py` — update import |
| **Modify** | `strategies/four_layer_resonance/signals.py` — update import |
| **Create/Modify** | `tests/strategies/test_conformance.py` — parametrized conformance tests |
| **Modify** | `tests/strategies/test_protocol.py` — add `config_model`/`describe_strategies` tests |
| **Modify** | `tests/research/test_run_config.py` — update for new fields |
| **Modify** | `tests/research/test_runners.py` — update dispatch tests |
| **Modify** | `tests/api/test_runs.py` — update request/response shape |
| **Create** | `tests/api/test_strategies.py` — `GET /strategies` tests |
| **Modify** | remaining 11 test files that reference `preset` — mechanical field rename |
| **Create** | `dev_docs/adrs/ADR-028-strategy-dispatch-contract.md` |
| **Modify** | `dev_docs/06_api_design_specification.md` — new routes |
| **Modify** | `dev_docs/21_data_contract.md` — runs record preset→strategy |
| **Modify** | `dev_docs/16_wbs.md` — progress entry |

---

## Execution Order (dependency-safe)

Tasks 1–3 are the foundation (no other task can run before them).
Tasks 4–6 build on the foundation.
Tasks 7–8 are the HTTP surface (depend on 4).
Task 9 is tests + docs.

---

## Task 1: Relocate `StrategyConfig` into four_layer (D6)

**Files:**
- Create: `backtest_platform/src/backtest_platform/strategies/four_layer_resonance/config.py`
- Delete: `backtest_platform/src/backtest_platform/config/strategy_config.py`
- Modify (import-path only, 27 files): see list below

This is a pure import-path migration — no logic changes.

- [ ] **Step 1.1: Create the new home**

  Create `strategies/four_layer_resonance/config.py` with the exact content of
  `config/strategy_config.py` **minus** the `PRESETS`/`get_preset` definitions
  (those are removed in Task 3). The file must contain only `StrategyConfig`.

  ```python
  # strategies/four_layer_resonance/config.py
  """StrategyConfig — four-layer resonance strategy parameters."""
  from __future__ import annotations
  from pydantic import BaseModel, Field, model_validator

  class StrategyConfig(BaseModel):
      """Strategy parameters for the four-layer resonance system."""
      model_config = {"frozen": True, "extra": "forbid"}

      # --- Structure layer (L1) ---
      box_period: int = Field(60, ge=10, le=250)
      # --- Chip layer (L3) ---
      chip_strong_threshold: float = Field(0.10, gt=0, le=1.0)
      # --- Scoring thresholds ---
      strong_buy_threshold: int = Field(5, ge=1, le=8)
      warning_threshold: int = Field(2, ge=-3, le=8)
      add_score_threshold: int = Field(6, ge=1, le=8)
      # --- Take-profit triggers ---
      takeprofit_volume_rate: float = Field(1.5, gt=0)
      takeprofit_shadow_rate: float = Field(1.5, gt=0)
      # --- Cost model ---
      fee_rate: float = Field(0.001425, ge=0, le=0.01)
      fee_discount: float = Field(0.6, gt=0, le=1.0)
      tax_stock_rate: float = Field(0.003, ge=0, le=0.01)
      slip_rate: float = Field(0.001, ge=0, le=0.05)
      # --- Risk / position sizing ---
      max_position_pct: float = Field(0.05, gt=0, le=1.0)
      # --- Signal confirmation ---
      confirmation_bars: int = Field(2, ge=1, le=5)
      # --- copy all remaining fields from the original file verbatim ---
  ```

  **Action:** Read `config/strategy_config.py` in full first, then write
  `strategies/four_layer_resonance/config.py` with **all** `StrategyConfig` fields
  copied verbatim. Do not copy `PRESETS`/`get_preset`.

- [ ] **Step 1.2: Update the 27 importers** (pure sed-style replacements)

  Replace `from backtest_platform.config.strategy_config import StrategyConfig`
  with `from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig`
  in all 27 files. Also update `from backtest_platform.config import StrategyConfig`
  patterns. Files:

  ```
  adapters/brokers/paper_broker.py
  api/response_models.py
  api/routers/presets.py              ← will be deleted in Task 7; update anyway
  api/schemas.py
  config/__init__.py                  ← remove StrategyConfig re-export
  engines/protocol.py
  engines/zipline_adapter/algorithms/four_layer_resonance.py
  engines/zipline_adapter/cli.py
  engines/zipline_adapter/controls/taiwan_stock_rules.py
  engines/zipline_adapter/validation/cross_check_vectorbt.py
  engines/zipline_adapter/validation/regression_vs_m1.py
  engines/zipline_adapter/validation/vectorized_pnl_check.py
  pipeline.py
  research/cli.py
  research/is_harness.py
  research/run_config.py              ← will be rewritten in Task 3
  research/sweep.py
  strategies/four_layer_resonance/runner.py
  strategies/four_layer_resonance/scoring.py
  strategies/four_layer_resonance/signals.py
  strategies/four_layer_resonance/sim.py
  strategies/momentum/strategy.py     ← grep showed docstring mention only; verify no import
  strategies/protocol.py
  ```

- [ ] **Step 1.3: Add `__init__.py` re-export in four_layer package**

  In `strategies/four_layer_resonance/__init__.py`, add:
  ```python
  from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
  __all__ = ["StrategyConfig"]
  ```

- [ ] **Step 1.4: Delete old file**

  Delete `config/strategy_config.py`. Confirm `config/__init__.py` no longer
  re-exports `StrategyConfig` or `PRESETS`.

- [ ] **Step 1.5: Run import smoke test**

  ```bash
  cd backtest_platform && uv run python -c "
  from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
  from backtest_platform.strategies.four_layer_resonance.runner import FourLayerRunner
  from backtest_platform.adapters.brokers.paper_broker import PaperBroker
  from backtest_platform.engines.protocol import Engine
  print('relocation ok')
  "
  ```
  Expected: `relocation ok` (no ImportError).

- [ ] **Step 1.6: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/strategies/four_layer_resonance/config.py
  git add backtest_platform/src/  # all modified importers
  git rm backtest_platform/src/backtest_platform/config/strategy_config.py
  git commit -m "refactor(four_layer): relocate StrategyConfig into its strategy folder (D6)

  StrategyConfig lived in the central config/ module, making four_layer
  a privileged citizen and coupling ~27 files to config/ just to access
  a strategy parameter class. Moving it next to its strategy (same pattern
  as MomentumConfig / InstFlowConfig) completes the de-privileging started
  by ADR-027. Pure import-path migration — no logic changes.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 2: Extend `StrategyRunner` protocol (`strategies/protocol.py`)

**Files:**
- Modify: `backtest_platform/src/backtest_platform/strategies/protocol.py`

- [ ] **Step 2.1: Write failing test**

  In `tests/strategies/test_protocol.py`, add:
  ```python
  def test_runner_has_config_model():
      from backtest_platform.research import runners  # noqa: F401 — triggers registration
      from backtest_platform.strategies.protocol import list_strategies, get_strategy
      for name in list_strategies():
          runner = get_strategy(name)
          assert hasattr(runner, "config_model"), f"{name} missing config_model"
          assert hasattr(runner, "title"), f"{name} missing title"

  def test_describe_strategies_returns_schemas():
      from backtest_platform.research import runners  # noqa: F401
      from backtest_platform.strategies.protocol import describe_strategies
      infos = describe_strategies()
      assert len(infos) >= 4  # template, momentum, inst_flow, four_layer
      for info in infos:
          assert info.name and info.title and info.config_schema
          assert "properties" in info.config_schema
  ```

  Run: `cd backtest_platform && uv run pytest tests/strategies/test_protocol.py -k "config_model or describe_strategies" -v`
  Expected: FAIL (AttributeError — config_model not yet declared).

- [ ] **Step 2.2: Add `StrategyInfo` dataclass and `describe_*` to `protocol.py`**

  After the existing `StrategyRun` dataclass (around line 72), add:
  ```python
  @dataclass(frozen=True)
  class StrategyInfo:
      """Self-description of a registered strategy — feeds GET /strategies."""
      name: str
      title: str
      description: str        # from runner class __doc__ (first non-empty line)
      config_schema: dict     # runner.config_model.model_json_schema()
  ```

  After the existing `list_strategies()` function, add:
  ```python
  def describe_strategy(name: str) -> StrategyInfo:
      """Full self-description for one registered strategy."""
      runner = get_strategy(name)  # raises ValueError on unknown
      doc = (runner.__class__.__doc__ or "").strip().splitlines()
      description = next((l.strip() for l in doc if l.strip()), "")
      return StrategyInfo(
          name=name,
          title=getattr(runner, "title", name),
          description=description,
          config_schema=runner.config_model.model_json_schema(),
      )

  def describe_strategies() -> list[StrategyInfo]:
      """Self-description of every registered strategy (sorted by name)."""
      return [describe_strategy(n) for n in list_strategies()]
  ```

  Add `StrategyInfo` to the `ClassVar` hint on the Protocol:
  ```python
  @runtime_checkable
  class StrategyRunner(Protocol):
      config_model: ClassVar[type[BaseModel]]
      title: ClassVar[str]
      def run(self, symbols, start, end, config, loader) -> StrategyRun: ...
  ```

  Add required imports at top of file:
  ```python
  from typing import ClassVar
  ```

- [ ] **Step 2.3: Add `config_model` + `title` to every runner**

  **`_template/runner.py`** — add at class body top:
  ```python
  config_model = TemplateConfig
  title = "Template (equal-weight buy-and-hold)"
  ```

  **`momentum/runner.py`** — add:
  ```python
  config_model = MomentumConfig
  title = "12-1 Cross-sectional Momentum"
  ```

  **`inst_flow/runner.py`** — add:
  ```python
  config_model = InstFlowConfig
  title = "Institutional Net-Buy Flow"
  ```

  **`four_layer_resonance/runner.py`** — add (import from new location):
  ```python
  from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
  # ... (already imported after Task 1)
  config_model = StrategyConfig
  title = "Four-Layer Resonance"
  ```

- [ ] **Step 2.4: Run tests — should pass**

  ```bash
  cd backtest_platform && uv run pytest tests/strategies/test_protocol.py -v
  ```
  Expected: PASS.

- [ ] **Step 2.5: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/strategies/
  git add backtest_platform/tests/strategies/test_protocol.py
  git commit -m "feat(strategies): add config_model + describe_strategies to StrategyRunner contract

  Each runner now declares config_model (its Pydantic config class) and
  title. describe_strategies() turns the registry into a self-describing
  catalog consumed by GET /strategies (Task 7) and the conformance gate
  (Task 4). This is the schema-exposure half of D2.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 3: Replace `RunConfig` (`research/run_config.py`)

**Files:**
- Modify: `backtest_platform/src/backtest_platform/research/run_config.py`
- Modify: `backtest_platform/tests/research/test_run_config.py`

- [ ] **Step 3.1: Write failing tests**

  In `tests/research/test_run_config.py`, replace/add:
  ```python
  from datetime import date
  from backtest_platform.research.run_config import RunConfig

  def test_run_config_accepts_strategy_and_params():
      cfg = RunConfig(
          hypothesis="test momentum edge",
          strategy="momentum",
          params={"lookback_days": 120},
          stocks=("2330", "2317"),
          is_start=date(2020, 1, 1),
          is_end=date(2023, 12, 31),
      )
      assert cfg.strategy == "momentum"
      assert cfg.params == {"lookback_days": 120}

  def test_run_config_rejects_preset_field():
      import pytest
      from pydantic import ValidationError
      with pytest.raises(ValidationError):
          RunConfig(
              hypothesis="h",
              preset="v3",  # old field — must be rejected (extra="forbid")
              stocks=("2330",),
              is_start=date(2020, 1, 1),
              is_end=date(2023, 12, 31),
          )

  def test_run_id_is_deterministic():
      common = dict(hypothesis="h", strategy="momentum", params={},
                    stocks=("2330",), is_start=date(2020,1,1), is_end=date(2023,12,31))
      assert RunConfig(**common).run_id == RunConfig(**common).run_id

  def test_run_id_differs_on_params():
      base = dict(hypothesis="h", strategy="momentum",
                  stocks=("2330",), is_start=date(2020,1,1), is_end=date(2023,12,31))
      r1 = RunConfig(**base, params={"lookback_days": 120})
      r2 = RunConfig(**base, params={"lookback_days": 252})
      assert r1.run_id != r2.run_id
  ```

  Run: `cd backtest_platform && uv run pytest tests/research/test_run_config.py -v`
  Expected: FAIL (no `strategy` field yet, `preset` not yet removed).

- [ ] **Step 3.2: Rewrite `run_config.py`**

  Full replacement of `backtest_platform/src/backtest_platform/research/run_config.py`:
  ```python
  """RunConfig — a backtest run as a first-class object.

  ``hypothesis`` is mandatory (anti-overfit pre-registration discipline).
  ``run_id`` is a deterministic hash over (strategy, params, engine, stocks,
  window) so the same run is identifiable without a wall-clock id.
  ``strategy`` names a registered StrategyRunner; ``params`` is validated
  against that runner's ``config_model`` at dispatch time (_run_is_core),
  not here — so RunConfig stays decoupled from concrete strategy types.
  """
  from __future__ import annotations

  import hashlib
  import json
  from datetime import date
  from typing import Any

  from pydantic import BaseModel, Field, field_validator, model_validator


  class RunConfig(BaseModel):
      """One IS run: which strategy, which params, which stocks, which window."""

      model_config = {"frozen": True, "extra": "forbid"}

      hypothesis: str = Field(..., min_length=1, description="預先註冊：這個 run 在驗什麼")
      strategy:   str = Field(..., description="registered strategy name (see list_strategies())")
      params:     dict[str, Any] = Field(default_factory=dict, description="strategy params — validated at dispatch")
      stocks:     tuple[str, ...] = Field(..., min_length=1)
      is_start:   date
      is_end:     date
      engine:     str = Field("sim", description="sim | zipline")

      @field_validator("hypothesis")
      @classmethod
      def _hypothesis_nonblank(cls, v: str) -> str:
          if not v.strip():
              raise ValueError("hypothesis must not be blank")
          return v.strip()

      @field_validator("engine")
      @classmethod
      def _engine_known(cls, v: str) -> str:
          if v not in ("sim", "zipline"):
              raise ValueError(f"unknown engine {v!r}")
          return v

      @model_validator(mode="after")
      def _window_ordered(self) -> RunConfig:
          if self.is_start >= self.is_end:
              raise ValueError("is_start must be before is_end")
          return self

      @property
      def run_id(self) -> str:
          """Deterministic 12-char id from the run's defining inputs."""
          key = "|".join([
              self.strategy,
              json.dumps(self.params, sort_keys=True, default=str),
              self.engine,
              ",".join(sorted(self.stocks)),
              self.is_start.isoformat(),
              self.is_end.isoformat(),
          ])
          return hashlib.sha1(key.encode()).hexdigest()[:12]
  ```

- [ ] **Step 3.3: Run tests — should pass**

  ```bash
  cd backtest_platform && uv run pytest tests/research/test_run_config.py -v
  ```
  Expected: PASS.

- [ ] **Step 3.4: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/research/run_config.py
  git add backtest_platform/tests/research/test_run_config.py
  git commit -m "feat(research): replace preset with strategy+params in RunConfig (D1/D5)

  The preset field was a pre-contract privileged path that hardwired
  RunConfig to the PRESETS bundle and implicitly to four_layer. Replacing
  it with strategy (name) + params (dict) makes RunConfig a neutral value
  object: strategy-name resolution and param validation happen at dispatch
  (_run_is_core, Task 5), not here, preserving the ADR-027 no-upward-import
  invariant. run_id now hashes over (strategy, sorted params, engine,
  sorted stocks, window) for determinism.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 4: Build conformance gate (`strategies/conformance.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/strategies/conformance.py`
- Create: `backtest_platform/tests/strategies/test_conformance.py`

- [ ] **Step 4.1: Write failing tests**

  Create `tests/strategies/test_conformance.py`:
  ```python
  """Parametrized conformance tests — every registered strategy must satisfy the contract."""
  import pytest
  from backtest_platform.research import runners as _runners  # noqa: F401 — triggers registration
  from backtest_platform.strategies.protocol import list_strategies
  from backtest_platform.strategies.conformance import check_strategy, ConformanceReport, REQUIRED_METRIC_KEYS

  @pytest.mark.parametrize("name", list_strategies())
  def test_strategy_conforms(name: str):
      report = check_strategy(name)
      assert report.ok, f"strategy {name!r} failed conformance:\n" + "\n".join(report.errors)

  def test_conformance_catches_missing_metric(monkeypatch):
      """check_strategy returns ok=False when a strategy omits a required metric key."""
      from backtest_platform.strategies.protocol import _REGISTRY, StrategyRun
      # Inject a minimal broken runner (returns empty metrics dict)
      class _BrokenRunner:
          config_model = __import__("pydantic", fromlist=["BaseModel"]).BaseModel
          title = "broken"
          def run(self, symbols, start, end, config, loader):
              return StrategyRun(metrics={}, returns=__import__("pandas").Series(dtype=float), trades=[])
      _REGISTRY["__broken__"] = _BrokenRunner()
      try:
          report = check_strategy("__broken__")
          assert not report.ok
          assert any("cagr" in e for e in report.errors)
      finally:
          del _REGISTRY["__broken__"]
  ```

  Run: `cd backtest_platform && uv run pytest tests/strategies/test_conformance.py -v`
  Expected: FAIL (module `conformance` doesn't exist yet).

- [ ] **Step 4.2: Implement `conformance.py`**

  Create `backtest_platform/src/backtest_platform/strategies/conformance.py`:
  ```python
  """Strategy conformance gate — proves any registered runner satisfies the contract.

  Used by:
  - CI: parametrized pytest over list_strategies() (test_conformance.py)
  - CLI: ``validate-strategy <name>`` (research/cli.py)
  - Sub-project ②: load-time gate before dynamic module registration
  """
  from __future__ import annotations

  from dataclasses import dataclass, field
  from datetime import date

  import numpy as np
  import pandas as pd

  from backtest_platform.strategies.protocol import Loader, get_strategy

  # The universal edge keys every strategy must return — aligns with gate_state.py
  # DEFAULT_GATE + MOMENTUM_GATE common keys; health keys are family-specific (excluded).
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
      """Return a Loader that generates a synthetic merged DataFrame per stock.

      Prices follow a geometric random walk; institutional/chip columns are
      random integers — sufficient for contract checks, not for signal quality.
      The loader ignores the stock_id (all symbols get the same synthetic shape).
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
      4. Return value is a StrategyRun with metrics ⊇ REQUIRED_METRIC_KEYS,
         returns is pd.Series, trades is list.
      """
      errors: list[str] = []

      # 1. Resolve
      try:
          runner = get_strategy(name)
      except ValueError as exc:
          return ConformanceReport(name=name, ok=False, errors=[str(exc)])

      # 2. Build default config
      try:
          cfg = runner.config_model()
      except Exception as exc:
          errors.append(f"config_model() raised: {exc}")
          return ConformanceReport(name=name, ok=False, errors=errors)

      # 3. Run
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
      if not isinstance(result.metrics, dict):
          errors.append("StrategyRun.metrics is not a dict")
      else:
          missing = REQUIRED_METRIC_KEYS - result.metrics.keys()
          if missing:
              errors.append(f"metrics missing required keys: {sorted(missing)}")

      if not isinstance(result.returns, pd.Series):
          errors.append("StrategyRun.returns is not a pd.Series")

      if not isinstance(result.trades, list):
          errors.append("StrategyRun.trades is not a list")

      return ConformanceReport(name=name, ok=len(errors) == 0, errors=errors)
  ```

- [ ] **Step 4.3: Run tests — should pass**

  ```bash
  cd backtest_platform && uv run pytest tests/strategies/test_conformance.py -v
  ```
  Expected: PASS (all registered strategies conform; broken-runner test also passes).

- [ ] **Step 4.4: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/strategies/conformance.py
  git add backtest_platform/tests/strategies/test_conformance.py
  git commit -m "feat(strategies): generic conformance gate — check_strategy + synthetic_loader (D3)

  Proves any registered runner satisfies the StrategyRun contract on
  synthetic data covering all canonical merged-parquet columns (doc 21).
  Required edge keys: {cagr, sharpe, slippage_sharpe, maxdd, trades, bars}.
  Used by parametrized CI (all built-ins auto-covered) and validate-strategy
  CLI (Task 6). Sub-project ② will reuse check_strategy as its load-time
  safety gate before trusting a dynamically-loaded module.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 5: Wire dispatch in `_run_is_core` (`research/is_harness.py`)

**Files:**
- Modify: `backtest_platform/src/backtest_platform/research/is_harness.py`
- Modify: `backtest_platform/tests/research/test_runners.py`

- [ ] **Step 5.1: Write failing test**

  In `tests/research/test_runners.py`, add:
  ```python
  from datetime import date
  from backtest_platform.research.run_config import RunConfig
  from backtest_platform.research.is_harness import run_is

  def test_dispatch_momentum_via_strategy_field(synthetic_parquet_dir):
      """run_is dispatches to momentum runner when strategy='momentum'."""
      cfg = RunConfig(
          hypothesis="dispatch test",
          strategy="momentum",
          params={"lookback_days": 120},
          stocks=("2330", "2317"),
          is_start=date(2020, 1, 1),
          is_end=date(2023, 12, 31),
      )
      metrics = run_is(cfg)
      assert "cagr" in metrics
      assert "sharpe" in metrics

  def test_dispatch_unknown_strategy_raises():
      import pytest
      from pydantic import ValidationError
      from backtest_platform.strategies.protocol import get_strategy
      with pytest.raises(ValueError, match="unknown strategy"):
          get_strategy("nonexistent_xyz")

  def test_dispatch_bad_params_raises():
      import pytest
      from backtest_platform.strategies.protocol import get_strategy
      runner = get_strategy("momentum")
      with pytest.raises(Exception):  # Pydantic ValidationError
          runner.config_model(lookback_days=99999)  # exceeds Field max
  ```

  Run: `cd backtest_platform && uv run pytest tests/research/test_runners.py -k "dispatch" -v`
  Expected: FAIL (is_harness still calls FourLayerRunner directly).

- [ ] **Step 5.2: Rewrite `_run_is_core` in `is_harness.py`**

  Replace the `_run_is_core` function body:
  ```python
  def _run_is_core(
      cfg: RunConfig,
      loader: Callable[[str], pd.DataFrame] = load_merged_parquet,
  ) -> tuple[dict, pd.Series, list[dict]]:
      """IS portfolio sim — dispatches to the registered strategy by name.

      Validates cfg.params against the strategy's own config_model (Pydantic
      frozen + extra=forbid) so bad params raise a clear ValidationError at
      the boundary rather than deep inside the runner.
      """
      from backtest_platform.strategies.protocol import get_strategy  # local to avoid circular
      runner = get_strategy(cfg.strategy)          # ValueError on unknown name → API 400
      sconf  = runner.config_model(**cfg.params)   # ValidationError on bad params → API 422
      run    = runner.run(list(cfg.stocks), cfg.is_start, cfg.is_end, sconf, loader)
      return run.metrics, run.returns, run.trades
  ```

  Also update the import at top of `is_harness.py`: remove
  `from backtest_platform.config.strategy_config import ...` and
  `from backtest_platform.strategies.four_layer_resonance.runner import FourLayerRunner`
  (no longer needed directly). Ensure `from backtest_platform.research import runners as _runners`
  is imported in `is_harness.py` (or in `app.py` startup — see Task 7) so all runners
  are registered before dispatch.

- [ ] **Step 5.3: Update `research/runners.py` startup import in `api/app.py`**

  In `api/app.py`, replace:
  ```python
  from backtest_platform.research.runners import FourLayerRunner
  ```
  with:
  ```python
  from backtest_platform.research import runners as _runners  # noqa: F401 — registers all strategies
  ```

- [ ] **Step 5.4: Remove `preset` from remaining research modules**

  **`research/sweep.py`** — replace `preset` field references with `strategy`+`params`.
  **`research/run_tags_store.py`** — replace `preset` key with `strategy`.
  **`research/saved_views_store.py`** — replace `preset` key with `strategy`.
  **`research/cli.py`** — update `run-is` (step 5 below handles CLI fully in Task 6).

- [ ] **Step 5.5: Run tests — should pass**

  ```bash
  cd backtest_platform && uv run pytest tests/research/test_runners.py -v
  ```
  Expected: PASS.

- [ ] **Step 5.6: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/research/
  git add backtest_platform/tests/research/test_runners.py
  git commit -m "feat(research): dispatch _run_is_core via strategy registry (D1)

  _run_is_core now resolves the strategy by name (get_strategy), validates
  params through config_model(**params), and delegates to runner.run() —
  replacing the hardwired FourLayerRunner + get_preset call. Unknown strategy
  name raises ValueError (→ API 400); invalid params raise ValidationError
  (→ API 422). preset removed from sweep / run_tags / saved_views stores.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 6: CLI — `validate-strategy` + update `run-is` (`research/cli.py`)

**Files:**
- Modify: `backtest_platform/src/backtest_platform/research/cli.py`

- [ ] **Step 6.1: Write failing test**

  In `tests/research/test_cli.py` (create if absent), add:
  ```python
  from click.testing import CliRunner
  from backtest_platform.research.cli import cli

  def test_validate_strategy_passes_for_momentum():
      runner = CliRunner()
      result = runner.invoke(cli, ["validate-strategy", "momentum"])
      assert result.exit_code == 0
      assert "ok" in result.output.lower()

  def test_validate_strategy_fails_for_unknown():
      runner = CliRunner()
      result = runner.invoke(cli, ["validate-strategy", "nonexistent_xyz"])
      assert result.exit_code != 0
  ```

  Run: `cd backtest_platform && uv run pytest tests/research/test_cli.py -k "validate_strategy" -v`
  Expected: FAIL (command not yet defined).

- [ ] **Step 6.2: Add `validate-strategy` command and update `run-is`**

  In `research/cli.py`:

  1. Remove all `--preset` options and `get_preset` calls from `run-is`.
  2. Add `--strategy` (required) and `--params` (optional JSON string, default `"{}"`).
  3. Add new command `validate-strategy`:

  ```python
  @cli.command("validate-strategy")
  @click.argument("name")
  def validate_strategy_cmd(name: str) -> None:
      """Run the conformance gate on a registered strategy and print the report."""
      from backtest_platform.research import runners as _runners  # noqa: F401
      from backtest_platform.strategies.conformance import check_strategy
      report = check_strategy(name)
      if report.ok:
          click.echo(f"[OK] strategy {name!r} conforms to the contract.")
      else:
          click.echo(f"[FAIL] strategy {name!r} failed conformance:", err=True)
          for e in report.errors:
              click.echo(f"  - {e}", err=True)
          raise SystemExit(1)
  ```

  Updated `run-is` signature fragment:
  ```python
  @cli.command("run-is")
  @click.option("--strategy", required=True, help="Registered strategy name")
  @click.option("--params", default="{}", help="JSON dict of strategy params")
  @click.option("--hypothesis", required=True)
  @click.option("--stocks", required=True, help="Comma-separated stock IDs")
  @click.option("--start", "is_start", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
  @click.option("--end",   "is_end",   required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
  @click.option("--engine", default="sim")
  @click.option("--tearsheet", is_flag=True)
  @click.option("--tearsheet-dir", default="reports/tearsheets")
  def run_is_cmd(strategy, params, hypothesis, stocks, is_start, is_end, engine, tearsheet, tearsheet_dir):
      import json
      from backtest_platform.research import runners as _runners  # noqa: F401
      params_dict = json.loads(params)
      cfg = RunConfig(
          hypothesis=hypothesis,
          strategy=strategy,
          params=params_dict,
          stocks=tuple(s.strip() for s in stocks.split(",")),
          is_start=is_start.date(),
          is_end=is_end.date(),
          engine=engine,
      )
      # ... rest of run-is body unchanged (run_and_judge_persist, tearsheet, etc.)
  ```

- [ ] **Step 6.3: Run tests — should pass**

  ```bash
  cd backtest_platform && uv run pytest tests/research/test_cli.py -v
  ```
  Expected: PASS.

- [ ] **Step 6.4: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/research/cli.py
  git add backtest_platform/tests/research/test_cli.py
  git commit -m "feat(cli): add validate-strategy; update run-is to --strategy/--params (D3/D5)

  validate-strategy <name> runs check_strategy and exits non-zero on failure
  — the author/AI self-check command. run-is replaces --preset with
  --strategy + --params (JSON). Both commands import runners at invocation
  time to ensure all strategies are registered.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 7: HTTP surface — `GET /strategies` + update `POST /runs` (`api/`)

**Files:**
- Modify: `api/schemas.py`
- Modify: `api/response_models.py`
- Create:  `api/routers/strategies.py`
- Modify: `api/routers/runs.py`
- Delete:  `api/routers/presets.py`
- Modify: `api/app.py`

- [ ] **Step 7.1: Write failing tests**

  Create `tests/api/test_strategies.py`:
  ```python
  from fastapi.testclient import TestClient
  from backtest_platform.api.app import create_app

  client = TestClient(create_app())

  def test_get_strategies_returns_list():
      r = client.get("/strategies")
      assert r.status_code == 200
      data = r.json()
      assert data["success"] is True
      names = [s["name"] for s in data["data"]]
      assert "momentum" in names
      assert "four_layer" in names

  def test_get_strategies_includes_schema():
      r = client.get("/strategies")
      strategies = r.json()["data"]
      for s in strategies:
          assert "config_schema" in s
          assert "properties" in s["config_schema"]
  ```

  In `tests/api/test_runs.py`, add:
  ```python
  def test_post_runs_with_strategy_and_params(mock_run_executor):
      r = client.post("/runs", json={
          "hypothesis": "test dispatch",
          "strategy": "momentum",
          "params": {"lookback_days": 120},
          "stocks": ["2330", "2317"],
          "is_start": "2020-01-01",
          "is_end": "2023-12-31",
      })
      assert r.status_code == 201
      assert r.json()["success"] is True

  def test_post_runs_unknown_strategy_returns_400(mock_run_executor):
      r = client.post("/runs", json={
          "hypothesis": "h",
          "strategy": "nonexistent_xyz",
          "params": {},
          "stocks": ["2330"],
          "is_start": "2020-01-01",
          "is_end": "2023-12-31",
      })
      assert r.status_code == 400
  ```

  Run: `cd backtest_platform && uv run pytest tests/api/ -v`
  Expected: FAIL (`/strategies` route not yet defined; `/runs` still expects `preset`).

- [ ] **Step 7.2: Update `api/schemas.py`**

  Replace `RunCreateRequest`:
  ```python
  class RunCreateRequest(BaseModel):
      hypothesis: str = Field(..., min_length=1)
      strategy:   str = Field(...)
      params:     dict[str, Any] = Field(default_factory=dict)
      stocks:     list[str] = Field(..., min_length=1)
      is_start:   date
      is_end:     date
      engine:     str = "sim"
  ```
  Remove `preset: str` field and its validator. Add `from typing import Any`.

- [ ] **Step 7.3: Update `api/response_models.py`**

  In run record models, replace `preset: str` field with `strategy: str` and
  `params: dict[str, Any]`.

- [ ] **Step 7.4: Create `api/routers/strategies.py`**

  ```python
  """GET /strategies — strategy catalog endpoint."""
  from __future__ import annotations

  from fastapi import APIRouter

  from backtest_platform.api.envelope import Envelope, ok
  from backtest_platform.strategies.protocol import describe_strategies

  router = APIRouter(prefix="/strategies", tags=["strategies"])


  @router.get("", response_model=Envelope)
  def list_strategies_endpoint():
      """Return all registered strategies with name, title, description, and config JSON-schema."""
      from backtest_platform.research import runners as _runners  # noqa: F401
      infos = describe_strategies()
      return ok([
          {
              "name": s.name,
              "title": s.title,
              "description": s.description,
              "config_schema": s.config_schema,
          }
          for s in infos
      ])
  ```

- [ ] **Step 7.5: Update `api/routers/runs.py`**

  In `POST /runs` and `POST /runs/async` handlers, replace:
  ```python
  # OLD
  cfg = RunConfig(hypothesis=body.hypothesis, preset=body.preset, ...)
  ```
  with:
  ```python
  # NEW
  cfg = RunConfig(
      hypothesis=body.hypothesis,
      strategy=body.strategy,
      params=body.params,
      stocks=tuple(body.stocks),
      is_start=body.is_start,
      is_end=body.is_end,
      engine=body.engine,
  )
  ```
  Ensure `ValueError` from `get_strategy` is caught → HTTP 400 (check existing exception handlers in `app.py`; add if needed).

- [ ] **Step 7.6: Delete `api/routers/presets.py`; update `api/app.py`**

  - Delete `api/routers/presets.py`.
  - In `api/app.py`: remove preset router import/registration; add strategies router:
    ```python
    from backtest_platform.api.routers.strategies import router as strategies_router
    app.include_router(strategies_router)
    ```
  - Remove `from backtest_platform.research.runners import FourLayerRunner` (replaced
    in Step 5.3 with `import runners as _runners`).
  - Remove preset references from `api/routers/research.py`,
    `api/routers/research_registry.py`, `api/routers/home.py`.

- [ ] **Step 7.7: Run tests — should pass**

  ```bash
  cd backtest_platform && uv run pytest tests/api/ -v
  ```
  Expected: PASS.

- [ ] **Step 7.8: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/api/
  git rm backtest_platform/src/backtest_platform/api/routers/presets.py
  git add backtest_platform/tests/api/
  git commit -m "feat(api): POST /runs accepts strategy+params; add GET /strategies (D4/D5)

  RunCreateRequest replaces preset with strategy+params. The strategies
  router exposes every registered strategy's name, title, description, and
  Pydantic JSON-schema — the contract surface the React frontend (③) will
  use to build auto-generated param forms. GET /presets removed.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 8: Sweep remaining `preset` references + 17 test files

**Files:**
- Modify: `data/db_writer.py`
- Modify: 17 test files (mechanical `preset` → `strategy` rename)

- [ ] **Step 8.1: Update `data/db_writer.py`**

  In `_RUNS_COLS` tuple, replace `"preset"` with `"strategy"`:
  ```python
  _RUNS_COLS = (
      "run_id",
      "hypothesis",
      "strategy",      # was "preset"
      "params",
      "engine",
      ...
  )
  ```
  Ensure any dict construction that set `record["preset"]` is updated to
  `record["strategy"]`. (Single-operator project — no DB migration of existing rows needed.)

- [ ] **Step 8.2: Fix the 17 test files**

  Search for `preset` in all test files and replace with `strategy` (field name)
  or remove entirely if the test was specifically testing preset validation:
  ```bash
  grep -rln "preset" backtest_platform/tests/
  ```
  For each file: replace `preset=` kwargs in `RunConfig(...)` calls with
  `strategy=..., params={}`. Remove tests that specifically tested
  `_preset_known` validator (that validator no longer exists).

- [ ] **Step 8.3: Run full test suite**

  ```bash
  cd backtest_platform && uv run pytest --tb=short -q
  ```
  Expected: all green (or only pre-existing failures unrelated to this work).

- [ ] **Step 8.4: Commit**

  ```bash
  git add backtest_platform/src/backtest_platform/data/db_writer.py
  git add backtest_platform/tests/
  git commit -m "chore: sweep remaining preset→strategy rename (db_writer + 17 test files) (D5)

  Mechanical completion of the preset removal: db_writer _RUNS_COLS and
  all test RunConfig fixtures updated to strategy+params. No logic changes.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 9: Doc sync (ADR-028 + dev_docs update)

Per `code-doc-sync.md` triggers: new dispatch mechanism (→ ADR), API routes changed
(→ doc 06), runs record schema changed (→ doc 21), milestone complete (→ doc 16 WBS).

- [ ] **Step 9.1: Write ADR-028**

  Create `dev_docs/adrs/ADR-028-strategy-dispatch-contract.md`:
  ```markdown
  # ADR-028: Strategy Dispatch Contract & Preset Removal

  **Date:** 2026-06-16
  **Status:** Accepted
  **Supersedes:** The preset/get_preset dispatch path introduced before ADR-027.

  ## Context
  ADR-027 introduced StrategyRunner + the registry, but dispatch (is_harness)
  still hardwired FourLayerRunner via a preset bundle. AI-authored strategies
  registered in the registry could not be reached via the HTTP API or CLI.

  ## Decision
  1. RunConfig carries strategy (name) + params (dict); params validated at
     dispatch by config_model(**params) — not in RunConfig (no upward import).
  2. StrategyRunner Protocol gains config_model ClassVar + title ClassVar.
  3. Generic conformance gate (check_strategy) on synthetic data; required
     keys = {cagr, sharpe, slippage_sharpe, maxdd, trades, bars}.
  4. HTTP: POST /runs accepts strategy+params; GET /strategies exposes schema.
  5. preset fully removed (PRESETS bundle, get_preset, RunConfig.preset,
     GET /presets, db_writer preset column, all test fixtures).
  6. StrategyConfig relocated from config/ to strategies/four_layer_resonance/config.py.

  ## Consequences
  - Any AI-authored strategy that follows the _template contract is auto-covered
    by the conformance pytest and reachable via POST /runs + GET /strategies.
  - Sub-project ② can reuse check_strategy as load-time gate for dynamic modules.
  - React frontend preset pages break until sub-project ③ rewires them.
  ```

- [ ] **Step 9.2: Update doc 06 (API design)**

  In `dev_docs/06_api_design_specification.md`:
  - Update `POST /runs` request body: `preset → strategy + params`.
  - Add `GET /strategies` entry.
  - Remove `GET /presets` entry.

- [ ] **Step 9.3: Update doc 21 (data contract)**

  In `dev_docs/21_data_contract.md`:
  - In the `runs` table DDL section: `preset VARCHAR` → `strategy VARCHAR`.
  - Note that params (JSONB) now carries the strategy-specific param snapshot.

- [ ] **Step 9.4: Update doc 16 WBS**

  In `dev_docs/16_wbs.md`:
  - Mark sub-project ① task(s) as complete with today's date.

- [ ] **Step 9.5: Commit**

  ```bash
  git add dev_docs/
  git commit -m "docs: ADR-028 + doc 06/21/16 sync for strategy dispatch contract (sub-project ①)

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 10: Final verification & equivalence guard

- [ ] **Step 10.1: Run full test suite in worktree**

  ```bash
  cd /home/os-sunnie.gd.weng/python_workstation/github_sunny/Quantitative_Trading--strategy-dispatch/backtest_platform
  uv run pytest --tb=short -q
  ```
  Expected: all green; coverage ≥ 80% on changed modules.

- [ ] **Step 10.2: Equivalence smoke test (four_layer)**

  ```bash
  uv run python -c "
  from backtest_platform.research import runners  # noqa
  from backtest_platform.research.run_config import RunConfig
  from backtest_platform.research.is_harness import run_is
  from backtest_platform.research.is_harness import load_merged_parquet
  from datetime import date

  cfg = RunConfig(
      hypothesis='equivalence guard — four_layer via new dispatch',
      strategy='four_layer',
      params={},   # all defaults
      stocks=('2330', '2317'),
      is_start=date(2023, 1, 1),
      is_end=date(2023, 12, 31),
  )
  m = run_is(cfg)
  assert 'cagr' in m, f'missing cagr in {m.keys()}'
  print('equivalence guard PASSED — four_layer dispatches cleanly via new contract')
  "
  ```
  Expected: prints PASSED.

- [ ] **Step 10.3: curl end-to-end (DB up + uvicorn running)**

  ```bash
  # Terminal 1
  uvicorn backtest_platform.api.app:app --port 8000

  # Terminal 2 — list strategies (no DB needed)
  curl -s http://localhost:8000/strategies | python3 -m json.tool | head -30

  # Terminal 3 — run momentum (DB optional; works with jsonl-only mode)
  curl -s -X POST http://localhost:8000/runs \
    -H "Content-Type: application/json" \
    -d '{"hypothesis":"e2e test","strategy":"momentum","params":{"lookback_days":120},"stocks":["2330","2317"],"is_start":"2022-01-01","is_end":"2023-12-31"}' \
    | python3 -m json.tool
  ```
  Expected: `GET /strategies` returns JSON array with name/title/config_schema;
  `POST /runs` returns HTTP 201 with run_id + metrics.

- [ ] **Step 10.4: Final commit (if any cleanup)**

  Commit any cleanup found during verification.

---

## Plan Self-Review Results

- **Spec coverage:** §4.1–4.7 all have corresponding Tasks 1–9. HTTP (§4.7) = Task 7. Conformance (§4.5) = Task 4. CLI (§4.6) = Task 6. Doc sync (§8.3) = Task 9. ✅
- **Placeholder scan:** No TBD/TODO. Every step has code. ✅
- **Type consistency:** `config_model: ClassVar[type[BaseModel]]` declared in Task 2; consumed in Task 4 (`runner.config_model()`) and Task 5 (`runner.config_model(**cfg.params)`). `StrategyInfo` defined in Task 2, consumed in Task 7. `ConformanceReport` defined in Task 4, consumed in Task 6. ✅
- **Open Q resolution:** Q1 (momentum no real import) → no action. Q2 (db_writer) → Task 8. Q3 (zipline) → Task 1 Step 1.2. Q4 (runners aggregator) → Task 5 Step 5.3. ✅
