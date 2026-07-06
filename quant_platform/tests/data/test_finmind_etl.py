"""Tests for FinMind ETL with a stub loader (no network)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from quant_platform.services.data_platform.finmind_etl import fetch_bundle, write_parquet
from quant_platform.services.data_platform.schemas import ETLBundle


class StubLoader:
    """Mimics FinMind DataLoader for offline tests."""

    def taiwan_stock_daily(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "stock_id": [stock_id, stock_id],
                "open": [100.0, 101.0],
                "max": [102.0, 103.0],
                "min": [99.5, 100.5],
                "close": [101.5, 102.5],
                "Trading_Volume": [5000, 6000],
            }
        )

    def taiwan_stock_institutional_investors(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-02", "2024-01-03"],
                "stock_id": [stock_id] * 3,
                "name": ["Foreign_Investor", "Investment_Trust", "Foreign_Investor"],
                "buy": [1000, 500, 800],
                "sell": [600, 200, 1000],
            }
        )

    def taiwan_stock_day_trading(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        # Real FinMind schema: date, stock_id, BuyAfterSale, Volume, BuyAmount, SellAmount
        return pd.DataFrame(
            {
                "stock_id": [stock_id, stock_id],
                "date": ["2024-01-02", "2024-01-03"],
                "BuyAfterSale": ["", ""],
                "Volume": [200, 250],
                "BuyAmount": [20000, 25000],
                "SellAmount": [20100, 25050],
            }
        )

    def taiwan_stock_dividend(
        self, stock_id: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        # No dividends in test range
        return pd.DataFrame()


def test_fetch_bundle_with_stub_loader_returns_valid_bundle() -> None:
    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    assert isinstance(bundle, ETLBundle)
    assert bundle.stock_id == "2330"
    assert len(bundle.daily_bars) == 2
    assert len(bundle.institutional) == 2
    assert len(bundle.broker_chips) == 2


def test_institutional_pivot_computes_net_correctly() -> None:
    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    inst = bundle.institutional.set_index("trade_date")
    # 2024-01-02: foreign 1000-600=400, trust 500-200=300
    assert inst.loc[date(2024, 1, 2), "foreign_buy"] == 400
    assert inst.loc[date(2024, 1, 2), "trust_buy"] == 300
    # 2024-01-03: foreign 800-1000=-200, trust absent → 0
    assert inst.loc[date(2024, 1, 3), "foreign_buy"] == -200
    assert inst.loc[date(2024, 1, 3), "trust_buy"] == 0


def test_merged_bundle_has_all_required_columns() -> None:
    """merged() output must satisfy compute_scores REQUIRED_COLUMNS."""
    from quant_platform.services.research_validation.strategies.four_layer_resonance.scoring import REQUIRED_COLUMNS

    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    merged = bundle.merged()
    missing = [c for c in REQUIRED_COLUMNS if c not in merged.columns]
    assert missing == [], f"merged bundle missing: {missing}"


def test_write_parquet_creates_three_files(tmp_path: Path) -> None:
    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=StubLoader(),
        rate_limit_seconds=0,
    )
    paths = write_parquet(bundle, tmp_path / "out")
    assert paths["daily_bars"].exists()
    assert paths["institutional"].exists()
    assert paths["broker_chips"].exists()
    roundtrip = pd.read_parquet(paths["daily_bars"])
    assert len(roundtrip) == 2


# --------------------------------------------------------------------------- #
# Extended coverage: error path, empty data, CLI
# --------------------------------------------------------------------------- #


class _EmptyLoader:
    """Loader returning empty DataFrames from every endpoint."""

    def taiwan_stock_daily(self, stock_id, start_date, end_date):
        return pd.DataFrame()

    def taiwan_stock_institutional_investors(self, stock_id, start_date, end_date):
        return pd.DataFrame()

    def taiwan_stock_day_trading(self, stock_id, start_date, end_date):
        return pd.DataFrame()

    def taiwan_stock_dividend(self, stock_id, start_date, end_date):
        return pd.DataFrame()


def test_fetch_bundle_with_all_empty_loader_returns_empty_bundle():
    """When every endpoint returns empty, fetch_bundle still constructs a valid ETLBundle."""
    bundle = fetch_bundle(
        stock_id="9999",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=_EmptyLoader(),
        rate_limit_seconds=0,
    )
    assert bundle.stock_id == "9999"
    assert bundle.daily_bars.empty
    assert bundle.institutional.empty
    assert bundle.broker_chips.empty
    # Empty bundle still has the correct column schema
    expected_daily_cols = {
        "stock_id", "trade_date", "open", "high", "low", "close", "volume", "adj_factor",
    }
    assert expected_daily_cols.issubset(set(bundle.daily_bars.columns))


def test_fetch_bundle_swallows_dividend_fetch_exception():
    """Adjustment is best-effort — if dividend fetch raises, daily still returned."""

    class DivFailsLoader(StubLoader):
        def taiwan_stock_dividend(self, stock_id, start_date, end_date):
            raise RuntimeError("FinMind 429 rate limit")

    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=DivFailsLoader(),
        rate_limit_seconds=0,
    )
    # Daily bars still populated despite dividend fetch failure
    assert len(bundle.daily_bars) == 2


def test_fetch_bundle_skips_adjustment_when_disabled():
    """apply_adjustment=False shortcuts the dividend fetch path."""

    class NoDivLoader(StubLoader):
        def taiwan_stock_dividend(self, stock_id, start_date, end_date):
            raise AssertionError("should not be called when apply_adjustment=False")

    bundle = fetch_bundle(
        stock_id="2330",
        start=date(2024, 1, 1),
        end=date(2024, 1, 31),
        loader=NoDivLoader(),
        rate_limit_seconds=0,
        apply_adjustment=False,
    )
    assert len(bundle.daily_bars) == 2


def test_normalize_institutional_handles_empty_input():
    """Empty raw → empty frame with expected output columns."""
    from quant_platform.services.data_platform.finmind_etl import _normalize_institutional

    out = _normalize_institutional(pd.DataFrame(), "2330")
    assert out.empty
    assert list(out.columns) == [
        "stock_id", "trade_date", "foreign_buy", "trust_buy", "dealer_buy",
    ]


def test_normalize_day_trading_handles_empty_input():
    from quant_platform.services.data_platform.finmind_etl import _normalize_day_trading

    out = _normalize_day_trading(pd.DataFrame(), "2330")
    assert out.empty
    assert "day_trade_volume" in out.columns


def test_normalize_daily_handles_empty_input():
    from quant_platform.services.data_platform.finmind_etl import _normalize_daily

    out = _normalize_daily(pd.DataFrame(), "2330")
    assert out.empty
    assert "open" in out.columns


def test_col_or_zero_falls_back_when_column_missing():
    from quant_platform.services.data_platform.finmind_etl import _col_or_zero

    df = pd.DataFrame({"a": [1, 2, 3]})
    s = _col_or_zero(df, "missing")
    assert (s == 0).all()
    assert len(s) == 3


# --------------------------------------------------------------------------- #
# CLI test
# --------------------------------------------------------------------------- #


def test_main_cli_dry_run_no_output_no_db(tmp_path):
    """Without --output or --db, CLI exits cleanly with "dry-run complete" log."""
    from unittest.mock import patch

    from click.testing import CliRunner

    from quant_platform.services.data_platform import finmind_etl as etl

    runner = CliRunner()
    fake_bundle = MagicMock_return_empty_bundle()

    with patch.object(etl, "fetch_bundle", return_value=fake_bundle):
        result = runner.invoke(
            etl.main,
            [
                "--stock-id", "2330",
                "--start", "2024-01-02",
                "--end", "2024-01-15",
            ],
        )
    assert result.exit_code == 0, result.output


def test_main_cli_writes_parquet(tmp_path):
    from unittest.mock import patch

    from click.testing import CliRunner

    from quant_platform.services.data_platform import finmind_etl as etl

    runner = CliRunner()
    fake_bundle = MagicMock_return_empty_bundle()
    fake_paths = {"daily_bars": tmp_path / "f1.parquet"}

    with (
        patch.object(etl, "fetch_bundle", return_value=fake_bundle),
        patch.object(etl, "write_parquet", return_value=fake_paths) as mock_wp,
    ):
        result = runner.invoke(
            etl.main,
            [
                "--stock-id", "2330",
                "--start", "2024-01-02",
                "--end", "2024-01-15",
                "--output", str(tmp_path),
            ],
        )
    assert result.exit_code == 0, result.output
    mock_wp.assert_called_once()


def MagicMock_return_empty_bundle():
    """Helper: construct a real ETLBundle (Pydantic) with empty frames for CLI tests."""
    return ETLBundle(
        stock_id="2330",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 15),
        daily_bars=pd.DataFrame(
            columns=["stock_id", "trade_date", "open", "high", "low", "close", "volume", "adj_factor"],
        ),
        institutional=pd.DataFrame(
            columns=["stock_id", "trade_date", "foreign_buy", "trust_buy", "dealer_buy"],
        ),
        broker_chips=pd.DataFrame(
            columns=[
                "stock_id", "trade_date",
                "top_broker_buy", "key_broker_buy", "gov_broker_buy", "geo_broker_buy",
                "day_trade_volume", "margin_offset_volume",
            ],
        ),
    )


def test_build_loader_with_token(monkeypatch):
    """_build_loader imports FinMind lazily and applies token when given."""
    from quant_platform.services.data_platform import finmind_etl as etl
    from unittest.mock import MagicMock as _MM, patch as _patch

    fake_dl = _MM()
    fake_dl_cls = _MM(return_value=fake_dl)

    fake_module = _MM()
    fake_module.DataLoader = fake_dl_cls

    fake_package = _MM()
    fake_package.data = fake_module

    monkeypatch.setitem(
        __import__("sys").modules, "FinMind", fake_package,
    )
    monkeypatch.setitem(
        __import__("sys").modules, "FinMind.data", fake_module,
    )
    loader = etl._build_loader("secret-token")
    assert loader is fake_dl
    fake_dl.login_by_token.assert_called_once_with(api_token="secret-token")


def test_build_loader_without_token(monkeypatch):
    from quant_platform.services.data_platform import finmind_etl as etl
    from unittest.mock import MagicMock as _MM

    fake_dl = _MM()
    fake_dl_cls = _MM(return_value=fake_dl)

    fake_module = _MM()
    fake_module.DataLoader = fake_dl_cls
    fake_package = _MM()
    fake_package.data = fake_module
    monkeypatch.setitem(__import__("sys").modules, "FinMind", fake_package)
    monkeypatch.setitem(__import__("sys").modules, "FinMind.data", fake_module)

    loader = etl._build_loader(None)
    assert loader is fake_dl
    fake_dl.login_by_token.assert_not_called()
