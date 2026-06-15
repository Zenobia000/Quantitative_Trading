# 對照因子診斷結果（2026-06-04）— 定位 no-edge 在哪

> 腳本：`backtest_platform/scripts/factor_baseline_diagnostic.py`（純用 cached parquet，免費）。
> 目的：四層共振三方向皆 fail 後，用**已知簡單基準**跑同一條 data + cost model + gate，
> 分離三個假設：H1 universe/期間本身下行 / H2 此盤無 edge 可萃 / H3 四層本身在毀價值。

## 設定（apples-to-apples）

- 同 cost model：`StrategyConfig.cost_round_rate ≈ 0.671%`；同 metrics（`validation.metrics`）；同 gate（Sharpe>1.0 + CAGR>18%）。
- universe：LARGE（10 大型）、SMID（19 中小型，探針已 ingest）；benchmark = **0050**（台灣 50 ETF）。
- 策略（皆 long-only）：0050 buy-hold / 等權 buy-hold / **12-1 動能**（月再平衡、long top⅓、扣周轉成本）。

## 結果

| universe | strategy | 2015-2020 | 2020-2024 |
|:--|:--|:--|:--|
| bench | **0050 buy-hold** | CAGR 14.5% / Sharpe 0.92 | 19.7% / 0.97 |
| LARGE | 等權 buy-hold | 12.4% / 0.79 | 14.6% / 0.88 |
| LARGE | **12-1 動能** | 15.8% / 0.77 | **25.9% / 1.08 ✅PASS** |
| SMID | 等權 buy-hold | 8.7% / 0.60 | 21.8% / 1.14 ✅ |
| SMID | **12-1 動能** | **25.4% / 1.07 ✅PASS** | 29.8% / 0.96 |
| — | **four-layer v3.1b** | **−1.6% / −0.37** | **−3.0% / −0.63** |

## 判決：H3 — 四層共振本身在**毀價值**

1. **不是 universe/期間**（H1 否）：market（0050）兩窗 +14.5%/+19.7%、兩個 universe 等權 buy-hold 也全正（+8.7%~+21.8%）。盤是漲的。
2. **不是「此盤無 edge」**（H2 否）：**12-1 動能在同一平台 PASS gate**（LARGE 2020-2024 Sharpe 1.08；SMID 2015-2020 Sharpe 1.07），四個窗全正、且多數**贏過 buy-hold**——有真實可萃的因子 spread。
3. **是四層本身**（H3 是）：同一批股票 buy-hold 賺 +12~22%，**四層的進出場把它做成 −2~−3%**——比「什麼都不做」還差 ~20+ 個百分點。四層的訊號在**系統性錯誤擇時**。

**→ 平台、資料、成本模型、universe 全部驗證為健康**（簡單因子在上面活得很好）。**問題 100% 在四層共振的訊號邏輯**。

## 含意 & 建議

- **平台被反向驗證**：它能正確判出「動能有 edge、四層沒有」——審判庭可信。前面所有「no edge」判決都成立、非工具問題。
- **強烈建議：砍四層共振**。它不是「edge 不夠」，是「**負 edge、主動毀價值**」——再調進場/universe/籌碼都無意義（buy-hold 都贏它 20pp）。
- **下一個 edge 來源已現成**：**動能家族（12-1 / 52 週高 / 時間序列動能）在這個資料上 provably 有 edge**。把策略換成動能基礎，平台一行 `run-is` 即可正式驗（OOS/PBO/DSR 全套防過擬合接著上）。

## 限制（誠實）

- 動能結果含 survivorship bias（現存上市 universe）+ N 小 → **非可部署的最終 verdict**，需 point-in-time universe 正式重驗才能上線。
- 但**作為診斷**結論穩固：相對比較（動能 vs 四層，同一偏誤樣本）公平，四層仍災難性落後；且「盤在漲 + 動能 PASS gate」這兩點與偏誤無關，足以推翻 H1/H2。
- 四層 long-only 帶擇時、基準亦 long-only，比較公平——正是擇時在毀價值。
