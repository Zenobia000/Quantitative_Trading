# 專案結構指南 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 設計原則

- 以七層與 Clean Architecture 對齊。
- Domain 不依賴 framework、DB、broker SDK。
- Research 與 Execution 物理隔離。
- Contract / schema 作為跨層真相。

## 2. 頂層結構

```text
quant_platform/
  apps/
    api/
    web_console/
    workers/
  packages/
    domain/
    application/
    adapters/
    infrastructure/
    contracts/
  services/
    data_platform/
    research_validation/
    governance_release/
    strategy_runtime/
    portfolio_engine/
    risk_gate/
    execution_gateway/
    monitoring_ops/
  tests/
  deploy/
  docs/
```

## 3. 服務結構

```text
services/research_validation/
  domain/
  application/
  adapters/
  strategies/
    <strategy_pkg>/
      __init__.py
      strategy.py          # alpha / signal / portfolio construction pure logic
      runner.py            # StrategyRunner adapter + @register_strategy
      research_config.py   # DOE / GO_GATES / TRUTH_GATE / PAPER_REPLAY / UNIVERSE
      README.md            # optional human docs
  tests/

services/execution_gateway/
  domain/
  application/
  adapters/broker/
  tests/
```

## 4. Contract 位置

```text
packages/contracts/
  openapi/
  events/
  schemas/
  examples/
```

## 4.1 Strategy Package 契約（ADR-008 / ADR-R06）

策略是資料夾，不是單一 script。每個 `strategies/<strategy_pkg>/` 透過
`runner.py` 註冊為可執行策略，透過 `config_model` 暴露動態參數 schema，
透過 `research_config.py` 暴露 DOE / validation workflow。前端不得直接讀
Python 檔案或任意執行使用者程式碼；一律消費後端 read model：

- `GET /strategies`：策略型錄與 `config_schema`
- `GET /strategies/{strategy}/asset`：策略資料夾 descriptor
- `GET /strategies/{strategy}/optimization-schema`：DOE grid read model
- `POST /runs` / `POST /research/workflows/doe`：執行單次 run / 參數最佳化

## 4.2 AI 研究撰寫 harness 面（ADR-009 / SPEC-03）

Claude Code（dev-time）在 repo 內以四個面取用平台，**無 MCP**：

```text
repo
├── strategies/<pkg>/          ① 撰寫面：agent 寫 strategy package
├── strategies/CLAUDE.md       ④ 紀律面：策略撰寫鐵律（execution off-limits、trials 誠實）
├── Claude Code skills         ④ 紀律面：策略撰寫 / 防過擬合 / 資料字典判讀
├── strategies/common/ 等積木   ② 積木面：panel/mechanics/metrics 可 import 積木（authoring SDK）
└── research.cli + importable   ③ 管道面：agent 跑回測/驗證/評估（非 MCP）
```

- agent 用 **Python + finlab SDK（`data.search` 離線可用）+ `research.cli`** 取用平台，不接 MCP tool 層。
- 邊界不靠 MCP：`research/strategies/validation ⊄ services` 由 import-linter 物理強制 + 人 review PR（見 §5）。

## 5. 禁止結構

- `research_validation` 不可 import `execution_gateway.adapters.broker`。
- `domain` 不可 import `sqlalchemy`, `fastapi`, `shioaji`, `requests`。
- UI 不可直接讀 DB。
- worker 不可繞過 application use case 直接寫資料。

## 6. 文檔結構

```text
docs/
  product/
  architecture/
  adrs/
  runbooks/
  api/
  operations/
```
