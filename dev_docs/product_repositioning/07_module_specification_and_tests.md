# 模組規格與測試案例 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 模組總覽

| 層 | 模組 | 核心契約 |
| :--- | :--- | :--- |
| Data | SourceAdapter、DataQualityGate、BundleBuilder | `DataBundle` |
| Research | FactorEngine、StrategyBacktester、ValidationEngine | `AlphaSignal`, `BacktestReport` |
| Governance | StrategyRegistry、ReleaseGate、PaperLedger | `ApprovedStrategyPackage` |
| Strategy/Portfolio | StrategyRuntime、PortfolioEngine | `TargetPosition`, `OrderIntent` |
| Risk | RiskGate、LimitPolicy、CircuitBreaker | `RiskDecision` |
| Execution | ExecutionGateway、BrokerAdapter、FillIngestor | `BrokerOrder`, `Fill` |
| Monitoring | PositionService、PnLService、AlertDispatcher | `DailyOpsReport`, `Alert` |
| Foundation | Scheduler、SecretsProvider、BackupService | jobs、credentials、snapshots |

## 2. Design by Contract

### DataQualityGate

| Contract | 內容 |
| :--- | :--- |
| Precondition | source data 有 trade_date、symbol、schema version |
| Postcondition | pass 才能產生 releaseable bundle |
| Invariant | DQ fail 不可被 Research/Governance 靜默忽略 |
| Tests | 缺值、重複列、calendar mismatch、source lag |

### StrategyBacktester

| Contract | 內容 |
| :--- | :--- |
| Precondition | frozen RunConfig + bundle_ref |
| Postcondition | 產出 report pack、trials、target portfolio time series |
| Invariant | 不 import broker / execution adapter |
| Tests | lookahead guard、cost model、reproducibility、sweep trials retained |

### ReleaseGate

| Contract | 內容 |
| :--- | :--- |
| Precondition | report pack 完整、WFA/OOS evidence 存在 |
| Postcondition | approved package immutable |
| Invariant | 未核准不可進 StrategyRuntime |
| Tests | missing report、failed risk assumptions、rollback metadata |

### RiskGate

| Contract | 內容 |
| :--- | :--- |
| Precondition | order intent、positions、cash、risk config 完整 |
| Postcondition | Pass/Block/Reduce/Escalate |
| Invariant | risk data unavailable => Block |
| Tests | concentration breach、cash breach、halt flag、reconciliation lock |

### FillIngestor

| Contract | 內容 |
| :--- | :--- |
| Precondition | broker report has broker_order_id + exec_id |
| Postcondition | fill appended idempotently |
| Invariant | duplicate exec_id 不改變 position |
| Tests | duplicate fill、partial fill、broker reject、out-of-order fill |

## 3. 測試分層

| 測試 | 目標 |
| :--- | :--- |
| Unit | domain policy、factor calculation、risk rule |
| Contract | API schema、event schema、broker adapter seam |
| Integration | package -> order intent -> risk -> execution |
| E2E Paper | data -> research -> governance -> paper -> monitoring |
| E2E Trading Dry Run | risk-approved order intent 到 paper broker fill |
| Architecture | import rules、no broker in research、event idempotency |

## 4. 必測負路徑

- Data bundle DQ fail。
- Research run 缺 `bundle_ref`。
- Release candidate 缺 rollback plan。
- Order intent 超過現金或集中度。
- Broker adapter timeout。
- Fill duplicate。
- Reconciliation mismatch。
- Kill switch enabled。

