"""Shared pytest fixtures.

Synthetic data here is hand-crafted to exercise specific branches in
``compute_scores`` / ``compute_signals``. Each row aligns to a deliberate
scenario; do not "fix" values without understanding which branch they hit.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig
from backtest_platform.data.schemas import ETLBundle


@pytest.fixture
def config() -> StrategyConfig:
    return StrategyConfig()


@pytest.fixture
def synthetic_uptrend() -> pd.DataFrame:
    """80 trading days, gentle uptrend, positive institutional flows.

    Long enough to clear the 60-day box warmup. Random noise seeded for
    reproducibility.
    """
    rng = np.random.default_rng(42)
    n = 80
    start = date(2024, 1, 2)
    trade_dates = [start + timedelta(days=i) for i in range(n)]

    base = np.linspace(100, 130, n)
    noise = rng.normal(0, 0.5, n)
    close = base + noise
    open_ = close - rng.normal(0.1, 0.3, n)
    high = np.maximum(close, open_) + rng.uniform(0.1, 0.6, n)
    low = np.minimum(close, open_) - rng.uniform(0.1, 0.6, n)
    volume = rng.integers(5000, 15000, n)

    return pd.DataFrame(
        {
            "trade_date": trade_dates,
            "stock_id": "TEST",
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "foreign_buy": rng.integers(100, 1000, n),
            "trust_buy": rng.integers(50, 500, n),
            "dealer_buy": rng.integers(-100, 200, n),
            "top_broker_buy": rng.integers(100, 800, n),
            "key_broker_buy": rng.integers(50, 400, n),
            "gov_broker_buy": rng.integers(0, 200, n),
            "geo_broker_buy": rng.integers(0, 100, n),
            "day_trade_volume": rng.integers(100, 1500, n),
            "margin_offset_volume": rng.integers(0, 300, n),
        }
    )


@pytest.fixture
def synthetic_flameout() -> pd.DataFrame:
    """Same shape as uptrend but trending down + negative flows for the last
    20 bars — exercises flameout / warning / exit signals."""
    rng = np.random.default_rng(7)
    n = 80
    start = date(2024, 1, 2)
    trade_dates = [start + timedelta(days=i) for i in range(n)]

    # rise then fall
    base = np.concatenate([np.linspace(100, 130, 60), np.linspace(130, 105, 20)])
    noise = rng.normal(0, 0.3, n)
    close = base + noise
    open_ = close + rng.normal(0.1, 0.2, n)
    high = np.maximum(close, open_) + rng.uniform(0.1, 0.4, n)
    low = np.minimum(close, open_) - rng.uniform(0.1, 0.4, n)
    volume = rng.integers(5000, 15000, n)

    foreign = np.concatenate([rng.integers(100, 1000, 60), rng.integers(-1000, -100, 20)])
    trust = np.concatenate([rng.integers(50, 400, 60), rng.integers(-400, -50, 20)])

    return pd.DataFrame(
        {
            "trade_date": trade_dates,
            "stock_id": "TEST",
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "foreign_buy": foreign,
            "trust_buy": trust,
            "dealer_buy": rng.integers(-200, 200, n),
            "top_broker_buy": rng.integers(-300, 300, n),
            "key_broker_buy": rng.integers(-200, 200, n),
            "gov_broker_buy": rng.integers(-100, 100, n),
            "geo_broker_buy": rng.integers(-50, 50, n),
            "day_trade_volume": rng.integers(100, 1500, n),
            "margin_offset_volume": rng.integers(0, 300, n),
        }
    )


@pytest.fixture
def empty_etl_bundle() -> ETLBundle:
    cols_daily = [
        "stock_id",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adj_factor",
    ]
    return ETLBundle(
        stock_id="9999",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        daily_bars=pd.DataFrame(columns=cols_daily),
        institutional=pd.DataFrame(
            columns=["stock_id", "trade_date", "foreign_buy", "trust_buy", "dealer_buy"]
        ),
        broker_chips=pd.DataFrame(
            columns=[
                "stock_id",
                "trade_date",
                "top_broker_buy",
                "key_broker_buy",
                "gov_broker_buy",
                "geo_broker_buy",
                "day_trade_volume",
                "margin_offset_volume",
            ]
        ),
    )
