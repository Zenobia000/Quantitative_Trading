"""Catalog loader shape + required-field contract (authoring-first data dictionary).

The catalog is a *curated* snapshot of FinLab ``data.get`` keys — a strategy
author's data dictionary, not a runtime manifest. These tests pin its shape (every
card answers "what is this data") and anchor a few keys to the verified source of
truth (``data.finlab_source``) so the snapshot can grow without silently drifting
into unverified keys.
"""
from __future__ import annotations

from backtest_platform.data import finlab_catalog as cat


def test_load_catalog_returns_specs():
    catalog = cat.load_catalog()
    assert isinstance(catalog, tuple)
    assert len(catalog) >= 20  # several representative keys per category
    assert all(isinstance(spec, cat.DatasetSpec) for spec in catalog)


def test_every_card_has_all_required_fields_nonempty():
    for spec in cat.load_catalog():
        for field in ("key", "name_zh", "category", "freq", "history_start", "description"):
            value = getattr(spec, field)
            assert isinstance(value, str) and value.strip(), f"{spec.key}.{field} empty"


def test_keys_are_unique():
    keys = [s.key for s in cat.load_catalog()]
    assert len(keys) == len(set(keys))


def test_categories_and_freqs_are_from_the_allowed_sets():
    for spec in cat.load_catalog():
        assert spec.category in cat.CATEGORIES, spec.category
        assert spec.freq in cat.FREQS, spec.freq


def test_catalog_version_is_a_nonempty_string():
    assert isinstance(cat.CATALOG_VERSION, str) and cat.CATALOG_VERSION.strip()


def test_every_category_has_at_least_a_few_representative_keys():
    from collections import Counter

    dist = Counter(s.category for s in cat.load_catalog())
    for category in cat.CATEGORIES:
        assert dist[category] >= 3, f"{category} under-represented: {dist[category]}"


def test_verified_finlab_source_keys_are_present():
    # These keys are used live by data.finlab_source (verified 2026-06-15); the
    # catalog must stay a superset-anchor of what the ingest path actually pulls.
    keys = {s.key for s in cat.load_catalog()}
    for verified in (
        "etl:adj_close",
        "etl:adj_open",
        "price:成交股數",
        "institutional_investors_trading_summary:投信買賣超股數",
        "institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)",
    ):
        assert verified in keys, verified
