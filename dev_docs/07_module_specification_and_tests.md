# 模組規格與測試案例 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26 | **狀態：** M1 模組已完成

**對應架構文件**：[05_architecture_and_design_document.md](./05_architecture_and_design_document.md)
**對應 BDD**：[03_behavior_driven_development_guide.md](./03_behavior_driven_development_guide.md)

---

## 模組一：`config.strategy_config.StrategyConfig`

### 規格：建構與驗證

**描述**：13 個策略參數的 Pydantic frozen model，加 3 個交叉驗證規則與 3 個衍生 cost rate property。

**契約式設計 (DbC)**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. 所有欄位符合 Field 範圍（如 `box_period ∈ [10, 250]`）<br>2. `warning_threshold < strong_buy_threshold`<br>3. `add_score_threshold >= strong_buy_threshold`<br>4. 無未知欄位（`extra="forbid"`） |
| **後置條件** | 1. instance frozen，不可修改<br>2. `cost_buy_rate / cost_sell_rate / cost_round_rate` property 可呼叫且 > 0 |
| **不變性** | 1. instance hash 一致（同參數 hash 相同）<br>2. 衍生 cost 隨 fee/discount/slip/tax 變動 |

### 測試案例

#### TC-001：預設值符合 v2.md 2.7.1
- **Arrange**：無
- **Act**：`config = StrategyConfig()`
- **Assert**：`config.box_period == 60`、`config.strong_buy_threshold == 5` 等 13 個欄位

#### TC-002：違反交叉驗證拋 ValidationError
- **Arrange**：`warning_threshold=5, strong_buy_threshold=3`
- **Act**：`StrategyConfig(warning_threshold=5, strong_buy_threshold=3)`
- **Assert**：拋 `ValidationError` 含 "warning_threshold must be < strong_buy_threshold"

#### TC-003：frozen 不可修改
- **Arrange**：`config = StrategyConfig()`
- **Act**：`config.box_period = 90`
- **Assert**：拋 `ValidationError`（frozen）

#### TC-004：衍生 cost 計算正確
- **Arrange**：預設 config
- **Act**：`config.cost_round_rate`
- **Assert**：≈ 0.0067 (`0.001425*0.6 + 0.001 + 0.001425*0.6 + 0.003 + 0.001`)

---

## 模組二：`data.finmind_etl.fetch_bundle`

### 規格

**描述**：拉一檔股票的 OHLCV + 法人 + 當沖三表，normalize 後組成 ETLBundle。

**契約式設計 (DbC)**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. `stock_id` 非空字串<br>2. `start <= end`<br>3. `loader` 為 None 時環境有 FinMind 套件可載入 |
| **後置條件** | 1. 回傳 `ETLBundle` 含三個 DataFrame（即使空也有 columns）<br>2. 三個 DataFrame 的 `stock_id` 都等於輸入 `stock_id`<br>3. `apply_adjustment=True` 時 daily 含 `adj_factor` 欄位 |
| **不變性** | 1. 同樣 input 同樣 output（loader mock 時）<br>2. rate_limit_seconds 不會被忽略（避免 FinMind 封鎖） |

### 測試案例

#### TC-001：正常路徑（mock loader）
- **Arrange**：mock loader 回三表 fixture
- **Act**：`fetch_bundle("2330", date(2024,1,1), date(2024,1,31), loader=mock_loader)`
- **Assert**：
  - `bundle.daily_bars["stock_id"].unique() == ["2330"]`
  - `len(bundle.daily_bars) == 21`
  - 三表的 columns 符合 schema

#### TC-002：空回應處理
- **Arrange**：mock loader 回空 DataFrame
- **Act**：`fetch_bundle(...)`
- **Assert**：bundle 三表都是 empty 但有正確 columns，不拋例外

#### TC-003：FinMind exception 直接拋出
- **Arrange**：mock loader 拋 `Exception("rate_limit")`
- **Act**：`fetch_bundle(...)`
- **Assert**：例外被往上拋（不應靜默吞掉）

#### TC-004：apply_adjustment=False 時 adj_factor 全 1.0
- **Arrange**：mock loader 三表，dividend 表非空
- **Act**：`fetch_bundle(..., apply_adjustment=False)`
- **Assert**：`bundle.daily_bars["adj_factor"].unique() == [1.0]`

---

## 模組三：`data.adjustment.compute_adj_factor`

### 規格

**描述**：從 FinMind dividend 資料反推前復權因子 series。

**契約式設計**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. `daily` 已按 `trade_date` 升序<br>2. `daily` 含 `trade_date` 與 `close` 欄位 |
| **後置條件** | 1. 回傳 Series 長度 == len(daily)<br>2. 最後一個值 == 1.0<br>3. 較早日期的 factor <= 較晚日期的 factor |
| **不變性** | 1. dividend 為空時所有 factor == 1.0<br>2. factor > 0（除權息不會導致負價） |

### 測試案例

