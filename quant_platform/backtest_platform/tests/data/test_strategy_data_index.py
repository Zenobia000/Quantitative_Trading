"""Strategy reverse-index — which strategies name a dataset's bundle column.

Strategies read *bundle columns* (``close`` / ``foreign_buy`` / …), not ``data.get``
keys, so the index maps each catalog key -> the strategies whose source names the
column(s) that key populates. The scan is a quoted-literal text scan of each
strategy package, which naturally catches indirect ``flow_cols`` references (the
column literals live in the strategy's own ``_SOURCES`` mapping). ``_template`` and
shared ``common`` infra are excluded — they are not author-selectable strategies.
"""
from __future__ import annotations

from backtest_platform.data import strategy_data_index as sdi


def _make_strategy(root, name, body):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "strategy.py").write_text(body, encoding="utf-8")


def _synthetic_root(tmp_path):
    root = tmp_path / "strategies"
    # direct quoted column reference
    _make_strategy(root, "alpha", 'x = df["close"]\ny = df["volume"]\n')
    # no data reference at all
    _make_strategy(root, "beta", "z = 1 + 2\n")
    # indirect flow_cols style: column literals declared in a _SOURCES-like dict
    _make_strategy(
        root, "gamma", '_SOURCES = {"all": ("foreign_buy", "trust_buy")}\n'
    )
    # excluded dirs still reference columns but must never be attributed
    _make_strategy(root, "_template", 'p = df["close"]\n')
    _make_strategy(root, "common", 'q = df["close"]\n')
    return root


# a minimal key->columns map so the test is independent of the real catalog
_KEYS = {
    "etl:adj_close": ("close",),
    "price:成交股數": ("volume",),
    "institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)": ("foreign_buy",),
    "institutional_investors_trading_summary:投信買賣超股數": ("trust_buy",),
    "monthly_revenue:當月營收": ("__unmapped__",),  # column no strategy names
}


def test_direct_reference_is_indexed(tmp_path):
    idx = sdi.build_strategy_data_index(_synthetic_root(tmp_path), key_columns=_KEYS)
    assert idx["etl:adj_close"] == ["alpha"]
    assert idx["price:成交股數"] == ["alpha"]


def test_indirect_flow_cols_reference_is_indexed(tmp_path):
    idx = sdi.build_strategy_data_index(_synthetic_root(tmp_path), key_columns=_KEYS)
    fk = "institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)"
    assert idx[fk] == ["gamma"]
    assert idx["institutional_investors_trading_summary:投信買賣超股數"] == ["gamma"]


def test_strategy_with_no_reference_never_appears(tmp_path):
    idx = sdi.build_strategy_data_index(_synthetic_root(tmp_path), key_columns=_KEYS)
    assert all("beta" not in strategies for strategies in idx.values())


def test_template_and_common_are_excluded(tmp_path):
    idx = sdi.build_strategy_data_index(_synthetic_root(tmp_path), key_columns=_KEYS)
    for strategies in idx.values():
        assert "_template" not in strategies
        assert "common" not in strategies


def test_unreferenced_key_maps_to_empty_or_absent(tmp_path):
    idx = sdi.build_strategy_data_index(_synthetic_root(tmp_path), key_columns=_KEYS)
    assert idx.get("monthly_revenue:當月營收", []) == []


def test_results_are_sorted(tmp_path):
    root = tmp_path / "strategies"
    _make_strategy(root, "zeta", 'df["close"]\n')
    _make_strategy(root, "alpha", 'df["close"]\n')
    idx = sdi.build_strategy_data_index(root, key_columns={"etl:adj_close": ("close",)})
    assert idx["etl:adj_close"] == ["alpha", "zeta"]


def test_real_catalog_keys_index_against_real_strategies():
    # request-time scan of the real strategies package; inst_flow + four_layer
    # both name the institutional flow columns.
    idx = sdi.build_strategy_data_index(sdi.default_strategies_root())
    fk = "institutional_investors_trading_summary:投信買賣超股數"
    assert "inst_flow" in idx.get(fk, [])
    assert "four_layer_resonance" in idx.get(fk, [])
    # adjusted close is named by the price strategies
    assert "momentum" in idx.get("etl:adj_close", [])
    assert "reversal" in idx.get("etl:adj_close", [])
