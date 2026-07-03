"""FinLab dataset catalog — a strategy author's data dictionary (curated snapshot).

This is the backing store for ``GET /system/datasets``: a hand-curated list of the
FinLab ``data.get`` keys a strategy author reaches for when *writing* a strategy —
the same role XQ's data browser plays. It answers "what data exists and what does
it mean", NOT "is my cache fresh". Deliberately there is no manifest read, no
FinLab-side timestamp, no staleness/coverage — those are runtime concerns, out of
scope by design (authoring-first).

Curation rules (why this file looks the way it does):

* **Verified > complete.** Every key here is one we are confident ``data.get``
  accepts. The price/adjusted/institutional keys are anchored to the ones
  :mod:`data.finlab_source` pulls live (verified 2026-06-15); the rest are common
  FinLab tables cross-checked against FinLab's own docs. Uncertain keys are
  **omitted, not guessed** — this snapshot does not pretend to be exhaustive and is
  expected to grow *as strategies actually use more data* (寧缺勿錯).
* ``history_start`` is an **approximate** first-data year, not a precise coverage
  edge (that would be a manifest concern).
* The ``指數`` (index/TAIEX) category is intentionally absent: FinLab exposes it,
  but we could not verify the exact ``data.get`` key string, so per the curation
  rule it waits rather than ship a wrong key.

To extend: add a :class:`DatasetSpec` row below and (if it maps to a local bundle
table / a strategy-visible column) wire it in :mod:`data.dataset_presence` /
:mod:`data.strategy_data_index`.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Snapshot identity surfaced via ``meta.catalog_version``; bump on curation edits.
CATALOG_VERSION = "2026-07-03"

# --- category slugs (stable API values; ``name_zh`` carries the display label) --- #
CATEGORY_PRICE_VOLUME = "price_volume"
CATEGORY_FINANCIALS = "financials"
CATEGORY_MONTHLY_REVENUE = "monthly_revenue"
CATEGORY_MARGIN_SHORT = "margin_short"
CATEGORY_INSTITUTIONAL = "institutional"

CATEGORIES: frozenset[str] = frozenset({
    CATEGORY_PRICE_VOLUME,
    CATEGORY_FINANCIALS,
    CATEGORY_MONTHLY_REVENUE,
    CATEGORY_MARGIN_SHORT,
    CATEGORY_INSTITUTIONAL,
})

#: Reporting cadence of the underlying data.
FREQS: frozenset[str] = frozenset({"日", "月", "季"})


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """One catalog card — the authoring-first answer to "what is this data".

    Pure metadata: it says nothing about local presence or freshness (those are
    layered on at request time by ``dataset_presence`` / ``strategy_data_index``).
    """

    key: str            # the exact ``data.get`` string
    name_zh: str        # human display label
    category: str       # one of ``CATEGORIES``
    freq: str           # one of ``FREQS`` (日 / 月 / 季)
    history_start: str  # approximate first-data year, e.g. "2007"
    description: str     # one-line "what is it"


# --------------------------------------------------------------------------- #
# The curated snapshot                                                          #
# --------------------------------------------------------------------------- #
_CATALOG: tuple[DatasetSpec, ...] = (
    # ---- 價量 (daily bars family) — anchored to data.finlab_source ---------- #
    DatasetSpec("price:收盤價", "收盤價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "未還原每日收盤價"),
    DatasetSpec("price:開盤價", "開盤價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "未還原每日開盤價"),
    DatasetSpec("price:最高價", "最高價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "未還原每日最高價"),
    DatasetSpec("price:最低價", "最低價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "未還原每日最低價"),
    DatasetSpec("price:成交股數", "成交量(股)", CATEGORY_PRICE_VOLUME, "日", "2007",
                "每日成交股數"),
    DatasetSpec("price:成交金額", "成交金額", CATEGORY_PRICE_VOLUME, "日", "2007",
                "每日成交金額(元)"),
    DatasetSpec("etl:adj_open", "還原開盤價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "除權息還原後開盤價"),
    DatasetSpec("etl:adj_high", "還原最高價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "除權息還原後最高價"),
    DatasetSpec("etl:adj_low", "還原最低價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "除權息還原後最低價"),
    DatasetSpec("etl:adj_close", "還原收盤價", CATEGORY_PRICE_VOLUME, "日", "2007",
                "除權息還原後收盤價（回測基準價）"),
    DatasetSpec("etl:market_value", "個股市值", CATEGORY_PRICE_VOLUME, "日", "2007",
                "個股總市值(元)"),

    # ---- 財報 / 估值 ------------------------------------------------------- #
    DatasetSpec("fundamental_features:ROE稅後", "股東權益報酬率(稅後)",
                CATEGORY_FINANCIALS, "季", "2007", "稅後淨利 / 股東權益"),
    DatasetSpec("price_earning_ratio:本益比", "本益比(PER)",
                CATEGORY_FINANCIALS, "日", "2007", "股價 / 近四季每股盈餘"),
    DatasetSpec("price_earning_ratio:股價淨值比", "股價淨值比(PBR)",
                CATEGORY_FINANCIALS, "日", "2007", "股價 / 每股淨值"),
    DatasetSpec("price_earning_ratio:殖利率(%)", "現金殖利率(%)",
                CATEGORY_FINANCIALS, "日", "2007", "年度現金股利 / 股價"),

    # ---- 月營收 ------------------------------------------------------------ #
    DatasetSpec("monthly_revenue:當月營收", "當月營收",
                CATEGORY_MONTHLY_REVENUE, "月", "2007", "每月10日前公告之單月營收(千元)"),
    DatasetSpec("monthly_revenue:去年同月增減(%)", "營收年增率(%)",
                CATEGORY_MONTHLY_REVENUE, "月", "2007", "單月營收年增率(YoY)"),
    DatasetSpec("monthly_revenue:上月比較增減(%)", "營收月增率(%)",
                CATEGORY_MONTHLY_REVENUE, "月", "2007", "單月營收月增率(MoM)"),

    # ---- 融資融券（籌碼：信用交易） --------------------------------------- #
    DatasetSpec("margin_transactions:融資今日餘額", "融資餘額",
                CATEGORY_MARGIN_SHORT, "日", "2007", "當日融資餘額"),
    DatasetSpec("margin_transactions:融券今日餘額", "融券餘額",
                CATEGORY_MARGIN_SHORT, "日", "2007", "當日融券餘額"),
    DatasetSpec("margin_transactions:融資使用率", "融資使用率",
                CATEGORY_MARGIN_SHORT, "日", "2007", "融資餘額 / 融資限額"),

    # ---- 三大法人買賣超 — anchored to data.finlab_source ------------------- #
    DatasetSpec("institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)",
                "外資買賣超(不含自營)", CATEGORY_INSTITUTIONAL, "日", "2018",
                "外資及陸資買賣超股數（不含外資自營商）"),
    DatasetSpec("institutional_investors_trading_summary:外資自營商買賣超股數",
                "外資自營商買賣超", CATEGORY_INSTITUTIONAL, "日", "2018",
                "外資自營商買賣超股數"),
    DatasetSpec("institutional_investors_trading_summary:投信買賣超股數",
                "投信買賣超", CATEGORY_INSTITUTIONAL, "日", "2012",
                "投信買賣超股數"),
    DatasetSpec("institutional_investors_trading_summary:自營商買賣超股數(自行買賣)",
                "自營商買賣超(自行)", CATEGORY_INSTITUTIONAL, "日", "2012",
                "自營商自行買賣之買賣超股數"),
    DatasetSpec("institutional_investors_trading_summary:自營商買賣超股數(避險)",
                "自營商買賣超(避險)", CATEGORY_INSTITUTIONAL, "日", "2012",
                "自營商避險部位之買賣超股數"),
)


def load_catalog() -> tuple[DatasetSpec, ...]:
    """The curated catalog snapshot (immutable tuple)."""
    return _CATALOG
