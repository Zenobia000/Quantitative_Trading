"""Strategy reverse-index — "which of my strategies already use this dataset".

A strategy author browsing the data dictionary wants the third answer: *who uses
this*. Strategies never name ``data.get`` keys; they read **bundle columns**
(``close`` / ``volume`` / ``foreign_buy`` / …) off the merged parquet frame. So the
index maps each catalog key -> the columns it populates (:data:`KEY_TO_COLUMNS`) ->
the strategies whose source *names* those columns.

Scan method (chosen by reading how the strategies actually reference data):

* We scan for **quoted column literals** (``"close"`` / ``'foreign_buy'``) in each
  strategy package's ``.py`` files. Quoting is what disambiguates a data column
  from Python's ``open`` builtin or a local ``high`` variable, and it naturally
  catches *indirect* ``flow_cols`` references: ``inst_flow`` never writes
  ``"close"`` literally, but its ``_SOURCES`` mapping declares the flow columns
  (``"foreign_buy"`` …) as literals in its own module — so the scan attributes them.
* ``_template`` and shared ``common`` infra are excluded — they are not
  author-selectable strategies (``common`` only *loads* columns on their behalf).

Pure + request-time: the strategies tree is tiny, so the scan runs per request with
no caching. Paths are injectable so tests drive a synthetic tree.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

#: Catalog key -> the bundle column(s) that key populates in the merged frame.
#: Only keys with a genuine strategy-visible column are listed; a key absent here
#: (raw price:收盤價, 財報, 月營收, 融資融券, …) has no strategy attribution by design
#: — the built-in strategies read adjusted OHLC + net-buy, nothing else.
KEY_TO_COLUMNS: dict[str, tuple[str, ...]] = {
    "etl:adj_open": ("open",),
    "etl:adj_high": ("high",),
    "etl:adj_low": ("low",),
    "etl:adj_close": ("close",),          # daily_bars.close IS the adjusted close
    "price:成交股數": ("volume",),
    "institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)": ("foreign_buy",),
    "institutional_investors_trading_summary:外資自營商買賣超股數": ("foreign_buy",),
    "institutional_investors_trading_summary:投信買賣超股數": ("trust_buy",),
    "institutional_investors_trading_summary:自營商買賣超股數(自行買賣)": ("dealer_buy",),
    "institutional_investors_trading_summary:自營商買賣超股數(避險)": ("dealer_buy",),
}

#: Sub-dirs of the strategies package that are not author-selectable strategies.
EXCLUDE_DIRS: frozenset[str] = frozenset({"_template", "common"})


def default_strategies_root() -> Path:
    """The real ``backtest_platform/strategies`` dir (sibling of ``data/``)."""
    return Path(__file__).resolve().parent.parent / "strategies"


def _columns_named_by(strategy_dir: Path) -> set[str]:
    """Set of bundle columns whose quoted literal appears anywhere in the package."""
    named: set[str] = set()
    all_columns = {col for cols in KEY_TO_COLUMNS.values() for col in cols}
    for py in strategy_dir.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except OSError:
            continue
        for col in all_columns:
            if f'"{col}"' in text or f"'{col}'" in text:
                named.add(col)
    return named


def build_strategy_data_index(
    strategies_root: Path,
    *,
    key_columns: Mapping[str, tuple[str, ...]] = KEY_TO_COLUMNS,
    exclude: frozenset[str] = EXCLUDE_DIRS,
) -> dict[str, list[str]]:
    """Map ``catalog key -> [strategy names]`` by scanning strategy source.

    ``strategies_root`` is scanned one level deep for strategy packages; each
    package contributes to a key iff its source names any of that key's columns.
    Only keys with at least one user appear in the result; lists are sorted.
    """
    # 1. strategy name -> columns it names
    per_strategy: dict[str, set[str]] = {}
    if strategies_root.is_dir():
        for child in sorted(strategies_root.iterdir()):
            if not child.is_dir() or child.name in exclude or child.name.startswith("."):
                continue
            per_strategy[child.name] = _columns_named_by(child)

    # 2. invert through key -> columns
    index: dict[str, list[str]] = {}
    for key, cols in key_columns.items():
        users = sorted(
            name for name, named in per_strategy.items()
            if any(col in named for col in cols)
        )
        if users:
            index[key] = users
    return index
