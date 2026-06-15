# FinLab Data Layer — Design Spec

> **Date:** 2026-06-15 · **Status:** Approved (Phase 1) · **Sub-project:** ① of {① data layer → ② re-verify gated → ③ market_reader/forward}
> **Author:** Self · **Relates:** [ADR-006](../../../dev_docs/adrs/ADR-006-data-source-finlab-paid.md) (FinLab 主), [ADR-024/025](../../../dev_docs/adrs/), WBS 3.B (FinLab bundle adapter)

## 1. Goal

Make **FinLab the primary market-data source**, sourced through the platform's *existing* parquet-cache schema so that every downstream consumer (validation, replay, `signal_fn`, `make_ingest`) works **unchanged**. This unblocks the previously-gated work: full-history OOS (the FinLab `#free` 2018-12-28 cutoff is gone with the paid token) and a **natively survivorship-clean universe** (delisted stocks are present).

FinMind is **retained as a fallback** (non-destructive): code, tokens, and tests stay; only the *default* source flips to FinLab.

## 2. Context & Verification (live probe, 2026-06-15)

Probed the paid FinLab API directly (`finlab.login(api_token=…)` + `finlab.data.get`):

| Fact | Value |
|:--|:--|
| `price:收盤價` coverage | **2007-04-23 → 2026-06-15 (today)**, shape `(4706, 2753)` |
| 2018 cutoff | **gone** — full history (paid token) |
| Survivorship | **2753 stocks**, **369** with last data >90d before latest → delisted/suspended **present** |
| Data shape | **wide** DataFrame (date × stock_id) — one `data.get` returns all stocks |
| Institutional net-buy datasets | `institutional_investors_trading_summary:外陸資買賣超股數(不含外資自營商)` · `投信買賣超股數` · `自營商買賣超股數(自行買賣)` |
| Quota | 224 / 5000 MB per day (generous) |
| ⚠️ Package | `finlab` 2.0.0 installed; `login(api_token=)` deprecated after **2026/08/01** (new: `python -m finlab login`) |

**Existing structures this design plugs into:**
- Parquet schema (written by `engines/zipline_adapter/bundles/finmind_bundle.py`): `daily_bars__{sid}.parquet` / `institutional__{sid}.parquet` / `broker_chips__{sid}.parquet` (all `index=False`, keyed by `stock_id` + `trade_date`).
- `research/is_harness.load_merged_parquet(sid)` merges those 3 → the frame all validation/replay reads.
- `data/finmind_etl.ETLBundle(daily_bars, institutional, broker_chips)` is the in-memory bundle that gets written to those parquet.
- `data/universe_builder.assign_membership(panel, …)` is **already source-agnostic**: it takes a point-in-time panel `(rebalance_date, stock_id, market_cap, avg_amount_20, listed_date, delisted_date)` and selects a survivorship-clean membership with no look-ahead. It was gated only on a source that supplies delisted stocks — which FinLab now does.

## 3. Architecture — drop-in source swap

FinLab produces the **same `ETLBundle` / parquet schema** the FinMind path produces. Nothing downstream changes; the source is swapped at the ingest boundary.

```
finlab.data.get (wide: date × all stocks)
        │  slice per symbol + normalize to long
        ▼
ETLBundle(daily_bars, institutional, broker_chips)      ← identical schema to FinMind
        │  to_parquet (same daily_bars__/institutional__/broker_chips__ paths)
        ▼
load_merged_parquet (UNCHANGED) → validation / replay / signal_fn
```

## 4. Components — new module `data/finlab_source.py`

Each unit has one responsibility, a defined interface, and is unit-testable with a mocked `finlab.data.get`.

### 4.1 `login() -> None`
Authenticate via `finlab.login(api_token=os.environ["FINLAB_API_TOKEN"])`. Keep token auth (headless-friendly — the daemon needs it); emit a one-line deprecation note (2026/08 → `python -m finlab login`). Missing token → `RuntimeError` with a clear message. Idempotent (safe to call once per process).