#### TC-001：無除權息資料
- **Arrange**：daily 100 列 + dividends 空表
- **Act**：`compute_adj_factor(daily, empty_div)`
- **Assert**：所有 factor == 1.0

#### TC-002：單次現金股利
- **Arrange**：daily 含 2024-07-15 ex-div、cash_div = 10、前一日 close = 100
- **Act**：`compute_adj_factor(daily, div)`
- **Assert**：2024-07-15 前的 factor == 0.9 (=(100-10)/100)；當天及之後 == 1.0

#### TC-003：壞 ratio 跳過 + log warning
- **Arrange**：cash_div > pre_close（不可能但測 robustness）
- **Act**：`compute_adj_factor(daily, div)`
- **Assert**：壞事件跳過，log 出現 "bad ratio"，其他事件正常

---

## 模組四：`data.db_writer.upsert_bundle`

### 規格

**描述**：將 ETLBundle 三表 upsert 進 TimescaleDB，重跑結果一致（idempotent）。

**契約式設計**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. TimescaleDB 已建表 (init.sql 跑過)<br>2. bundle 三表的 columns 符合 schema |
| **後置條件** | 1. 回傳 dict 含 `{"daily_bars": n1, "institutional_flows": n2, "broker_chips": n3}`<br>2. 同 bundle 重跑後 DB 狀態一致（rows 不重複） |
| **不變性** | 1. ON CONFLICT (stock_id, trade_date) DO UPDATE 確保 idempotent<br>2. 任一表 fail → rollback 全部（事務） |

### 測試案例

#### TC-001：空 bundle 不寫 DB
- **Arrange**：empty_etl_bundle fixture
- **Act**：`upsert_bundle(bundle)`（mock conn）
- **Assert**：cursor.execute_values 未被呼叫

#### TC-002：缺欄位拋 ValueError
- **Arrange**：daily_bars 缺 `adj_factor`
- **Act**：`upsert_bundle(bundle)`
- **Assert**：`ValueError` 含 "missing columns: ['adj_factor']"

#### TC-003 (integration, @integration)：實際 DB 重跑
- **Arrange**：跑 docker-compose up + 跑兩次 upsert
- **Act**：兩次都用同 bundle
- **Assert**：DB rows 不重複，最終值等於 bundle 內容

---

## 模組五：`data.universe.apply_filters`

### 規格

**描述**：對 metadata DataFrame 套用 v2.md 2.2 過濾規則，回傳含 excluded_reason 的全表。

**契約式設計**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. metadata 含 `UNIVERSE_METADATA_COLUMNS` 全 16 欄 |
| **後置條件** | 1. 回傳 DataFrame 長度 == 輸入<br>2. 新增 `excluded_reason` 欄位（"" = 通過）<br>3. 第一個觸發的 reason 留下（不會被後續覆蓋） |
| **不變性** | 1. 輸入 metadata 不被修改（copy）<br>2. 通過所有條件的 row：excluded_reason == "" |

### 測試案例

#### TC-001：大型股全通過
- **Arrange**：metadata 含 1 檔市值 100 億、量 5000 張、上市 5 年的股票
- **Act**：`apply_filters(metadata)`
- **Assert**：`excluded_reason == ""`

#### TC-002：ETF 被排除
- **Arrange**：`is_etf=True` 的 row
- **Act**：`apply_filters(metadata)`
- **Assert**：`excluded_reason == "etf"`

#### TC-003：第一個 reason 優先
- **Arrange**：同時 `is_etf=True` + `market_cap < 50 億`
- **Act**：`apply_filters(metadata)`
- **Assert**：`excluded_reason == "etf"`（ETF 先於 market_cap_low 檢查）

#### TC-004：缺欄位拋 ValueError
- **Arrange**：metadata 缺 `industry`
- **Act**：`apply_filters(metadata)`
- **Assert**：`ValueError` 含 "missing columns"

---

## 模組六：`strategy.indicators`

### 規格：`stochastic_kd / macd_weighted / rsi / rolling_swing_high / rolling_swing_low`

**描述**：技術指標純函式，對齊 XQ XScript 語意。

**契約式設計**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. 輸入為 pandas Series，index 已 align |
| **後置條件** | 1. 輸出 Series 長度 == 輸入<br>2. 暖機期回 NaN，不是 0<br>3. `rolling_swing_*` 已 shift(1) 確保 breakout 可比 |
| **不變性** | 1. 函式 pure，無副作用<br>2. 同樣 input 同樣 output |

### 測試案例

#### TC-001：rsi 飆漲時應接近 100
- **Arrange**：close 連續上漲 14 天
- **Act**：`rsi(close, 14).iloc[-1]`
- **Assert**：> 80

#### TC-002：rolling_swing_high 已 shift(1)
- **Arrange**：series = [1,2,3,4,5]
- **Act**：`rolling_swing_high(series, 3).iloc[-1]`
- **Assert**：== 4 (NOT 5; 5 是當前 bar，不應在 window 內)

