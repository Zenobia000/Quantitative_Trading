"""``/presets`` — expose the named StrategyConfig presets.

Read-only window onto ``config.strategy_config.PRESETS`` so a frontend can list
the available strategy variants (v2 / v3 / v3.1b / ...) and inspect one preset's
full parameter set without hard-coding them client-side.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backtest_platform.api.envelope import Envelope, ok
from backtest_platform.api.response_models import PresetData, PresetsListData
from backtest_platform.config.strategy_config import PRESETS, get_preset

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=Envelope[PresetsListData])
def list_presets() -> Envelope:
    """List preset names plus each preset's full parameter dict."""
    configs = {name: cfg.model_dump() for name, cfg in PRESETS.items()}
    return ok({"presets": sorted(PRESETS), "configs": configs})


@router.get("/{name}", response_model=Envelope[PresetData])
def get_one_preset(name: str) -> Envelope:
    """Return one preset's parameters; 404 if the name is unknown."""
    try:
        cfg = get_preset(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return ok(cfg.model_dump())
