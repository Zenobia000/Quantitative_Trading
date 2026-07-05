# 策略研究 DOE 完整模板

> **版本**：v1.0
> **建立日期**：2026-05-26
> **目的**：為四層共振戰法（v2.md）建立完整的 Design of Experiments 框架
> **原則**：所有 DOE 必須**預註冊**（pre-register），跑完不可回頭改設計
> **上游**：`strategy/v2.md` v2.1.0、`strategy/research/v2.2_ic_test_plan.md`

---

## 目錄

- [Part 0：為什麼需要 DOE](#part-0為什麼需要-doe)
- [Part 1：DOE 分層架構](#part-1doe-分層架構)
- [Part 2：10 個 DOE 詳細規格](#part-210-個-doe-詳細規格)
  - [DOE-1：單因子 IC 篩選](#doe-1單因子-ic-篩選)
  - [DOE-2：因子交互效應](#doe-2因子交互效應-24-full-factorial)
  - [DOE-3：參數篩選](#doe-3參數篩選plackett-burman)
  - [DOE-4：響應曲面優化](#doe-4響應曲面優化ccd)
  - [DOE-5：進場模型擂台](#doe-5進場模型擂台abc-tournament)
  - [DOE-6：Regime 分層分析](#doe-6regime-分層分析)
  - [DOE-7：成本敏感度](#doe-7成本敏感度-grid)
  - [DOE-8：Universe Filter 敏感度](#doe-8universe-filter-敏感度)
  - [DOE-9：Walk-Forward 穩健性 + CSCV](#doe-9walk-forward-穩健性--cscv)
  - [DOE-10：Bootstrap 與 Monte Carlo](#doe-10bootstrap-與-monte-carlo)
- [Part 3：統計工具箱](#part-3統計工具箱)
- [Part 4：預註冊紀律](#part-4預註冊紀律)
- [Part 5：執行流程與時程](#part-5執行流程與時程)
- [Part 6：失敗的處理](#part-6失敗的處理)

---

# Part 0：為什麼需要 DOE

## 0.1 DOE vs ad-hoc 回測

| ad-hoc 回測 | DOE |
| :--- | :--- |
| 改一個參數、跑一次、看結果 | 一次性測試完整參數空間 |
| 容易陷入 multiple testing 而不自知 | 預先計算 effect size 與 N |
| 結果無法重現 | 設計矩陣公開、結果可重現 |
| 因果歸因模糊 | ANOVA 拆解主效應與交互效應 |
| 「再試一個參數說不定就過了」 | 預註冊跑完即定案 |

**核心問題**：策略研究本質是**多因子實驗**，但業界常用「改一個跑一次」的試誤法，等於 **N 次單因子實驗**而非 DOE。
這會導致：
- 漏掉因子間交互效應（兩個因子單獨無用，組合有效）
- 過度依賴「最近一次跑的結果」
- 無法量化策略「真的有 Edge」vs「運氣好調出來」的機率

## 0.2 量化交易特殊性

DOE 在製造業、農業、心理學成熟，套到交易需注意：

| 領域差異 | 影響 |
| :--- | :--- |
| 時間序列不獨立 | 不能簡單 random shuffle，需 block by time |
| 樣本量受市場給定 | 不能「再多做幾次實驗」 |
| Non-stationarity | 因子效應隨 regime 變化，需 stratify |
| Multiple testing | 一年內測 100 組參數，5 組顯著也可能全是運氣 |
| Look-ahead bias | 設計矩陣本身可能洩漏未來 |

## 0.3 本文件的範圍

涵蓋 v2.md 從**因子驗證**到**統計顯著性檢驗**的完整 DOE 鏈：

```
階段 1：因子驗證  → DOE 1, 2, 3
階段 2：參數優化  → DOE 3, 4
階段 3：規則驗證  → DOE 5
階段 4：環境穩健  → DOE 6, 7, 8
階段 5：統計檢定  → DOE 9, 10
```

**不涵蓋**：
- 實作具體回測引擎程式（屬 NO PASS 區的工程工作）
- 個別參數的最佳值（DOE 是找方法、不是給答案）

---

# Part 1：DOE 分層架構

## 1.1 5 層架構

```
┌─────────────────────────────────────────────────────┐
│  Layer 5：統計檢定（Statistical Validation）       │
│    DOE-9 WFA/CSCV   DOE-10 Bootstrap/MC            │
├─────────────────────────────────────────────────────┤
│  Layer 4：環境穩健（Environmental Robustness）     │
│    DOE-6 Regime   DOE-7 Cost   DOE-8 Universe      │
├─────────────────────────────────────────────────────┤
│  Layer 3：規則驗證（Rule Validation）              │
│    DOE-5 進場模型擂台                              │
├─────────────────────────────────────────────────────┤
│  Layer 2：參數優化（Parameter Optimization）       │
│    DOE-3 Screening   DOE-4 Response Surface        │
├─────────────────────────────────────────────────────┤
│  Layer 1：因子驗證（Factor Validation）            │
│    DOE-1 IC   DOE-2 Interaction                    │
└─────────────────────────────────────────────────────┘
```

## 1.2 依賴關係

```
DOE-1 (單因子 IC)
  └── DOE-2 (因子交互)
        └── DOE-3 (參數篩選)
              └── DOE-4 (響應曲面)
                    └── DOE-5 (進場模型)
                          └── DOE-6/7/8 (環境穩健，並行)
                                └── DOE-9 (WFA)
                                      └── DOE-10 (MC/Bootstrap)
```

**鐵律**：上層 DOE 失敗 → 下層不必跑（節省時間與避免過擬合）

## 1.3 工時總覽

| DOE | 工時 | 累計 |
| :---: | :---: | :---: |
| 1 | 30h | 30h |
| 2 | 15h | 45h |
| 3 | 20h | 65h |
| 4 | 25h | 90h |
| 5 | 15h | 105h |
| 6 | 10h | 115h |
| 7 | 8h | 123h |
| 8 | 10h | 133h |
| 9 | 30h | 163h |
| 10 | 15h | 178h |

**總計約 180h**，全職 1 個月、兼職 2–3 個月。

---

# Part 2：10 個 DOE 詳細規格

每個 DOE 採用統一模板，含 11 個欄位：

```
1. 目的 / 假設
2. 因子定義
3. 響應變數
4. 設計類型
5. 設計矩陣
6. 樣本量計算
7. 執行步驟
8. 分析方法
9. 通過標準
10. 失敗處理
11. 工時 / 依賴
```

---

## DOE-1：單因子 IC 篩選

### 1. 目的 / 假設

驗證四層計分系統（L1–L4）的每個因子是否有獨立預測力。

| H0 | 該因子對未來報酬無預測力 (IC = 0) |
| :--- | :--- |
| H1 | 該因子 IC ≠ 0 且具經濟顯著性 (|IC| ≥ 0.03) |

### 2. 因子定義

| 因子 | 類型 | 區間 | 計算（依 v2.md 2.3） |
| :--- | :--- | :---: | :--- |
| L1 結構分 | 數值 | 0–2 | 突破/中線/中線下 |
| L2 法人方向分 | 數值 | -1 ~ 2 | 同步/單邊/賣 |
| L3 籌碼強度分 | 數值 | -1 ~ 2 | chip_ratio 分級 |
| L4 動能分 | 數值 | -1 ~ 2 | 三陽/金叉/中性/熄火 |

### 3. 響應變數

| 主要 | Spearman IC（cross-sectional rank correlation） |
| :--- | :--- |
| 次要 | IC_IR、t-stat、Hit Rate、Q5-Q1 spread |
| 約束 | 樣本量 N ≥ 30 trading days × 100 stocks |

### 4. 設計類型

**One-Factor-At-a-Time (OFAT) IC scan**
- 4 factors × 6 holding periods = **24 cells**
- 每 cell 獨立計算（不混合）

### 5. 設計矩陣

詳見 `v2.2_ic_test_plan.md` 第二階段表格。

### 6. 樣本量計算

```
Power analysis（α=0.05, β=0.20, two-tailed）：
  detect |IC| = 0.03 with power 0.80
  → 需 N ≈ 7,000 (stock × day) observations
  → 10 年 × 250 days × ≥ 100 stocks = 250,000 充裕
```

### 7. 執行步驟

```python
for factor in [L1, L2, L3, L4]:
    for holding_period in [1, 3, 5, 10, 20, 60]:
        ic_series = []
        for date in all_trading_days:
            stocks = universe_at(date)
            factor_values = compute_factor(stocks, factor, date)
            forward_returns = compute_return(stocks, date, date + holding_period)
            ic_t = spearmanr(factor_values, forward_returns)
            ic_series.append(ic_t)
        record(factor, holding_period, ic_series)
```

### 8. 分析方法

- IC mean、std、IR
- t-test for H0: IC=0
- Plot IC time series（檢查穩定性）
- Plot Q1–Q5 cumulative returns

### 9. 通過標準

| 指標 | 綠燈 | 紅燈 |
| :--- | :---: | :---: |
| \|IC\| | ≥ 0.03 | < 0.02 |
| IC_IR | ≥ 0.5 | < 0.3 |
| t-stat | ≥ 2 | < 1 |
| Hit Rate | ≥ 52% | < 50% |

### 10. 失敗處理

- 1 個因子全紅 → 該因子砍掉（從四層變三層）
- 2+ 因子全紅 → 策略 hypothesis 失效，回 Part 2.1 重思考

### 11. 工時 / 依賴

- 工時：**30h**
- 依賴：資料準備完成（FinMind / TEJ）

---

## DOE-2：因子交互效應 (2^4 Full Factorial)

### 1. 目的 / 假設

驗證四因子是否存在**交互效應**：兩因子同時為強訊號時，預測力是否大於單獨之和。

| H0 | 因子效應加性（無交互） |
| :--- | :--- |
| H1 | 存在顯著交互（interaction p < 0.05） |

### 2. 因子定義

每因子二值化為「強」(score = 2) vs 「弱」(score < 2)：

| 因子 | Level (-) 弱 | Level (+) 強 |
| :--- | :---: | :---: |
| L1 | 0, 1 | 2 |
| L2 | -1, 0, 1 | 2 |
| L3 | -1, 0, 1 | 2 |
| L4 | -1, 0, 1 | 2 |

### 3. 響應變數

| 主要 | 10 天前向報酬均值 |
| :--- | :--- |
| 次要 | Win rate、Sharpe、Sortino |

### 4. 設計類型

**2^4 Full Factorial**
- 16 個 cells（所有因子強弱組合）
- 含 4 個主效應 + 6 個 2-way 交互 + 4 個 3-way + 1 個 4-way

### 5. 設計矩陣

| Run | L1 | L2 | L3 | L4 |
| :---: | :---: | :---: | :---: | :---: |
| 1 | − | − | − | − |
| 2 | + | − | − | − |
| 3 | − | + | − | − |
| 4 | + | + | − | − |
| 5 | − | − | + | − |
| 6 | + | − | + | − |
| 7 | − | + | + | − |
| 8 | + | + | + | − |
| 9 | − | − | − | + |
| 10 | + | − | − | + |
| 11 | − | + | − | + |
| 12 | + | + | − | + |
| 13 | − | − | + | + |
| 14 | + | − | + | + |
| 15 | − | + | + | + |
| 16 | + | + | + | + |

### 6. 樣本量計算

每 cell 至少需 30 個樣本（trade-level）：
- 10 年 × ~250 trading days × ~100 stocks = 250,000 stock-day
- 篩選後落在每 cell 預估 1,000–10,000 → **充裕**

若某些 cell 樣本過少（< 30），標記為「unreliable」，不納入分析。

### 7. 執行步驟

1. 對全 universe 每日計算 (L1, L2, L3, L4) 分數
2. 二值化為 ± 後，分到 16 個 bucket
3. 計算各 bucket 的 10 天前向報酬
4. ANOVA 拆解效應

### 8. 分析方法

**4-way ANOVA**：

```
return ~ L1 + L2 + L3 + L4
       + L1*L2 + L1*L3 + L1*L4 + L2*L3 + L2*L4 + L3*L4
       + L1*L2*L3 + L1*L2*L4 + L1*L3*L4 + L2*L3*L4
       + L1*L2*L3*L4
```

關注：
- 主效應大小（哪個因子最重要）
- 2-way 交互（哪兩個因子協同）
- High-order 交互（通常雜訊，可 pool）

### 9. 通過標準

| 結果 | 解讀 |
| :--- | :--- |
| 所有主效應顯著 (p<0.05) + 無 2-way 交互 | 四因子可加性，等權加總合理 |
| 主效應 + 強 2-way 交互 | 改用 IC 加權 + 交互項 |
| 高階交互主導 | 模型結構錯，改 logical AND/OR |

### 10. 失敗處理

- 若 4-way 交互最強 → 「四層共振」可能就是 AND 邏輯而非加總
- 對應 v2.md 修改：score 改為 `min(L1, L2, L3, L4)` 或 `prod`

### 11. 工時 / 依賴

- 工時：**15h**
- 依賴：DOE-1 至少 3 個因子綠燈

---

## DOE-3：參數篩選（Plackett-Burman）

### 1. 目的 / 假設

從 v2.md 13 個參數中，篩出**真正影響績效**的少數重要參數。

| H0 | 該參數對 Sharpe 無影響 |
| :--- | :--- |
| H1 | 該參數 main effect ≠ 0 |

### 2. 因子定義

| # | 參數 | Level (-) | Level (0) | Level (+) |
| :---: | :--- | :---: | :---: | :---: |
| 1 | box_period | 30 | 60 | 90 |
| 2 | chip_strong_threshold | 0.05 | 0.10 | 0.15 |
| 3 | strong_buy_threshold | 4 | 5 | 6 |
| 4 | warning_threshold | 1 | 2 | 3 |
| 5 | add_score_threshold | 5 | 6 | 7 |
| 6 | takeprofit_volume_rate | 1.0 | 1.5 | 2.0 |
| 7 | takeprofit_shadow_rate | 1.0 | 1.5 | 2.0 |
| 8 | slip_rate | 0.0005 | 0.001 | 0.002 |
| 9 | min_edge_rate | 0.004 | 0.006 | 0.008 |
| 10 | tp_min_net_rate | 0.010 | 0.015 | 0.025 |
| 11 | stoploss_atr_mult | 1.5 | 2.0 | 2.5 |
| 12 | risk_pct | 0.003 | 0.005 | 0.008 |
| 13 | max_positions | 5 | 8 | 10 |

### 3. 響應變數

| 主要 | Sharpe Ratio |
| :--- | :--- |
| 次要 | CAGR、Max DD |

### 4. 設計類型

**Plackett-Burman Design (PB-16)**
- 13 因子 × 2 levels（用 ± 訓練，0 為驗證點）
- 16 runs（最小化實驗次數）
- 只解析主效應，假設交互可忽略（後續 DOE-4 處理交互）

### 5. 設計矩陣

Plackett-Burman 12-run 矩陣（標準 PB12 + 3 dummy），完整矩陣由 `pyDOE2.pbdesign(13)` 生成。

### 6. 樣本量計算

每 run = 一次完整回測（10 年）。
- 16 runs × 一次回測時長
- 若一次回測 = 10 min → 總計 ~3 hours

### 7. 執行步驟

1. 生成 PB 設計矩陣
2. 對每個 run 執行完整回測（用基準的 universe + cost）
3. 記錄 Sharpe / CAGR / DD
4. 計算每個因子的 main effect

### 8. 分析方法

```
main_effect_i = mean(Sharpe | factor_i = +) - mean(Sharpe | factor_i = -)
```

**Pareto plot**：依絕對值排序，前 ~3-5 名為「重要參數」。

### 9. 通過標準

- 識別出 3–5 個 main effect 顯著的參數（前 80% 變異）
- 其餘參數固定為 v2.md 預設值

### 10. 失敗處理

- 若所有參數 effect 都微弱 → 策略對參數不敏感（好事，無過擬合風險）
- 若全部都很重要 → 模型過於複雜，需簡化

### 11. 工時 / 依賴

- 工時：**20h**（含回測引擎建置）
- 依賴：DOE-1 通過

---

## DOE-4：響應曲面優化（CCD）

### 1. 目的 / 假設

對 DOE-3 篩出的 3–5 個重要參數，**找出最佳組合**。

| H0 | 績效在參數空間隨機 |
| :--- | :--- |
| H1 | 存在局部最佳值（responsesurface 有曲率） |

### 2. 因子定義

DOE-3 篩出的 top 3 參數，每個 3 levels（low/mid/high）+ axial points。

### 3. 響應變數

| 主要 | Sharpe Ratio |
| :--- | :--- |
| 次要 | Calmar、PF |

### 4. 設計類型

**Central Composite Design (CCD)**
- 3 factors × CCD = 8 (factorial) + 6 (axial) + 5 (center) = **19 runs**
- 可擬合二次多項式：`Y = β₀ + Σβᵢxᵢ + Σβᵢᵢxᵢ² + Σβᵢⱼxᵢxⱼ`

### 5. 設計矩陣

由 `pyDOE2.ccdesign(3, center=(0,5), alpha='r', face='ccc')` 生成。

### 6. 樣本量計算

19 runs × 一次回測（10 年）≈ 3 hours

### 7. 執行步驟

1. 取 DOE-3 top 3 參數
2. 跑 CCD 19 runs
3. 擬合二次響應曲面
4. 找局部最佳：`∂Y/∂xᵢ = 0`

### 8. 分析方法

- 二次回歸（least squares）
- R²、Adjusted R² 檢驗模型擬合度
- Lack-of-fit test
- Contour plot 視覺化

### 9. 通過標準

- R² > 0.7（曲面合理）
- 最佳值落在設計範圍內（非邊界）
- 最佳值的 Sharpe 比 DOE-3 中位數高 20%+

### 10. 失敗處理

- 最佳落在邊界 → 擴大參數範圍重跑
- 多個局部最佳 → 模型不穩，警示過擬合
- R² 太低 → 響應非二次，需 higher-order 或非線性模型

### 11. 工時 / 依賴

- 工時：**25h**
- 依賴：DOE-3 完成

---

## DOE-5：進場模型擂台（A/B/C Tournament）

### 1. 目的 / 假設

對 v2.md 2.6.3 的三個進場模型（A: VWAP / B: ORB / C: EMA20）做擂台賽，只留**最佳一個**。

| H0 | 三模型績效無顯著差異 |
| :--- | :--- |
| H1 | 至少一個模型顯著優於其他 |

**為什麼必要**：原 v2.md「擇一觸發」隱含 model selection bias，相當於變相放寬進場條件。

### 2. 因子定義

| 因子 | Levels |
| :--- | :--- |
| Entry Model | A (VWAP) / B (ORB) / C (EMA20) / D (Naive T+1 Open，對照組) |

### 3. 響應變數

| 主要 | 平均單筆 R 倍數（trade-level Expectancy） |
| :--- | :--- |
| 次要 | Win rate、Avg holding period、Slippage |

### 4. 設計類型

**Randomized Complete Block Design**
- Block: trading day（消除日效應）
- Treatment: 4 entry models
- 每 day 對所有 signal 套用所有 4 模型 → 配對比較

### 5. 設計矩陣

```
Day 1: signal_stock_1 → run model A, B, C, D（記錄各自報酬）
Day 2: signal_stock_2 → run model A, B, C, D
...
```

### 6. 樣本量計算

Paired t-test, effect size d=0.2, α=0.05, β=0.20：
- N ≥ 200 signals per model
- 10 年 × 預估每年 50–100 signals = 500–1000 → 充裕

### 7. 執行步驟

1. 識別所有 v2.md 強多訊號日
2. 對每個 signal 平行模擬 4 種進場
3. 記錄各自 5/10/20 天報酬

### 8. 分析方法

- Repeated measures ANOVA
- Pairwise comparison with Bonferroni correction
- Box plot per model

### 9. 通過標準

- 至少一個模型顯著優於 D (naive)
- 最佳模型 Expectancy ≥ 0.3R
- 確認**唯一冠軍**保留，其餘從 v2.md 刪除

### 10. 失敗處理

- 三模型都輸給 D → 三模型沒價值，直接用 T+1 開盤
- 三模型相當 → 用最簡單（D）或最便宜（B 不需 VWAP 計算）

### 11. 工時 / 依賴

- 工時：**15h**
- 依賴：DOE-3 完成（用 DOE-3 篩出的參數）

---

## DOE-6：Regime 分層分析

### 1. 目的 / 假設

驗證策略在不同市場 regime 下的穩健性。

| H0 | 策略績效在 regime 間無差異 |
| :--- | :--- |
| H1 | 至少一個 regime 顯著劣於整體 |

### 2. 因子定義

| 因子 | Levels |
| :--- | :--- |
| Regime | 多頭 / 盤整 / 空頭 |

Regime 定義（依 v2.md 2.1.2）：
- 多頭：大盤 200MA 上升 + 年漲 > 5%
- 盤整：大盤 ±5% 區間
- 空頭：大盤 200MA 下降

### 3. 響應變數

每 regime 分別計算：Sharpe / CAGR / MaxDD / PF / 訊號頻率

### 4. 設計類型

**Stratified Analysis**
- 按 regime 切資料
- 對每段獨立計算指標

### 5. 設計矩陣

| Regime | 預估期間（依 2015–2024） |
| :--- | :--- |
| 多頭 | 2016–2017、2020/04–2021、2023–2024 |
| 盤整 | 2015、2019、2024/H2 |
| 空頭 | 2018 中、2020/02–03、2022 |

### 6. 樣本量計算

每 regime 至少 12 個月，含 30+ trades，否則合併 regime。

### 7. 執行步驟

1. 對 2015–2024 每日標註 regime
2. 按 regime 切回測結果
3. 每段獨立計算指標

### 8. 分析方法

- ANOVA: Sharpe ~ Regime
- Post-hoc: Tukey HSD pairwise comparison

### 9. 通過標準

| Regime | 最低要求 |
| :--- | :--- |
| 多頭 | Sharpe > 1.2 |
| 盤整 | PF > 1.0（不虧） |
| 空頭 | DD < 15% |

### 10. 失敗處理

- 空頭崩盤 → 加 regime filter（大盤 200MA 下行時停機）
- 盤整虧損 → 加震盪過濾（ADX、波動率）

### 11. 工時 / 依賴

- 工時：**10h**
- 依賴：DOE-4 完成

---

## DOE-7：成本敏感度 Grid

### 1. 目的 / 假設

驗證策略 Edge 對成本假設的敏感度。

| H0 | 績效不受成本變化影響 |
| :--- | :--- |
| H1 | 成本增加導致績效顯著退化 |

### 2. 因子定義

| 因子 | Levels |
| :--- | :--- |
| Slippage | 0.05%, 0.1%, 0.2%, 0.5%, 1.0% |
| Fee discount | 0.4, 0.6, 0.8（不同券商） |

### 3. 響應變數

Sharpe、CAGR、訊號通過率（被成本濾網擋下的比例）

### 4. 設計類型

**Full Factorial Grid**
- 5 × 3 = 15 cells

### 5. 設計矩陣

略（5 × 3 grid）

### 6. 樣本量計算

15 runs × 完整回測 ≈ 2.5 hours

### 7. 執行步驟

對每個 cell 跑完整回測，繪製等高線圖。

### 8. 分析方法

- Heatmap (Slippage × Fee) → Sharpe
- 找 break-even 線（Sharpe = 1.0 等高線）

### 9. 通過標準

- 滑點 0.3% 下 Sharpe > 1.0
- 滑點 0.5% 下 Sharpe > 0.7
- 滑點 1.0% 下 Sharpe > 0.3（極限）

### 10. 失敗處理

- 0.3% 就崩 → Edge 太薄，實盤危險
- 對成本太敏感 → 拉長 holding period 攤薄

### 11. 工時 / 依賴

- 工時：**8h**
- 依賴：DOE-4 完成

---

## DOE-8：Universe Filter 敏感度

### 1. 目的 / 假設

驗證策略對標的池定義（v2.md 2.2）的依賴。

| H0 | Universe 變化不影響績效 |
| :--- | :--- |
| H1 | Universe 過嚴/過寬導致顯著差異 |

### 2. 因子定義

| 因子 | Levels |
| :--- | :--- |
| 市值門檻 | 30 / 50 / 100 / 300 億 |
| 日均量門檻 | 500 / 1000 / 2000 / 5000 張 |
| 上市時間 | > 0.5 / 1 / 2 / 3 年 |

### 3. 響應變數

Sharpe、訊號頻率、平均部位大小

### 4. 設計類型

**3^3 Fractional Factorial**
- 27 runs full，減為 **9 runs** (1/3 fraction)

### 5. 設計矩陣

由 `pyDOE2.fracfact("a b c")` 變體生成。

### 6. 樣本量計算

9 runs × 完整回測 ≈ 1.5 hours

### 7. 執行步驟

對每組 universe filter，重跑回測。

### 8. 分析方法

- 3-way ANOVA
- 找出 universe 邊界對哪些指標最敏感

### 9. 通過標準

- 預設 universe（v2.md 2.2）的 Sharpe 不是極端值
- 鬆/嚴 universe 的 Sharpe 變動 < 30%

### 10. 失敗處理

- 嚴 universe 大幅勝 → 預設 universe 過寬，需收緊
- 鬆 universe 大幅勝 → 預設 universe 過嚴，限制了 alpha

### 11. 工時 / 依賴

- 工時：**10h**
- 依賴：DOE-4 完成

---

## DOE-9：Walk-Forward 穩健性 + CSCV

### 1. 目的 / 假設

跨時間檢驗策略穩定性，並計算過擬合機率（PBO）。

| H0 | 策略在 OOS 期間維持 IS 績效 |
| :--- | :--- |
| H1 | OOS 績效顯著低於 IS（過擬合） |

### 2. 因子定義

無 manipulated factor，是 robustness check。

### 3. 響應變數

- IS Sharpe、OOS Sharpe（per window）
- PBO（probability of backtest overfitting）

### 4. 設計類型

**Walk-Forward Analysis (WFA) + CSCV**
- WFA: rolling window，IS 252 + OOS 63 days
- CSCV: combinatorial split, N=16 blocks, C(16,8) = 12,870 splits

### 5. 設計矩陣

```
Window 1: IS [2015/01–2015/12], OOS [2016/Q1]
Window 2: IS [2015/04–2016/03], OOS [2016/Q2]
...
Window 30: IS [2022/10–2023/09], OOS [2023/Q4]
```

### 6. 樣本量計算

- 30 windows × 一次回測
- CSCV: 12,870 splits，每 split ~ 1 second 計算 → ~3.5 hours

### 7. 執行步驟

1. WFA: 30 windows 逐一執行
2. 對每 window 在 IS 找最佳參數、OOS 驗證
3. CSCV: 用 v2.md 4.6.1 演算法計算 PBO

### 8. 分析方法

- Plot IS vs OOS Sharpe scatter
- PBO 計算
- Deflated Sharpe Ratio (DSR)

### 9. 通過標準

| 指標 | 綠燈 |
| :--- | :---: |
| OOS Sharpe / IS Sharpe | > 0.6 |
| OOS positive return windows | > 60% |
| PBO | < 30%（v2.1 標準） |
| DSR | > 0.95 |

### 10. 失敗處理

- PBO ≥ 50% → 嚴重過擬合，砍條件 / 砍參數重做
- PBO 30–50% → 警告，需簡化模型
- OOS/IS ratio < 0.5 → 策略不穩，需 regime filter

### 11. 工時 / 依賴

- 工時：**30h**
- 依賴：DOE-2 至 DOE-8 全部完成

---

## DOE-10：Bootstrap 與 Monte Carlo

### 1. 目的 / 假設

用隨機抽樣建立各指標的信賴區間，與破產機率。

| H0 | 策略指標的真值 = 樣本估計值 |
| :--- | :--- |
| H1 | 真值落在 95% CI 內，破產機率 < 1% |

### 2. 因子定義

無，純 simulation。

### 3. 響應變數

- Sharpe / CAGR / MaxDD 的 95% CI
- 破產機率 P(DD > 50%)

### 4. 設計類型

**Bootstrap + Monte Carlo Path Simulation**
- Bootstrap: bar-level resampling 1,000 次
- MC: trade-level random permutation 10,000 次

### 5. 設計矩陣

略（純 simulation）

### 6. 樣本量計算

- Bootstrap 1,000 iterations × ~1 sec = ~15 min
- MC 10,000 iterations × ~0.5 sec = ~80 min

### 7. 執行步驟

```python
# Bootstrap
for i in range(1000):
    resampled_bars = sample_with_replacement(daily_returns, len(daily_returns))
    metrics_i = compute_metrics(resampled_bars)

# Monte Carlo
for i in range(10000):
    shuffled_trades = random_permutation(trade_pnl_list)
    equity_curve_i = cumulative_sum(shuffled_trades)
    max_dd_i = max_drawdown(equity_curve_i)
```

### 8. 分析方法

- Percentile method for CI
- Distribution plots
- 計算 P(MaxDD > X) 各 threshold

### 9. 通過標準

| 指標 | 綠燈 |
| :--- | :---: |
| Sharpe 95% CI 下界 | > 0.5 |
| CAGR 5% percentile | > 8% |
| MaxDD 95% percentile | < 35% |
| 破產機率 P(DD > 50%) | < 1% |

### 10. 失敗處理

- CI 過寬 → 樣本量不足，需更多資料
- 破產機率 > 1% → 風控加嚴或砍策略

### 11. 工時 / 依賴

- 工時：**15h**
- 依賴：DOE-9 完成

---

# Part 3：統計工具箱

## 3.1 Power Analysis

決定 N（樣本量）的工具。

```python
from statsmodels.stats.power import TTestPower

power = TTestPower()
n = power.solve_power(effect_size=0.2, alpha=0.05, power=0.8)
# → N ≈ 200
```

**規則**：每次 DOE 設計時，先 power analysis 確認 N 足夠，否則結果無效。

## 3.2 Effect Size

| 指標 | 公式 | 小/中/大 |
| :--- | :--- | :--- |
| Cohen's d | (μ₁-μ₂)/σ | 0.2 / 0.5 / 0.8 |
| Cohen's f² | R²/(1-R²) | 0.02 / 0.15 / 0.35 |
| IC | 相關係數 | 0.03 / 0.05 / 0.10 |

**只看 p-value 不看 effect size 是錯的**：N 夠大時 p < 0.05 但 effect 微不足道。

## 3.3 Multiple Testing Correction

| 方法 | 適用 | 寬鬆度 |
| :--- | :--- | :--- |
| Bonferroni | 嚴格控制 FWER | 最嚴 |
| Holm-Bonferroni | 嚴格但更 powerful | 嚴 |
| BH (FDR) | 控制 false discovery rate | 中 |
| Sidak | independent tests | 中 |

**規則**：
- DOE 內部對比 → Bonferroni
- 跨 DOE 對比 → FDR 0.05
- 從不修正 → 你在自欺欺人

## 3.4 Confidence Intervals

```python
# Bootstrap CI
from scipy.stats import bootstrap
ci = bootstrap(
    (trade_returns,),
    statistic=np.mean,
    n_resamples=10000,
    confidence_level=0.95
).confidence_interval
```

**規則**：所有報告的 metric 都附 95% CI，否則不算 evidence。

## 3.5 ANOVA / Regression

```python
import statsmodels.formula.api as smf

# Factor interaction
model = smf.ols('sharpe ~ L1 * L2 * L3 * L4', data=df).fit()
print(model.summary())

# Type II ANOVA
from statsmodels.stats.anova import anova_lm
anova_lm(model, typ=2)
```

## 3.6 PBO 演算法（Bailey, López de Prado）

```python
def compute_pbo(strategies_returns, n_blocks=16):
    """
    strategies_returns: dict[strategy_name -> daily_returns]
    """
    from itertools import combinations
    blocks = split_into_blocks(strategies_returns, n_blocks)
    half = n_blocks // 2
    rankings = []
    for is_blocks in combinations(range(n_blocks), half):
        oos_blocks = [b for b in range(n_blocks) if b not in is_blocks]
        is_sharpe = {s: sharpe(merge(blocks[s], is_blocks)) for s in strategies_returns}
        best = max(is_sharpe, key=is_sharpe.get)
        oos_rank = rank(best, {s: sharpe(merge(blocks[s], oos_blocks)) for s in strategies_returns})
        rankings.append(oos_rank)
    pbo = sum(1 for r in rankings if r > len(strategies_returns)/2) / len(rankings)
    return pbo
```

---

# Part 4：預註冊紀律

## 4.1 為什麼需要預註冊

跑完才決定假設 = **p-hacking**。
預註冊把假設、設計、分析方法**鎖死在開跑前**。

## 4.2 預註冊文件範本

每個 DOE 開跑前寫一份：

```markdown
# DOE-X 預註冊（YYYY-MM-DD）

## 1. 假設
H0: ...
H1: ...

## 2. 設計
- 因子：...
- 響應：...
- 設計類型：...
- 樣本量：N = ..., power = ...

## 3. 分析計畫
- 主要分析：...
- 次要分析：...
- 修正方法：Bonferroni / FDR

## 4. 通過標準
- 主要指標 > X 且 p < 0.05
- 次要指標 ...

## 5. 失敗處理（事先決定）
- 主要失敗 → 行動 A
- 次要失敗 → 行動 B

## 6. 排除規則
什麼情況下不納入分析（如樣本量 < 30 的 cell）

## 7. 簽名
- 日期：YYYY-MM-DD
- 開跑時間：HH:MM
- 預期完成：YYYY-MM-DD
```

## 4.3 違反預註冊的處理

- 跑完想改假設 → **不可**。
- 跑完想加響應變數 → 標記為 exploratory，不可當 confirmatory evidence
- 跑完想改修正方法 → 不可。

跑完發現設計有問題 → 寫 v2 預註冊，**重跑完整實驗**，不可只跑差異部分。

---

# Part 5：執行流程與時程

## 5.1 階段路徑

```
階段 1（因子驗證）— 45h
├── DOE-1 (30h) ─────┐
└── DOE-2 (15h) ─────┤
                     │ 因子全綠 → 階段 2
                     │ 否則 → 砍因子或砍策略
                     ↓
階段 2（參數優化）— 45h
├── DOE-3 (20h) ─────┐
└── DOE-4 (25h) ─────┤
                     │ 找到最佳參數 → 階段 3
                     ↓
階段 3（規則驗證）— 15h
└── DOE-5 (15h) ─────┐
                     │ 確定進場模型 → 階段 4
                     ↓
階段 4（環境穩健，並行）— 28h
├── DOE-6 (10h)
├── DOE-7 (8h)
└── DOE-8 (10h)
                     │ 全綠 → 階段 5
                     ↓
階段 5（統計檢定）— 45h
├── DOE-9 (30h) ─────┐
└── DOE-10 (15h) ────┤
                     │ PBO < 30% → Paper Trading
                     ↓
                  進入 v2.md Part 4.7 五階段晉升
```

## 5.2 早期停止規則

| 階段 | 失敗情境 | 立即停止做什麼 |
| :--- | :--- | :--- |
| 1 | 2+ 因子 IC < 0.02 | 回 v2.md Part 2.1 重思考 Hypothesis |
| 2 | 響應曲面 R² < 0.5 | 模型不穩定，砍變數 |
| 3 | 三模型都輸對照組 | 用 naive T+1 開盤 |
| 4 | 任一 regime 崩盤 | 加 regime filter |
| 5 | PBO ≥ 50% | 過擬合，回階段 2 砍參數 |

**鐵律**：早期失敗 = 早期省時間，不要硬拗。

## 5.3 時程估計

| 工作模式 | 預估完成 |
| :--- | :--- |
| 全職（40h/週） | 4–5 週 |
| 兼職（10h/週） | 4–5 個月 |
| 假日（5h/週） | 8–10 個月 |

## 5.4 必要工具

```bash
pip install \
    pyDOE2 \           # DOE 設計矩陣生成
    statsmodels \      # ANOVA, regression
    scipy \            # Statistical tests, bootstrap
    scikit-learn \     # Cross-validation
    matplotlib seaborn \  # Visualization
    pandas numpy \     # 基礎
    finmind            # 資料源
```

---

# Part 6：失敗的處理

## 6.1 失敗類型與對策

| 失敗類型 | 症狀 | 對策 |
| :--- | :--- | :--- |
| **方法失敗** | DOE 設計有 bug | 修正、重跑 |
| **統計失敗** | 樣本量不足 / N inadequate | 重跑或承認結論不足 |
| **假設失敗** | 因子 IC 都很差 | 砍策略，回 hypothesis |
| **過擬合失敗** | OOS 遠差於 IS | 簡化，重做 |
| **執行失敗** | Paper trading 與回測差距大 | 校準成本模型 |

## 6.2 何時放棄

連續發生以下 **2 項**以上 → **放棄策略本體**：

- DOE-1 兩個以上因子 IC < 0.02
- DOE-2 沒有顯著主效應
- DOE-9 PBO > 50%
- DOE-7 滑點 0.3% 就崩
- DOE-6 多頭以外全虧

放棄不是失敗，是省下時間做下一個策略。

## 6.3 失敗紀錄

每個失敗的 DOE 必須寫**事後分析報告**：

```markdown
# DOE-X 事後分析

## 結果
- 觀察到的結果：...
- 與 H1 偏離程度：...

## 假設失敗的原因
- 方法問題 / 資料問題 / 假設錯誤？
- 哪些前提沒成立？

## 學到什麼
- 對策略本體的啟示
- 對未來 DOE 的改進

## 後續行動
- 是否進入下一階段？（通常 NO）
- 是否回頭重做？
- 是否終止策略？
```

---

## 變更紀錄

### v1.0 — 2026-05-26
- **初版**：建立 10 個必要 DOE 的完整模板
- 涵蓋因子驗證 → 參數優化 → 規則驗證 → 環境穩健 → 統計檢定
- 加入預註冊紀律、統計工具箱、失敗處理流程
