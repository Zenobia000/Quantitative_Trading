# ADR-027: 策略契約 + registry — 平台↔策略接縫，解除 four_layer 引擎特權

> **狀態：** 已接受 | **日期：** 2026-06-16 | **決策者：** Self
> **相關：** [ADR-003](./ADR-003-pure-function-strategy-layer.md)（策略層純函式，本 ADR 沿用不破壞）、[ADR-026](./ADR-026-extract-shared-backtest-mechanics-from-momentum.md)（策略間零互相依賴；本 ADR 接續：策略與**平台**零硬綁）、[ADR-022](./ADR-022-multi-strategy-fleet-operations.md)（刻意不做重型 model registry，本 ADR 的 registry 是輕量 dict 不是版本族譜）、[ADR-007](./ADR-007-dual-engine-zipline-vectorbt.md)（`engines.protocol` 的 `Engine` 工廠是本 ADR registry 的鏡像範式）

---

## 1. 背景與問題

ADR-026 解除了策略**彼此**的耦合（不再反向挖對方私有函式）。但還有一層更上游的設計債：**平台本身硬綁 four_layer_resonance**。

證據（重構前）：

- 平台累積到 4 隻策略，卻是 **3 種不同形狀**：four_layer（`compute_scores + compute_signals/evaluate_bar`，per-stock event-driven）、momentum / inst_flow（`backtest_*(panel, cfg) → Result`，cross-sectional）。
- **只有 four_layer 被引擎掛載**（`engines/zipline_adapter/algorithms/four_layer_resonance.py`），且 `engines/protocol.py` 的 `Engine.run(..., config: StrategyConfig)` 把 four_layer 的 config 型別焊死進通用引擎介面。
- **每隻策略一個 harness**：`research/is_harness.py`（four_layer 硬線）、`research/momentum_harness.py`（momentum 硬線）、inst_flow 連 harness 都還沒有。
- 結果：新增一隻策略要動 **7-12 個檔案**（策略碼 + 自己的 harness + CLI 分支 + 引擎 wrapper + …），four_layer 是「唯一被引擎認得的特權公民」。

### 為什麼這是問題

通用平台的職責是**以同一套基礎建設（metrics / gate / ledger）公平評斷任何策略**。若上層硬綁某一隻策略，這個職責就破功——平台變成「four_layer 的專用跑馬機 + 其他策略的拼裝臨時碼」。這與 four_layer 的訊號邏輯複不複雜無關；是**接縫畫錯位置**。

---

## 2. 關鍵洞察 — 接縫畫在輸出，不是輸入

策略的**輸入**形狀天生不同（four_layer 要 per-stock merged frame 走狀態機；momentum 要 close panel；inst_flow 要 close+flow+volume 三 panel）。硬塞單一輸入簽名會把特殊情況推進契約裡，是過早抽象。

但它們的**輸出是共通的**：metrics / gate / ledger 只需要 `daily_returns` 序列 + trades + 一個 gate-ready metrics dict。所以契約畫在**輸出邊界**：

> 一隻策略 = 「給定 universe + 視窗 + 自己的 frozen config + 共用 per-stock loader，產出 `StrategyRun(metrics, returns, trades)`」的東西。

runner 私下知道自己要什麼資料，從**同一個** loader（`load_merged_parquet` 回傳 daily+法人+籌碼 merged，是每隻策略的超集）切出所需欄位。平台只有一個資料存取接縫，不是一隻策略一個。

---

## 3. 考量的選項

### 選項一：維持現狀（平台硬綁 four_layer）
- **缺點**：新策略持續要動 7-12 檔；four_layer 永遠是特權公民；多策略艦隊（ADR-022）無從落地。**拒絕**。

### 選項二：物件導向 `StrategyClass.on_bar()` 統一介面
- **缺點**：ADR-003 已否決——狀態洩漏、難 vectorize、難測試。重蹈覆轍。**拒絕**。

### 選項三：強制單一輸入簽名（所有策略吃同一個 panel）
- **缺點**：four_layer 的 per-stock 狀態機與 cross-sectional panel 形狀根本不同；硬塞會把 if/else 特殊情況灌進契約。**拒絕**。

### 選項四：輸出契約 `StrategyRunner` Protocol + 輕量 registry ★採納
- **描述**：契約畫在輸出（`StrategyRun`）；runner 是薄 adapter（沿用 ADR-003 純函式，不引入狀態物件）；`register_strategy`/`get_strategy` 為 name→runner 的 dict 工廠，鏡像 `engines.protocol.get_engine`。
- **優點**：消除 four_layer 特權；新策略 = 寫純策略碼 + 註冊 runner（2-3 檔）；上層對契約 dispatch，不認得具體策略名。
- **缺點**：一次性把 four_layer sim helper 下移 + harness 改委派（機械式、有等價測試守門）。

---

## 4. 決策

**採納選項四。**

