# 部署與運維指南 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 部署架構

```text
Local Dev → Staging/Paper → Production Personal VPS
```

| 元件 | 技術 |
| :--- | :--- |
| API / Worker / UI | Docker Compose |
| 排程 | systemd timers |
| DB | PostgreSQL + TimescaleDB |
| Artifact | local volume / object storage |
| Backup | restic / rsync |
| Alert | Discord webhook / Email |

## 2. CI/CD

| 階段 | Gate |
| :--- | :--- |
| Build | lint、typecheck、unit |
| Contract | OpenAPI/event schema diff |
| Architecture | import-linter、no-broker-in-research |
| Test | integration、BDD smoke |
| Security | secret scan、dependency scan |
| Deploy | staging smoke、backup check |

## 3. 日常排程

| 時間 | Job |
| :--- | :--- |
| 盤後 | data ingest、DQ、bundle build |
| 晚間 | research/paper evaluation、daily report |
| 開盤前 | approved package load、target/order preview、risk gate |
| 開盤 | personal execution submit |
| 收盤後 | fill reconciliation、PnL、alert |

## 4. 監控與告警

| 指標 | 等級 |
| :--- | :--- |
| data bundle fail | ERROR |
| DQ fail for trading date | CRIT if live strategy depends on it |
| risk gate unavailable | CRIT |
| broker submit failed | ERROR/CRIT |
| reconciliation mismatch | CRIT |
| strategy drawdown breach | WARN/CRIT |
| disk/db backup failed | ERROR |

## 5. Rollback

| 類型 | 方法 |
| :--- | :--- |
| Strategy rollback | deactivate current package，activate prior approved package |
| Execution rollback | disable broker submit，fallback paper mode |
| App rollback | deploy previous container image |
| Data rollback | use previous bundle_ref |

## 6. Runbook: Reconciliation Mismatch

1. Halt affected strategy。
2. Fetch broker position/fill report。
3. Compare with internal fill store。
4. Identify missing/duplicate/out-of-order fill。
5. Append correction event，不直接改歷史 fill。
6. Run reconciliation again。
7. Manual approval to resume。

## 7. Runbook: Kill Switch

1. Trigger `/execution/kill-switch`。
2. Confirm all future order intents blocked。
3. Notify Discord CRIT。
4. Record reason and operator。
5. Resume only through audited manual action。

