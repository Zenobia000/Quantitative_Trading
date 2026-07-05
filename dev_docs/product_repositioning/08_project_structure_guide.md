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

