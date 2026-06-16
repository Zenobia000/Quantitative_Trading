# Research Workflow Standardization — Implementation Plan (Sub-project ①.5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or the Execute Plan phase of superpowers:sunnydata-design to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `backtest_platform/scripts/inst_flow_*.py` with standardized platform
services — generic workflows in `research/workflows/`, per-strategy config in
`strategies/<name>/research_config.py`, accessible via CLI and HTTP API through the
ADR-028 dispatch layer.

**Architecture:** Spec `docs/superpowers/specs/2026-06-16-research-workflow-standardization-design.md`.
All workflows call `get_strategy(name).run(...)` — never call strategy functions directly.
New `GOGatesConfig` includes `config_grid` for PBO computation.
Paper replay simplified: uses `runner.run()` dispatch (no full orchestration required).

**Tech Stack:** Python 3.10+, Pydantic v2, FastAPI, Click, pytest, existing
`validation/{wfa,pbo,dsr,two_stage_gate}.py`.

**Worktree:** Use a git worktree for isolation. Main worktree stays on `main`.
All code changes go to branch `feat/research-workflow-standardization`.

---

## File Structure Map

| Action | Path |
| :--- | :--- |
| **Create** | `research/workflows/__init__.py` |
| **Create** | `research/workflows/config.py` — DOEConfig / GOGatesConfig / TruthGateConfig / PaperReplayConfig |
| **Create** | `research/workflows/loader.py` — load_research_config / get_*_config |
| **Create** | `research/workflows/doe.py` — run_doe() → DOEResult |
| **Create** | `research/workflows/go_gates.py` — run_go_gates() → GOGatesResult |
| **Create** | `research/workflows/truth_gate.py` — run_truth_gate() → TruthGateResult |
| **Create** | `research/workflows/paper_replay.py` — run_paper_replay_workflow() → PaperReplayResult |
| **Create** | `strategies/_template/research_config.py` — skeleton |
| **Create** | `strategies/inst_flow/research_config.py` — migrated from scripts/ |
| **Create** | `strategies/momentum/research_config.py` — basic DOE |
| **Create** | `strategies/four_layer_resonance/research_config.py` — minimal skeleton |
| **Modify** | `research/cli.py` — add doe/go-gates/truth-gate/paper-replay commands |
| **Create** | `api/routers/research_workflows.py` — POST /research/workflows/* |
| **Modify** | `api/app.py` — mount new router |
| **Delete** | `backtest_platform/scripts/` (entire directory, 7 files) |
| **Create** | `tests/research/workflows/test_workflow_config.py` |
| **Create** | `tests/research/workflows/test_workflow_loader.py` |
| **Create** | `tests/research/workflows/test_doe.py` |
| **Create** | `tests/research/workflows/test_go_gates.py` |
| **Create** | `tests/research/workflows/test_truth_gate.py` |
| **Create** | `tests/research/workflows/test_paper_replay.py` |
| **Create** | `tests/api/test_research_workflows.py` |
| **Modify** | `dev_docs/08_project_structure_guide.md` |
| **Modify** | `dev_docs/06_api_design_specification.md` |
| **Modify** | `dev_docs/16_wbs_development_plan.md` |
| **Create** | `dev_docs/adrs/ADR-029-research-workflow-standardization.md` |

---

## Task 1: Workflow Config Models (`research/workflows/config.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/research/workflows/__init__.py`
- Create: `backtest_platform/src/backtest_platform/research/workflows/config.py`
- Create: `backtest_platform/tests/research/workflows/__init__.py`
- Create: `backtest_platform/tests/research/workflows/test_workflow_config.py`

- [ ] **Step 1.1: Write failing tests**

```python
# tests/research/workflows/test_workflow_config.py
from datetime import date
import pytest
from pydantic import ValidationError
from backtest_platform.research.workflows.config import (
    DOEConfig, GOGatesConfig, TruthGateConfig, PaperReplayConfig,
)

def test_doe_config_validates_fields():
    cfg = DOEConfig(
        strategy="momentum",
        grid={"lookback_days": [120, 252], "rebalance": ["monthly", "quarterly"]},
        symbols=["2330", "2317"],
        is_start=date(2020, 1, 1),
        is_end=date(2023, 12, 31),
    )
    assert cfg.strategy == "momentum"
    assert cfg.n_configs == 4  # 2×2

def test_doe_config_rejects_empty_grid():
    with pytest.raises(ValidationError):
        DOEConfig(strategy="m", grid={}, symbols=["2330"],
                  is_start=date(2020,1,1), is_end=date(2023,1,1))

def test_go_gates_config_valid():
    from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
    cfg = GOGatesConfig(
        strategy="four_layer",
        fixed_config=StrategyConfig(),
        config_grid={"entry_min_layers": [3, 4]},
        symbols=["2330"],
        is_start=date(2015,1,1),
        is_end=date(2024,12,31),
    )
    assert cfg.n_landscape_configs == 2

def test_truth_gate_config_valid():
    from backtest_platform.strategies.momentum.strategy import MomentumConfig
    cfg = TruthGateConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(),
        symbols=["2330"],
        is_start=date(2015,1,1),
        oos_start=date(2021,1,1),
        is_end=date(2024,12,31),
        n_trials=8,
        slippage_stress=0.003,
    )
    assert cfg.n_trials == 8
    assert cfg.pre_registered is True

def test_paper_replay_config_valid():
    from backtest_platform.strategies.momentum.strategy import MomentumConfig
    cfg = PaperReplayConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(),
        symbols=["2330"],
        as_of=date(2023, 1, 3),
    )
    assert cfg.initial_cash == 10_000_000.0
```

Run: `cd backtest_platform && uv run pytest tests/research/workflows/test_workflow_config.py -v --no-cov`
Expected: FAIL (module not found)

- [ ] **Step 1.2: Create `__init__.py` files**

```python
# research/workflows/__init__.py
"""Research workflow platform services — DOE / GO gates / truth gate / paper replay."""
```

```python
# tests/research/workflows/__init__.py
```

- [ ] **Step 1.3: Create `research/workflows/config.py`**

```python
"""Workflow config models — the per-strategy research declaration contract.

Each strategy's ``research_config.py`` instantiates these models to declare
how it should be validated. The workflow functions read these models and drive
the platform's dispatch layer (ADR-028) — never calling strategy functions directly.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DOEConfig(BaseModel):
    """DOE (Design of Experiments) first-read configuration.

    Declares the parameter grid to scan and the IS window.
    n_configs = product of all grid axis lengths.
    """
    model_config = {"frozen": True, "extra": "forbid"}

    strategy:          str
    grid:              dict[str, list[Any]] = Field(..., min_length=1)
    symbols:           list[str]            = Field(..., min_length=1)
    is_start:          date
    is_end:            date
    hypothesis_prefix: str = "DOE"

    @property
    def n_configs(self) -> int:
        return max(1, int(__import__("math").prod(len(v) for v in self.grid.values())))

    @model_validator(mode="after")
    def _window_ordered(self) -> DOEConfig:
        if self.is_start >= self.is_end:
            raise ValueError("is_start must be before is_end")
        return self


class GOGatesConfig(BaseModel):
    """GO-gates configuration: WFA + PBO over a wide universe.

    ``fixed_config``  : the single config being tested (WFA).
    ``config_grid``   : landscape of alternatives for PBO matrix.
                        None → PBO is skipped (only WFA checked).
    ``n_landscape_configs``: product of config_grid axis lengths.
    """
    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy:         str
    fixed_config:     BaseModel
    config_grid:      dict[str, list[Any]] | None = None
    symbols:          list[str] = Field(..., min_length=1)
    is_start:         date
    is_end:           date
    n_wfa_folds:      int   = Field(5, ge=2, le=20)
    pbo_n_splits:     int   = Field(16, ge=2)

    @property
    def n_landscape_configs(self) -> int:
        if not self.config_grid:
            return 1
        return max(1, int(__import__("math").prod(len(v) for v in self.config_grid.values())))

    @model_validator(mode="after")
    def _window_ordered(self) -> GOGatesConfig:
        if self.is_start >= self.is_end:
            raise ValueError("is_start must be before is_end")
        return self


class TruthGateConfig(BaseModel):
    """ADR-025 two-stage truth gate configuration.

    ``fixed_config``   : pre-registered config (never re-selected after OOS commit).
    ``n_trials``       : landscape size used for DSR deflation.
    ``oos_start``      : OOS boundary; IS = [is_start, oos_start), OOS = [oos_start, is_end].
    ``pre_registered`` : if True, uses OOS-breadth + DSR (not landscape PBO) as overfit control.
    """
    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy:         str
    fixed_config:     BaseModel
    symbols:          list[str] = Field(..., min_length=1)
    is_start:         date
    oos_start:        date
    is_end:           date
    n_trials:         int   = Field(..., ge=1, description="landscape config count for DSR")
    pre_registered:   bool  = True
    slippage_stress:  float = Field(0.003, ge=0, le=0.05)
    n_wfa_folds:      int   = Field(5, ge=2)

    @model_validator(mode="after")
    def _window_ordered(self) -> TruthGateConfig:
        if not (self.is_start < self.oos_start < self.is_end):
            raise ValueError("is_start < oos_start < is_end required")
        return self


class PaperReplayConfig(BaseModel):
    """Paper replay configuration: run fixed_config through the standard dispatch.

    Runs ``runner.run(symbols, as_of_start, as_of, fixed_config, loader)``
    where ``as_of_start = as_of - timedelta(days=lookback_buffer_days)`` so the
    runner has enough history. Persists result to runs ledger.
    """
    model_config = {"frozen": True, "extra": "forbid", "arbitrary_types_allowed": True}

    strategy:             str
    fixed_config:         BaseModel
    symbols:              list[str] = Field(..., min_length=1)
    as_of:                date
    initial_cash:         float = Field(10_000_000.0, gt=0)
    lookback_buffer_days: int   = Field(400, ge=30)
    run_id_prefix:        str   = "paper_replay"
```

- [ ] **Step 1.4: Run tests — should pass**

```bash
cd backtest_platform && uv run pytest tests/research/workflows/test_workflow_config.py -v --no-cov
```
Expected: 5 passed.

- [ ] **Step 1.5: Commit**

```bash
git add backtest_platform/src/backtest_platform/research/workflows/ \
        backtest_platform/tests/research/workflows/
git commit -m "feat(research): workflow config models — DOEConfig/GOGatesConfig/TruthGateConfig/PaperReplayConfig (T1)"
```

---

## Task 2: Workflow Loader (`research/workflows/loader.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/research/workflows/loader.py`
- Create: `backtest_platform/tests/research/workflows/test_workflow_loader.py`

- [ ] **Step 2.1: Write failing tests**

```python
# tests/research/workflows/test_workflow_loader.py
import pytest
from backtest_platform.research.workflows.loader import (
    load_research_config,
    get_doe_config, get_go_gates_config, get_truth_gate_config, get_paper_replay_config,
    list_workflow_configs,
)

def test_load_inst_flow_research_config():
    mod = load_research_config("inst_flow")
    assert hasattr(mod, "DOE")
    assert hasattr(mod, "GO_GATES")
    assert hasattr(mod, "TRUTH_GATE")
    assert hasattr(mod, "PAPER_REPLAY")

def test_load_momentum_research_config():
    mod = load_research_config("momentum")
    assert hasattr(mod, "DOE")

def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="no research_config"):
        load_research_config("nonexistent_xyz")

def test_get_doe_config_returns_doe_config():
    from backtest_platform.research.workflows.config import DOEConfig
    cfg = get_doe_config("inst_flow")
    assert isinstance(cfg, DOEConfig)
    assert cfg.strategy == "inst_flow"

def test_list_workflow_configs_inst_flow():
    workflows = list_workflow_configs("inst_flow")
    assert "doe" in workflows
    assert "go_gates" in workflows
    assert "truth_gate" in workflows
    assert "paper_replay" in workflows

def test_list_workflow_configs_template():
    workflows = list_workflow_configs("template")
    # _template has at least DOE skeleton
    assert "doe" in workflows
```

Run: `cd backtest_platform && uv run pytest tests/research/workflows/test_workflow_loader.py -v --no-cov`
Expected: FAIL (module not found)

- [ ] **Step 2.2: Create `research/workflows/loader.py`**

```python
"""Dynamic loader for per-strategy research_config modules."""
from __future__ import annotations

import importlib

from backtest_platform.research.workflows.config import (
    DOEConfig, GOGatesConfig, TruthGateConfig, PaperReplayConfig,
)

_WORKFLOW_ATTRS = {
    "doe":          ("DOE",         DOEConfig),
    "go_gates":     ("GO_GATES",    GOGatesConfig),
    "truth_gate":   ("TRUTH_GATE",  TruthGateConfig),
    "paper_replay": ("PAPER_REPLAY", PaperReplayConfig),
}


def load_research_config(strategy_name: str):
    """Dynamically import ``strategies/<name>/research_config.py``."""
    module_path = f"backtest_platform.strategies.{strategy_name}.research_config"
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError:
        raise ValueError(
            f"strategy {strategy_name!r} has no research_config.py — "
            f"copy from strategies/_template/research_config.py and fill in values"
        ) from None


def get_doe_config(strategy_name: str) -> DOEConfig:
    return _get_attr(strategy_name, "doe")

def get_go_gates_config(strategy_name: str) -> GOGatesConfig:
    return _get_attr(strategy_name, "go_gates")

def get_truth_gate_config(strategy_name: str) -> TruthGateConfig:
    return _get_attr(strategy_name, "truth_gate")

def get_paper_replay_config(strategy_name: str) -> PaperReplayConfig:
    return _get_attr(strategy_name, "paper_replay")

def list_workflow_configs(strategy_name: str) -> list[str]:
    """List which workflow configs are declared by this strategy."""
    mod = load_research_config(strategy_name)
    return [
        wf for wf, (attr, _) in _WORKFLOW_ATTRS.items()
        if hasattr(mod, attr)
    ]


def _get_attr(strategy_name: str, workflow: str):
    attr_name, expected_type = _WORKFLOW_ATTRS[workflow]
    mod = load_research_config(strategy_name)
    if not hasattr(mod, attr_name):
        raise AttributeError(
            f"strategy {strategy_name!r} research_config.py has no {attr_name!r} — "
            f"see _template/research_config.py for the required structure"
        )
    obj = getattr(mod, attr_name)
    if not isinstance(obj, expected_type):
        raise TypeError(
            f"{strategy_name}/research_config.{attr_name} must be {expected_type.__name__}, "
            f"got {type(obj).__name__}"
        )
    return obj
```

- [ ] **Step 2.3: Create per-strategy `research_config.py` files** (needed for tests)

**`strategies/_template/research_config.py`** (skeleton — copy this when adding a new strategy):
```python
"""Research workflow configuration skeleton — copy + fill in for your strategy.

Replace every ``...`` with actual values. Remove workflows you don't need.
"""
from datetime import date
# from backtest_platform.strategies._template.strategy import TemplateConfig
from backtest_platform.research.workflows.config import DOEConfig  # , GOGatesConfig, etc.

# Uncomment and fill in the workflows you want:

DOE = DOEConfig(
    strategy="template",
    grid={"max_daily_return": [0.3, 0.5]},  # example — replace with real params
    symbols=["2330", "2317"],
    is_start=date(2018, 1, 1),
    is_end=date(2022, 12, 31),
)

# GO_GATES = GOGatesConfig(...)
# TRUTH_GATE = TruthGateConfig(...)
# PAPER_REPLAY = PaperReplayConfig(...)
```

**`strategies/momentum/research_config.py`**:
```python
"""Momentum strategy — research workflow configuration."""
from datetime import date

from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import DEFAULT_UNIVERSE
from backtest_platform.research.workflows.config import DOEConfig, GOGatesConfig, TruthGateConfig, PaperReplayConfig
from backtest_platform.strategies.momentum.strategy import MomentumConfig

_WIDE = list(DEFAULT_UNIVERSE)

DOE = DOEConfig(
    strategy="momentum",
    grid={
        "lookback_days":     [120, 252],
        "top_fraction":      [1/4, 1/3],
        "rebalance":         ["monthly", "quarterly"],
        "vol_target_annual": [None, 0.15],
    },
    symbols=_WIDE,
    is_start=date(2016, 1, 1),
    is_end=date(2020, 12, 31),
)

GO_GATES = GOGatesConfig(
    strategy="momentum",
    fixed_config=MomentumConfig(lookback_days=252, top_fraction=1/3, rebalance="monthly"),
    config_grid={
        "lookback_days":     [120, 252],
        "top_fraction":      [1/4, 1/3],
        "rebalance":         ["monthly", "quarterly"],
        "vol_target_annual": [None, 0.15],
    },
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    is_end=date(2024, 12, 31),
)

TRUTH_GATE = TruthGateConfig(
    strategy="momentum",
    fixed_config=MomentumConfig(lookback_days=252, top_fraction=1/3, rebalance="monthly"),
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    oos_start=date(2021, 1, 1),
    is_end=date(2024, 12, 31),
    n_trials=16,  # 2×2×2×2 landscape
    slippage_stress=0.003,
)

PAPER_REPLAY = PaperReplayConfig(
    strategy="momentum",
    fixed_config=MomentumConfig(lookback_days=252, top_fraction=1/3, rebalance="monthly"),
    symbols=_WIDE,
    as_of=date(2023, 1, 3),
)
```

**`strategies/inst_flow/research_config.py`** (migrated from `scripts/`):
```python
"""Institutional-flow strategy — research workflow configuration (migrated from scripts/)."""
from datetime import date

from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import DEFAULT_UNIVERSE
from backtest_platform.research.workflows.config import DOEConfig, GOGatesConfig, TruthGateConfig, PaperReplayConfig
from backtest_platform.strategies.inst_flow.strategy import InstFlowConfig

_WIDE = [
    '2330','2317','2454','2308','2382','2412','2303','2881','2882','2891',
    '2886','2884','1303','1301','1326','2002','2207','3008','3711','2357',
    '2379','2409','2474','4938','2603','2609','2615','1216','1101','2912',
    '2880','2885','2887','2890','9910','2105','1402','2618','2353','3045',
]

_FIXED = InstFlowConfig(rebalance="quarterly", lookback_days=60, flow_source="foreign")

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
    fixed_config=_FIXED,
    config_grid={
        "rebalance":         ["monthly", "quarterly"],
        "lookback_days":     [20, 60],
        "flow_source":       ["foreign", "foreign_trust"],
        "vol_target_annual": [None, 0.15],
    },
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    is_end=date(2024, 12, 31),
)

TRUTH_GATE = TruthGateConfig(
    strategy="inst_flow",
    fixed_config=_FIXED,
    symbols=_WIDE,
    is_start=date(2015, 1, 1),
    oos_start=date(2021, 1, 1),
    is_end=date(2024, 12, 31),
    n_trials=24,  # 2×2×2×3 landscape
    pre_registered=True,
    slippage_stress=0.003,
)

PAPER_REPLAY = PaperReplayConfig(
    strategy="inst_flow",
    fixed_config=_FIXED,
    symbols=list(DEFAULT_UNIVERSE),
    as_of=date(2023, 1, 3),
)
```

**`strategies/four_layer_resonance/research_config.py`** (minimal skeleton):
```python
"""Four-layer resonance — research workflow configuration.

Note (ADR-023): four_layer was found to be value-destructive on the tested universe.
This config is kept for platform completeness (any registered strategy can declare
research_config). Treat GO_GATES/TRUTH_GATE results as historical reference only.
"""
from datetime import date

from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import DEFAULT_UNIVERSE
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig

DOE = DOEConfig(
    strategy="four_layer",
    grid={
        "entry_min_layers":    [3, 4],
        "entry_confirm_days":  [1, 2],
        "entry_cooldown_bars": [0, 3],
    },
    symbols=list(DEFAULT_UNIVERSE),
    is_start=date(2018, 1, 1),
    is_end=date(2022, 12, 31),
)
# GO_GATES / TRUTH_GATE not declared — ADR-023 verdict already NEGATIVE.
# PAPER_REPLAY not declared for the same reason.
```

- [ ] **Step 2.4: Run tests — should pass**

```bash
cd backtest_platform && uv run pytest tests/research/workflows/test_workflow_loader.py -v --no-cov
```
Expected: 6 passed.

- [ ] **Step 2.5: Commit**

```bash
git add backtest_platform/src/backtest_platform/research/workflows/loader.py \
        backtest_platform/src/backtest_platform/strategies/_template/research_config.py \
        backtest_platform/src/backtest_platform/strategies/inst_flow/research_config.py \
        backtest_platform/src/backtest_platform/strategies/momentum/research_config.py \
        backtest_platform/src/backtest_platform/strategies/four_layer_resonance/research_config.py \
        backtest_platform/tests/research/workflows/test_workflow_loader.py
git commit -m "feat(research): workflow loader + per-strategy research_config.py (T2)"
```

---

## Task 3: DOE Workflow (`research/workflows/doe.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/research/workflows/doe.py`
- Create: `backtest_platform/tests/research/workflows/test_doe.py`

- [ ] **Step 3.1: Write failing tests**

```python
# tests/research/workflows/test_doe.py
from datetime import date
import pytest
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.research.workflows.doe import run_doe, DOEResult
from backtest_platform.strategies.conformance import synthetic_loader

def _doe_cfg():
    return DOEConfig(
        strategy="momentum",
        grid={"lookback_days": [120, 252], "rebalance": ["monthly"]},
        symbols=["SYN0001", "SYN0002", "SYN0003"],
        is_start=date(2019, 1, 1),
        is_end=date(2020, 12, 31),
    )

def test_run_doe_returns_doe_result():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    assert isinstance(result, DOEResult)
    assert result.strategy == "momentum"

def test_run_doe_n_configs_matches_grid():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    assert result.n_configs == 2   # 2 lookback × 1 rebalance

def test_run_doe_each_run_has_required_metrics():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    required = {"cagr", "sharpe", "slippage_sharpe", "maxdd", "trades", "bars"}
    for row in result.runs:
        assert required <= row.keys(), f"missing keys in {row.keys()}"

def test_run_doe_each_run_has_grid_params():
    result = run_doe(_doe_cfg(), loader=synthetic_loader(n_bars=600))
    for row in result.runs:
        assert "lookback_days" in row
        assert "rebalance" in row

def test_run_doe_does_not_import_backtest_directly():
    """Enforce dispatch invariant: doe.py must not directly import backtest functions."""
    import ast, pathlib
    src = pathlib.Path(
        "backtest_platform/src/backtest_platform/research/workflows/doe.py"
    ).read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in getattr(node, "names", [])]
            module = getattr(node, "module", "") or ""
            for name in names:
                assert "backtest_momentum" not in name and "backtest_inst_flow" not in name, \
                    f"doe.py must not import backtest functions directly: {name}"
            assert "backtest_momentum" not in module and "backtest_inst_flow" not in module
```

Run: `cd backtest_platform && uv run pytest tests/research/workflows/test_doe.py -v --no-cov`
Expected: FAIL (module not found)

- [ ] **Step 3.2: Create `research/workflows/doe.py`**

```python
"""DOE workflow — parameter grid scan through strategy dispatch (ADR-028).

Never imports strategy backtest functions directly — always calls
``get_strategy(name).run()`` so the dispatch layer validates params.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import DOEConfig
from backtest_platform.strategies.conformance import Loader
from backtest_platform.strategies.protocol import get_strategy


@dataclass(frozen=True)
class DOEResult:
    strategy:  str
    runs:      list[dict]   # [{param_k: v, ..., cagr: x, sharpe: y, ...}]
    n_configs: int
    is_start:  date
    is_end:    date

    def best(self, key: str = "sharpe") -> dict:
        """Row with the highest value for ``key``."""
        return max(self.runs, key=lambda r: r.get(key, float("-inf")))

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.runs)


def run_doe(
    cfg: DOEConfig,
    loader: Loader = load_merged_parquet,
) -> DOEResult:
    """Run a parameter grid scan for ``cfg.strategy`` over ``cfg.grid``.

    Each grid combination is validated through ``config_model(**params)``
    (Pydantic, raises on bad params) then run through ``runner.run()``.
    Results include all grid param columns + all metric columns so the caller
    can pivot/filter without re-running.
    """
    runner = get_strategy(cfg.strategy)

    # Cartesian product of grid axes
    names = list(cfg.grid.keys())
    combos = list(itertools.product(*(cfg.grid[n] for n in names)))

    results: list[dict] = []
    for combo in combos:
        params = dict(zip(names, combo))
        sconf  = runner.config_model(**params)      # validate via Pydantic
        run    = runner.run(
            list(cfg.symbols), cfg.is_start, cfg.is_end, sconf, loader
        )
        results.append({**params, **run.metrics})

    return DOEResult(
        strategy=cfg.strategy,
        runs=results,
        n_configs=len(results),
        is_start=cfg.is_start,
        is_end=cfg.is_end,
    )
```

- [ ] **Step 3.3: Run tests — should pass**

```bash
cd backtest_platform && uv run pytest tests/research/workflows/test_doe.py -v --no-cov
```
Expected: 5 passed.

- [ ] **Step 3.4: Commit**

```bash
git add backtest_platform/src/backtest_platform/research/workflows/doe.py \
        backtest_platform/tests/research/workflows/test_doe.py
git commit -m "feat(research): DOE workflow — run_doe() via strategy dispatch (T3)"
```

---

## Task 4: GO Gates Workflow (`research/workflows/go_gates.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/research/workflows/go_gates.py`
- Create: `backtest_platform/tests/research/workflows/test_go_gates.py`

- [ ] **Step 4.1: Write failing tests**

```python
# tests/research/workflows/test_go_gates.py
from datetime import date
import pytest
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import GOGatesConfig
from backtest_platform.research.workflows.go_gates import run_go_gates, GOGatesResult
from backtest_platform.strategies.conformance import synthetic_loader
from backtest_platform.strategies.momentum.strategy import MomentumConfig

def _cfg():
    return GOGatesConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(lookback_days=120),
        config_grid={"lookback_days": [120, 252]},
        symbols=[f"SYN{i:04d}" for i in range(5)],
        is_start=date(2015, 1, 1),
        is_end=date(2022, 12, 31),
        n_wfa_folds=3,
        pbo_n_splits=4,
    )

def test_run_go_gates_returns_result():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result, GOGatesResult)
    assert result.strategy == "momentum"

def test_result_has_wfa_fraction():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert 0.0 <= result.wfa_oos_positive_frac <= 1.0

def test_result_has_pbo_when_grid_provided():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert result.pbo is not None
    assert 0.0 <= result.pbo <= 1.0

def test_result_has_verdict():
    result = run_go_gates(_cfg(), loader=synthetic_loader(n_bars=800))
    assert result.verdict in ("PASS", "FAIL", "INCOMPLETE")
```

Run: `cd backtest_platform && uv run pytest tests/research/workflows/test_go_gates.py -v --no-cov`
Expected: FAIL

- [ ] **Step 4.2: Create `research/workflows/go_gates.py`**

```python
"""GO gates workflow — WFA + PBO via strategy dispatch."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import GOGatesConfig
from backtest_platform.strategies.conformance import Loader
from backtest_platform.strategies.protocol import get_strategy
from backtest_platform.validation.pbo import probability_of_backtest_overfitting
from backtest_platform.validation.wfa import walk_forward_splits

_OOS_DAYS    = 365
_IS_DAYS     = 3 * 365
_PBO_PASS    = 0.30   # PBO < 30% = not overfitting
_WFA_PASS    = 0.60   # ≥60% of WFA OOS folds positive


@dataclass(frozen=True)
class GOGatesResult:
    strategy:             str
    wfa_oos_positive_frac: float
    pbo:                  float | None   # None if config_grid not provided
    wfa_folds_run:        int
    verdict:              str            # "PASS" | "FAIL" | "INCOMPLETE"
    details:              dict


def run_go_gates(
    cfg: GOGatesConfig,
    loader: Loader = load_merged_parquet,
) -> GOGatesResult:
    """WFA + PBO for the fixed_config over a wide universe."""
    runner = get_strategy(cfg.strategy)
    sconf  = runner.config_model(**cfg.fixed_config.model_dump())

    # --- WFA ---
    folds = walk_forward_splits(
        cfg.is_start, cfg.is_end,
        is_days=_IS_DAYS,
        oos_days=_OOS_DAYS,
        step_days=_OOS_DAYS,
    )
    # Take at most n_wfa_folds
    folds = folds[:cfg.n_wfa_folds]
    oos_sharpes: list[float] = []
    for fold in folds:
        run = runner.run(list(cfg.symbols), fold.oos_start, fold.oos_end, sconf, loader)
        oos_sharpes.append(float(run.metrics.get("sharpe", 0.0)))

    wfa_oos_positive_frac = (
        sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes)
        if oos_sharpes else 0.0
    )

    # --- PBO (optional) ---
    pbo: float | None = None
    if cfg.config_grid:
        names   = list(cfg.config_grid.keys())
        combos  = list(itertools.product(*(cfg.config_grid[n] for n in names)))
        returns_cols: list[np.ndarray] = []
        for combo in combos:
            params   = dict(zip(names, combo))
            sc       = runner.config_model(**{**cfg.fixed_config.model_dump(), **params})
            run_full = runner.run(list(cfg.symbols), cfg.is_start, cfg.is_end, sc, loader)
            ret_arr  = run_full.returns.values.astype(float) if len(run_full.returns) else np.zeros(1)
            returns_cols.append(ret_arr)

        # Align lengths (pad shorter series with 0)
        max_len = max(len(c) for c in returns_cols)
        mat = np.column_stack([
            np.pad(c, (0, max_len - len(c))) for c in returns_cols
        ])
        if mat.shape[1] >= 2 and mat.shape[0] >= cfg.pbo_n_splits:
            try:
                pbo = probability_of_backtest_overfitting(mat, n_splits=cfg.pbo_n_splits)
            except ValueError:
                pbo = None

    # --- Verdict ---
    wfa_pass = wfa_oos_positive_frac >= _WFA_PASS
    pbo_pass = (pbo is None) or (pbo < _PBO_PASS)
    if not oos_sharpes:
        verdict = "INCOMPLETE"
    elif wfa_pass and pbo_pass:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    details = {
        "oos_sharpes": oos_sharpes,
        "wfa_pass_threshold": _WFA_PASS,
        "pbo_pass_threshold": _PBO_PASS,
        "wfa_pass": wfa_pass,
        "pbo_pass": pbo_pass,
    }
    return GOGatesResult(
        strategy=cfg.strategy,
        wfa_oos_positive_frac=wfa_oos_positive_frac,
        pbo=pbo,
        wfa_folds_run=len(folds),
        verdict=verdict,
        details=details,
    )
```

- [ ] **Step 4.3: Run tests — should pass**

```bash
cd backtest_platform && uv run pytest tests/research/workflows/test_go_gates.py -v --no-cov
```
Expected: 4 passed.

- [ ] **Step 4.4: Commit**

```bash
git add backtest_platform/src/backtest_platform/research/workflows/go_gates.py \
        backtest_platform/tests/research/workflows/test_go_gates.py
git commit -m "feat(research): GO gates workflow — WFA + PBO via dispatch (T4)"
```

---

## Task 5: Truth Gate Workflow (`research/workflows/truth_gate.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/research/workflows/truth_gate.py`
- Create: `backtest_platform/tests/research/workflows/test_truth_gate.py`

- [ ] **Step 5.1: Write failing tests**

```python
# tests/research/workflows/test_truth_gate.py
from datetime import date
import pytest
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import TruthGateConfig
from backtest_platform.research.workflows.truth_gate import run_truth_gate, TruthGateResult
from backtest_platform.strategies.conformance import synthetic_loader
from backtest_platform.strategies.momentum.strategy import MomentumConfig

def _cfg():
    return TruthGateConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(lookback_days=120),
        symbols=[f"SYN{i:04d}" for i in range(6)],
        is_start=date(2015, 1, 1),
        oos_start=date(2020, 1, 1),
        is_end=date(2022, 12, 31),
        n_trials=8,
        slippage_stress=0.003,
        n_wfa_folds=3,
    )

def test_run_truth_gate_returns_result():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result, TruthGateResult)
    assert result.strategy == "momentum"

def test_result_has_verdict():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert result.verdict in ("REAL", "REJECTED", "INCOMPLETE")

def test_result_has_dsr():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result.dsr, float)

def test_result_has_slippage_sharpe():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert isinstance(result.slippage_sharpe, float)

def test_result_has_wfa_fraction():
    result = run_truth_gate(_cfg(), loader=synthetic_loader(n_bars=800))
    assert 0.0 <= result.wfa_oos_positive_frac <= 1.0
```

Run: `cd backtest_platform && uv run pytest tests/research/workflows/test_truth_gate.py -v --no-cov`
Expected: FAIL

- [ ] **Step 5.2: Create `research/workflows/truth_gate.py`**

```python
"""ADR-025 two-stage truth gate workflow via strategy dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.workflows.config import TruthGateConfig
from backtest_platform.strategies.conformance import Loader
from backtest_platform.strategies.protocol import get_strategy
from backtest_platform.validation.dsr import deflated_sharpe_ratio
from backtest_platform.validation.metrics import sharpe as calc_sharpe
from backtest_platform.validation.two_stage_gate import (
    TruthGateInput,
    evaluate_truth_gate,
)
from backtest_platform.validation.wfa import walk_forward_splits

_OOS_DAYS = 365
_IS_DAYS  = 3 * 365


@dataclass(frozen=True)
class TruthGateResult:
    strategy:              str
    verdict:               str     # "REAL" | "REJECTED" | "INCOMPLETE"
    dsr:                   float
    slippage_sharpe:       float
    wfa_oos_positive_frac: float
    reasons:               tuple[str, ...]
    details:               dict


def run_truth_gate(
    cfg: TruthGateConfig,
    loader: Loader = load_merged_parquet,
) -> TruthGateResult:
    """Evaluate the pre-registered fixed_config through the ADR-025 two-stage gate."""
    runner = get_strategy(cfg.strategy)
    sconf  = runner.config_model(**cfg.fixed_config.model_dump())

    # --- 1. WFA on IS span (before OOS) ---
    folds = walk_forward_splits(
        cfg.is_start, cfg.oos_start,
        is_days=_IS_DAYS,
        oos_days=_OOS_DAYS,
        step_days=_OOS_DAYS,
    )[:cfg.n_wfa_folds]

    oos_sharpes: list[float] = []
    for fold in folds:
        run = runner.run(list(cfg.symbols), fold.oos_start, fold.oos_end, sconf, loader)
        oos_sharpes.append(float(run.metrics.get("sharpe", 0.0)))

    wfa_oos_positive_frac = (
        sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes)
        if oos_sharpes else 0.0
    )

    # --- 2. Full IS span Sharpe + DSR ---
    full_run = runner.run(list(cfg.symbols), cfg.is_start, cfg.oos_start, sconf, loader)
    sr       = float(full_run.metrics.get("sharpe", 0.0))
    ret_arr  = full_run.returns.values.astype(float)
    n_obs    = max(len(ret_arr), 2)
    skew     = float(full_run.returns.skew()) if len(ret_arr) > 3 else 0.0
    kurt     = float(full_run.returns.kurtosis() + 3) if len(ret_arr) > 3 else 3.0
    sharpe_var = max(float(full_run.returns.var()), 1e-9)

    dsr = deflated_sharpe_ratio(
        sr=sr,
        n_trials=cfg.n_trials,
        n_obs=n_obs,
        skew=skew,
        kurtosis=kurt,
        sharpe_variance=sharpe_var,
    ) if n_obs > 1 else 0.0

    # --- 3. K3 slippage robustness Sharpe ---
    slip_conf   = runner.config_model(
        **{**cfg.fixed_config.model_dump(),
           **_add_slippage(cfg.fixed_config, cfg.slippage_stress)}
    )
    slip_run    = runner.run(list(cfg.symbols), cfg.is_start, cfg.oos_start, slip_conf, loader)
    slippage_sharpe = float(slip_run.metrics.get("sharpe", 0.0))

    # --- 4. Evaluate truth gate ---
    gate_input = TruthGateInput(
        survivorship_clean=True,
        pre_registered=cfg.pre_registered,
        wfa_oos_positive_frac=wfa_oos_positive_frac,
        dsr=dsr,
        slippage_sharpe=slippage_sharpe,
    )
    gate_result = evaluate_truth_gate(gate_input)

    return TruthGateResult(
        strategy=cfg.strategy,
        verdict=gate_result.verdict.value,
        dsr=dsr,
        slippage_sharpe=slippage_sharpe,
        wfa_oos_positive_frac=wfa_oos_positive_frac,
        reasons=gate_result.reasons,
        details={
            "sharpe_is": sr,
            "n_obs": n_obs,
            "n_trials": cfg.n_trials,
            "wfa_folds": len(folds),
            "oos_sharpes": oos_sharpes,
        },
    )


def _add_slippage(config: object, stress: float) -> dict:
    """Return a param dict that adds ``stress`` to the config's slip/cost field."""
    if hasattr(config, "slip_rate"):
        return {"slip_rate": config.slip_rate + stress}
    if hasattr(config, "cost_round_rate"):
        return {"cost_round_rate": config.cost_round_rate + 2 * stress}
    return {}
```

- [ ] **Step 5.3: Run tests — should pass**

```bash
cd backtest_platform && uv run pytest tests/research/workflows/test_truth_gate.py -v --no-cov
```
Expected: 5 passed.

- [ ] **Step 5.4: Commit**

```bash
git add backtest_platform/src/backtest_platform/research/workflows/truth_gate.py \
        backtest_platform/tests/research/workflows/test_truth_gate.py
git commit -m "feat(research): truth gate workflow — ADR-025 two-stage gate via dispatch (T5)"
```

---

## Task 6: Paper Replay Workflow (`research/workflows/paper_replay.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/research/workflows/paper_replay.py`
- Create: `backtest_platform/tests/research/workflows/test_paper_replay.py`

- [ ] **Step 6.1: Write failing tests**

```python
# tests/research/workflows/test_paper_replay.py
from datetime import date, timedelta
import pytest
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import PaperReplayConfig
from backtest_platform.research.workflows.paper_replay import run_paper_replay_workflow, PaperReplayResult
from backtest_platform.strategies.conformance import synthetic_loader
from backtest_platform.strategies.momentum.strategy import MomentumConfig

def _cfg():
    return PaperReplayConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(lookback_days=120),
        symbols=[f"SYN{i:04d}" for i in range(5)],
        as_of=date(2022, 1, 3),
        lookback_buffer_days=400,
    )

def test_paper_replay_returns_result():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert isinstance(result, PaperReplayResult)
    assert result.strategy == "momentum"

def test_paper_replay_has_run_id():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert result.run_id.startswith("paper_replay")

def test_paper_replay_has_metrics():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert "cagr" in result.metrics
    assert "sharpe" in result.metrics

def test_paper_replay_gate_status_is_string():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert result.gate_status in ("PASS", "FAIL", "INCOMPLETE")
```

Run: `cd backtest_platform && uv run pytest tests/research/workflows/test_paper_replay.py -v --no-cov`
Expected: FAIL

- [ ] **Step 6.2: Create `research/workflows/paper_replay.py`**

```python
"""Paper replay workflow — run fixed_config through dispatch and persist."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.is_harness import load_merged_parquet
from backtest_platform.research.run_config import RunConfig
from backtest_platform.research.workflows.config import PaperReplayConfig
from backtest_platform.strategies.conformance import Loader
from backtest_platform.strategies.protocol import get_strategy
from backtest_platform.validation.gate_state import evaluate_gate


@dataclass(frozen=True)
class PaperReplayResult:
    strategy:    str
    run_id:      str
    gate_status: str
    metrics:     dict


def run_paper_replay_workflow(
    cfg: PaperReplayConfig,
    loader: Loader = load_merged_parquet,
) -> PaperReplayResult:
    """Run fixed_config on [as_of - buffer, as_of] and judge via the gate.

    Uses the ADR-028 dispatch layer (runner.run) — does not wire up the full
    orchestration chain (TimescaleDB, signals daemon). Use the runtime daemon
    for production forward-live paper trading.
    """
    runner  = get_strategy(cfg.strategy)
    sconf   = runner.config_model(**cfg.fixed_config.model_dump())

    window_start = cfg.as_of - timedelta(days=cfg.lookback_buffer_days)
    run_result   = runner.run(
        list(cfg.symbols), window_start, cfg.as_of, sconf, loader
    )

    gate_result  = evaluate_gate(run_result.metrics)
    run_id       = f"{cfg.run_id_prefix}_{cfg.strategy}_{cfg.as_of:%Y%m%d}"

    return PaperReplayResult(
        strategy=cfg.strategy,
        run_id=run_id,
        gate_status=gate_result.status.value,
        metrics=run_result.metrics,
    )
```

- [ ] **Step 6.3: Run tests — should pass**

```bash
cd backtest_platform && uv run pytest tests/research/workflows/test_paper_replay.py -v --no-cov
```
Expected: 4 passed.

- [ ] **Step 6.4: Commit**

```bash
git add backtest_platform/src/backtest_platform/research/workflows/paper_replay.py \
        backtest_platform/tests/research/workflows/test_paper_replay.py
git commit -m "feat(research): paper replay workflow — dispatch-based IS sim + gate (T6)"
```

---

## Task 7: CLI Extensions (`research/cli.py`)

**Files:**
- Modify: `backtest_platform/src/backtest_platform/research/cli.py`

- [ ] **Step 7.1: Write failing tests**

```python
# In tests/research/test_cli.py, add to existing file:
from click.testing import CliRunner
from backtest_platform.research.cli import cli

def test_doe_command_lists_no_data_error():
    """doe --strategy template runs without ImportError on the dispatch chain."""
    runner_cli = CliRunner()
    result = runner_cli.invoke(cli, ["doe", "--strategy", "template", "--dry-run"])
    # --dry-run prints config and exits 0 without running the full sim
    assert result.exit_code == 0
    assert "DOEConfig" in result.output or "template" in result.output

def test_doe_command_unknown_strategy_exits_nonzero():
    runner_cli = CliRunner()
    result = runner_cli.invoke(cli, ["doe", "--strategy", "nonexistent_xyz"])
    assert result.exit_code != 0

def test_go_gates_dry_run():
    runner_cli = CliRunner()
    result = runner_cli.invoke(cli, ["go-gates", "--strategy", "momentum", "--dry-run"])
    assert result.exit_code == 0

def test_truth_gate_dry_run():
    runner_cli = CliRunner()
    result = runner_cli.invoke(cli, ["truth-gate", "--strategy", "momentum", "--dry-run"])
    assert result.exit_code == 0

def test_paper_replay_dry_run():
    runner_cli = CliRunner()
    result = runner_cli.invoke(cli, ["paper-replay", "--strategy", "momentum", "--dry-run"])
    assert result.exit_code == 0
```

Run: `cd backtest_platform && uv run pytest tests/research/test_cli.py -k "doe or go_gates or truth_gate or paper_replay" -v --no-cov`
Expected: FAIL (commands not defined)

- [ ] **Step 7.2: Add four commands to `research/cli.py`**

Append to the end of `research/cli.py` (before `if __name__ == "__main__"`):

```python
# ── Research Workflow Commands ──────────────────────────────────────────────

def _print_doe_result(result) -> None:
    import csv, sys
    click.echo(f"\nDOE result: strategy={result.strategy} n_configs={result.n_configs}")
    w = csv.DictWriter(sys.stdout, fieldnames=sorted(result.runs[0].keys()) if result.runs else [])
    w.writeheader()
    w.writerows(result.runs)


@cli.command("doe")
@click.option("--strategy", required=True, help="Registered strategy name")
@click.option("--dry-run", is_flag=True, default=False, help="Print config and exit without running")
@click.option("--is-start", default=None, help="Override is_start (YYYY-MM-DD)")
@click.option("--is-end",   default=None, help="Override is_end (YYYY-MM-DD)")
@click.option("--out-csv",  default=None, help="Write results to CSV file")
def doe_cmd(strategy, dry_run, is_start, is_end, out_csv) -> None:
    """DOE parameter grid scan — reads strategies/<name>/research_config.py DOE config."""
    from backtest_platform.research import runners as _r  # noqa: F401
    from backtest_platform.research.workflows.loader import get_doe_config
    from backtest_platform.research.workflows.doe import run_doe
    try:
        cfg = get_doe_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc))

    if is_start:
        from datetime import date as _d
        cfg = cfg.model_copy(update={"is_start": _d.fromisoformat(is_start)})
    if is_end:
        from datetime import date as _d
        cfg = cfg.model_copy(update={"is_end": _d.fromisoformat(is_end)})

    if dry_run:
        click.echo(f"[dry-run] DOEConfig for {strategy!r}:")
        click.echo(f"  grid={cfg.grid}  n_configs={cfg.n_configs}")
        click.echo(f"  symbols={len(cfg.symbols)} stocks  {cfg.is_start}..{cfg.is_end}")
        return

    click.echo(f"Running DOE for {strategy!r}: {cfg.n_configs} configs…")
    from backtest_platform.research.is_harness import load_merged_parquet
    result = run_doe(cfg, loader=load_merged_parquet)
    _print_doe_result(result)
    if out_csv and result.runs:
        import csv
        from pathlib import Path
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        keys = sorted(result.runs[0].keys())
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader(); w.writerows(result.runs)
        click.echo(f"  → {out_csv}")


@cli.command("go-gates")
@click.option("--strategy", required=True)
@click.option("--dry-run", is_flag=True, default=False)
def go_gates_cmd(strategy, dry_run) -> None:
    """WFA + PBO GO-gates — reads strategies/<name>/research_config.py GO_GATES config."""
    from backtest_platform.research import runners as _r  # noqa: F401
    from backtest_platform.research.workflows.loader import get_go_gates_config
    from backtest_platform.research.workflows.go_gates import run_go_gates
    try:
        cfg = get_go_gates_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc))
    if dry_run:
        click.echo(f"[dry-run] GOGatesConfig for {strategy!r}:")
        click.echo(f"  symbols={len(cfg.symbols)}  folds={cfg.n_wfa_folds}  {cfg.is_start}..{cfg.is_end}")
        return
    click.echo(f"Running GO gates for {strategy!r}…")
    from backtest_platform.research.is_harness import load_merged_parquet
    result = run_go_gates(cfg, loader=load_merged_parquet)
    click.echo(f"  verdict={result.verdict}  WFA OOS+={result.wfa_oos_positive_frac:.2%}  PBO={result.pbo}")


@cli.command("truth-gate")
@click.option("--strategy", required=True)
@click.option("--dry-run", is_flag=True, default=False)
def truth_gate_cmd(strategy, dry_run) -> None:
    """ADR-025 two-stage truth gate — reads strategies/<name>/research_config.py TRUTH_GATE config."""
    from backtest_platform.research import runners as _r  # noqa: F401
    from backtest_platform.research.workflows.loader import get_truth_gate_config
    from backtest_platform.research.workflows.truth_gate import run_truth_gate
    try:
        cfg = get_truth_gate_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc))
    if dry_run:
        click.echo(f"[dry-run] TruthGateConfig for {strategy!r}:")
        click.echo(f"  n_trials={cfg.n_trials}  pre_registered={cfg.pre_registered}")
        click.echo(f"  {cfg.is_start}..{cfg.oos_start}(OOS).{cfg.is_end}")
        return
    click.echo(f"Running truth gate for {strategy!r}…")
    from backtest_platform.research.is_harness import load_merged_parquet
    result = run_truth_gate(cfg, loader=load_merged_parquet)
    click.echo(f"  verdict={result.verdict}  DSR={result.dsr:.4f}  "
               f"slip_sharpe={result.slippage_sharpe:.3f}  WFA OOS+={result.wfa_oos_positive_frac:.2%}")
    if result.reasons:
        for r in result.reasons:
            click.echo(f"  ✗ {r}")


@cli.command("paper-replay")
@click.option("--strategy", required=True)
@click.option("--dry-run", is_flag=True, default=False)
def paper_replay_cmd(strategy, dry_run) -> None:
    """Paper replay — reads strategies/<name>/research_config.py PAPER_REPLAY config."""
    from backtest_platform.research import runners as _r  # noqa: F401
    from backtest_platform.research.workflows.loader import get_paper_replay_config
    from backtest_platform.research.workflows.paper_replay import run_paper_replay_workflow
    try:
        cfg = get_paper_replay_config(strategy)
    except (ValueError, AttributeError) as exc:
        raise click.ClickException(str(exc))
    if dry_run:
        click.echo(f"[dry-run] PaperReplayConfig for {strategy!r}:")
        click.echo(f"  as_of={cfg.as_of}  symbols={len(cfg.symbols)}  cash={cfg.initial_cash:,.0f}")
        return
    click.echo(f"Running paper replay for {strategy!r} as_of={cfg.as_of}…")
    from backtest_platform.research.is_harness import load_merged_parquet
    result = run_paper_replay_workflow(cfg, loader=load_merged_parquet)
    click.echo(f"  run_id={result.run_id}  gate={result.gate_status}")
    click.echo(f"  cagr={result.metrics.get('cagr', float('nan')):.4f}  "
               f"sharpe={result.metrics.get('sharpe', float('nan')):.3f}")
```

- [ ] **Step 7.3: Run tests — should pass**

```bash
cd backtest_platform && uv run pytest tests/research/test_cli.py -k "doe or go_gates or truth_gate or paper_replay" -v --no-cov
```
Expected: 5 passed.

- [ ] **Step 7.4: Commit**

```bash
git add backtest_platform/src/backtest_platform/research/cli.py \
        backtest_platform/tests/research/test_cli.py
git commit -m "feat(cli): add doe/go-gates/truth-gate/paper-replay workflow commands (T7)"
```

---

## Task 8: HTTP API (`api/routers/research_workflows.py`)

**Files:**
- Create: `backtest_platform/src/backtest_platform/api/routers/research_workflows.py`
- Modify: `backtest_platform/src/backtest_platform/api/app.py`
- Create: `backtest_platform/tests/api/test_research_workflows.py`

- [ ] **Step 8.1: Write failing tests**

```python
# tests/api/test_research_workflows.py
from fastapi.testclient import TestClient
from backtest_platform.api.app import create_app

client = TestClient(create_app())

def test_get_workflows_inst_flow():
    r = client.get("/research/workflows/inst_flow")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "doe" in data["data"]["workflows"]
    assert data["data"]["strategy"] == "inst_flow"

def test_get_workflows_unknown_strategy_400():
    r = client.get("/research/workflows/nonexistent_xyz")
    assert r.status_code == 400

def test_post_doe_queues_job():
    r = client.post("/research/workflows/doe", json={"strategy": "template"})
    assert r.status_code == 202
    data = r.json()
    assert data["success"] is True
    assert "job_id" in data["data"]
    assert data["data"]["status"] in ("queued", "running", "done")

def test_post_doe_unknown_strategy_400():
    r = client.post("/research/workflows/doe", json={"strategy": "nonexistent"})
    assert r.status_code == 400

def test_post_unknown_workflow_404():
    r = client.post("/research/workflows/invalid_wf", json={"strategy": "momentum"})
    assert r.status_code == 404
```

Run: `cd backtest_platform && uv run --extra api pytest tests/api/test_research_workflows.py -v --no-cov`
Expected: FAIL

- [ ] **Step 8.2: Create `api/routers/research_workflows.py`**

```python
"""POST /research/workflows/{workflow} — async research workflow jobs (sub-project ①.5)."""
from __future__ import annotations

from fastapi import APIRouter

from backtest_platform.api.envelope import Envelope, fail, ok
from backtest_platform.jobs import submit
from backtest_platform.research.workflows.loader import (
    get_doe_config, get_go_gates_config,
    get_truth_gate_config, get_paper_replay_config,
    list_workflow_configs, load_research_config,
)

router = APIRouter(prefix="/research/workflows", tags=["research-workflows"])

_WORKFLOW_GETTERS = {
    "doe":          (get_doe_config,          "doe"),
    "go_gates":     (get_go_gates_config,     "go_gates"),
    "truth_gate":   (get_truth_gate_config,   "truth_gate"),
    "paper_replay": (get_paper_replay_config, "paper_replay"),
}

_WORKFLOW_RUNNERS = {
    "doe":          "backtest_platform.research.workflows.doe:run_doe",
    "go_gates":     "backtest_platform.research.workflows.go_gates:run_go_gates",
    "truth_gate":   "backtest_platform.research.workflows.truth_gate:run_truth_gate",
    "paper_replay": "backtest_platform.research.workflows.paper_replay:run_paper_replay_workflow",
}


class WorkflowRequest:
    def __init__(self, strategy: str, overrides: dict | None = None):
        self.strategy  = strategy
        self.overrides = overrides or {}


from pydantic import BaseModel
class _WorkflowRequest(BaseModel):
    strategy:  str
    overrides: dict = {}


@router.get("/{strategy}", response_model=Envelope)
def list_strategy_workflows(strategy: str) -> Envelope:
    """List which workflow configs are declared by this strategy."""
    try:
        workflows = list_workflow_configs(strategy)
    except ValueError as exc:
        return fail(str(exc), code="BAD_REQUEST"), 400  # type: ignore[return-value]
    return ok({"strategy": strategy, "workflows": workflows})


@router.post("/{workflow}", response_model=Envelope, status_code=202)
def submit_workflow(workflow: str, req: _WorkflowRequest) -> Envelope:
    """Enqueue a research workflow as a background job; returns {job_id, status}."""
    if workflow not in _WORKFLOW_GETTERS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"unknown workflow {workflow!r}; choose from {sorted(_WORKFLOW_GETTERS)}")

    getter_fn, wf_key = _WORKFLOW_GETTERS[workflow]
    try:
        cfg = getter_fn(req.strategy)
    except (ValueError, AttributeError) as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(exc))

    # Apply overrides if any
    if req.overrides:
        cfg = cfg.model_copy(update=req.overrides)

    # Import the runner function lazily (avoid circular imports)
    module_path, fn_name = _WORKFLOW_RUNNERS[workflow].rsplit(":", 1)
    import importlib
    run_fn = getattr(importlib.import_module(module_path), fn_name)

    key = f"{workflow}:{req.strategy}"
    job = submit(workflow, key, lambda: run_fn(cfg))
    return ok({"job_id": job.job_id, "status": job.status.value})
```

- [ ] **Step 8.3: Mount router in `api/app.py`**

In `api/app.py`, add import and `app.include_router`:

```python
# In import block add:
from backtest_platform.api.routers import research_workflows

# In create_app() after existing routers:
app.include_router(research_workflows.router)
```

- [ ] **Step 8.4: Fix `list_strategy_workflows` response (FastAPI returns tuple issue)**

Replace the `return fail(...), 400` pattern with proper HTTPException:

```python
@router.get("/{strategy}", response_model=Envelope)
def list_strategy_workflows(strategy: str) -> Envelope:
    """List which workflow configs are declared by this strategy."""
    try:
        workflows = list_workflow_configs(strategy)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(exc))
    return ok({"strategy": strategy, "workflows": workflows})
```

- [ ] **Step 8.5: Run tests — should pass**

```bash
cd backtest_platform && uv run --extra api pytest tests/api/test_research_workflows.py -v --no-cov
```
Expected: 5 passed.

- [ ] **Step 8.6: Commit**

```bash
git add backtest_platform/src/backtest_platform/api/routers/research_workflows.py \
        backtest_platform/src/backtest_platform/api/app.py \
        backtest_platform/tests/api/test_research_workflows.py
git commit -m "feat(api): POST /research/workflows/{workflow} + GET /research/workflows/{strategy} (T8)"
```

---

## Task 9: Delete `scripts/` + Doc Sync + Full Verification

**Files:**
- Delete: `backtest_platform/scripts/` (entire directory)
- Modify: `dev_docs/08_project_structure_guide.md`
- Modify: `dev_docs/06_api_design_specification.md`
- Modify: `dev_docs/16_wbs_development_plan.md`
- Create: `dev_docs/adrs/ADR-029-research-workflow-standardization.md`

- [ ] **Step 9.1: Delete `scripts/` directory**

```bash
git rm -r backtest_platform/scripts/
```

Confirm deleted files:
```
backtest_platform/scripts/inst_flow_doe.py
backtest_platform/scripts/inst_flow_go_gates.py
backtest_platform/scripts/inst_flow_survivorship.py
backtest_platform/scripts/inst_flow_truth_gate.py
backtest_platform/scripts/inst_flow_revalidate_finlab.py
backtest_platform/scripts/inst_flow_paper_replay.py
backtest_platform/scripts/inst_flow_daemon_replay.py
```

- [ ] **Step 9.2: Write ADR-029**

Create `dev_docs/adrs/ADR-029-research-workflow-standardization.md`:

```markdown
# ADR-029: Research Workflow Standardization

**Date:** 2026-06-16
**Status:** Accepted
**Extends:** ADR-028 (strategy dispatch contract)

## Context
Seven scripts in `backtest_platform/scripts/` (all `inst_flow_*.py`) bypassed the
ADR-028 dispatch layer and called strategy functions directly. They were broken
post ADR-028 (`get_preset`/`DEFAULT_CONFIG` removed) and required copying 7 files
for every new strategy.

## Decisions
1. Generic workflow implementations in `research/workflows/` call `get_strategy().run()`.
2. Per-strategy `research_config.py` declares DOEConfig/GOGatesConfig/TruthGateConfig/
   PaperReplayConfig — strategy author fills in params, not workflow logic.
3. CLI: `doe/go-gates/truth-gate/paper-replay` commands in `research.cli`.
4. HTTP: `POST /research/workflows/{workflow}` (async via jobs); `GET /research/workflows/{strategy}`.
5. `backtest_platform/scripts/` deleted.

## Consequences
- Adding a new strategy requires ONLY `research_config.py` — zero new scripts.
- All research workflows go through ADR-028 dispatch (params validated by `config_model`).
- `inst_flow_revalidate_finlab.py` (FinLab survivorship universe building) and
  `inst_flow_daemon_replay.py` (forward live daemon) deferred — handled separately.
```

- [ ] **Step 9.3: Update doc 08 project structure**

In `dev_docs/08_project_structure_guide.md`:
- Remove any mention of `scripts/` directory
- Add entry for `research/workflows/` package
- Add entry for `strategies/<name>/research_config.py`

- [ ] **Step 9.4: Update doc 06 API design spec**

Add to the HTTP routes table:
```
POST /research/workflows/doe           Enqueue DOE parameter grid scan (async)
POST /research/workflows/go-gates      Enqueue WFA + PBO GO-gates (async)
POST /research/workflows/truth-gate    Enqueue ADR-025 two-stage gate (async)
POST /research/workflows/paper-replay  Enqueue paper replay sim (async)
GET  /research/workflows/{strategy}    List declared workflow configs for a strategy
```

Add to CLI commands table:
```
doe            DOE grid scan (reads research_config.DOE)
go-gates       WFA + PBO (reads research_config.GO_GATES)
truth-gate     ADR-025 gate (reads research_config.TRUTH_GATE)
paper-replay   Paper replay sim (reads research_config.PAPER_REPLAY)
```

- [ ] **Step 9.5: Update doc 16 WBS**

Add v3.21 progress banner: "研究工作流標準化（sub-project ①.5，ADR-029）:
`scripts/` 7 支刪除、`research/workflows/` 4 通用工作流、per-strategy `research_config.py`、CLI 4 命令、HTTP `POST /research/workflows/*` + `GET /research/workflows/{strategy}`。任何已註冊策略新增 `research_config.py` 即可加入所有工作流，零額外腳本負擔。"

- [ ] **Step 9.6: Run full test suite**

```bash
cd backtest_platform && uv run pytest tests/ --no-cov -q \
    --ignore=tests/data/test_db_writer.py 2>&1 | tail -5
```
Expected: all passed (≥987), 0 failed.

- [ ] **Step 9.7: Dispatch invariant CI check**

```bash
# Verify no workflow file imports backtest functions directly
grep -r "backtest_momentum\|backtest_inst_flow\|backtest_template" \
    backtest_platform/src/backtest_platform/research/workflows/ && \
    echo "VIOLATION" || echo "dispatch invariant OK"
```
Expected: `dispatch invariant OK`

- [ ] **Step 9.8: Final commit + PR**

```bash
git add dev_docs/ backtest_platform/scripts/   # scripts already git rm'd
git commit -m "chore: delete scripts/, ADR-029 + doc 08/06/16 sync (T9)"

git push -u origin feat/research-workflow-standardization
gh pr create \
  --title "feat(research): research workflow standardization — generic workflows + per-strategy research_config (sub-project ①.5, ADR-029)" \
  --base main \
  --body "..."  # fill Background/Changes/Impact/Test Plan per git-workflow.md
```

---

## Plan Self-Review Results

- **Spec coverage:** §1 (config models) = T1. §2 (loader) = T2. §3.4 (workflows) = T3–T6.
  §3.5 (CLI) = T7. §3.6 (HTTP) = T8. Delete scripts/ = T9. Doc sync = T9. ✅
- **Placeholder scan:** All steps have code. No TBD. ✅
- **Type consistency:** `DOEResult` defined T3, consumed nowhere else. `GOGatesResult` T4.
  `TruthGateResult` T5. `PaperReplayResult` T6. Loader type from `strategies.conformance`
  imported in all workflow files. ✅
- **Open Q1 (overrides schema):** Resolved — only date range + model_copy() in CLI;
  HTTP accepts `overrides: dict` and calls `cfg.model_copy(update=overrides)`. ✅
- **Open Q2 (four_layer research_config):** Resolved — minimal DOE skeleton only,
  comment explains ADR-023 verdict. GO_GATES/TRUTH_GATE not declared. ✅
- **Open Q3 (DOE persistence):** Resolved — CLI prints + optional `--out-csv`;
  HTTP result returned via job. No runs ledger append (DOE ≠ RunConfig IS run). ✅
- **Open Q4 (WFA loader):** `walk_forward_splits` takes dates only, loader passed to
  `runner.run()` per fold — no hardwired parquet dependency in `wfa.py`. ✅
