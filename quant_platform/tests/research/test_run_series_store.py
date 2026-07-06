"""run_series_store — per-run equity/drawdown/trades sidecar (no DB, JSON)."""
from __future__ import annotations

from quant_platform.packages.adapters.run_series_store import (
    read_series,
    series_path,
    write_series,
)


def test_write_then_read_roundtrip(tmp_path) -> None:
    write_series(
        "abc123",
        equity=[1.0, 1.02, 0.99],
        drawdown=[0.0, 0.0, -0.029],
        trades=[{"ret": 0.05, "hold": 7, "entry_structure": 2}],
        series_dir=tmp_path,
    )
    got = read_series("abc123", series_dir=tmp_path)
    assert got is not None
    assert got["run_id"] == "abc123"
    assert got["equity"] == [1.0, 1.02, 0.99]
    assert got["drawdown"][2] == -0.029
    assert got["trades"][0]["hold"] == 7


def test_read_missing_returns_none(tmp_path) -> None:
    assert read_series("nope", series_dir=tmp_path) is None


def test_write_coerces_numpy_like_to_float(tmp_path) -> None:
    import numpy as np

    write_series(
        "np1",
        equity=np.array([1.0, 1.1]),
        drawdown=np.array([0.0, -0.01]),
        trades=[],
        series_dir=tmp_path,
    )
    got = read_series("np1", series_dir=tmp_path)
    assert got["equity"] == [1.0, 1.1]
    assert all(isinstance(x, float) for x in got["equity"])


def test_series_path_shape(tmp_path) -> None:
    assert series_path("xyz", tmp_path).name == "xyz.json"
