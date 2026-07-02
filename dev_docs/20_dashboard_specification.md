# 儀表板規格 — backtest_platform（React 三 zone GUI + Discord 告警）

> **版本：** v2.0 | **更新：** 2026-07-02 | **狀態:** 對齊實作（React 前端已落地）
> **決策依據:** [ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md)（React 升級）、[ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md)（研究迴圈優先）、[ADR-021](./adrs/ADR-021-unify-rest-contract-into-single-doc-and-openapi.md)（REST 契約合一）、[ADR-010](./adrs/ADR-010-discord-alerter-supersedes-telegram.md)（Discord 告警）。
>
> **本檔定位**：GUI 頁面 / 面板的 **FUNCTION + data-needs 真相源**（每個面板要哪張表 / 哪個欄 / 怎麼算），**不定義 REST shape**。
> REST 契約唯一真相源 = **[`25_fe_be_rest_contract.md`](./25_fe_be_rest_contract.md)**；本檔的 Monitor data-needs 是 25 §6.2 端點的**上游 feeder**。
> 前端技術 stack / 分層 / 設計令牌見 **[`12_frontend_architecture_specification.md`](./12_frontend_architecture_specification.md)**；頁面旅程見 `web_design/`。

---

## 1. 總覽

監控由三個獨立面向組成，各自時間尺度與旅程不同：

| 面向 | 工具 | 時間尺度 | 旅程 | 現況 |
| :--- | :--- | :--- | :--- | :--- |
| **策略研究 + 艦隊 GUI** | React 三 zone SPA | 日 / 分鐘 | 「策略真不真？」「艦隊健不健康？」| ✅ 已落地（17 路由）|
| **系統健康面板** | Grafana + InfluxDB | 秒 / 分鐘 | 「系統活著嗎？」| 🟡 M4 選配（4 面板已 provisioning）|
| **主動告警** | Discord Bot | 事件級 | 「出事快通知我」| ✅ 已落地（`monitoring/`）|

### 1.1 為什麼這樣分

- **React SPA**：策略研究迴圈與艦隊營運都需要 filter / drill-down / 圖表互動 → 前端頁面。
- **Grafana**：秒級系統 metrics（CPU / ETL / quota / 排程）不適合塞進 SPA，交給時序 dashboard。
- **Discord**：告警若仰賴使用者開頁面等於沒告警 → push 而非 pull。

### 1.2 三 zone IA + Home（真相源 `frontend/src/app/nav.ts`）

| Zone | 定位 | 頁面 | 資料來源（契約）|
| :--- | :--- | :--- | :--- |
| **Research**（主軸）| 策略研究者研究迴圈 | 策略庫 / New Run / Runs / Run Report / 逐筆覆盤 / Compare / Sweep / Validate / Promote | `/runs*`、`/research/*`、`/gate/*`、`/metrics/*` |
| **Monitor**（telemetry-driven）| 艦隊運維者 live 子視圖 | 艦隊總控 / 觀察艙 / 績效 / 部位 / 訊號 / 風控 | `/monitor/*`（M4 前 typed-empty stub；觀察艙 `/monitor/watch` 已 LIVE，ADR-033）|
| **System** | 資料 / 告警管理 | 資料管理 / 告警設定 | `/system/*` |
| **Home**（root `/`）| 每日進場 cockpit | 跨三區聚合 | `/home/*`（BFF 聚合）|

### 1.3 四態與 Cmd-K

- **四態完備**：每 section 必備 default / loading(skeleton) / empty / error（`WiredPage` 統一渲染）；Monitor stub 端點回 `meta.data_source==="pending_m4"` → 渲染明確空狀態「live 資料 M4 上線」，**非 0 值**（25 §5.4）。
- **Cmd-K CommandPalette**：跨頁快速跳轉（strategy / run / 頁面）。

---

## 2. Research zone（研究迴圈，GUI 主軸）

