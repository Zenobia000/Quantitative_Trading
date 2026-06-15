# inst_flow Re-validation on FinLab Survivorship-Clean Universe (②)

> **Date:** 2026-06-15 · **Sub-project:** ② (FinLab data unification) · **Methodology:** unchanged ([ADR-025](adrs/) two-stage gate + [ADR-016](adrs/) thresholds) — only the data is honest now.
> **Driver:** `scripts/inst_flow_revalidate_finlab.py` → builds a point-in-time survivorship-clean universe from FinLab (`research/finlab_universe.py`), ingests via `data/finlab_source.py` (①), re-runs `scripts/inst_flow_truth_gate.py`.

## Why

The first truth-gate run used only the **10 large-cap survivors** I had cached → CAGR ~33% (survivor-inflated). Paid FinLab (①) gives full history 2007→today + delisted stocks, so this re-validates inst_flow on a genuinely survivorship-clean, full-span (2010-2024) universe with real WFA OOS.

## Results (real, verified runs)

| Universe (per-quarter top-N by mcap, union) | Names | Delisted | Full-span CAGR | Full Sharpe | WFA median OOS | OOS>0 | landscape PBO | DSR | Truth Gate |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| top-40 (large-cap) | 78 | 3 | **20.6%** | 1.36 | 1.54 | 84% | 42.9% | 1.00 | **REAL** |
| top-200 (broad) | 423 | (churning) | **16.2%** | 1.17 | 1.48 | 89% | 42.9% | 1.00 | **REAL** |
| _ADR-024 ref (116, 76 delisted)_ | _116_ | _76_ | _13.1%_ | _0.90_ | _1.30_ | _—_ | _42.9%_ | _—_ | _(pre-ADR-025: NO-GO on binary CAGR)_ |

Span 2010-01-01..2024-12-31, 3681 bars; fixed config `quarterly / lookback 60 / foreign`; K3 (+0.3%/leg) Sharpe unchanged from full (1.36 / 1.17).

## Findings

1. **Universe-selection by market cap is itself survivor-biased.** Top-40-by-mcap picks the largest names, which almost never delist (3/78 delisted) → CAGR 20.6% ≈ the old ADR-024 "40-name 18.9%" survivor number. Broadening to top-200 (423 names, includes the churning mid-cap segment) drops it to 16.2%, trending toward ADR-024's honest survivorship-clean **13.1%**. **Absolute CAGR is universe-dependent** — sizing should use the broad/honest figure (~16%), not the large-cap 20%.

2. **The ADR-025 truth-gate verdict is ROBUST to universe breadth.** Both 78-name and 423-name universes return **REAL**: WFA median OOS Sharpe stays ~1.5, OOS>0 ≥84%, DSR ≈1.00. The verdict rests on **pre-registered OOS breadth + deflated DSR**, not the absolute CAGR that the universe shifts around.

3. **landscape PBO 42.9% reproduced exactly** (same as ADR-024's 116-name) — and ADR-025's thesis is validated on full FinLab data: landscape PBO measures *config-selection* overfit and is **correctly ignored** for a single pre-registered config (which is judged by OOS + DSR). The binary-PBO that killed inst_flow pre-ADR-025 was the wrong test.

## Conclusion

**inst_flow is paper-ready — confirmed on honest full-FinLab survivorship-clean data**, not just the rosy 10-survivor cache. The factor has a real, OOS-robust edge (median OOS Sharpe ~1.5, DSR ≈1.0) that survives across universe definitions; the absolute CAGR (16–20%) depends on universe breadth. This **strengthens** ADR-024/025: the conditional GO that was revoked under the binary ADR-016 CAGR gate is restored under ADR-025's two-stage gate, now on genuinely better data.

**Next (③):** `market_reader` + forward paper to collect *live* OOS (execution friction) — the only remaining gate, and the only part that needs real calendar time. Sizing input CAGR should use the broad-universe ~16%.

## Reproduce

```bash
cd backtest_platform
set -a; . ./.env; set +a   # FINLAB_API_TOKEN
uv run --extra data_paid --extra sprint1 --extra dev python scripts/inst_flow_revalidate_finlab.py
# TOP_N_PER_QUARTER in the script controls universe breadth (default 200 = broad/honest)
```
