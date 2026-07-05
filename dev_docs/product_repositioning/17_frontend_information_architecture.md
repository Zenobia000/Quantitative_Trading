# 前端資訊架構規範 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 目的與範圍

前端 Console 支援單一操作者完成研究、發布、paper、風控、執行監控與事故處理。它不是策略 IDE，也不是高頻交易台。

## 2. 資訊架構總覽

```text
/
├── /overview
├── /data
├── /research
│   ├── /strategies
│   ├── /runs
│   └── /reports/:id
├── /governance
│   ├── /candidates
│   ├── /packages
│   └── /paper
├── /trading
│   ├── /targets
│   ├── /order-intents
│   ├── /risk-decisions
│   └── /fills
├── /monitoring
│   ├── /pnl
│   ├── /positions
│   ├── /alerts
│   └── /incidents
└── /system
    ├── /jobs
    ├── /settings
    └── /audit
```

## 3. 主導航

| 區域 | 問題 |
| :--- | :--- |
| Overview | 今天系統能不能交易？ |
| Data | 資料是否完整且可用？ |
| Research | 哪些策略有證據？ |
| Governance | 哪些策略可 paper / release / rollback？ |
| Trading | 今天要買賣什麼？被風控擋了什麼？ |
| Monitoring | 實際部位、PnL、告警、事故？ |
| System | jobs、secrets、audit、backup 狀態？ |

## 4. 核心旅程

| Journey | Path |
| :--- | :--- |
| 驗證策略 | Research Strategies → New Run → Report → Candidate |
| 發布策略 | Candidate → Release Gate → Paper → Approved Package |
| 交易前檢查 | Overview → Targets → Order Intents → Risk Decisions |
| 事故處理 | Alerts → Incident → Audit → Kill Switch / Resume |
| 對帳修復 | Fills → Reconciliation → Correction Event → Resume |

## 5. 頁面規格

### Overview

- 今日 trading readiness。
- Data bundle status。
- Active packages。
- Risk / reconciliation / kill switch status。
- Daily PnL and drawdown。

### Research Report

- thesis、config、bundle_ref。
- equity、drawdown、turnover、cost。
- WFA/OOS、DSR/PBO、trials。
- Target portfolio preview。

### Release Candidate

- checklist：data、research、risk assumptions、rollback。
- approve/reject actions。
- audit reason required。

### Risk Decisions

- order intent。
- rule results。
- final decision。
- link to package、positions、cash。

### Incident

- severity。
- timeline。
- affected strategies。
- actions taken。
- resume conditions。

## 6. 路由與資料載體

| 資料 | URL | Query |
| :--- | :--- | :--- |
| strategy_id | path | `/research/strategies/:strategy_id` |
| run_id | path | `/research/reports/:run_id` |
| package_id | path | `/governance/packages/:package_id` |
| date range | query | `?from=YYYY-MM-DD&to=YYYY-MM-DD` |
| filters | query | `?status=halted&severity=crit` |

## 7. 可用性檢查

- CRIT 狀態全站可見。
- 高風險操作必須二次確認與原因。
- 所有表格可 drill down 到 audit trail。
- 空狀態要告訴使用者下一步，不寫教學長文。

