# 主規劃 — 現況與剩餘路線

> **本文件為「路線與計畫書」，不含進度狀態。** 里程碑狀態的單一真相源是 [16 WBS](./16_wbs_development_plan.md)；本文件描述現況能力邊界與剩餘關鍵路徑。

## 產品定位

backtest_platform 是 **個人量化 edge 驗證工廠 + 晉升管線**（single-user、standalone、台股專用）。策略是消耗品、審判庭（兩段驗證閘）是核心資產、連續 NO-GO 是平台正常運作的證據。本規劃的每個里程碑都服務同一條價值鏈：**假設 → 誠實判決 → 不可逆晉升**。完整敘事見 [02 PRD v4.0](./02_project_brief_and_prd.md)。

---

## 1. 現況 — 已成立的能力

平台的完整驗證 pipeline 已端到端可用，並已給出校準真相（抓出四層共振毀價值、動能 12-1 未達可部署門檻）。「平台優先於策略」已獲鐵證。

| 能力 | 現行實作 | 依據 |
| :--- | :--- | :--- |
| **資料層** | FinLab 付費全史（2007→今、原生 survivorship-clean 2753 檔含 369 下市）主源、FinMind fallback；parquet 快取 + manifest 血統；TimescaleDB telemetry | [ADR-006](./adrs/ADR-006-data-source-finlab-paid.md)、[ADR-032](./adrs/ADR-032-survivorship-universe-workflow.md) |
| **回測引擎** | 離線 close-to-close sim + 橫斷面 panel runner（研究迴圈唯一引擎；zipline/vectorbt 引擎殘骸已移除、engines/ 樹刪除）| [ADR-037](./adrs/ADR-037-remove-zipline-engine-remnants.md)（supersedes [ADR-013](./adrs/ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md)/[ADR-014](./adrs/ADR-014-zipline-reloaded-3-1-1-upgrade-reverses-adr-013-constraints.md)）|
| **策略契約 + registry** | `StrategyRunner` 輸出契約 + name→runner registry + conformance gate + per-strategy `gate` dispatch；新增策略複製 `_template/` 4 檔 + 1 行 | [ADR-027](./adrs/ADR-027-strategy-contract-and-registry.md)/[ADR-028](./adrs/ADR-028-strategy-dispatch-contract.md) |
| **研究工作流** | `doe` / `go_gates` / `truth_gate` / `paper_replay` / `build_universe` 五泛用工作流；各策略以 `research_config.py` 宣告參數、平台 dispatch 執行；CLI 4+1 命令 + HTTP `POST /research/workflows/{workflow}` 非同步 job | [ADR-029](./adrs/ADR-029-research-workflow-standardization.md)/[ADR-032](./adrs/ADR-032-survivorship-universe-workflow.md) |
| **審判庭（兩段閘）** | 真偽閘（survivorship-clean + PBO / DSR / WFA OOS 廣度 + 滑價 + OOS holdout，hard-fail）+ 配置閘（OOS Sharpe / 相關性 / 容量 → 連續倉位）；試驗計數 DSR deflate | [ADR-025](./adrs/ADR-025-two-stage-validation-gate-and-paper-promotion.md)/ADR-030 |
| **Paper 鏈** | `daily_flow` staged engine（ETL→signals→risk→orders→log，fail-fast）+ `collaborators` production factory + `paper_broker` 撮合 + `risk_gate` 12 檢查 + circuit_breaker 三級熔斷 | [ADR-008](./adrs/ADR-008-tri-mode-shared-strategy-code.md)、[24 風控規格](./24_risk_management_spec.md) |
| **REST API + 前端** | FastAPI 15 router；React 19 三 zone（Research/Monitor/System）+ Home cockpit + Cmd-K，17 路由全實頁；telemetry-driven（daemon 餵入即點亮） | [ADR-021](./adrs/ADR-021-unify-rest-contract-into-single-doc-and-openapi.md)/[ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md) |
| **機器守門** | CI 三 job：pytest+coverage（≥80%）/ tsc+vitest / contract-drift hard gate | — |

### 策略終局（現況）

| 策略 | 判決 | 狀態 |
| :--- | :--- | :--- |
| 四層共振 | 對照診斷證實**負 edge、毀價值**（buy-hold +12~22%，策略做成負） | 廢止（[ADR-023](./adrs/ADR-023-momentum-no-go-hold-gate.md)）；保留 pipeline 承重 + DOE skeleton |
| 動能 12-1 / 多因子 / long-short | 真偽閘 PBO 43-77% NO-GO（selected config 過擬合） | 對的 family、未達可部署門檻 |
| **inst_flow（三大法人資金流）** | survivorship universe 工作流平台化後**重驗中** | 現行 `_WIDE` fallback 態續 REJECTED；paper-ready 續 gated（見下方 §2） |

