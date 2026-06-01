# BDD 行為驅動情境 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26

---

## Gherkin 速查

| 關鍵字 | 用途 |
| :--- | :--- |
| `Feature` | 功能（對應 PRD Epic） |
| `Scenario` | 業務場景 |
| `Given` | 初始狀態 |
| `When` | 操作 |
| `Then` | 預期結果 |

---

## Feature 1：ETL 資料抓取

**檔案**：`features/etl.feature`
**對應 PRD**：US-002

```gherkin
Feature: FinMind ETL 資料抓取
  # 對應 backtest_platform/src/backtest_platform/data/finmind_etl.py

  Background:
    Given FinMind API 可正常存取
    And FINMIND_TOKEN 已設定於環境變數

  @happy-path @smoke-test
  Scenario: 拉取台積電 2024 年 11 月資料
    Given 標的 stock_id "2330"
    And 時間區間 "2024-11-01" 至 "2024-11-30"
    When 執行 ETL fetch_bundle
    Then 應取得 daily_bars 共 21 筆
    And 應取得 institutional 資料含 foreign_buy / trust_buy / dealer_buy
    And 應取得 broker_chips 含 day_trade_volume
    And 所有欄位應通過 pydantic schema 驗證

  @happy-path
  Scenario: 寫入 parquet 後可重新讀取
    Given 已執行 fetch_bundle 取得 ETLBundle
    When 呼叫 write_parquet(bundle, "data/parquet")
    Then 應產生 daily_bars__2330.parquet
    And 應產生 institutional__2330.parquet
    And 應產生 broker_chips__2330.parquet
    And pandas.read_parquet 重新讀取後資料一致

  @sad-path
  Scenario: API 失敗時不污染 parquet
    Given FinMind API 回傳 rate_limit_exceeded
    When 執行 fetch_bundle
    Then 應拋出 Exception 而非寫入空 parquet

  @edge-case
  Scenario: 空回應的處理
    Given FinMind API 回傳空 DataFrame
    When 執行 _normalize_daily
    Then 應回傳具備完整 columns 的空 DataFrame
    And 後續 merged() 不應拋出 KeyError
```

---

## Feature 2：四層計分（compute_scores）

**檔案**：`features/scoring.feature`
**對應 PRD**：US-001
**對應 v2.md**：Part 2.3

```gherkin
Feature: 四層計分系統
  # 對應 backtest_platform/src/backtest_platform/strategy/scoring.py

  Background:
    Given 已有 60+ 個交易日的 OHLCV + 法人 + 籌碼資料
    And StrategyConfig 使用預設值

  @happy-path
  Scenario: 突破箱頂時結構分 = 2
    Given 過去 60 日箱頂為 100
    And 今日收盤為 105（高於箱頂）
    When 執行 compute_scores
    Then structure_score 應為 2

  @happy-path
  Scenario: 外資投信同步買時方向分 = 2
    Given foreign_buy > 0
    And trust_buy > 0
    When 執行 compute_scores
    Then direction_score 應為 2

  @happy-path
  Scenario: 籌碼比例超過門檻時 chip_score = 2
    Given chip_total / net_volume = 0.15
    And chip_strong_threshold = 0.10
    When 執行 compute_scores
    Then chip_score 應為 2

  @happy-path
  Scenario: 三陽開泰時動能分 = 2
    Given close >= ma5, ma10, ma20
    And ema5 >= ema10
    And rsi_5, k, dif_sl, osc_d 全部上升
    When 執行 compute_scores
    Then momentum_score 應為 2

  @edge-case
  Scenario Outline: 分數範圍邊界
    When 執行 compute_scores
    Then <factor>_score 應落在 <min> 至 <max> 之間

    Examples:
      | factor    | min | max |
      | structure | 0   | 2   |
      | direction | -1  | 2   |
      | chip      | -1  | 2   |
      | momentum  | -1  | 2   |

  @sad-path
  Scenario: 缺少必要欄位時拋出 ValueError
    Given df 缺少 "foreign_buy" 欄位
    When 執行 compute_scores
    Then 應拋出 ValueError 含 "missing required columns"
```

