# 業界 Reference Architecture 與指標規格 — 7 層 × 30+ 指標

> **版本：** v1.0 | **更新：** 2026-05-31 | **狀態：** Single Source of Truth for M2–M5 metrics 實作
> **適用：** `validation/metrics.py`、`validation/pbo.py`、`validation/dsr.py`、`validation/wfa.py`、`engines/vectorbt_adapter.py`
> **對應 plan：** [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) §3、§9
> **對應 ADR：** ADR-005（雙引擎）、ADR-009（自寫 PBO/DSR）

---

## 1. 目的

### 1.1 為什麼要有這份規格

| 痛點 | 後果 | 本文件對策 |
| :--- | :--- | :--- |
| 「想到才加」指標 | M3 寫完 Sharpe，M4 才發現缺 PSR；驗收前才補；指標 enum 沒一次定義 | 一次列出 30+ 指標 enum，function stub 預先建立 |
| 缺業界 reference | 自寫 PBO 公式錯誤無法察覺；reviewer 沒 baseline 對比 | 每個指標附論文引用 + 公式 + 對拍對象 |
| 7 層架構模糊 | Risk gate 放哪？Attribution 算什麼？實作時才爭論 | 每層職責、典型實作、本專案對應一次寫清楚 |
| 業界 OSS 哪些可抄 | 重造輪子或漏抄精華 | 對照表列出 LEAN/Nautilus/Zipline/Qlib/vectorbt 各自完整度 |

### 1.2 使用方式

- **M2 啟動時**：`validation/metrics.py` 一次性建立 30+ enum 與 function stub（即使本 sprint 不實作）
- **M3 寫 PBO/DSR**：對照本文 §4 D 類 + 論文表格驗證
- **新指標需求**：先檢查是否已在本文 §4，未在則更新本文 + ADR
- **架構決策**：對照本文 §3 7 層職責，避免 component 放錯層

---

## 2. 業界 Reference 來源

