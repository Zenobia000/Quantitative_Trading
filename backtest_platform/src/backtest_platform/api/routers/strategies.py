"""GET /strategies — strategy catalog + strategy-package descriptors (ADR-028/008)."""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.research import runners as _runners  # noqa: F401 — registers all strategies
from backtest_platform.research.workflows.loader import get_doe_config, list_workflow_configs
from backtest_platform.strategies.protocol import describe_strategies, describe_strategy, get_strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


class StrategyPackageFile(BaseModel):
    path: str
    role: str
    present: bool


class StrategyAssetData(BaseModel):
    strategy: str
    package: str
    package_path: str
    files: list[StrategyPackageFile]
    workflows: list[str]
    endpoints: dict[str, str]


class StrategyOptimizationData(BaseModel):
    strategy: str
    config_schema: dict[str, Any]
    optimization: dict[str, Any] | None


_PACKAGE_FILES: tuple[tuple[str, str], ...] = (
    ("__init__.py", "package_export"),
    ("strategy.py", "alpha_logic"),
    ("runner.py", "platform_adapter"),
    ("research_config.py", "research_workflows"),
    ("README.md", "human_docs"),
)


def _strategy_or_404(strategy: str):
    try:
        return get_strategy(strategy)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"resource": "strategy", "id": strategy, "message": str(exc)},
        ) from None


def _package_info(strategy: str) -> tuple[str, Path]:
    runner = _strategy_or_404(strategy)
    package = type(runner).__module__.rsplit(".", 1)[0]
    mod = importlib.import_module(package)
    package_file = getattr(mod, "__file__", None)
    if package_file is None:
        raise HTTPException(
            status_code=500,
            detail={"resource": "strategy", "id": strategy, "message": "strategy package has no __file__"},
        )
    return package, Path(package_file).resolve().parent


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


@router.get("", response_model=Envelope)
def list_strategies_endpoint() -> Envelope:
    """Return all registered strategies with name, title, description, and config JSON-schema."""
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


@router.get("/{strategy}/asset", response_model=Envelope[StrategyAssetData])
def strategy_asset(strategy: str) -> Envelope:
    """Strategy Package descriptor (ADR-008).

    Projects the repo folder behind one registered strategy into a frontend-safe
    read model. The browser never reads Python files directly; it sees which
    package files are present and which workflow/config endpoints can be used.
    """
    package, package_dir = _package_info(strategy)
    try:
        workflows = list_workflow_configs(strategy)
    except ValueError:
        workflows = []
    files = [
        StrategyPackageFile(path=name, role=role, present=(package_dir / name).exists())
        for name, role in _PACKAGE_FILES
    ]
    return ok(
        StrategyAssetData(
            strategy=strategy,
            package=package,
            package_path=_display_path(package_dir),
            files=files,
            workflows=workflows,
            endpoints={
                "catalog": "/strategies",
                "run": "/runs",
                "optimization_schema": f"/strategies/{strategy}/optimization-schema",
                "workflow_submit": "/research/workflows/doe",
            },
        )
    )


@router.get("/{strategy}/optimization-schema", response_model=Envelope[StrategyOptimizationData])
def strategy_optimization_schema(strategy: str) -> Envelope:
    """Per-strategy DOE grid read model for the optimization UI (ADR-008)."""
    _strategy_or_404(strategy)
    info = describe_strategy(strategy)
    optimization: dict[str, Any] | None = None
    try:
        doe = get_doe_config(strategy)
    except (ValueError, AttributeError):
        optimization = None
    else:
        optimization = {
            "workflow": "doe",
            "grid": doe.grid,
            "n_configs": doe.n_configs,
            "is_start": doe.is_start.isoformat(),
            "is_end": doe.is_end.isoformat(),
            "symbols_count": len(doe.symbols),
            "symbols_preview": list(doe.symbols[:8]),
        }
    return ok(
        StrategyOptimizationData(
            strategy=strategy,
            config_schema=info.config_schema,
            optimization=optimization,
        )
    )
