# FinLab Data Layer — Implementation Plan

> **For agentic workers:** Execute task-by-task (TDD). Steps are checkboxes.

**Goal:** FinLab as primary market-data source via the existing parquet schema; FinMind retained as fallback. Implements spec `docs/superpowers/specs/2026-06-15-finlab-data-layer-design.md`.

**Architecture:** New `data/finlab_source.py` fetches FinLab wide frames once and writes the *same* `ETLBundle`→`write_parquet` schema, so `load_merged_parquet` + all consumers are unchanged. A `source` flag on `make_ingest` selects FinLab (default) vs FinMind.

**Tech Stack:** Python, pandas, finlab 2.0, pytest (mock `data.get` via injected `getter` — no live calls in suite).

---

## Resolved FinLab dataset keys (verified live 2026-06-15)

| Field | FinLab key |
|:--|:--|
| OHLC (adjusted) | `etl:adj_open` / `etl:adj_high` / `etl:adj_low` / `etl:adj_close` |
| volume (shares) | `price:成交股數` |
| turnover (NTD) | `price:成交金額` |
| market cap | `etl:market_value` |
| foreign net-buy | `…:外陸資買賣超股數(不含外資自營商)` + `…:外資自營商買賣超股數` |
| trust net-buy | `…:投信買賣超股數` |
| dealer net-buy | `…:自營商買賣超股數(自行買賣)` + `…:自營商買賣超股數(避險)` |

(`…` = `institutional_investors_trading_summary`)

## Target schema (must match FinMind `data/schemas.ETLBundle`)

- `daily_bars`: `[stock_id, trade_date(date), open, high, low, close, volume, adj_factor=1.0]`
- `institutional`: `[stock_id, trade_date(date), foreign_buy, trust_buy, dealer_buy]` (int64, net)
- `broker_chips`: `[stock_id, trade_date(date), top_broker_buy, key_broker_buy, gov_broker_buy, geo_broker_buy, day_trade_volume, margin_offset_volume]` (zero-filled in ①)

## File Structure

- Create: `src/backtest_platform/data/finlab_source.py`
- Create: `tests/data/test_finlab_source.py`
- Modify: `src/backtest_platform/orchestration/collaborators.py` (`make_ingest` + `source` param)
- Modify: `tests/orchestration/test_collaborators.py` (selector test)
- Modify: `dev_docs/adrs/ADR-006-data-source-finlab-paid.md` (amendment: realized + finlab 2.0 auth)
- Modify: `dev_docs/16_wbs_development_plan.md` (3.B done, §2 3.0 bump, changelog v3.8)

---

### Task 1: `ingest_universe_finlab` — schema-parity ingest

**Files:** Create `data/finlab_source.py`, `tests/data/test_finlab_source.py`

- [ ] **Step 1: failing test — schema parity + round-trip via `load_merged_parquet`**

```python
import pandas as pd, pytest
from backtest_platform.data import finlab_source as fl
from backtest_platform.research.is_harness import load_merged_parquet

def _wide(vals, cols, idx):  # date×stock fixture
    return pd.DataFrame(vals, index=pd.to_datetime(idx), columns=cols)

def fake_getter():
    idx = ["2023-01-03","2023-01-04"]; cols = ["2330","2317"]
    base = {"etl:adj_open": _wide([[100,50],[101,51]],cols,idx),
            "etl:adj_high": _wide([[102,52],[103,53]],cols,idx),
            "etl:adj_low":  _wide([[99,49],[100,50]],cols,idx),
            "etl:adj_close":_wide([[101,51],[102,52]],cols,idx),
            "price:成交股數": _wide([[1000,2000],[1100,2100]],cols,idx),
            "institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)": _wide([[10,20],[11,21]],cols,idx),
            "institutional_investors_trading_summary:外資自營商買賣超股數": _wide([[1,2],[1,2]],cols,idx),
            "institutional_investors_trading_summary:投信買賣超股數": _wide([[5,6],[5,6]],cols,idx),
            "institutional_investors_trading_summary:自營商買賣超股數(自行買賣)": _wide([[3,4],[3,4]],cols,idx),
            "institutional_investors_trading_summary:自營商買賣超股數(避險)": _wide([[1,1],[1,1]],cols,idx)}
    return lambda key: base[key]

def test_finlab_ingest_matches_finmind_schema(tmp_path):
    from datetime import date
    res = fl.ingest_universe_finlab(["2330","2317"], date(2023,1,1), date(2023,1,31),
                                    cache_dir=tmp_path, getter=fake_getter())
    assert set(res.ok_symbols) == {"2330","2317"} and res.failed_symbols == ()
    m = load_merged_parquet("2330", parquet_dir=str(tmp_path))
    assert {"open","high","low","close","volume","adj_factor",
            "foreign_buy","trust_buy","dealer_buy"} <= set(m.columns)
    assert m["foreign_buy"].dtype == "int64"
    # foreign_buy = 外陸資 + 外資自營商 = 10 + 1 = 11 on day 1
    assert int(m.sort_values("trade_date")["foreign_buy"].iloc[0]) == 11
```

- [ ] **Step 2: run → FAIL** (`pytest tests/data/test_finlab_source.py -q`; module missing)