| 頁面 | route | 職責 | 主要端點 |
| :--- | :--- | :--- | :--- |
| 策略庫 | `/research/strategies` | 已註冊策略 catalog + 版本 timeline + 觸發研究工作流 | `/strategies`、`/research/strategies*`、`/research/workflows/{strategy}` |
| New Run | `/research/runs/new` | 設定並送出一次 IS run（`{strategy, params, stocks, is_start, is_end}`）| `POST /runs`、`/research/universe-filters`、`/runs/estimate` |
| Runs Table | `/research/runs` | run 帳本（filter / sort / 分頁；DOE 一次 16–24 configs，分頁必要）| `GET /runs 📄` |
| Run Report | `/research/runs/:id` | 單 run 完整報告 + equity / trades + IS gate | `/runs/{id}`、`/runs/{id}/{equity,trades,log}`、`/gate/*` |
| 逐筆覆盤 | `/research/runs/:id/trades` | 逐股交易 + K 線 markers + 因子歸因 | `/runs/{id}/{traded-symbols,candles,attribution,day-context}` |
| Compare | `/research/compare` | 多 run 排名 + delta + 符號一致性 | `GET /runs/compare` |
| Sweep | `/research/sweep` | 參數網格掃描 + heatmap | `POST /research/sweep`、`/research/sweep/{id}/{status,heatmap}` |
| Validate | `/research/validate` | IS→WFA→OOS 不可逆 gate + OOS sealed vault | `/research/validate/{run_id}/*` |
| Promote | `/research/promote/:strategyId` | 晉升狀態機（advance 未過 gate → 409，前後端雙防線）| `/research/promote/{strategyId}/*` |

### 2.1 研究工作流入口現況（ADR-029）

現行研究方法真相源是通用工作流 **doe / go_gates / truth_gate / paper_replay / build_universe**：

- **CLI**（主路徑，已 shipped）：`research doe|go-gates|truth-gate|paper-replay|build-universe --strategy <name>`。
- **HTTP**（已 shipped）：`GET /research/workflows/{strategy}` 列該策略宣告的工作流；`POST /research/workflows/{workflow}` → 202 `{job_id, status}`（非同步，25 §5.2）。
- **GUI IA**：策略卡觸發工作流的入口尚在收斂中（審查缺陷 #25）；現以策略庫 + Runs 為主敘事。

### 2.2 Research 資料呈現要點

- **metrics-dict-first**：先回結構化 metrics dict 秒判綠 / 紅，重圖（tear sheet / equity）按需 render。
- **gate 依策略 dispatch**：run 以其自身策略宣告的 gate 判決（非四層預設），GUI 判定須與 CLI truth-gate 一致。
- **equity 圖**：疊 IS / OOS / live_start_date 邊界（Recharts）；sweep heatmap 走 Plotly（nan→null 佔位）。

---

## 3. Monitor zone（telemetry-driven，M4 前 stub）

Monitor 面板無 live 資料源前（無 daemon 託管 PaperBroker / CircuitBreaker）以 typed 空 envelope 上線，讓前端對穩定 shape 建頁；M4 swap 真 producer，契約 shape 不變（25 §5.4）。以下為各面板 **data-needs**（餵 25 §6.2 契約）。

### 3.1 艦隊總控 `/monitor`（monitor_fleet）

| 元件 | 表 / 來源 | 計算 |
| :--- | :--- | :--- |
| 各策略 stage / 健康 / live KPI / 退化旗標 | `equity_snapshots` + 晉升狀態 | 退化判定（live vs 回測 KPI 偏離）|
| 組合 equity / 曝險 / Heat / 計數 | `equity_snapshots` + `positions` | portfolio 聚合 |
| 策略間報酬相關性矩陣 | 多策略 `equity_snapshots` | 相關性（需 ≥2 live 策略）|

### 3.2 績效總覽 `/monitor/performance`（monitor_a）

| 元件 | 表 | 計算 |
| :--- | :--- | :--- |
| KPI cards（total_return / cagr / sharpe / mdd / win_rate / trades）| `equity_snapshots` | `/metrics/summary`（計算機已 shipped）|
| Equity + benchmark(0050) | `equity_snapshots` + `daily_bars(0050)` | normalize 同起點 |
| Drawdown / Rolling Sharpe / Monthly heatmap | `equity_snapshots` | 已預算 / rolling / resample |

### 3.3 部位狀態 `/monitor/positions`（monitor_b）

| 元件 | 表 | 計算 |
| :--- | :--- | :--- |
| Positions table（qty / entry / current / pnl% / days / stop）| `positions` + `daily_bars`(current) | `pnl_pct=(current-entry)/entry` |
| 產業分布 / 集中度 | `positions` + `universe`(industry) | HHI = Σ(mv_i/total)² |
| Heat / Cash / Open KPIs | `positions` + `equity_snapshots` | — |