### 4.2 `ingest_universe_finlab(symbols, start, end, *, cache_dir=DEFAULT_CACHE_DIR) -> IngestResult`
- Fetch the wide FinLab datasets **once** (not per symbol): `price:收盤價/開盤價/最高價/最低價/成交股數/成交金額` + the 3 institutional net-buy series.
- For each requested symbol: slice the wide frames to `[start, end]` + that column → build `ETLBundle(daily_bars, institutional, broker_chips)` matching the FinMind normaliser's columns/dtypes (`broker_chips` = empty/zero-filled; FinLab day-trading chips are out of scope for ①).
- Write the identical parquet paths via the existing writer.
- Return `IngestResult(ok_symbols, failed_symbols)` — same shape `make_ingest` already consumes.
- ⚡ One batch fetch for all symbols → far fewer API calls than FinMind's per-symbol loop (quota-friendly).

### 4.3 `build_survivorship_universe(rebalance_dates, *, top_n, min_turnover) -> Ledger`
- Build the point-in-time attribute panel from FinLab: `delisted_date` = last valid `price:收盤價` date per stock; `avg_amount_20` = trailing-20 mean of turnover; `market_cap` = FinLab market-value dataset (exact key resolved in Phase 2 probe — design unaffected, builder just needs the column).
- Feed `universe_builder.assign_membership` → survivorship-clean, no-look-ahead membership ledger including delisted names.

### 4.4 Source selector
`make_ingest(..., source: Literal["finlab","finmind"] = "finlab")` chooses the ingester. FinLab default; FinMind path unchanged as fallback. No existing call site breaks (param defaulted).

## 5. Contract — the invariant that makes this safe

`ingest_universe_finlab` output parquet must be **schema-compatible** with the FinMind bundle: same file names, same columns, same dtypes, same `trade_date`/`stock_id` keys, flow columns zero-filled (not NaN) as FinMind does. Guaranteed by a parity test (§7.1). This is what lets every consumer stay untouched.

## 6. Error handling

- Login/token errors → fail fast, clear message, never silently continue.
- Unknown FinLab dataset key → raise with the offending key (so a FinLab API change is loud).
- Per-symbol gaps (e.g., a name with no flow data in range) → zero-fill flows, mark symbol ok if it has price bars; only mark failed if no price data at all. Never abort the batch on one bad symbol (matches FinMind resilience).
- Quota/network errors → propagate (caller decides retry); log the daily-usage line FinLab returns.

## 7. Testing (TDD, mocked FinLab — no live calls in the suite)

1. **Schema parity** — mock `finlab.data.get` with a tiny wide fixture; assert `ingest_universe_finlab` writes parquet whose `load_merged_parquet` output has identical columns/dtypes to a FinMind-bundle fixture.
2. **Round-trip** — written parquet → `load_merged_parquet` → assert merged frame is well-formed (flow cols int64, zero-filled; sorted by date).
3. **Survivorship/no-look-ahead** — synthetic FinLab-shaped panel including one delisted stock; assert `build_survivorship_universe` includes it for dates while alive, excludes after delist, and never reads across dates.
4. **Source selector** — `make_ingest(source="finmind")` still routes to the FinMind path (fallback intact); default routes to FinLab.

Target: new module ≥ 90% coverage; suite stays green (no regression to the 959 pass / current cache-backed tests).

## 8. Scope

**In ①:** `finlab_source.py` (login / batch ingest / survivorship universe / source flag), schema-parity + round-trip + universe + selector tests, ADR-006 amendment (FinLab primary-in-practice + finlab 2.0 auth note), WBS 3.B / 16 §2 update.

**Out of ① (later sub-projects):**
- ② the re-validation run itself (inst_flow + structures on the full survivorship-clean universe with a real OOS split → real deployment numbers).
- ③ `market_reader` live EOD path + forward daemon wiring (reuses this loader).
- Broker-chip (券商分點 L3) ingestion — not needed by inst_flow; out of scope.
- finlab 2.0 new-auth migration — noted as follow-up, not blocking (token auth works until 2026/08).

## 9. Resolved-in-planning (Phase 2)
- Exact FinLab dataset keys for **market-cap** and **turnover/成交金額** (one tiny live probe). Design is unaffected — `build_survivorship_universe` only needs *a* panel.
- Whether `成交股數` (shares) vs `成交金額` (turnover NTD) is the liquidity floor unit (spec §6 of universe_builder uses NTD turnover → use `成交金額`).
