# Architecture Decision Records - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Accepted baseline

## ADR-001: 整體產品採 golden SAD 七層權威架構

### 背景

產品不能只是一個回測工具；完整交易閉環需要資料、研究、治理、生產策略、投組、風控、執行、監控與基礎設施。

### 決策

整體產品採 golden SAD 七層，right-size 為個人級 EOD。

### 後果

- 所有功能必須標示所屬層。
- Research 層不得直接下單。
- 非 Research 層仍屬產品內子系統，不是外部平台。

## ADR-002: FinLab / backtest_platform 僅屬 Research & Validation

### 決策

FinLab / backtest_platform 是第 2 層 Research & Validation，輸出 `StrategyDefinition`、`AlphaSignal`、`TargetPortfolio`、`BacktestReport`。

### 後果

- 不允許 broker dependency 進入 Research。
- PaperBroker / Shioaji adapter 屬 Execution / Integration，不屬 Research。

## ADR-003: 個人級 EOD，不做 Tick/HFT/EMS/K8s

### 決策

初版只支援 EOD batch、隔日開盤 / 低頻下單、單機或小 VPS。

### 後果

- Execution Backtest / Market Replay 為 scale-up。
- VWAP/TWAP/POV 不列入當前設計。
- Docker Compose + systemd 足夠；K8s 為 scale-up。

## ADR-004: Fill 是交易後單一真相

### 決策

部位、PnL、對帳、監控皆由 broker fill / paper fill fold 得出。

### 後果

- Target portfolio 不是實際部位。
- Broker report mismatch 觸發 halt。

## ADR-005: Risk Gate fail closed

### 決策

任何資料缺失、規則錯誤、對帳失敗、風控服務不可用，交易預設 Block / Halt。

### 後果

- 可錯過交易，不可錯誤交易。
- manual override 必須 append-only audit。

## ADR-006: Contract-first 與 Architecture Fitness Functions

### 決策

API、Event、Schema、Layer dependency 都是 living contract，需自動化驗證。

### 後果

- 新增跨層資料先改 `06_api_design_specification.md`。
- 新增模組先改 `07` / `08` / `09` / `10`。

## ADR-007: 具名股票池（Named Universe）為一等實體，策略以 N:1 引用

> 日期: 2026-07-05 | 關聯: `specs/SPEC-01-named-universe-artifact.md`、ADR-006（Contract-first）
>
> 註：現況碼有 ADR-032/035/038–041 等字串引用，係重定位前舊 SAD 編號殘留；golden 產品層 ADR 以本檔 001– 連號為準，本則取 007。

### 背景

前端資料管理四功能（資料字典 / 資料匯入 / 股票池建置 / 資料集清單）彼此斷線：股票池「建置」寫出 survivorship-clean 母體 + `universe_manifest.json`，但研究區 New Run 只有自由文字 `stocks`、選不到既有池；策略↔股票池對接藏在各策略 `research_config.py` 程式碼裡；build 篩選只有 `top_n`+`min_turnover`，缺可交易性排除；資料字典把財報/月營收/融資融券列為 key，但本地 bundle 只三表，這些永遠 `not_cached`（「看得到下不了」）。以本機 finlab 2.0.0 實測（SPEC-01 §2）確認 eligibility 資料 finlab 原生皆有、現有 catalog 13 key 全部存在。

### 決策

1. **具名 Universe 升為一等實體**（`id`/`name`，可選、可引用）——消除「自由打 symbols / 自由打 strategy」特殊情況，survivorship-clean 保證隨選擇一起走。
2. **策略 → Universe 為 N:1**（因子中性池跨策略共用）——`universe_manifest.json` 的 `strategy: str` 升為 `strategies: list[str]`（讀相容舊欄位）；禁止為單一策略造專屬重複池。
3. **build 留資料層、select 進研究層**——不搬 build 到研究。
4. **Eligibility 用 finlab 原生**：靜態（板別/產業/ETF）透傳 `data.set_universe`；時變（全額交割=`change_transaction:變更交易`、處置/注意=`esb_attention_disposal:*`）以遮罩排除；不自建重造。
5. **Q1 三類資料（財報/月營收/融資融券）暫採「執行時 `data.get` 即抓、不入 bundle」**，UI 明示「不入本地」而非誤導灰態；待實際策略需求再評估擴充 ingest。

### 後果

- 四個斷點收斂到單一資料結構；eligibility 補回「回測看得到、實盤買得到」落差。
- manifest schema 升版（`strategy`→`strategies[]`）需讀相容；New Run 契約由自由 `stocks` → `universe_id` + fallback。
- 新增 `GET /system/universes` 端點（無破壞）；既有策略自由宣告 symbols 路徑保留為 advanced fallback，不強制遷移。
- 落地切片與同步文件見 `specs/SPEC-01-named-universe-artifact.md` §4–5、`16_wbs` WP10。

## ADR-008: 策略是 Strategy Package，UI 只透過後端 read model 互動

> 日期: 2026-07-05 | 關聯: `specs/SPEC-02-dynamic-strategy-params-and-optimization-ui.md`、`adrs/ADR-R06-strategy-package-read-models.md`、ADR-006、ADR-007

### 背景

「新建回測」若只提供寫死策略欄位與 raw JSON params，會把使用者推回手寫欄位名，無法支援每個策略不同的 config，也無法把 DOE 參數最佳化產品化。另一方面，策略不是單一 Python 腳本；它是一個完整策略資料夾，包含 alpha 邏輯、runner adapter、research workflow config、測試與文件。若第一版把瀏覽器做成 Python IDE，需承擔 sandbox、依賴、版本、測試與安全成本，會偏離 single-user EOD 平台的最短可用路徑。

### 決策

1. **策略為 Strategy Package**：`strategies/<pkg>/` 至少包含 `strategy.py`（策略純邏輯）、`runner.py`（`@register_strategy` adapter）、`research_config.py`（DOE/GO/Truth/Paper 宣告），測試與 README 為 readiness 證據。
2. **策略撰寫留在 repo / AI coding / IDE**：Claude Code、Codex 或外部 IDE 負責新增/修改策略資料夾；前端不直接接收任意 Python 程式碼進 backend process 執行。
3. **前端透過 read model 互動**：新增 `GET /strategies/{strategy}/asset` 暴露 package descriptor；既有 `GET /strategies` 暴露 `config_schema`；新增 `GET /strategies/{strategy}/optimization-schema` 暴露 DOE grid。
4. **UI 負責參數化與 workflow orchestration**：New Run 由 `config_schema` 動態產生 params 表單；最佳化 UI 由 `DOE.grid` 產生 grid editor，送 `POST /research/workflows/doe`。

### 後果

- 新增策略時不改 React；只要策略 package 被註冊並提供 config/research config，UI 自動取得可互動面。
- raw JSON params 保留為 advanced fallback，但 guided schema form 是主路徑。
- 未來若要接 Claude Code/Agent SDK，應作為 repo-level branch/PR/job workflow，而不是把任意 Python 編輯器直接嵌進回測服務。
- 策略中心從「策略名列表」提升為「策略資產頁」：可顯示 package 結構、workflow readiness、參數 schema、最佳化入口與報表鏈路。