> live 即時部位為唯一 WebSocket `/ws/positions/live`（M5）；M4 前走 60s 輪詢（25 §5.3）。

### 3.4 訊號日誌 `/monitor/signals`（monitor_c）

| 元件 | 表 | 備註 |
| :--- | :--- | :--- |
| 今日訊號（time / symbol / action / reason / status）| `signals` | `reason_json` 展開 scores / prices / context |
| 訊號時間軸 / 漏斗 | `signals` + `fills` | generated→submitted→filled funnel + latency |

### 3.5 風控指標 `/monitor/risk`（monitor_d）

| 元件 | 表 | 計算 |
| :--- | :--- | :--- |
| Status badge + 水位（DD / VaR / Heat）| `risk_metrics`(latest) | status 由 `event_type` 推導 |
| MDD 趨勢 + 熔斷線 | `risk_metrics` | L1/L2/L3 hline（24 §4）|
| 風控事件 | `risk_metrics` where `event_type IS NOT NULL` | drill-down `event_context` |

### 3.6 Paper-Watch 觀察艙 `/monitor/watch`（monitor_watch，[ADR-033](./adrs/ADR-033-paper-watch-tier.md)）

> **例外：此頁已 LIVE**（非 M4 stub）。資料源是 event-sourced JSONL（`watch_registry.jsonl` + `after_close_markers.jsonl`），非 daemon telemetry——排程本體留 systemd（OS 保證準時），GUI 負責「看見與管理」。補審查缺陷 #17（paper 階段介面覆蓋率趨近零）。

| 元件 | 表 / 來源 | 計算 |
| :--- | :--- | :--- |
| 觀察艙清單卡（狀態 badge / 觀察日 N/~60 進度 / 到期倒數 / DSR）| `watch_registry.jsonl`（fold `all_watches`）| 觀察日 = 進艙後交易日計數；到期 = 進艙 +90 日 |
| Timer 健康度（ok / stale / never_ran）| `after_close_markers.jsonl` vs 交易日曆 | stale = 最後成功 marker < 上一交易日（`previous_trading_day` 回推，假日不誤判）|
| 最近 10 筆 session 時間線（date + OK/FAILED/NO_DATA/SKIP）| `after_close_markers.jsonl` | newest-first，capped 10 |
| 暫停 / 恢復鈕（app 層 pause）| `POST /monitor/watch/{s}/pause\|resume` | after-close 尊重 pause → 略過（exit 0，不發 Discord）|

- **timer stale / never_ran**：卡片顯示可複製的 `systemctl --user enable --now after-close.timer` 指令塊 + deploy/README 指引（14 §運維）。
- **四態完備**：loading / error / pending / data 比照其餘 monitor 頁（`QueryState`）。

> 風控門檻與熔斷邏輯真相源 = [24_risk_management_spec.md](./24_risk_management_spec.md)；`/system/risk/spec` 鏡射 gate 規則供 GUI 顯示。

---

## 4. System zone

| 頁面 | route | 職責 | 端點 |
| :--- | :--- | :--- | :--- |
| 資料管理 | `/system/data` | bundle 清單 + DQ 品質 + 觸發 ingest | `/system/bundles*`、`/system/ingest*` |
| 告警設定 | `/system/alerts` | 告警規則 catalog + 通道（遮罩）+ test-push + 歷史 | `/system/alerts/{rules,channels,test,history}` |

- 資料血統：bundle `manifest.json`（parquet cache 的 `bundle_ref`）+ FinLab survivorship-clean `universe_manifest.json`（見 21 §parquet manifest）。
- 告警通道回應**一律遮罩**（`bot_token → "***"`，25 §4）。

---

## 5. Discord 告警規格（對齊 `monitoring/` 實作）

告警經兩個模組：**`monitoring/alert_rules.py`**（決策層：三級規則 + 去重 + 靜默時段，純函式可測）+ **`monitoring/discord_notifier.py`**（發送層：httpx REST embed，讀 `DISCORD_*` env，ADR-010）。決策與發送分離，規則邏輯零網路可測。

### 5.1 等級定義