---

## Feature 3：執行訊號優先序

**檔案**：`features/signals.feature`
**對應 v2.md**：Part 2.4.2

```gherkin
Feature: 執行訊號狀態機與優先序
  # 對應 backtest_platform/src/backtest_platform/strategy/signals.py
  # 優先序：stoploss > exit > takeprofit > reduce > add > buy > hold

  Background:
    Given 已執行 compute_scores 的 DataFrame
    And StrategyConfig 預設值

  @happy-path
  Scenario: 強多首次成立 + 突破箱頂 → 觸發 buy
    Given in_position = 0
    And state_strong_buy = 1
    And structure_score = 2
    And 昨日 total_score < strong_buy_threshold
    And edge_ok = 1
    When 執行 evaluate_bar
    Then 應回傳 "buy"

  @happy-path
  Scenario: 持倉中跌破箱底 → 觸發 stoploss（風控優先）
    Given in_position = 1
    And close < box_lower
    When 執行 evaluate_bar
    Then 應回傳 "stoploss"
    And 即使 takeprofit 條件也成立，仍應回傳 "stoploss"

  @happy-path
  Scenario: 持倉中分數健康 → 續抱
    Given in_position = 1
    And total_score >= 3
    And momentum_score >= 1
    And 無其他高優先訊號觸發
    When 執行 evaluate_bar
    Then 應回傳 "hold"

  @edge-case
  Scenario: 多訊號同時為真，應回傳優先序最高的
    Given in_position = 1
    And stoploss / takeprofit / reduce 條件都成立
    When 執行 evaluate_bar
    Then 應回傳 "stoploss"

  @sad-path
  Scenario: 風控訊號不被成本濾網擋住
    Given in_position = 1
    And close < box_lower（停損條件成立）
    And net_profit_rate < cost_round_rate（賣會虧成本）
    When 執行 evaluate_bar
    Then 仍應回傳 "stoploss"

  @happy-path
  Scenario: 強多但未過 edge 濾網 → 不買
    Given in_position = 0
    And state_strong_buy = 1
    And edge_ok = 0（波動率不足）
    When 執行 evaluate_bar
    Then 應回傳 "none"
```

---

## Feature 4：Universe Filter

**檔案**：`features/universe.feature`
**對應 v2.md**：Part 2.2

```gherkin
Feature: 標的池過濾
  # 對應 backtest_platform/src/backtest_platform/data/universe.py

  @happy-path
  Scenario: 大型股通過所有過濾條件
    Given stock metadata 含：市值 100億、日均量 5000張、上市 5 年、價格 200
    When 執行 apply_filters
    Then 該股應出現在 survivors 中
    And excluded_reason 應為空字串

  @edge-case
  Scenario Outline: 過濾理由優先序（第一個觸發者贏）
    Given stock 同時觸發多個過濾條件 <conditions>
    When 執行 apply_filters
    Then excluded_reason 應為 <first_reason>

    Examples:
      | conditions                                | first_reason       |
      | ETF + market_cap_low                      | etf                |
      | warrant + price_above_cap                 | warrant            |
      | full_delivery + bad_governance            | full_delivery      |

  @sad-path
  Scenario: metadata 缺欄位
    Given metadata 缺少 "industry" 欄位
    When 執行 apply_filters
    Then 應拋出 ValueError 含 "missing columns"
```

---

## Feature 5：端到端 Pipeline

**檔案**：`features/pipeline.feature`
**對應 PRD**：US-001

