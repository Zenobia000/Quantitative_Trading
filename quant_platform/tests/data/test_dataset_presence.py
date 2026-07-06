"""Local-presence mapping — the honest three-table binary.

The local parquet cache is a three-table bundle (``daily_bars`` / ``institutional``
/ ``broker_chips``), NOT one file per ``data.get`` key. Presence therefore answers
a coarse but honest question: does the *table family* a catalog category maps to
exist locally? Categories with no bundle backing (financials / revenue / margin)
are honestly ``not_cached`` — never force-fitted onto an unrelated table.
"""
from __future__ import annotations

from quant_platform.services.data_platform import dataset_presence as dp


def _seed(root, table, stock="2330"):
    """Write an empty ``{table}__{stock}.parquet`` into a ``parquet*`` cache dir."""
    cache = root / "parquet"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"{table}__{stock}.parquet").write_bytes(b"")


def test_category_to_table_covers_all_three_bundle_tables():
    assert dp.table_for_category("price_volume") == "daily_bars"
    assert dp.table_for_category("institutional") == "institutional"
    assert dp.table_for_category("broker_chips") == "broker_chips"


def test_unmapped_category_has_no_table():
    for category in ("financials", "monthly_revenue", "margin_short", "nonsense"):
        assert dp.table_for_category(category) is None


def test_presence_not_cached_on_empty_root(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    assert dp.presence_for_category("price_volume", root) == dp.NOT_CACHED


def test_presence_cached_per_table(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    _seed(root, "daily_bars")
    assert dp.presence_for_category("price_volume", root) == dp.CACHED
    # other tables still absent -> not_cached (independent per table family)
    assert dp.presence_for_category("institutional", root) == dp.NOT_CACHED
    assert dp.presence_for_category("broker_chips", root) == dp.NOT_CACHED

    _seed(root, "institutional")
    _seed(root, "broker_chips")
    assert dp.presence_for_category("institutional", root) == dp.CACHED
    assert dp.presence_for_category("broker_chips", root) == dp.CACHED


def test_unmapped_categories_are_not_cached_even_with_bundle_present(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    _seed(root, "daily_bars")
    _seed(root, "institutional")
    for category in ("financials", "monthly_revenue", "margin_short"):
        assert dp.presence_for_category(category, root) == dp.NOT_CACHED


def test_missing_data_root_degrades_to_not_cached(tmp_path):
    ghost = tmp_path / "does_not_exist"
    assert dp.presence_for_category("price_volume", ghost) == dp.NOT_CACHED


def test_presence_values_are_the_two_literals(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    assert {dp.CACHED, dp.NOT_CACHED} == {"cached", "not_cached"}
