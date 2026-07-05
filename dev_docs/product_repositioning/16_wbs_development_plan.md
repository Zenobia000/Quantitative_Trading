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
| 10.2 | New Run 股票池選單 + 後端解析（SPEC-01 Slice 2，接 Q2/Q4/Q5：預設池+提示）— ✅ 落地 | 10.1 |
| 10.2b | 資料字典/策略頁 UX：反向索引搬策略頁、卡片教 data.get 用法、収合（SPEC-01 Slice 2.5）— ✅ 落地 | 10.1 |
| 10.3 | Eligibility 篩選層：finlab set_universe 靜態 + 處置/注意/變更交易時變遮罩（SPEC-01 Slice 3、Q3）— ✅ 落地 | 10.1 |
| 10.4a | 資料字典 runtime-only 標示 + ingest default universe fallback（SPEC-01 Slice 4a、Q1）— ✅ 落地 | 10.1 |
| 10.4b | 資料字典下載對接、presence 相對 Universe+span（SPEC-01 Slice 4b/4c、Q1）— ⏳ | 10.4a |
| 11.1 | Strategy Package descriptor：`GET /strategies/{strategy}/asset`（SPEC-02、ADR-008、ADR-R06）— ✅ 落地 | 4.1, 8.1 |
| 11.2 | New Run 動態 params form：由 `config_schema` 產生 guided params，raw JSON 僅 advanced fallback（SPEC-02）— ✅ 落地 | 11.1 |
| 11.3 | DOE 最佳化 schema + grid editor：`GET /strategies/{strategy}/optimization-schema` + `POST /research/workflows/doe`（SPEC-02）— ✅ 落地 | 11.1 |

> **WP 10（具名股票池對接）**：真相源為 `specs/SPEC-01-named-universe-artifact.md` + `adrs/ADR-007`。收斂前端資料管理四功能（資料字典/資料匯入/股票池建置/資料集清單）的斷線。finlab SDK 事實已本機實測（見 SPEC-01 §2）。
>
> **WP 11（策略資產包與動態研究 UI）**：真相源為 `specs/SPEC-02-dynamic-strategy-params-and-optimization-ui.md` + ADR-008 + `adrs/ADR-R06-strategy-package-read-models.md`。策略撰寫留在 repo/AI coding/IDE；UI 透過策略 package descriptor、config schema 與 DOE schema 互動。

## 5. 風險管理

| 風險 | 影響 | 緩解 |
| :--- | :--- | :--- |
| Research/Execution 邊界被破壞 | 錯誤下單 | import fitness function |
| Broker SDK 行為不穩 | 錯單/漏單 | PaperBroker、dry run、idempotency |
| 資料品質不穩 | 回測與交易失真 | DQ gate、bundle manifest |
| 單人維運負擔 | 無法恢復 | runbook、backup、alert |
