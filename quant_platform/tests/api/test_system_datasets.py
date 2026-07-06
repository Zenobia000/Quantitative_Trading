"""``GET /system/datasets`` — the authoring-first data-dictionary endpoint.

Each card answers three things for a strategy author: what the data is (key / name
/ category / freq / history / description), whether it is local (binary), and which
of my strategies already use it. These tests pin the card shape, the two filters
(``?category`` / ``?q``), the local-presence wiring, and the reverse-index wiring.
"""
from __future__ import annotations

_CARD_FIELDS = {
    "key", "name_zh", "category", "freq", "history_start", "description",
    "local", "used_by", "bundle_backed",
}


def test_datasets_returns_cards_with_full_shape(client):
    body = client.get("/system/datasets").json()
    assert body["success"] is True
    cards = body["data"]
    assert isinstance(cards, list) and len(cards) >= 20
    sample = cards[0]
    assert set(sample) == _CARD_FIELDS
    assert sample["local"] in {"cached", "not_cached"}
    assert isinstance(sample["used_by"], list)
    assert isinstance(sample["bundle_backed"], bool)


def test_bundle_backed_true_only_for_bundle_categories(client):
    # price_volume / institutional land in a local bundle; financials / monthly_revenue
    # / margin_short are fetch-at-runtime only (ADR-007 Q1).
    cards = client.get("/system/datasets").json()["data"]
    by_cat = {}
    for c in cards:
        by_cat.setdefault(c["category"], set()).add(c["bundle_backed"])
    assert by_cat.get("price_volume") == {True}
    assert by_cat.get("institutional") == {True}
    assert by_cat.get("financials") == {False}
    assert by_cat.get("monthly_revenue") == {False}
    assert by_cat.get("margin_short") == {False}


def test_meta_carries_catalog_version(client):
    meta = client.get("/system/datasets").json()["meta"]
    assert isinstance(meta.get("catalog_version"), str) and meta["catalog_version"]
    assert meta["total"] == len(client.get("/system/datasets").json()["data"])


def test_category_filter(client):
    cards = client.get("/system/datasets", params={"category": "institutional"}).json()["data"]
    assert len(cards) >= 3
    assert {c["category"] for c in cards} == {"institutional"}


def test_q_filter_matches_key_and_name_case_insensitive(client):
    # key substring
    by_key = client.get("/system/datasets", params={"q": "adj_"}).json()["data"]
    assert by_key and all("adj_" in c["key"] for c in by_key)
    # name substring (Chinese)
    by_name = client.get("/system/datasets", params={"q": "營收"}).json()["data"]
    assert by_name and all(
        "營收" in c["name_zh"] or "營收" in c["key"] for c in by_name
    )


def test_empty_data_root_shows_all_not_cached(client):
    # the api conftest injects an empty tmp data_root
    cards = client.get("/system/datasets").json()["data"]
    assert {c["local"] for c in cards} == {"not_cached"}


def test_presence_reflects_seeded_bundle(client, data_root):
    cache = data_root / "parquet"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "daily_bars__2330.parquet").write_bytes(b"")
    cards = client.get("/system/datasets", params={"category": "price_volume"}).json()["data"]
    assert cards and all(c["local"] == "cached" for c in cards)


def test_used_by_reflects_reverse_index(client):
    cards = {c["key"]: c for c in client.get("/system/datasets").json()["data"]}
    trust = cards["institutional_investors_trading_summary:投信買賣超股數"]
    assert "inst_flow" in trust["used_by"]
    assert "four_layer_resonance" in trust["used_by"]
