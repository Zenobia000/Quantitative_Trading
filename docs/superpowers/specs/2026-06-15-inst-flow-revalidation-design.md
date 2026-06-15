# inst_flow Re-validation on FinLab Survivorship-Clean — Spec + Plan

> **Date:** 2026-06-15 · **Status:** Approved (sequence pre-approved by user: ①→②→③) · **Sub-project:** ②
> **Relates:** [ADR-024](../../../dev_docs/adrs/) (inst_flow), [ADR-025](../../../dev_docs/adrs/) (two-stage gate), [ADR-016](../../../dev_docs/adrs/) (thresholds). Builds on ① `data/finlab_source.py`.

## Goal

Produce inst_flow's **honest deployment numbers** by re-running the ADR-025 two-stage truth gate on a **FinLab-sourced, survivorship-clean universe** (incl. delisted) over a real OOS span — replacing the misleading 10-survivor run (CAGR 33%). Methodology is **unchanged** (ADR-025 two-stage + ADR-016 thresholds); only the data improves.

## Approach

1. **Universe** — vectorized point-in-time survivorship-clean selection from FinLab (`etl:market_value`, `price:成交金額`, `etl:adj_close`): at each quarter-end in span, rank alive names (close valid in trailing window) by market cap, apply the 成交金額 liquidity floor, take top-N; **union across quarters (incl. delisted)** → a fixed factor universe. This is the survivorship-clean set the factor trades.
2. **Ingest** — `finlab_source.ingest_universe_finlab(universe, span)` into a dedicated parquet dir.
3. **Re-run** — the existing `inst_flow_truth_gate` harness (WFA OOS breadth + 24-config landscape PBO + deflated DSR + K3 slippage → `evaluate_truth_gate`/`compute_position_size`) over that dir + span.
4. **Report** — write the real verdict + numbers to a result doc; update WBS/ADR-024/025.

## File Structure

- Create: `src/backtest_platform/research/finlab_universe.py` — `select_survivorship_universe(...)` (pure, testable).
- Modify: `scripts/inst_flow_truth_gate.py` — parametrize `_all_symbols(parquet_dir)`, `_load(symbols, parquet_dir)`, `main(*, parquet_dir, span) -> dict` (return verdict/numbers; defaults preserve current behavior).
- Create: `scripts/inst_flow_revalidate_finlab.py` — build universe → ingest → call harness → print + write result doc.
- Create: `tests/research/test_finlab_universe.py` — selection on synthetic wide frames (delisted included while alive; liquidity floor; top-N; union).
- Create: `dev_docs/inst_flow_truth_gate_finlab_result_2026-06-15.md` — result.
- Modify: WBS (②), ADR-024/025 cross-ref.

## Tasks (TDD)

1. **`select_survivorship_universe`** — test first (synthetic mv/close/turnover with a delisted name → assert it's selected in a quarter while alive, excluded after; illiquid dropped; result is sorted unique list capped at the per-quarter top-N union). Implement vectorized (`reindex(method="ffill")` as-of; alive = close valid in trailing 90d; no look-ahead). Commit.
2. **Parametrize harness** — `_all_symbols`/`_load`/`main` take `parquet_dir`/`span`; `main` returns `{verdict, median_oos, oos_positive_frac, landscape_pbo, dsr, cagr, sharpe, slippage_sharpe, n_names, size}`. Existing `python scripts/inst_flow_truth_gate.py` unchanged. Commit.
3. **`inst_flow_revalidate_finlab.py`** — `login()` → build universe (top_n≈40/quarter, min_turnover 2e7, span 2010-2024) → `ingest_universe_finlab` into `data/parquet_finlab_universe/` → `inst_flow_truth_gate.main(parquet_dir=…, span=…)` → print + write result doc. Commit.
4. **Run live** → capture real numbers. Write result doc with verdict + comparison (10-survivor 33% → real survivorship-clean X%). Commit.
5. **Doc sync** — WBS v3.8→v3.9 (② done, real numbers), ADR-024/025 cross-ref the result. Commit.

## Test Plan
- [ ] `test_finlab_universe` green (pure-function selection, no live calls).
- [ ] Full suite stays green.
- [ ] Live re-validation run completes → verdict (REAL/REJECTED) + numbers recorded; honest CAGR/Sharpe vs the 10-survivor figure documented.

## Non-goals
- New thresholds / new gate logic (reuse ADR-025/016).
- The 4 `stock_strategy/` candidates (optional stretch; primary ② target is inst_flow). market_reader/forward = ③.