### 4.1 新增契約 + registry — `strategies/protocol.py`
- `StrategyRun(metrics, returns, trades)`：統一輸出 dataclass（frozen）。
- `StrategyRunner` Protocol：`run(symbols, start, end, config, loader) → StrategyRun`。
- `Loader = Callable[[str], DataFrame]`：共用 per-stock merged frame 存取點。
- `register_strategy(name)` / `get_strategy(name)` / `list_strategies()`：name→runner dict。**刻意不做** 版本族譜 / 血統 / 跨人 leaderboard（ADR-022 已否決重型 registry）。
- config 型別界用 `pydantic.BaseModel`（各策略傳自己的 frozen config），**刻意不引入** `StrategyConfigBase`：那會逼 `config.StrategyConfig` 反向 import `strategies` 造成上行依賴，零行為收益（YAGNI）。

### 4.2 每隻策略自包含 — runner 與策略同住一個資料夾
> **設計修正（使用者回饋）**：runner 最初放在 `research/runners.py`，但這違反「玩家複製一個資料夾即得一隻策略」的模板願景。改為**每隻策略自包含於 `strategies/<name>/`**（config + 純邏輯 + runner）。

- 各策略新增 `strategies/<name>/runner.py`，實作 `StrategyRunner` 並 `@register_strategy`：`four_layer_resonance/runner.py`、`momentum/runner.py`、`inst_flow/runner.py`。
- four_layer 的純 sim helper（`signaled_window`/`daily_returns`/`trades`/`sharpe`/`metrics`）從 `research/is_harness.py` 下移到 `strategies/four_layer_resonance/sim.py`（本是純函式，本就該住策略層）。
- 橫斷面策略共用的 panel 建構 + 指標（`column_panel`/`flow_panels`/`panel_metrics`，後者用 `validation.metrics`）抽到 `strategies/common/panel.py`（`strategies → validation` 無循環，已驗證）。
- 新增 **`strategies/_template/`**：可複製的撰寫骨架（`strategy.py` config+純邏輯 + `runner.py` adapter + `README.md` checklist），本身是個可運作的等權買進持有 baseline，註冊為 `"template"`，兼作契約活範例與冒煙測試。
- `research/runners.py` 降為 **aggregator**：import 四隻 runner 觸發註冊 + re-export panel helper 舊名（向後相容）。Python 模組快取確保 `@register_strategy` 只觸發一次（無重複註冊）。
- `is_harness._run_is_core` 委派 `FourLayerRunner`；`momentum_harness.run_momentum_is` 委派 `MomentumRunner`。is_harness 從 sim **re-export** 舊底線名（`_signaled_window` 等），所以 `engines/protocol.py`、`research/sweep.py`、測試**完全不用改**（Never Break Userspace）。

依賴方向：`strategies/<name>/runner.py` → `strategies.common.panel` + `strategies.protocol` + `validation`（皆下行/無循環）；`research/runners` → 四隻策略 runner；`is_harness`/`momentum_harness` → `research/runners`（委派）。

### 4.3 範圍邊界（刻意留給後續）
- CLI `--strategy` 多策略 dispatch 與 `RunConfig.strategy` 欄位**留待後續**：它依賴 per-strategy preset 解析（現 `RunConfig.preset` 是 four_layer 專屬的 `PRESETS`），而 preset 統一屬重構 Stage 2。先交付乾淨的 library 層接縫，避免半接線的尷尬中間態。

---

## 5. 影響

- **擴展性**：新增策略從動 7-12 檔降到 **2-3 檔**（`strategies/<name>/`、`runners.py` 註冊、測試）。`tests/strategies/test_protocol.py` 以一個 throwaway 假策略證明此點。
- **去特殊化**：four_layer 不再是引擎唯一認得的策略；它與 momentum/inst_flow 走同一條 `get_strategy(name).run(...)`。
- **去重**：momentum 的 metrics 計算從 `momentum_harness` 收斂；four_layer sim 單一真實來源在 `sim.py`。
- **行為保持**：`tests/research/test_runners.py` 斷言 `FourLayerRunner` 路徑與 legacy `run_is` 數值逐項相等；全套 **998 passed / coverage 94%**。
- **無破壞性變更**：所有舊 import 路徑經 re-export 保留。

### 受影響模組
`strategies/protocol.py`（新）、`strategies/four_layer_resonance/sim.py`（新）、`research/runners.py`（新）、`research/is_harness.py`（委派 + re-export）、`research/momentum_harness.py`（委派）。引擎層 / API / sweep 不動。

### 後續動作
- **Stage 2（已完成 2026-06-16）**：
  - **metrics 去重**：Sharpe 公式的四份複製（four_layer `sim`、zipline `cli.sharpe_naive`、`cross_check._sharpe_from_equity`、外加 panel 策略）收斂到單一規範源 `validation.metrics.sharpe`；four_layer `sim` 的 cagr 亦改用 `validation.metrics.cagr`。`maxdd` 維持 four_layer 的負值報表慣例（非 gated criterion）。
  - **config 集中**：新增 `config/settings.py`（`Settings(BaseSettings)`），把散落於 `data/`/`api/`/`engines/` 的憑證（FINMIND/FINLAB token）、Postgres 連線、runs 路徑等 `os.environ.get` 收斂到單一型別化來源；只讀真實環境變數（不讀 `.env` 檔，保持原 `os.environ.get` 行為）。env-IPC（`UNIVERSE_FINMIND`/`STRATEGY_PRESET`）刻意保留。
- **仍待後續**：per-strategy preset 統一 → `RunConfig.strategy` + CLI `--strategy` dispatch（依賴 preset 系統擴展；屬 feature 非 cleanup，獨立交付）。