| 等級 | Icon | 觸發類別 | SLA |
| :--- | :--- | :--- | :--- |
| **Critical** | 🚨 | 熔斷觸發、下單失敗連 3、資料源全斷、Container down | 即時（5 秒內）|
| **High** | ⚠️ | ETL 失敗、訊號缺漏、部位偏離 > 5%、API quota < 500MB | 5 分鐘內 |
| **Info** | ℹ️ | 每日盤後績效 + 訊號 digest | 每日一次 |

### 5.2 觸發規則表（`alert_rules.py` `RULES`，宣告式 data）

| Rule ID | 等級 | 條件 | 來源 |
| :--- | :--- | :--- | :--- |
| `CRIT-001` | 🚨 | 成交 REJECTED 連續 3 筆 | telemetry |
| `CRIT-002` | 🚨 | Shioaji `connected=0` 持續 60s | 系統 metric |
| `CRIT-003` | 🚨 | 風控事件 `L2_CUT` / `L3_HALT` | `risk_metrics` |
| `CRIT-004` | 🚨 | Container restart_count > 0 | 系統 metric |
| `HIGH-001` | ⚠️ | ETL `status=FAIL` | 系統 metric |
| `HIGH-002` | ⚠️ | 盤後訊號數 = 0（預期 > 0）| `signals` |
| `HIGH-003` | ⚠️ | 部位偏離 `|qty_actual − qty_expected| / qty_expected > 5%` | `positions` |
| `HIGH-004` | ⚠️ | `api_quota.finlab.remaining_mb < 500` | 系統 metric |
| `INFO-001` | ℹ️ | 每日盤後 digest（績效 + 訊號摘要）| scheduled |
| `INFO-002` | ℹ️ | 每筆 buy/sell 成交 | `fills` |

### 5.3 去重與靜默（`alert_rules.py` 常數）

- **去重**：同 `rule_id` 30 分鐘內只發一次（`DEDUPE_WINDOW`）。
- **靜默時段**：本地 22:00–08:00 只推 Critical（`SILENT_START` / `SILENT_END`）。
- **時鐘注入**：時間經單一 seam（`clock` callable）進入，測試 pin、production 預設 `datetime.now(UTC)`。

### 5.4 訊息格式

Discord Embed（顏色 + 欄位 + 時戳）：Critical `0xB71C1C` / High `0xFFA000` / Info `0x1976D2`。純發訊不需 event loop，可在 sync CLI / 排程 task 直呼。測試送達：`POST /system/alerts/test`。

---

## 6. Grafana 系統面板（M4 選配）

系統健康（秒 / 分鐘級 metrics）走 Grafana + InfluxDB，**不經 React SPA**。已 provisioning 於 `backtest_platform/docker/grafana/`，容器啟動自動載入：

| 面板 | 內容 | InfluxDB measurement |
| :--- | :--- | :--- |
| ETL 健康 | duration / 成功率 / last_data_ts | `etl_run` |
| API quota | FinLab remaining_mb / connected / latency | `api_quota` / `api_health` |
| 排程 | run ok state-timeline + duration by step | `scheduler_run` |
| 系統資源 | CPU / mem / disk gauge | `system` |

- Flux query 對齊 `monitoring/influx_writer.py` emit 的 measurements。
- 結構驗證：`tests/monitoring/test_grafana_dashboards.py`（JSON 合法 + 必填鍵 + uid 唯一 + panel 綁 datasource/Flux/threshold）。
- **待補**：`node_exporter`（資源）/ `data_quality`（缺資料偵測）/ `api_error`（錯誤計數）三個 emitter 尚未由 app 寫出；live Grafana import 為手動驗證（CI 環境無 Grafana）。

---

## 7. 交付里程碑

| Milestone | Research | Monitor | System | 告警 |
| :--- | :--- | :--- | :--- | :--- |
| **現況** | ✅ 頁面落地（研究迴圈欄位對齊）| 🟡 頁面落地、typed-empty stub | ✅ 資料 / 告警頁 | ✅ Discord 三級 |
| **M4** | + 工作流 GUI 入口收斂 | swap live daemon（真 producer）| bundle / DQ 接真 | + Grafana 系統面板 |
| **M5** | Promote stepper 全鏈 | + `/ws/positions/live` | — | + 熔斷推播 |
