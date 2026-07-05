# WBS 開發計劃 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 專案總覽

| 項目 | 內容 |
| :--- | :--- |
| 總目標 | 乾淨新建個人級 EOD 量化交易平台 |
| 方法 | Contract-first + ADR-first + 七層分工 |
| 總期程 | 6 milestones |
| 當前進度 | M0 文件 baseline |

## 2. WBS 結構

```text
1.0 Foundation
2.0 Data Platform
3.0 Research & Validation
4.0 Governance & Paper
5.0 Strategy / Portfolio / Risk
6.0 Execution / Broker / Fill
7.0 Monitoring / Operations
8.0 Frontend Console
9.0 Security / Deployment / Readiness
```

## 3. 里程碑

| Milestone | 交付物 | Gate |
| :--- | :--- | :--- |
| M0 Golden Docs | 00-17 文件、ADR baseline | 文件一致性 |
| M1 Foundation + Data | DB、artifact store、bundle、DQ | bundle reproducible |
| M2 Research | strategy definition、backtest、WFA、report | no broker in research |
| M3 Governance + Paper | release gate、paper ledger、rollback | package immutable |
| M4 Strategy/Portfolio/Risk | runtime、sizing、risk gate、kill switch | fail closed |
| M5 Execution | broker adapter、order/fill、reconciliation | dry run pass |
| M6 Operations | dashboard、alerts、backup/restore、runbooks | production readiness |

## 4. 詳細工作包

| WBS | 工作包 | 依賴 |
| :--- | :--- | :--- |
| 1.1 | repo scaffold + CI | M0 |
| 1.2 | contracts package | 1.1 |
| 2.1 | source adapters | 1.2 |
| 2.2 | DQ gate + bundle builder | 2.1 |
| 3.1 | strategy definition schema | 1.2 |
| 3.2 | backtest runner | 2.2 |
| 3.3 | validation report pack | 3.2 |
| 4.1 | strategy registry | 3.3 |
| 4.2 | release gate + audit | 4.1 |
| 4.3 | paper ledger | 4.2 |
| 5.1 | strategy runtime | 4.2 |
| 5.2 | portfolio engine | 5.1 |
| 5.3 | risk gate + policies | 5.2 |
| 6.1 | broker adapter interface | 5.3 |
| 6.2 | paper broker | 6.1 |
| 6.3 | fill store + reconciliation | 6.2 |
| 7.1 | daily ops report | 6.3 |
| 7.2 | alert dispatcher | 7.1 |
| 8.1 | web console IA + shell | 4.1 |
| 8.2 | monitoring dashboards | 7.1 |
| 9.1 | secret management | 1.1 |
| 9.2 | backup/restore rehearsal | 6.3 |
| 10.1 | 具名 Universe 讀模型 + `GET /system/universes`（SPEC-01 Slice 1、ADR-007）— 🔨 進行中 | 2.2, 8.1 |
| 10.2 | New Run 股票池選單（SPEC-01 Slice 2，接 Q2/Q4）— ⏳ | 10.1 |
| 10.3 | Eligibility 篩選層：finlab set_universe 靜態 + 處置/注意/變更交易時變遮罩（SPEC-01 Slice 3、Q3）— ⏳ 前置需 token 驗 frame 形狀 | 10.1 |
| 10.4 | 資料字典下載對接、presence 相對 Universe+span（SPEC-01 Slice 4、Q1）— ⏳ | 10.1 |

> **WP 10（具名股票池對接）**：真相源為 `specs/SPEC-01-named-universe-artifact.md` + `adrs/ADR-007`。收斂前端資料管理四功能（資料字典/資料匯入/股票池建置/資料集清單）的斷線。finlab SDK 事實已本機實測（見 SPEC-01 §2）。

## 5. 風險管理

| 風險 | 影響 | 緩解 |
| :--- | :--- | :--- |
| Research/Execution 邊界被破壞 | 錯誤下單 | import fitness function |
| Broker SDK 行為不穩 | 錯單/漏單 | PaperBroker、dry run、idempotency |
| 資料品質不穩 | 回測與交易失真 | DQ gate、bundle manifest |
| 單人維運負擔 | 無法恢復 | runbook、backup、alert |