---

## 2. 剩餘關鍵路徑

> 對齊 [02 PRD v4.0 §3.3](./02_project_brief_and_prd.md) 與 [platform_full_audit_2026-07-02](./platform_full_audit_2026-07-02.md) 路線圖 Phase 2/3。每個里程碑不通過 acceptance 不晉升。

```
修好審判庭 ──► 重驗 inst_flow ──► after-close 排程器收 live OOS ──► 3 個月 paper ──► M5 小倉位實盤
  (完成)         (進行中)          (下一個 blocker)              (M4)            (2027-Q2)
```

### 里程碑 1 — inst_flow 真實重驗（進行中）

- **前提**：`build-universe` 工作流已平台化（FinLab 寬表 → 季度 survivorship rebalance → ingest → `universe_manifest.json` 血統）。
- **待執行**：在有 `FINLAB_API_TOKEN` 的環境跑 `build-universe`（2010→2024 全史 ingest）→ `truth-gate --strategy inst_flow`，用修正後的閘（ADR-030）驗判決可重現。
- **現況**：worktree / CI 無 FinLab 資料，`inst_flow` 走 survivor-only `_WIDE` fallback（反自欺，續 REJECTED）；過閘前 paper-ready 續 gated。
- **驗收**：判決在標準化工作流下可重現（平台 KPI「判決可重現性」）。

### 里程碑 2 — after-close 排程器（收 live OOS 唯一 blocker）

- **內容**：cron / systemd timer 級 after-close 排程器（真實日曆時間），觸發 `paper_daemon` 逐日跑 chain + Discord 成敗通知。個人 standalone 不需企業 scheduler。
- **前置**：paper 風控鏈已修復（`collaborators` 從 broker 快照建 `AccountState`、批次內遞減現金、side 詞彙轉換）。
- **驗收**：inst_flow（過閘後）每日 after-close emit 訊號 + 對比實際成交，開始累積 forward live OOS。

### 里程碑 3 — M4 三個月 paper

- **內容**：連續 3 個月每日成功 emit 訊號 + 模擬撮合；paper 期 live OOS 與 backtest 回溯對拍（reconciliation）；Monitor zone 接真 telemetry。
- **驗收**：live OOS 落在 WFA 信賴區間內、風控與執行摩擦符合回測假設。

### 里程碑 4 — M5 小倉位實盤（2027-Q2 暫定）

- **內容**：`shioaji_broker` 接線（永豐金）；總資本 5% 小倉位；配置閘 sign-off（不可逆晉升）；熔斷規則實盤驗證。
- **前置**：需重開遠端存取的 auth 決策（[ADR-031](./adrs/ADR-031-standalone-auth-decision.md) 將 Bearer 降至 M5 重議）。
- **驗收**：實盤 1 個月績效落在 WFA 95% 信賴區間內；DD > 限額自動停單通過測試。

---

## 3. 韌性與收斂（Phase 3，M4 前）

隨主路徑推進、非阻塞的補強項（對齊 audit Phase 3）：

- **台股微結構補課**：±10% 漲跌停 `TradingControl`、停牌合成資料測試、signal 層 look-ahead leak detector。
- **韌性補強**：`db_writer` 單交易 Unit of Work、FinMind/FinLab 呼叫加 retry/退避、jobs 提交冪等去重。
- **防過擬合工具化**：hypothesis property-based 測試導入 validation/risk（DSR 對 n_trials 單調、WFA fold 不重疊等）。
- **IA 收斂**：17 頁往活躍頁收斂、equity 疊 IS/OOS/live 邊界圖、paper daemon 狀態卡與觀察期進度。

---

## 4. 不做什麼（standalone lite 護欄）

明確不做的清單與要做的清單同等正式（呼應 [ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md)「補齊研究迴圈前不擴張監控」）：

| 不做 | 理由 |
| :--- | :--- |
| 多市場 / 期權 / 多帳戶 | 台股純股票策略，範圍護欄 |
| 跨人 leaderboard / staking / 完整 champion-challenger registry / 多人簽核 | single-user standalone（[ADR-022](./adrs/ADR-022-multi-strategy-fleet-operations.md) 界定：研究單策略、營運多策略 lite）|
| 分散式掃描叢集 / 自建計算圖引擎 / hosted notebook / K8s / 企業 scheduler | 單機自託管，cron 級足夠 |
| 自建回測 framework | zipline-reloaded event 引擎已就位，只寫薄 adapter |

範圍界線：艦隊營運層維持 gated 於「≥1 策略完成 3 個月 paper」（現 0）。
