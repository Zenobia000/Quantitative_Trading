"""Tests for `ingest_universe` batch helper + zipline bundle registry checks.

Per 5.A.7 Wave 2: mock FinMind (no real API hits) and verify:
  - single-stock cache hit / miss paths
  - batch ingest_universe returns {symbol: ETLBundle} + failed_symbols list
  - one-stock failure doesn't abort the rest
  - zipline bundle registry sees 'finmind'

KPI tests requiring a live 9-stock ingest are placeholders (skipped) — Wave 3.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backtest_platform.data.schemas import ETLBundle


def _stub_bundle(stock_id: str, n_rows: int = 5) -> ETLBundle:
    """Minimal valid ETLBundle for mocks."""
    dates = pd.date_range("2024-01-02", periods=n_rows, freq="B")
    daily = pd.DataFrame(
        {
            "stock_id": [stock_id] * n_rows,
            "trade_date": [d.date() for d in dates],
            "open": [100.0] * n_rows,
            "high": [101.0] * n_rows,
            "low": [99.0] * n_rows,
            "close": [100.5] * n_rows,
            "volume": [1000] * n_rows,
            "adj_factor": [1.0] * n_rows,
        }
    )
    return ETLBundle(
        stock_id=stock_id,
        start_date=dates[0].date(),
        end_date=dates[-1].date(),
        daily_bars=daily,
        institutional=pd.DataFrame(),
        broker_chips=pd.DataFrame(),
    )


# ===== 5.A.7.3 — zipline bundle registry =====


def test_finmind_bundle_registered_in_zipline_registry():
    """``ensure_registered()`` registers the 'finmind' bundle with zipline.

    Registration is now an explicit call (dependency-untangle refactor), not a
    package-import side-effect — so we invoke it directly instead of relying on
    importing ``engines.zipline_adapter``.
    """
    from backtest_platform.engines.zipline_adapter.bundles import finmind_bundle

    finmind_bundle.ensure_registered()
    from zipline.data import bundles

    # zipline-reloaded exposes the registry via `bundles.bundles` mapping
    registered = set(bundles.bundles.keys())
    assert "finmind" in registered, (
        f"'finmind' must be registered after ensure_registered(); got {registered}"
    )


# ===== 5.A.7.1 — single-stock ingest via mocked fetch path =====


def test_ingest_single_stock_uses_cache_on_hit(tmp_path):
    """When ParquetCache reports the bundle covers the requested range,
    cached_or_fetch must NOT call FinMind."""
    from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
        ParquetCache,
        cached_or_fetch,
    )

    cache = ParquetCache(root=tmp_path)
    bundle = _stub_bundle("2330")

    fake_fetch = MagicMock()

    # Pre-seed cache via load_or_none path: patch exists/load to return cached bundle
    with patch.object(ParquetCache, "load_or_none", return_value=bundle):
        result = cached_or_fetch(
            "2330", date(2024, 1, 2), date(2024, 1, 5), cache, fetch_fn=fake_fetch
        )

    assert result.stock_id == "2330"
    fake_fetch.assert_not_called()


def test_ingest_single_stock_falls_back_to_fetch_on_miss(tmp_path):
    """Cache miss → fetch_fn called and result persisted."""
    from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
        ParquetCache,
        cached_or_fetch,
    )

    cache = ParquetCache(root=tmp_path)
    bundle = _stub_bundle("2454")
    fake_fetch = MagicMock(return_value=bundle)

    with patch.object(ParquetCache, "load_or_none", return_value=None), patch(
        "backtest_platform.data.finmind_etl.write_parquet"
    ) as mock_write:
        result = cached_or_fetch(
            "2454", date(2024, 1, 2), date(2024, 1, 5), cache, fetch_fn=fake_fetch
        )

    assert result.stock_id == "2454"
    fake_fetch.assert_called_once_with("2454", date(2024, 1, 2), date(2024, 1, 5))
    mock_write.assert_called_once()


def test_ingest_single_stock_refetches_when_cache_range_insufficient(tmp_path):
    """Cache covers Jan only, request goes to Feb → fetch the gap and merge.

    The merge policy fetches only the missing tail and unions it with the cached
    rows, so the returned bundle is a *new merged* bundle spanning both — never a
    raw overwrite that would drop cached history."""
    from backtest_platform.engines.zipline_adapter.bundles.parquet_cache import (
        ParquetCache,
        cached_or_fetch,
    )

    cache = ParquetCache(root=tmp_path)
    cached = _stub_bundle("2317")  # covers 2024-01-02..2024-01-08 only

    new_bundle = _stub_bundle("2317", n_rows=20)  # spans 2024-01-02..2024-01-29
    fake_fetch = MagicMock(return_value=new_bundle)

    with patch.object(ParquetCache, "load_or_none", return_value=cached), patch(
        "backtest_platform.data.finmind_etl.write_parquet"
    ):
        result = cached_or_fetch(
            "2317", date(2024, 1, 2), date(2024, 2, 28), cache, fetch_fn=fake_fetch
        )

    # Range doesn't fit → only the missing tail is fetched, then merged.
    fake_fetch.assert_called_once()
    gap_start = fake_fetch.call_args.args[1]
    assert gap_start > cached.end_date  # no re-fetch of cached history
    assert result is not new_bundle  # merged bundle, not the raw fetch
    assert result.stock_id == "2317"
    assert result.start_date == date(2024, 1, 2)  # cached head preserved
    assert result.end_date == new_bundle.end_date  # extended by fetched tail


# ===== 5.A.7.2 — ingest_universe batch =====


def test_ingest_universe_returns_dict_and_failed_list(tmp_path):
    """ingest_universe loops through symbols, returns (bundles_dict, failed_list)."""
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        ingest_universe,
    )

    universe = ["2330", "2454", "2317"]
    bundles_by_sym = {sym: _stub_bundle(sym) for sym in universe}

    def fake_cached_or_fetch(symbol, start, end, cache, fetch_fn=None):
        return bundles_by_sym[symbol]

    with patch(
        "backtest_platform.engines.zipline_adapter.bundles.finmind_bundle.cached_or_fetch",
        side_effect=fake_cached_or_fetch,
    ):
        result = ingest_universe(
            universe, start=date(2024, 1, 2), end=date(2024, 1, 5), cache_dir=tmp_path
        )

    assert set(result.bundles.keys()) == set(universe)
    assert result.failed_symbols == []
    assert all(isinstance(b, ETLBundle) for b in result.bundles.values())


def test_ingest_universe_default_universe(tmp_path):
    """Calling ingest_universe() with no universe arg uses DEFAULT_UNIVERSE."""
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        DEFAULT_UNIVERSE,
        ingest_universe,
    )

    bundles_by_sym = {sym: _stub_bundle(sym) for sym in DEFAULT_UNIVERSE}

    def fake_cached_or_fetch(symbol, start, end, cache, fetch_fn=None):
        return bundles_by_sym[symbol]

    with patch(
        "backtest_platform.engines.zipline_adapter.bundles.finmind_bundle.cached_or_fetch",
        side_effect=fake_cached_or_fetch,
    ):
        result = ingest_universe(
            start=date(2024, 1, 2), end=date(2024, 1, 5), cache_dir=tmp_path
        )

    assert len(result.bundles) == len(DEFAULT_UNIVERSE)


# ===== 5.A.7.7 — error handling: partial failure continues =====


def test_ingest_universe_continues_on_single_stock_failure(tmp_path):
    """When one stock raises, others must still ingest and be tracked in failed_symbols."""
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        ingest_universe,
    )

    universe = ["2330", "BADSTOCK", "2317"]

    def fake_cached_or_fetch(symbol, start, end, cache, fetch_fn=None):
        if symbol == "BADSTOCK":
            raise RuntimeError("FinMind 404")
        return _stub_bundle(symbol)

    with patch(
        "backtest_platform.engines.zipline_adapter.bundles.finmind_bundle.cached_or_fetch",
        side_effect=fake_cached_or_fetch,
    ):
        result = ingest_universe(
            universe, start=date(2024, 1, 2), end=date(2024, 1, 5), cache_dir=tmp_path
        )

    assert set(result.bundles.keys()) == {"2330", "2317"}
    assert result.failed_symbols == ["BADSTOCK"]


def test_ingest_universe_raises_when_all_fail(tmp_path):
    """If every symbol fails, surface as RuntimeError rather than returning empty silently.

    Justification: silent empty result is the worst failure mode for an ingest
    job — downstream zipline would write an empty bundle and confuse the user.
    """
    from backtest_platform.engines.zipline_adapter.bundles.finmind_bundle import (
        ingest_universe,
    )

    def always_fail(symbol, start, end, cache, fetch_fn=None):
        raise RuntimeError(f"FinMind down for {symbol}")

    with patch(
        "backtest_platform.engines.zipline_adapter.bundles.finmind_bundle.cached_or_fetch",
        side_effect=always_fail,
    ):
        with pytest.raises(RuntimeError, match="no stocks ingested"):
            ingest_universe(
                ["2330", "2454"],
                start=date(2024, 1, 2),
                end=date(2024, 1, 5),
                cache_dir=tmp_path,
            )


# ===== 5.A.7.8 — M2 acceptance KPI placeholder (Wave 3) =====


@pytest.mark.skip(
    reason="Wave 3: requires real 9-stock FinMind ingest + Portfolio 5.A.6 implementation"
)
def test_m2_acceptance_kpi_universe_ingest_9_stocks():
    """Acceptance: full DEFAULT_UNIVERSE ingest → 9+ symbols in zipline bundle.

    Will be filled in Wave 3 once Stream A finishes Portfolio adapter (5.A.6)
    and user has run live ingest on their machine.
    """


@pytest.mark.skip(reason="Wave 3: requires live FinMind cache + 7y data window")
def test_m2_acceptance_kpi_seven_year_window():
    """Acceptance: ingest covers 2018-01-02 .. 2024-12-31 with no row gaps."""


# ===== 5.A.7.6 — CLI subprocess test placeholder =====


@pytest.mark.skip(
    reason="subprocess pytest in worktree is unstable; covered manually via "
    "`zipline ingest -b finmind` in Wave 3 acceptance run"
)
def test_cli_zipline_ingest_finmind_bundle():
    """Acceptance: `zipline ingest -b finmind` exits 0 with valid env."""
