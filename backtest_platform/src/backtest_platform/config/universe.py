"""Default backtest universe — the platform-wide stock-list constant.

Extracted from ``data.finmind_bundle`` (dependency-untangle refactor) so
strategy-layer ``research_config`` modules can declare their universe WITHOUT
importing the ingest module. Before this, a strategy's ``research_config``
reached down into the bundle module just for this constant, which (pre-ADR-037)
dragged in the heavy zipline engine and triggered its process-global
bundle-registry side-effect on any import path that touched a research_config.

This module has ZERO heavy dependencies. ``finmind_bundle`` re-exports
``DEFAULT_UNIVERSE`` from here for backward compatibility, so existing importers
(CLI, algorithms) keep working unchanged.
"""
from __future__ import annotations

# Default M2 development universe — small enough to backfill in minutes,
# representative of TSE large/mid caps. Override with UNIVERSE_FINMIND env.
DEFAULT_UNIVERSE: tuple[str, ...] = (
    "2330",  # 台積電
    "2317",  # 鴻海
    "2454",  # 聯發科
    "1101",  # 台泥
    "3008",  # 大立光
    "2882",  # 國泰金
    "1303",  # 南亞
    "2412",  # 中華電
    "2308",  # 台達電
    "2891",  # 中信金
)