| Reference | 類型 | 用途 |
| :--- | :--- | :--- |
| [QuantConnect LEAN](https://github.com/QuantConnect/Lean) | 開源（C#/Python，Apache-2.0） | 7 層架構最完整實作參考 |
| [Nautilus Trader](https://github.com/nautechsystems/nautilus_trader) | 開源（Rust/Python，LGPL-3.0） | 機構級事件驅動 + OMS 設計 |
| [Zipline-reloaded](https://github.com/stefan-jansen/zipline-reloaded) | 開源（Python，Apache-2.0） | **本專案主骨架** (M2，ADR-013) |
| ~~[TQuant-Lab](https://github.com/tejtw/TQuant-Lab)~~ | ~~開源（Python，MIT）~~ | ~~Zipline 台股 fork~~ — 原規劃採用，ADR-013 棄用（zipline-tej import 強綁 TEJ key）|
| **López de Prado**, *Advances in Financial Machine Learning* (2018) | 書 | D 類統計穩健性（PBO/DSR/CPCV）原始公式 |
| **López de Prado**, *Machine Learning for Asset Managers* (2020) | 書 | Strategy Risk、Min Track Record Length |
| **Bailey & López de Prado** (2014), *The Deflated Sharpe Ratio* | 論文 | DSR 公式與 reference table 5.2 |
| **CFA Institute**, GIPS Standards | 標準 | 報酬計算規範（TWR/MWR） |
| **Grinold & Kahn**, *Active Portfolio Management* (2000) | 書 | F 類 Factor 評估（IC/ICIR/Fundamental Law） |
| **Bloomberg/Barra** Risk Model | 業界標準 | Factor 風險分解、Attribution |
| [vectorbt](https://github.com/polakowo/vectorbt) | 開源（Python，Apache + Commons Clause） | 向量化 portfolio simulation 標竿 |
| [Microsoft Qlib](https://github.com/microsoft/qlib) | 開源（Python，MIT） | ML-Quant 全棧 + Factor research 流程 |

---

## 3. 7 層架構詳述

### L1 — Data Layer

| 項目 | 內容 |
| :--- | :--- |
| **定義** | 所有原始資料的擷取、清洗、儲存、版本化 |
| **職責** | Market data (OHLCV)、Fundamental (財報、股利)、Reference (universe、產業分類、交易日曆)、Alternative (法人籌碼、券商分點) |
| **典型實作** | Bundle pattern (Zipline)、Adapter pattern (LEAN `IDataReader`) |
| **本專案對應** | `adapters/data_bundle/finlab_bundle.py` (主) + `adapters/data_bundle/finmind_bundle.py` (fallback) + TimescaleDB cache (`data/db_writer.py`) |
| **業界參考** | Zipline `bundles/core.py`、LEAN `Engine/DataFeeds/`、Qlib `qlib/data/` |

### L2 — Research / Signal

| 項目 | 內容 |
| :--- | :--- |
| **定義** | Alpha factor 計算、IC 分析、signal generation |
| **職責** | 從 L1 資料產出可交易訊號；純函式無 IO |
| **典型實作** | Pipeline DSL (Zipline `Pipeline`)、Expression engine (Qlib `qlib.contrib.alpha`) |
| **本專案對應** | M1 既有 `strategy/scoring.py` + `strategy/signals.py` + `strategy/indicators.py`（純函式設計，見 ADR-003） |
| **業界參考** | Zipline Pipeline、Qlib Alpha158/Alpha360、LEAN `Indicators/` |

### L3 — Backtest Engine

| 項目 | 內容 |
| :--- | :--- |
| **定義** | 將訊號 + 撮合規則 + 滑點 + 手續費組合，產出 trade log + equity curve |
| **職責** | 兩種範式：(a) Event-driven（精確、單次） (b) Vectorized（快速、grid） |
| **典型實作** | Event-driven: Zipline / LEAN / Nautilus / rqalpha；Vectorized: vectorbt / bt |
| **本專案對應** | 主：zipline-reloaded 3.1.1 (event-driven，ADR-013 + ADR-014)；副：`engines/vectorbt_adapter.py` (vectorized for grid/WFA — 2026-06-01 隨 ADR-014 升級恢復可用) |
| **業界參考** | Zipline `algorithm.py`、vectorbt `Portfolio.from_signals`、LEAN `Engine/Algorithm/` |

### L4 — Portfolio Construction

| 項目 | 內容 |
| :--- | :--- |
| **定義** | 從 signal 決定 position size、權重、再平衡時機 |
| **職責** | Position sizing（固定 R / Kelly / Vol target）、權重分配、再平衡頻率、現金管理 |
| **典型實作** | LEAN `Portfolio/`、Zipline `pipeline/factors/`、Riskfolio-Lib |
| **本專案對應** | Zipline `Pipeline` + 自寫 allocator（M3）；對應 v2.md Heat 6% / R 0.5% 規則 |
| **業界參考** | LEAN `Portfolio/MeanVarianceOptimizationPortfolioConstructionModel.cs`、PyPortfolioOpt |

### L5 — Risk Management

| 項目 | 內容 |
| :--- | :--- |
| **定義** | Ex-ante 限額、ex-post 監控、熔斷機制 |
| **職責** | 部位限額、產業集中度、leverage cap、VaR/CVaR、drawdown 熔斷 |
| **典型實作** | LEAN `Risk/`、Nautilus `RiskEngine`、Zipline `set_max_position_size` |
| **本專案對應** | 自寫 risk gates + Zipline order hook（M4）；Discord Critical 告警（M5，見 ADR-010） |
| **業界參考** | LEAN `Risk/MaximumDrawdownPercentPortfolio.cs`、Nautilus `model/risk/` |

### L6 — Execution / OMS

| 項目 | 內容 |
| :--- | :--- |
| **定義** | Order Management System：訂單路由、撮合模擬、實盤接口、滑點建模 |
| **職責** | OrderType (Market/Limit/Stop)、Order lifecycle、Fill simulation、Live broker adapter |
| **典型實作** | Zipline `Blotter` + `Broker` 介面、LEAN `Brokerages/`、Nautilus `ExecutionEngine` |
| **本專案對應** | Backtest: Zipline `SimulationBlotter`；Paper: `adapters/brokers/paper_broker.py`；Live: `adapters/brokers/shioaji_broker.py` |
| **業界參考** | Zipline `finance/blotter/`、LEAN `Brokerages/InteractiveBrokers/` |

### L7 — Monitor & Attribution

| 項目 | 內容 |
| :--- | :--- |
| **定義** | 即時績效監控、儀表板、告警、績效歸因 |
| **職責** | 策略績效 dashboard、系統健康 dashboard、主動告警、Brinson/Fama-French attribution |
| **典型實作** | quantstats（報表）、Grafana（時序儀表板）、pyfolio（歸因）、Discord/Slack bot（告警） |
| **本專案對應** | Streamlit（策略 5 面板）+ Grafana（系統 4 面板）+ Discord Bot（3 級告警，見 ADR-010）— 詳見 plan §4 |
| **業界參考** | quantstats、Grafana TimescaleDB datasource、Prometheus client |

---

## 4. 30+ 指標 Taxonomy

> 全部寫進 `validation/metrics.py`：先 enum，後 function stub，M2–M5 漸次填滿。
> **單位約定**：年化基期 252（台股交易日）；無風險利率採 1Y 台債殖利率。

### 4.1 A 類 — 報酬類

| 指標 | 公式 / 定義 | 引用 | 實作位置 | M |
| :--- | :--- | :--- | :--- | :---: |
| Total Return | `(equity_end / equity_start) - 1` | CFA GIPS | `metrics.total_return()` | M2 |
| CAGR | `(1 + total_return)^(252/N) - 1` | CFA GIPS | `metrics.cagr()` | M2 |
| Annualized Return | `mean(daily_returns) * 252` | CFA GIPS | `metrics.annualized_return()` | M2 |
| Excess Return | `return - benchmark_return` | CFA GIPS | `metrics.excess_return()` | M3 |
| Alpha (Jensen) | `R_p - [R_f + β(R_m - R_f)]` | Jensen (1968) | `metrics.jensen_alpha()` | M3 |

### 4.2 B 類 — 風險類

| 指標 | 公式 / 定義 | 引用 | 實作位置 | M |
| :--- | :--- | :--- | :--- | :---: |
| Volatility (σ) | `std(daily_returns) * sqrt(252)` | 教科書 | `metrics.volatility()` | M2 |
| Max Drawdown (MDD) | `max((peak - trough) / peak)` | quantstats | `metrics.max_drawdown()` | M2 |
| MDD Duration | 從 peak 到 recovery 的最長日數 | quantstats | `metrics.mdd_duration()` | M3 |
| Ulcer Index | `sqrt(mean(drawdown_pct^2))` | Martin (1989) | `metrics.ulcer_index()` | M3 |
| VaR (95%) | `np.percentile(returns, 5)` | Jorion (2006) | `metrics.var()` | M3 |
| CVaR (95%) / Expected Shortfall | `mean(returns[returns <= VaR])` | Rockafellar & Uryasev | `metrics.cvar()` | M3 |
| Downside Deviation | `sqrt(mean(min(r - MAR, 0)^2))`（全長分母，與 Sortino 配對標準式；MAR=0 預設） | Sortino & Price | `metrics.downside_deviation()` | M3 |

### 4.3 C 類 — 風險調整

| 指標 | 公式 / 定義 | 引用 | 實作位置 | M |
| :--- | :--- | :--- | :--- | :---: |
| Sharpe Ratio | `(R - R_f) / σ * sqrt(252)` | Sharpe (1966) | `metrics.sharpe()` | M2 |
| Sortino Ratio | `(R - R_f) / downside_dev * sqrt(252)` | Sortino & Price (1994) | `metrics.sortino()` | M2 |
| Calmar Ratio | `CAGR / |MDD|` | Young (1991) | `metrics.calmar()` | M2 |
| Omega Ratio | `sum(returns > τ) / sum(τ - returns)` | Keating & Shadwick (2002) | `metrics.omega()` | M3 |
| Information Ratio | `(R - R_b) / tracking_error * sqrt(252)` | Grinold & Kahn | `metrics.information_ratio()` | M3 |
| Treynor Ratio | `(R - R_f) / β` | Treynor (1965) | `metrics.treynor()` | M3 |
| MAR Ratio | `CAGR / |MDD|`（Calmar 變體，期間設定不同） | Managed Account Reports | `metrics.mar()` | M3 |
| **Probabilistic Sharpe Ratio (PSR)** | `Φ((SR - SR*) * sqrt(N-1) / sqrt(1 - γ3*SR + (γ4-1)/4 * SR^2))` | Bailey & López de Prado (2012) | `metrics.psr()` | M3 |

### 4.4 D 類 — 統計穩健性（López de Prado）

> **這類自寫實作，避 pypbo (AGPL) 與 mlfinlab（商業）。** 對拍：Bailey 論文 reference table。

| 指標 | 公式 / 定義 | 引用 | 實作位置 | M |
| :--- | :--- | :--- | :--- | :---: |
| **PBO** (Probability of Backtest Overfitting) | 用 CSCV (Combinatorially-Symmetric Cross-Validation) 切 IS/OOS，計算 IS-top 在 OOS 落後中位數的機率 | Bailey, Borwein, López de Prado, Zhu (2017), *The probability of backtest overfitting*, J. Comp. Finance | `validation/pbo.py` | **M3** |
| **DSR** (Deflated Sharpe Ratio) | `PSR(SR*)`，其中 `SR*` 為考量多重檢定後 deflate 的閾值 | Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, J. Portfolio Management | `validation/dsr.py` | **M3** |
| **CPCV** (Combinatorial Purged Cross-Validation) | k-fold + purge + embargo，避免 leakage | López de Prado (2018), AFML Ch. 12 | `validation/cpcv.py`（M3 延伸） | M3 |
| Strategy Risk | 從 trade win rate 估失敗機率上界 | López de Prado, *MLAM* (2020) Ch. 5 | `metrics.strategy_risk()` | M4 |
| Min Track Record Length (MinTRL) | `1 + (1 - γ3*SR + (γ4-1)/4 * SR^2) * (z_α / (SR - SR*))^2` | Bailey & López de Prado (2012) | `metrics.mintrl()` | M4 |

### 4.5 E 類 — 交易品質

| 指標 | 公式 / 定義 | 引用 | 實作位置 | M |
| :--- | :--- | :--- | :--- | :---: |
| Win Rate | `wins / total_trades` | 標準 | `metrics.win_rate()` | M2 |
| Profit Factor | `sum(profits) / abs(sum(losses))` | 標準 | `metrics.profit_factor()` | M2 |
| Avg Win / Avg Loss | `mean(profits) / abs(mean(losses))` | 標準 | `metrics.avg_win_loss_ratio()` | M2 |
| Expectancy | `(win_rate * avg_win) - (loss_rate * avg_loss)` | Van Tharp | `metrics.expectancy()` | M3 |
| Kelly % | `(p * b - q) / b`（p=win rate, b=odds, q=1-p） | Kelly (1956) | `metrics.kelly_fraction()` | M3 |
| Turnover | `sum(|trade_value|) / avg_equity / years` | 標準 | `metrics.turnover()` | M3 |
| Capacity | 假設 X% ADV 參與率下，策略最大可管理 AUM | LEAN / Investment Strategy Capacity | `metrics.capacity()` | M4 |
| Slippage Realized vs Modeled | 實際成交價 - 模型假設價（per share） | 標準 | `metrics.slippage_realized()` | M4 |

### 4.6 F 類 — Factor / Alpha 評估

| 指標 | 公式 / 定義 | 引用 | 實作位置 | M |
| :--- | :--- | :--- | :--- | :---: |
| IC (Information Coefficient) | `corr(factor_t, return_{t+1})` (Pearson) | Grinold & Kahn (2000) | `metrics.ic()` | M3 |
| Rank IC | `spearman_corr(factor_t, return_{t+1})` | Grinold & Kahn | `metrics.rank_ic()` | M3 |
| ICIR | `mean(IC) / std(IC) * sqrt(N)` | Grinold & Kahn (Fundamental Law) | `metrics.icir()` | M3 |
| Quantile Returns (Q1–Q5) | 按因子值分 5 組各自的平均報酬 | Alphalens / Qlib | `metrics.quantile_returns()` | M3 |
| Factor Decay | IC 對 horizon 衰減曲線 | López de Prado, AFML | `metrics.factor_decay()` | M4 |
| Half-life | IC 衰減到一半所需期數 | López de Prado | `metrics.factor_halflife()` | M4 |

### 4.7 指標 enum 寫入規範

```python
# validation/metrics.py 骨架（M2 第 1 週建立）
from enum import Enum

class MetricCategory(str, Enum):
    RETURN = "A_return"
    RISK = "B_risk"
    RISK_ADJUSTED = "C_risk_adjusted"
    STATISTICAL_ROBUSTNESS = "D_statistical"
    TRADE_QUALITY = "E_trade_quality"
    FACTOR = "F_factor"

class MetricID(str, Enum):
    # A 類
    TOTAL_RETURN = "total_return"
    CAGR = "cagr"
    # ... (30+ 全列出)
    PBO = "pbo"
    DSR = "dsr"
    # ...

METRIC_REGISTRY: dict[MetricID, MetricSpec] = { ... }
```

**規範**：
- 每個 MetricID 對應 function stub，未實作時 `raise NotImplementedError("M<x> 才實作")`
- 每個 function 強制標 `__doc__` 含公式 + 引用
- 單元測試對拍：所有 D 類必須對 Bailey 論文表 5.2 數值匹配（容許 1e-4）

---

## 5. Backtest 標準 Pipeline

> 業界共識的 9 階段。每階段在本專案的對應位置與業界對標：

| # | 階段 | 職責 | 本專案位置 | 業界對標 |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Data Prep** | ETL、清洗、對齊、缺值處理、survivorship bias 修正 | `adapters/data_bundle/finlab_bundle.py` | Zipline `bundles/quandl.py` |
| 2 | **Signal Generation** | 因子計算、訊號規則 | `strategies/four_layer_resonance/signals.py` | Zipline `Pipeline` |
| 3 | **Position Sizing** | R 計算、Heat 限額 | Zipline algorithm `before_trading_start` | LEAN `PositionSizing` |
| 4 | **Order Generation** | 訊號 → Order 物件 | Zipline `order_target_percent` | LEAN `IAlgorithm.OnData` |
| 5 | **Execution Simulation** | 撮合、滑點、手續費 | Zipline `SimulationBlotter` | Nautilus `SimulatedExchange` |
| 6 | **Performance Attribution** | 報酬拆解 | `validation/reports.py` (quantstats wrapper) | pyfolio |
| 7 | **Statistical Validation** | PBO/DSR/CPCV | `validation/pbo.py` + `dsr.py` + `cpcv.py` | López de Prado AFML 範例 |
| 8 | **Walk-Forward Analysis** | 滾動 IS/OOS | `validation/wfa.py` | vectorbt `Splitter` |
| 9 | **Final OOS Test** | 凍結期間單次驗證 | `engines/vectorbt_adapter.py` final run | López de Prado AFML §11 |

---

## 6. 業界 OSS Reference 對照表

| 框架 | L1 Data | L2 Signal | L3 BT Event | L3 BT Vector | L4 Portfolio | L5 Risk | L6 OMS | L7 Monitor | 對標部分 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **zipline-reloaded** ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | — | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | **本專案主骨架（L1, L2, L3-event；L6 自寫 broker adapter，ADR-013）** |
| **vectorbt** | ⭐⭐ | ⭐⭐⭐⭐ | — | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | — | ⭐⭐⭐ | 本專案副引擎（L3-vector for grid/WFA）— ADR-013 期暫停，ADR-014 升級後 vectorbt 1.0+ 可同棧 |
| **LEAN** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | L4/L5 設計思想參考 |
| **Nautilus Trader** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | L5/L6 機構級設計 |
| ~~TQuant-Lab~~ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | — | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ (含 Shioaji 範例) | ⭐⭐ | 原規劃主骨架（ADR-005，已 superseded by ADR-013：zipline-tej 強綁 TEJ key） |
| **Microsoft Qlib** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ (Alpha158/360) | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | — | ⭐⭐⭐ | L2 Alpha factor 設計 |
| **quantstats** | — | — | — | — | — | — | — | ⭐⭐⭐⭐⭐ | L7 報表 |
| **pyfolio-reloaded** | — | — | — | — | — | — | — | ⭐⭐⭐⭐ | L7 歸因 |
| **pypbo** | — | — | — | — | — | — | — | ⭐⭐⭐ (D 類) | D 類對拍（不依賴，AGPL）|
| **FinMind** | ⭐⭐⭐⭐ (台股) | — | — | — | — | — | — | — | L1 fallback 資料源 |
| **Shioaji** | ⭐⭐⭐ (台股報價) | — | — | — | — | — | ⭐⭐⭐⭐⭐ (台股實盤) | — | L6 實盤接口 |

---

## 7. 本專案規格 Ceiling

> **7 層 × 30 指標 × 9 階段 Pipeline = 完整 ceiling。M2–M5 只是填空進度。**

### 7.1 完整度 Roadmap

| 層 / 類 | M1 ✅ | M2 | M3 | M4 | M5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| L1 Data | ⭐⭐ FinMind | ⭐⭐⭐⭐ +FinLab | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ +live feed | ⭐⭐⭐⭐⭐ |
| L2 Signal | ⭐⭐⭐⭐ 四層計分 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ +IC analysis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| L3 Backtest | — | ⭐⭐⭐ Zipline | ⭐⭐⭐⭐ +vectorbt | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| L4 Portfolio | ⭐ R/Heat 規則 | ⭐⭐ | ⭐⭐⭐⭐ +allocator | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| L5 Risk | — | — | — | ⭐⭐⭐ +risk gates | ⭐⭐⭐⭐⭐ +熔斷 |
| L6 OMS | — | ⭐⭐ Sim | ⭐⭐ | ⭐⭐⭐⭐ +Paper | ⭐⭐⭐⭐⭐ +Shioaji |
| L7 Monitor | — | — | ⭐⭐⭐ Streamlit A+B+C | ⭐⭐⭐⭐⭐ +Grafana+TG | ⭐⭐⭐⭐⭐ +D+E |
| A 報酬 | — | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| B 風險 | — | ⭐⭐⭐ MDD/σ | ⭐⭐⭐⭐⭐ +VaR/CVaR | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| C 風險調整 | — | ⭐⭐⭐ Sharpe/Sortino/Calmar | ⭐⭐⭐⭐⭐ +PSR/IR/Omega | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| D 統計穩健 | — | — | ⭐⭐⭐⭐⭐ PBO/DSR/CPCV | ⭐⭐⭐⭐⭐ +Strategy Risk | ⭐⭐⭐⭐⭐ |
| E 交易品質 | — | ⭐⭐⭐ WR/PF | ⭐⭐⭐⭐ +Expectancy/Kelly | ⭐⭐⭐⭐⭐ +Capacity | ⭐⭐⭐⭐⭐ |
| F Factor | — | — | ⭐⭐⭐⭐ IC/RankIC/ICIR | ⭐⭐⭐⭐⭐ +Decay/Halflife | ⭐⭐⭐⭐⭐ |

### 7.2 反清單（永遠不做）

| ❌ | 為什麼 |
| :--- | :--- |
| 不自寫指標公式而不附論文引用 | review 時無從驗證 |
| 不單獨實作某指標卻不在 `metrics.py` enum | 散落各檔失去 single source |
| 不用 pypbo / mlfinlab 直接 import | AGPL / 商業授權，污染本專案 |
| 不為 GIPS 標準的 MWR (Money-Weighted Return) | 我們是 strategy backtest，TWR 即可 |
| 不實作 Black-Scholes / option Greeks | 純股票策略，不做衍生品 |
| 不接 Bloomberg / Barra 商業 risk model | 個人專案，自寫單因子風控即可 |

---

## 8. 與既有文檔的關係

| 文檔 | 關係 |
| :--- | :--- |
| [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) §3 | 本文件是其詳細展開 |
| [05_architecture_and_design_document.md](./05_architecture_and_design_document.md) §1.4 | 技術選型對標本文 §6 OSS 對照 |
| [05_architecture_and_design_document.md](./05_architecture_and_design_document.md) §3.3 元件職責 | 對應本文 §3 7 層職責 |
| [07_module_specification_and_tests.md](./07_module_specification_and_tests.md) | `validation/metrics.py` 規格應引用本文 §4 |
| [adrs/ADR-009](./adrs/) (待新增) | 自寫 PBO/DSR 的決策，引用本文 §4 D 類 |
| [research_open_source_backtest_platforms.md](./research_open_source_backtest_platforms.md) | 本文 §6 的調研基礎 |

---

## 變更紀錄

| 版本 | 日期 | 變更 |
| :--- | :--- | :--- |
| v1.0 | 2026-05-31 | 初版（7 層 × 30+ 指標 × 9 階段 Pipeline 一次定義到位）|
