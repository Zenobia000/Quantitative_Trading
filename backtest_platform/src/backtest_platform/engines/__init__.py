"""Backtest engine adapters (rqalpha primary, vectorbt secondary).

Implementations land in M2. This package exists so the import path is stable
and so the engines submodule can be referenced from tests / docs.
"""
from backtest_platform.engines.protocol import (
    Engine,
    EngineName,
    Loader,
    SimEngine,
    get_engine,
)

__all__ = ["Engine", "EngineName", "Loader", "SimEngine", "get_engine"]