#### TC-003：stochastic 暖機期 NaN
- **Arrange**：3 列資料、n=5
- **Act**：`stochastic_kd(high, low, close, 5, 3, 3)`
- **Assert**：rsv 全部 NaN

---

## 模組七：`strategy.scoring.compute_scores`

### 規格

**描述**：給含 14 欄位的 DataFrame，加上四層計分 + total_score。

**契約式設計**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. df 含 `REQUIRED_COLUMNS` (14 欄)<br>2. df 按 date 升序、無重複 |
| **後置條件** | 1. df 新增 score 欄位（structure / direction / chip / momentum / total）<br>2. score 落在 v2.md 2.3 範圍內<br>3. 暖機期（前 box_period 列）score 可能為 NaN |
| **不變性** | 1. 輸入 df 不被修改（copy）<br>2. 同 config 同 input 同 output |

### 測試案例

#### TC-001：突破箱頂時結構分 = 2
- 已在 `test_scoring.py::test_structure_breakout_scores_two` 實作

#### TC-002：scores 落在範圍內
- 已在 `test_scoring.py::test_scores_within_documented_ranges`

#### TC-003：缺欄位拋 ValueError
- 已在 `test_scoring.py::test_missing_columns_raises`

#### TC-004：L2 方向分各組合
- 已在 `test_scoring.py::test_l2_direction_both_positive_scores_two`

#### TC-005：L3 籌碼超門檻
- 已在 `test_scoring.py::test_l3_chip_ratio_above_threshold_scores_two`

#### TC-006：L4 三陽開泰
- 已在 `test_scoring.py`

#### TC-007：L4 熄火
- 已在 `test_scoring.py`

---

## 模組八：`strategy.signals.evaluate_bar / compute_signals`

### 規格

**描述**：給 scored DataFrame + position state，產出最高優先序的 action。

**契約式設計**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. df 已過 compute_scores（含 score 欄位）<br>2. `EvaluateBar` 包含完整 21 欄位 |
| **後置條件** | 1. action 為 SIGNAL_PRIORITY 中第一個觸發的訊號<br>2. 風控訊號（stoploss/exit）不被 cost filter 阻擋<br>3. 主動訊號（buy/add）必須過 edge_ok / profit_ok |
| **不變性** | 1. 同樣 bar + config + position → 同樣 action<br>2. 優先序固定：stoploss > exit > takeprofit > reduce > add > buy > hold |

### 測試案例

#### TC-001：強多首次成立觸發 buy
- 已在 `test_signals.py`

#### TC-002：跌破箱底觸發 stoploss
- 已在 `test_signals.py`

#### TC-003：多訊號同時為真，回傳優先序最高
- 已在 `test_signals.py`

#### TC-004：風控不被 cost 擋
- 已在 `test_signals.py::test_stoploss_ignores_cost`

#### TC-005：未過 edge_ok 不買
- 已在 `test_signals.py`

---

## 模組九：`pipeline.run_pipeline`

### 規格

**描述**：端到端 ETL → Scoring → Signals 編排，產出可消費 calendar。

**契約式設計**：

| 類型 | 條件 |
| :--- | :--- |
| **前置條件** | 1. FinMind API 可用<br>2. `start <= end` |
| **後置條件** | 1. 回傳 signaled DataFrame 含完整欄位<br>2. 暖機後 ready rows >= 1（如資料足夠） |
| **不變性** | 1. 內部呼叫 compute_scores / compute_signals 純函式 |

### 測試案例（手動 integration）

#### TC-001：2330 跑 2023–2024 兩年
- **Arrange**：FINMIND_TOKEN 已設
- **Act**：`run_pipeline("2330", date(2023,1,1), date(2024,12,31))`
- **Assert**：
  - signaled 長度 >= 480 bars
  - 暖機後 >= 420 bars
  - `action` 含 "buy" / "exit" / "hold" 至少各一次

實際結果（M1 已驗證）：481 bars → 421 ready → 8 buy / 8 exit / 6 reduce / 4 add。

---

## 測試覆蓋現況

| 模組 | 測試檔 | 單元測試數 |
| :--- | :--- | :---: |
| config/strategy_config | tests/test_strategy_config.py | 6 |
| data/finmind_etl | tests/data/test_finmind_etl.py | 5 |
| data/adjustment | tests/data/test_adjustment.py | 6 |
| data/db_writer | tests/data/test_db_writer.py | 3 (含 1 integration) |
| data/universe | tests/data/test_universe.py | 8 |
| strategy/scoring | tests/strategy/test_scoring.py | 8 |
| strategy/signals | tests/strategy/test_signals.py | 12 |
| **總計** | | **48** |

執行：
```bash
PYTHONPATH=src python3 -m pytest -p no:asyncio
```

---

## 未覆蓋（M2 補）

- 端到端 pipeline integration test（目前手動驗證）
- 各 engine wrapper 測試（rqalpha / vectorbt）
- 對齊測試（兩 engine 結果一致性）
- WFA / PBO / MC 演算法測試