- [ ] **Step 3: implement `finlab_source.py`** — `login()`, dataset-key constants, `_sum_wide`, `_bundle_for`, `ingest_universe_finlab(symbols, start, end, *, cache_dir=None, getter=None) -> FinlabIngestResult`. Reuse `data.schemas.ETLBundle` + `data.finmind_etl.write_parquet`. Build per-symbol bundle aligned to adjusted-close dates; flows summed + `int64`; broker_chips zero-filled; missing symbol (no close col / empty) → `failed_symbols`.

- [ ] **Step 4: run → PASS**

- [ ] **Step 5: commit** (`feat(data): FinLab ingest writing FinMind-parity parquet (① )`)

### Task 2: `build_survivorship_universe`

**Files:** `data/finlab_source.py`, `tests/data/test_finlab_source.py`

- [ ] **Step 1: failing test — delisted included while alive, excluded after; no look-ahead**

```python
def test_survivorship_universe_includes_then_excludes_delisted():
    from datetime import date
    idx = pd.date_range("2020-01-01","2021-12-31",freq="D")
    cols = ["A","B","DEAD"]
    mv = pd.DataFrame(3e9, index=idx, columns=cols)          # all in band
    close = pd.DataFrame(50.0, index=idx, columns=cols)
    close.loc["2020-07-01":, "DEAD"] = float("nan")           # DEAD delists mid-2020
    turn = pd.DataFrame(5e7, index=idx, columns=cols)
    g = {"etl:market_value": mv, "etl:adj_close": close, "price:成交金額": turn}
    led = fl.build_survivorship_universe([date(2020,4,1), date(2020,10,1)],
            top_n=300, min_turnover=2e7, getter=lambda k: g[k])
    alive = led[(led.rebalance_date=="2020-04-01") & (led.stock_id=="DEAD")]
    dead  = led[(led.rebalance_date=="2020-10-01") & (led.stock_id=="DEAD")]
    assert bool(alive["selected"].iloc[0]) is True            # present while alive
    assert dead["excluded_reason"].iloc[0] == "delisted"      # gone after delist
```

- [ ] **Step 2: run → FAIL**

- [ ] **Step 3: implement** `build_survivorship_universe(rebalance_dates, *, top_n, min_turnover, getter=None)`: from `etl:market_value` (as-of last value ≤ date), `price:成交金額` rolling-20 mean (as-of), `etl:adj_close` first/last-valid → `listed_date`/`delisted_date`; assemble panel cols `(stock_id, rebalance_date, market_cap, avg_amount_20, listed_date, delisted_date)`; call `universe_builder.assign_membership(panel, SmallCapUniverseConfig(top_exclude_rank=0, max_rank=top_n, min_avg_amount=min_turnover))`.

- [ ] **Step 4: run → PASS**

- [ ] **Step 5: commit**

### Task 3: `source` flag on `make_ingest`

**Files:** `orchestration/collaborators.py`, `tests/orchestration/test_collaborators.py`

- [ ] **Step 1: failing test** — `make_ingest(..., source="finlab")` routes to `finlab_source.ingest_universe_finlab`; `source="finmind"` routes to the FinMind `ingest_universe`; injected `ingest_fn` still wins.

```python
def test_make_ingest_source_selects_finlab(monkeypatch):
    from backtest_platform.orchestration import collaborators as c
    called = {}
    monkeypatch.setattr("backtest_platform.data.finlab_source.ingest_universe_finlab",
                        lambda syms, s, e, **k: type("R",(),{"failed_symbols":()})())
    ing = c.make_ingest(start=__import__("datetime").date(2023,1,1),
                        end=__import__("datetime").date(2023,1,2), source="finlab")
    assert ing(["2330"]) == {"2330": True}
```

- [ ] **Step 2: run → FAIL**

- [ ] **Step 3: implement** — add `source: str = "finlab"` to `make_ingest`; when `ingest_fn is None`, dispatch by source (finlab → `finlab_source.ingest_universe_finlab`, finmind → existing `ingest_universe`); normalise both results' `.failed_symbols` → ok-map.

- [ ] **Step 4: run → PASS** + full suite green (`uv run pytest -q`)

- [ ] **Step 5: commit**

### Task 4: Doc sync (code↔doc rule)

**Files:** `dev_docs/adrs/ADR-006-*.md`, `dev_docs/16_wbs_development_plan.md`

- [ ] ADR-006 amendment: status realized (paid token, full history + survivorship verified 2026-06-15); `finlab_source.py` is the impl; finlab 2.0 `api_token=` deprecation (2026/08) noted as follow-up.
- [ ] WBS: 3.B.1 FinLab bundle adapter ⏳→✅; §2 module 3.0 progress bump; banner v3.7→v3.8 + changelog row; balance `**`.
- [ ] Commit.

## Plan Self-Review
- Spec coverage: §4.1 login✓(T1) §4.2 ingest✓(T1) §4.3 universe✓(T2) §4.4 source flag✓(T3) §7 tests✓ §8 ADR/WBS✓(T4). 
- Placeholder scan: dataset keys concrete; test code complete. 
- Type consistency: `FinlabIngestResult.failed_symbols` (tuple) matches `make_ingest`'s `result.failed_symbols` consumption; `assign_membership(panel, SmallCapUniverseConfig)` signature matches; panel columns match `PANEL_COLUMNS`.
