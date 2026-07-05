"""OHLC candles + entry/exit markers for one run's stock (Trade Review K-line).

``GET /runs/{id}/candles`` (runs_series router) backs the逐筆覆盤 page's
candlestick chart: daily OHLC bars for one stock over the run's IS window, plus
entry ▲ / exit ▼ markers derived from the SAME signal pipeline that produces
``/runs/{id}/trades``.

Why re-derive markers instead of reading the trades sidecar
-----------------------------------------------------------
The persisted per-run trades (``run_series_store``) carry only
``{ret, hold, entry_structure}`` — no dates, prices, or symbol — so they cannot
place a marker on a calendar axis. This module re-runs the strategy's signaled
window for the requested stock and pairs its ``buy`` → ``stoploss``/``exit``
actions into dated markers. Real signals, never fabricated points
(``frontend/GOAL.md`` #8 / ``rules/coding-style.md`` 輸入驗證).

Design
------
Pure transforms (``bars_to_candles`` / ``sig_to_markers``) are split from IO
(``load_daily_bars`` / ``derive_markers``) so they unit-test without the parquet
cache. A cache miss makes ``build_candles`` return ``None`` → the router emits a
typed-empty ``pending`` envelope (never a 500), matching the platform's
typed-empty convention (``api/routers/system.py``).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

#: Default parquet cache root (mirrors ``research.is_harness.PARQUET_DIR``).
PARQUET_DIR = "data/parquet"

#: The one per-stock, event-driven strategy that exposes a per-bar signaled
#: window; panel strategies (momentum/inst_flow) have no per-bar entry/exit.
_MARKER_STRATEGY = "four_layer"


def load_daily_bars(
    stock: str, parquet_dir: str | Path = PARQUET_DIR
) -> pd.DataFrame | None:
    """Read one stock's ``daily_bars__<sid>.parquet``; ``None`` on cache miss."""
    path = Path(parquet_dir) / f"daily_bars__{stock}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def _window_bounds(record: Mapping[str, Any]) -> tuple[Any, Any]:
    """Resolve a run's IS window, tolerating both ledger shapes.

    The real executor writes ``window: [is_start, is_end]``; the list/summary
    projection and test fixtures carry flat ``is_start`` / ``is_end``. Missing
    bounds pass through as ``None`` (no slice).
    """
    win = record.get("window")
    if isinstance(win, Sequence) and not isinstance(win, str) and len(win) >= 2:
        return win[0], win[1]
    return record.get("is_start"), record.get("is_end")


def _slice_window(daily: pd.DataFrame, start: Any, end: Any) -> pd.DataFrame:
    """Slice ``daily`` to ``[start, end]`` (inclusive); blank bounds pass through."""
    df = daily.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    if start:
        df = df[df["trade_date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["trade_date"] <= pd.Timestamp(end)]
    return df.sort_values("trade_date").reset_index(drop=True)


def bars_to_candles(daily: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Pure: a daily_bars frame → an ascending list of OHLC candle dicts.

    Each candle is ``{time: 'YYYY-MM-DD', open, high, low, close, volume}`` — the
    shape lightweight-charts' candlestick series consumes (business-day string
    time). Empty / ``None`` in → ``[]`` out.
    """
    if daily is None or daily.empty:
        return []
    df = daily.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date")
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        vol = row.get("volume")
        out.append(
            {
                "time": row["trade_date"].date().isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(vol) if pd.notna(vol) else 0,
            }
        )
    return out


def sig_to_markers(sig: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Pure: a four-layer signaled window → entry/exit markers (round-trip paired).

    Mirrors ``four_layer_resonance.sim.trades`` pairing (``buy`` →
    ``stoploss``/``exit``) but keeps each leg's date + close so the chart can place
    ▲ (entry) / ▼ (exit). Only completed round-trips emit markers; a still-open
    position at window end does not. Output is time-ascending (entries precede
    their exits, round-trips are chronological) — the order lightweight-charts'
    ``createSeriesMarkers`` requires.
    """
    if sig is None or sig.empty or "action" not in sig.columns:
        return []
    s = sig.reset_index(drop=True)
    dates = pd.to_datetime(s["trade_date"])
    closes = s["close"].astype(float)
    out: list[dict[str, Any]] = []
    entry_i: int | None = None
    for i, action in enumerate(s["action"]):
        if entry_i is None and action == "buy":
            entry_i = i
        elif entry_i is not None and action in ("stoploss", "exit"):
            entry_px = float(closes.iloc[entry_i])
            exit_px = float(closes.iloc[i])
            out.append(
                {
                    "time": dates.iloc[entry_i].date().isoformat(),
                    "kind": "entry",
                    "price": entry_px,
                }
            )
            out.append(
                {
                    "time": dates.iloc[i].date().isoformat(),
                    "kind": "exit",
                    "price": exit_px,
                    "ret": exit_px / entry_px - 1.0 if entry_px else 0.0,
                }
            )
            entry_i = None
    return out


def derive_markers(
    record: Mapping[str, Any],
    stock: str,
    start: Any,
    end: Any,
    loader: Callable[[str], pd.DataFrame] | None = None,
) -> list[dict[str, Any]]:
    """Best-effort entry/exit markers for one stock via the run's signal pipeline.

    Only ``four_layer`` (per-stock event-driven) has a per-bar signaled window;
    panel strategies return no markers (honest — they have no per-bar entry/exit).
    The caller wraps this so any failure (missing flow parquet, param drift)
    degrades to ``[]`` while the candles still render.
    """
    if str(record.get("strategy") or "") != _MARKER_STRATEGY:
        return []
    from backtest_platform.research.is_harness import load_merged_parquet
    from backtest_platform.strategies.four_layer_resonance import sim as fl_sim
    from backtest_platform.strategies.four_layer_resonance.config import StrategyConfig

    cfg = StrategyConfig(**dict(record.get("params") or {}))
    merged = (loader or load_merged_parquet)(stock)
    if merged is None or merged.empty:
        return []
    dates = pd.to_datetime(merged["trade_date"])
    win_start = start or dates.min()
    win_end = end or dates.max()
    sig = fl_sim.signaled_window(merged, cfg, win_start, win_end)
    return sig_to_markers(sig)


def build_candles(
    record: Mapping[str, Any],
    stock: str,
    parquet_dir: str | Path = PARQUET_DIR,
    marker_loader: Callable[[str], pd.DataFrame] | None = None,
) -> dict[str, Any] | None:
    """Assemble ``{candles, markers}`` for one run's stock, or ``None`` on OHLC miss.

    ``None`` tells the router to emit a typed-empty ``pending`` envelope (the
    parquet cache lacks this symbol) instead of a 500.
    """
    start, end = _window_bounds(record)
    daily = load_daily_bars(stock, parquet_dir)
    if daily is None or daily.empty:
        return None
    candles = bars_to_candles(_slice_window(daily, start, end))
    if not candles:
        return None
    try:
        markers = derive_markers(record, stock, start, end, marker_loader)
    except Exception:
        # Markers are a best-effort overlay — a re-derivation failure must never
        # cost the user their (real) candles. Degrade to candles-only.
        markers = []
    return {"candles": candles, "markers": markers}