```gherkin
Feature: 端到端 Pipeline
  # 對應 backtest_platform/src/backtest_platform/pipeline.py

  @happy-path @integration
  Scenario: 對 2330 跑 2 年 pipeline 並產出 calendar
    Given 已設定 FINMIND_TOKEN
    When 執行 CLI: pipeline run --stock-id 2330 --start 2023-01-01 --end 2024-12-31
    Then 應產生 reports/calendar__2330__2023-01-01__2024-12-31.csv
    And 應印出 Signal Calendar last 20 rows
    And 應印出 buy/exit/reduce/add 統計
    And 暖機後的 bars 應達 400+ 筆

  @sad-path
  Scenario: 資料不足時警告但不報錯
    Given 拉取資料 < box_period + 5 筆
    When 執行 run_pipeline
    Then 應 log warning "only X bars after merge"
    And 仍回傳 DataFrame（scores 為 NaN 但不崩潰）
```

---

## 最佳實踐

1. **每個 Scenario 只測一件事**
2. **使用陳述式** — `Then structure_score 應為 2`，非 `Then 系統應計算結構分為 2`
3. **避免實作細節** — `When 執行 compute_scores`，非 `When 呼叫 np.where(...)`
4. **從策略研究者角度寫** — 非技術人員也應能讀懂

---

## BDD 與單元測試的對應

| BDD Scenario | Pytest 對應 |
| :--- | :--- |
| F1 Happy path | `tests/data/test_finmind_etl.py::test_fetch_bundle_happy_path` |
| F2 結構分 = 2 | `tests/strategy/test_scoring.py::test_structure_breakout_scores_two` |
| F3 stoploss 優先 | `tests/strategy/test_signals.py::test_stoploss_overrides_takeprofit` |
| F4 universe 過濾 | `tests/data/test_universe.py` |
| F5 端到端 | `backtest_platform/docs/M1_setup.md` 端到端驗證段落（手動） |

當前 BDD scenarios 為**文檔**形式（給人讀），未自動化執行。若需引入 `behave` / `pytest-bdd` 把 .feature 自動跑起來，列入 M3 待補事項。

---

## 6. 測試金字塔（總覽，詳見 22 號文件）

> **2026-05-31 增補**：本章節為 22 號文件的高層摘要，**完整測試規範詳見 [22_test_strategy.md](./22_test_strategy.md)**。

### 6.1 測試金字塔比例

```
           ┌──────────────────┐
           │   E2E  (10%)     │  pytest + zipline run + docker
           │  ~30 scenarios   │  smoke test per mode
           ├──────────────────┤
           │ Integration (20%)│  pytest + docker-compose
           │  ~80 tests       │  DB / API sandbox / 對拍
           ├──────────────────┤
           │   Unit  (70%)    │  pytest + hypothesis
           │  ~280 tests      │  pure functions / adapters
           └──────────────────┘
```

| 層 | 比例 | 跑時 | 失敗影響 |
| :--- | :---: | :--- | :--- |
| Unit | 70% | < 30s | block PR |
| Integration | 20% | < 5min | block PR |
| E2E | 10% | < 30min | block release |
| 對拍 (Recon) | 跨層 | < 10min | block milestone |
| Performance | 跨層 | < 2h | warn only |

### 6.2 對拍測試矩陣（M2-5 必過）

| ID | 對拍對 | 容忍 | M | 失敗動作 |
| :--- | :--- | :--- | :---: | :--- |
| R-001 | Zipline vs vectorbt | < 0.5% | M3 | 找撮合假設差異 |
| R-002 | VectorBtEngine vs M1 pipeline.py | < 0.1% | M2 | regression test 必過 |
| R-003 | FinLab vs FinMind OHLCV | < 1% | M2 | log + 採 FinLab |
| R-004 | 自寫 PBO vs pypbo | < 1e-4 | M3 | 數學 bug |
| R-005 | EventDriven vs Vectorized paper | < 0.5% | M4 | 模擬精度問題 |

### 6.3 BDD 與測試金字塔的關係

BDD scenarios（本文 §1-5）對應 unit + integration + E2E 三層的 **行為敘述**；22 號文件補完 **比例、工具、執行策略、CI/CD 整合**。兩者互補：
- 寫 BDD scenario → 產出 pytest test 案例
- 22 號 §1 金字塔比例 → 約束各層 test 數量配比
- 22 號 §3 對拍矩陣 → 跨引擎一致性閘門
