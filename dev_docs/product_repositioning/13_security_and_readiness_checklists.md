# 安全與生產準備檢查清單 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## A. 核心安全原則

- Broker credential 最高敏感度。
- 交易預設 fail closed。
- Audit log append-only。
- Secrets 不進 git、artifact、log、frontend。
- 研究 agent（Claude Code）不持有 broker/finlab 憑證，只碰 research 表面（ADR-009）。

## B. 資料安全

| 檢查 | 狀態 |
| :--- | :--- |
| 資料分類完成：market data / strategy / credential / fills | [ ] |
| DB backup 加密 | [ ] |
| artifact hash 與 manifest 保存 | [ ] |
| PII 最小化 | [ ] |

## C. 應用安全

| 檢查 | 狀態 |
| :--- | :--- |
| API 認證啟用 | [ ] |
| 高風險 mutation 需 CSRF/confirmation/idempotency | [ ] |
| 輸入 schema validation | [ ] |
| Rate limiting for mutation endpoints | [ ] |
| Dependency scan | [ ] |

## D. Trading Readiness

| 檢查 | 狀態 |
| :--- | :--- |
| Research 不能 import broker | [ ] |
| 未核准 package 不能交易 | [ ] |
| RiskGate unavailable => Block | [ ] |
| Kill switch 可 halt all | [ ] |
| Fill ingestion idempotent | [ ] |
| Reconciliation mismatch => halt next trading | [ ] |
| 研究 agent 不 import/呼叫 execution/broker（research⊄services） | [ ] |
| 研究 agent 不持有憑證（finlab/broker 走 env / secret manager） | [ ] |
| sweep/DOE trials 誠實計數，DSR deflation 未被繞過 | [ ] |
| 跨 governance 閘門（select-live-oos / promote）須人核准 | [ ] |

## E. 生產準備

| 類別 | 檢查 |
| :--- | :--- |
| Observability | logs/metrics/alerts/dashboard |
| Reliability | backup/restore tested |
| Operations | runbook、rollback、incident template |
| Security | secrets rotation plan |
| Compliance | order/fill/audit retention |

## F. Go/No-Go

No-Go 條件：

- broker credential 管理未完成。
- risk gate 或 kill switch 不可用。
- fill/reconciliation 未測。
- CRIT alert 無法送達。
- rollback / restore 未演練。

