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

