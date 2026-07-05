"""Local-presence resolver — the honest "do I have this locally" binary.

The local parquet cache is a **three-table bundle** written by
:func:`data.finmind_etl.write_parquet` — ``daily_bars__*.parquet`` /
``institutional__*.parquet`` / ``broker_chips__*.parquet`` under each
``<data_root>/parquet*`` cache dir — NOT one file per ``data.get`` key. So presence
can only be answered at *table-family* granularity, and we answer it honestly:

* a catalog **category** maps to at most one bundle table (:data:`CATEGORY_TO_TABLE`);
* a key is ``cached`` iff that table exists locally, else ``not_cached``;
* categories with **no** bundle backing (財報 / 月營收 / 融資融券) map to nothing and
  are always ``not_cached`` — we never force-fit a key onto an unrelated table.

The mapping is deliberately explicit and extensible: add a ``category -> table`` row
when a new category becomes bundle-backed. Every filesystem touch is defensive —
a missing / unreadable data root degrades to ``not_cached``, never raises.
"""
from __future__ import annotations

from pathlib import Path

#: The two presence states (a binary — see module docstring).
CACHED = "cached"
NOT_CACHED = "not_cached"

#: The three bundle tables written per stock (mirrors ``write_parquet``).
TABLE_DAILY_BARS = "daily_bars"
TABLE_INSTITUTIONAL = "institutional"
TABLE_BROKER_CHIPS = "broker_chips"

#: Catalog category -> backing bundle table. Categories absent here have no local
#: representation and resolve to ``not_cached`` (honest, not force-fitted).
CATEGORY_TO_TABLE: dict[str, str] = {
    "price_volume": TABLE_DAILY_BARS,
    "institutional": TABLE_INSTITUTIONAL,
    # 分點/當沖 chips land in broker_chips; no catalog key uses it yet, but the
    # mapping is wired so a future 分點 category resolves correctly (extensible).
    "broker_chips": TABLE_BROKER_CHIPS,
}

#: Only these prefixed subdirs of the data root hold bundle caches (mirrors
#: ``bundle_registry._CACHE_GLOB`` — default + universe caches).
_CACHE_GLOB = "parquet*"


def table_for_category(category: str) -> str | None:
    """Bundle table backing ``category``, or ``None`` if it has no local backing."""
    return CATEGORY_TO_TABLE.get(category)


def table_exists(table: str, data_root: Path) -> bool:
    """True iff any ``{table}__*.parquet`` exists under a ``parquet*`` cache dir.

    Defensive by construction: a missing root or an unreadable dir is treated as
    "absent" rather than raised, so the endpoint degrades to ``not_cached``.
    """
    try:
        if not data_root.is_dir():
            return False
        for cache in data_root.glob(_CACHE_GLOB):
            if not cache.is_dir():
                continue
            if next(cache.glob(f"{table}__*.parquet"), None) is not None:
                return True
    except OSError:
        return False
    return False


def presence_for_category(category: str, data_root: Path) -> str:
    """``cached`` iff ``category``'s backing table exists locally, else ``not_cached``."""
    table = table_for_category(category)
    if table is None:
        return NOT_CACHED
    return CACHED if table_exists(table, data_root) else NOT_CACHED
