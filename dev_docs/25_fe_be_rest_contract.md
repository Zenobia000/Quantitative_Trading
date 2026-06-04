# 25 — 前後端 REST API 契約（FE ↔ BE REST Contract）

> **版本:** v1.0 | **建立:** 2026-06-04 | **狀態:** 契約定版（M3.0 合一閘）
> **決策依據:** [ADR-021](./adrs/ADR-021-unify-rest-contract-into-single-doc-and-openapi.md)（契約合一）、[ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md)（研究迴圈優先）、[ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md)（React 升級）。
>
> **本文件是前後端 REST 契約的唯一真相源（single source of truth）。**
> FastAPI 於 `/docs` 自動輸出的 **OpenAPI schema 是機器可驗證的對應真相**；本文件宣告意圖，OpenAPI 落地驗證，兩者以 CI diff 對齊（見 §7、§9）。
>
> ### 真相源邊界（誰擁有什麼）
>
> | 你想找的 | 看這份 | 本檔關係 |
> |---|---|---|
> | **每個 REST 端點的路徑/方法/req-resp/錯誤碼/分頁/TTL** | **25（本檔）§1–§6** | 擁有 |
> | 哪些**頁面**存在、頁面職責、`[DATA & API]` 需求 | `web_design/pages/*.md` | 消費者（by reference，§6 消費頁欄回指）|
> | 每個 Monitor 面板要哪張表/哪個欄/怎麼算 | `20_dashboard_specification.md` | 上游 feeder（data-needs，非 REST shape）|
> | 資料層 schema / TimescaleDB DDL / 攝取契約 | `21_data_contract.md`（§1–§7）| 上游 feeder（L1 資料契約）|
> | 前端 stack / 分層 / API client 技術選型 | `12_frontend_architecture_specification.md` | 消費者（§7 回指本檔）|
> | v0.6 已實作的後端 CLI + Python API | `06_api_design_specification.md` | 已實作子集（§9 回指本檔）|
>
> ⚠️ **降級宣告**：`06 §9`（已實作研究面）與 `21 §8`（Monitor A–E）原各自描述部分 REST 契約，**自本檔起降為 feeder by reference**——以本檔的慣例為準，歧異一律以 25 為主（見各檔 banner）。

---

## §0 為什麼需要這份文件

截至 v0.6，後端 FastAPI 只落地 **11 條路由**（`/runs`、`/gate`、`/metrics`、`/presets` + `/health`），而 `web_design/` 的 **17 個頁面**（Research 8 + Monitor 4 + System 2 + Home cockpit `/` + Monitor fleet `/monitor` + Trade review `/research/runs/:id/trades` 3 新，2026-06-04）共需要約 **83 條端點**。在本檔之前，契約**分裂於三處且互相衝突**：

| 衝突項 | `06 §9`（已實作） | `21 §8`（Monitor A–E） | per-page `[DATA & API]` |
| :--- | :--- | :--- | :--- |
| base-path | 裸 root `/runs` | `/api/dashboard` | 發明 `/api/research/*`、`/api/performance/*` |
| envelope.error | 字串 | 物件 `{code,message,detail}` | — |
| 分頁 | offset `page/limit` | keyset `cursor` | — |
| auth | 無 | Bearer | 單人防呆 401/403 |

**最高風險**：前端（Lovable / React）一旦照 per-page 路徑生成，會對著**後端不存在、彼此也不一致**的端點寫程式。本檔把三處合一、釘死單一慣例，並把 per-page 路徑全部 reconcile 到 §6 registry（對照見附錄 A）。

---

## §1 通用慣例（Conventions）

### §1.1 統一信封（Envelope）

**每一個回應（成功與錯誤）都包在同一個信封**，由 `api/envelope.py` 的 `Envelope` model 定義：

```jsonc
{
  "success": true,            // bool，必有
  "data":    <payload>|null,  // 成功時為酬載；錯誤時 null（除非附帶部分資料）
  "error":   <ErrorObject>|null, // 成功時 null；錯誤時見 §2
  "meta":    <object>|null    // 分頁 / TTL / 旗標；見 §3、§5
}
```

**v0.6 → v1.0 唯一變更**：`error` 由「裸字串」**升級為結構化物件** `{code, message, detail}`（§2）。這是**向後相容的擴充**：

- `ok(data, meta)` → `success=true, error=null`（簽章不變）。
- `fail(message, code=…, detail=…)` → 內部包成 `{code, message, detail}`；舊呼叫 `fail("xxx")` 自動帶 `code=INTERNAL`（或由 exception handler 推導），**呼叫端不需改**。
- `app.py` 的兩個 exception handler 改一次（HTTPException、RequestValidationError → 填對應 `code`）。
- **行為不變，只有 error 子形狀變**；M3.0 加 regression test 驗證 11 條已實作端點。

> 鐵律：永不回裸 `{"detail": ...}`；404／422／500 都長得跟成功回應同一個信封形狀。

### §1.2 base-path 慣例（裸 root + 五區）

**無 `/api` 前綴、無 `/v1` 路徑版本**（版本走 OpenAPI metadata，見 §1.4）。所有路由掛在裸 root，依 IA 三區 + 共用分五個前綴：

| 前綴 | 區 | 內容 |
| :--- | :--- | :--- |
| `/runs`、`/gate`、`/metrics`、`/presets` | Research（已實作） | run 帳本、IS gate、指標計算機、preset（**v0.6 已落地，路徑零改動**）；run 子資源含 equity/trades/log/traded-symbols/candles/attribution/day-context（Trade review）|
| `/research/*` | Research（新增） | strategies、saved-views、trials、sweep、validate、promote |
| `/monitor/*` | Monitor | performance、positions、signals、risk（**全 stub 至 M4**，§5.4）；`/monitor/fleet*` 艦隊板 |
| `/system/*` | System | bundles、ingest、alerts、risk-spec |
| `/home/*` | Home（cockpit） | landing 聚合：fleet / research-status / system-health / recent（BFF 風格，§6.4）|
| `/health`、`/ws/*` | 全域 | liveness、WebSocket（唯一 WS，§5.3）|

> **決策（ADR-021）**：沿用 v0.6 已實作的裸 root，**11 條既有路由零遷移**（never break userspace）。per-page 規格發明的 `/api/research/*`、`/api/performance/*` 一律映射到上表（附錄 A）。前端 API client 的 `BASE_URL` 是唯一可調環境變數，路徑本身不帶版本。

### §1.3 資料型別慣例

- **日期/時間**：ISO 8601 帶 offset（`2026-06-04T13:20:00+08:00`）；純日期 `YYYY-MM-DD`。
- **股票代號**：`stock_id` 一律 `TEXT`（含前導零，如 `"0050"`），**禁止數值化**。
- **數值序列**：`NaN`/`Inf` 一律序列化為 `null`（前端 tabular-nums 對齊；heatmap/series 缺值以 null 佔位）。
- **金額/績效**：原始 float，不在後端格式化（前端以 `Intl` 處理千分位與 tabular-nums）。
- **百分比**：契約一律傳**小數**（`0.183` 表 18.3%），前端負責 ×100 與符號。

### §1.4 版本

`API_VERSION`（`app.py` 常數，現 `0.6.0`）→ FastAPI app version + `/health.data.version`。**路徑不帶版本**；contract 破壞性變更時升 minor 並在本檔 §0 banner 記變更，OpenAPI metadata 同步。

---

## §2 錯誤碼 enum（單一）

`error` 物件：`{ "code": <ENUM>, "message": <人類可讀繁中/英>, "detail": <object|array|null> }`。**全系統共用以下 enum**，HTTP status 與 code 一對一：

| HTTP | `code` | 語意 | `detail` 內容 | 觸發頁面/端點（既已隱含）|
| :--- | :--- | :--- | :--- | :--- |
| 422 | `VALIDATION_ERROR` | schema 驗證失敗（逐欄）| `[{loc, msg}]`（per-field）| RunConfig（New Run）、所有 `extra='forbid'` body |
| 409 | `IS_GATE_NOT_PASSED` | 違反 IS-gate 前置（如 pin 未過 IS 的候選）| `{run_id, gate_status}` | Runs Table tag/pin、Promote advance |
| 423 | `OOS_VAULT_LOCKED` | sealed OOS 在條件未滿足前被存取 | `{run_id, reason}` | Validate-gate OOS unseal |
| 404 | `NOT_FOUND` | 資源不存在 | `{resource, id}` | `/runs/{id}`、`/presets/{name}`、compare baseline |
| 400 | `BAD_REQUEST` | 請求語意錯（如 trade record 缺 key）| `{hint}` | `/metrics/trades` |
| 401 | `UNAUTHORIZED` | 缺/錯 Bearer（§4）| `null` | 全端點（單人防呆）|
| 504 | `QUERY_TIMEOUT` | 後端查詢/計算逾時 | `{op}` | 重查詢（sweep heatmap、telemetry）|
| 500 | `INTERNAL` | 未預期錯誤 | `null`（**不洩漏 stack/秘密**，`rules/security.md`）| 全域 fallback |

> **v0.6 對應**：現行 handler 把 HTTPException→`fail(str(detail))`、422→單字串。M3.0 升級為：依 status 對映上表 `code`，422 的 `_format_validation_errors` 改填 `detail=[{loc,msg}]` 陣列（保留人類可讀 `message`）。

---

## §3 分頁（offset，單一）

**全系統唯一分頁方案 = offset**（沿用 v0.6 `/runs`，零遷移）：

- Query：`?page=<int ge1, default 1>&limit=<int 1..500, default 50>`（1-based）。
- 切片：`start = (page-1)*limit; items = records[start:start+limit]`。
- Meta：`meta = {"total": <int>, "page": <int>, "limit": <int>}`。
- **不提供 cursor/keyset**；若日後 telemetry 大表證明 offset 痛，**per-endpoint** 再加 keyset，**不全站雙軌**（ADR-021）。

需分頁的端點（§6 標 `📄`）：`GET /runs`、`GET /research/strategies`、`GET /monitor/signals`、`GET /monitor/risk/events`、`GET /system/alerts/history`、`GET /system/bundles`。其餘為固定/小集合，不分頁。

---

## §4 認證（single-user static Bearer）

**單人自託管平台**，認證從簡但**從 day-one 預留**（避免 M5 回頭硬補）：

- 機制：**static Bearer token**（`Authorization: Bearer <token>`），token 由後端環境變數持有；或前置 reverse-proxy guard。
- 範圍：所有非 `/health` 端點要求 Bearer；缺/錯 → `401 UNAUTHORIZED`（§2）。`/health` 永遠開放（liveness probe）。
- 前端：API client wrapper **day-one 帶 auth header slot**（即使開發期 token 為固定值）。401/403 → 導向登入為防呆，**非多角色 RBAC**（對齊 `12 §7`）。
- 秘密：`FINLAB_API_TOKEN`、`DISCORD_*`、`INFLUX_*` **僅後端持有，絕不出現在任何回應或前端 bundle**（`rules/security.md`）；`/system/alerts/channels` 回傳一律 **遮罩**（`bot_token` → `"***"`）。

> v0.6 現況為**無 auth**；M3.0 加 Bearer dependency + 環境變數，11 條既有端點一律納入（測試用固定 token）。

---

## §5 即時協定（Realtime）

**決策（ADR-021）**：非 WS 一律 **HTTP polling + `meta.ttl`**；長任務走 **poll-status**；**唯一 WebSocket** 為 `/ws/positions/live`（M5）。不投機建 SSE。

### §5.1 cache-TTL 表（per-endpoint `meta.ttl` 秒）

回應 `meta.ttl` 宣告「此資料建議快取秒數」，前端 TanStack Query 據此設 `staleTime`/輪詢間隔。對齊 `12 §4` + 各頁更新策略：

| 資料類 | TTL(s) | 端點（§6）| 頁面 |
| :--- | :---: | :--- | :--- |
| 研究/驗證 batch 產物 | 300 | `/runs`、`/runs/{id}/*`、`/research/strategies`、compare、validate | research_03/04/05/07 |
| 部位（Monitor B）| 60 | `/monitor/positions/*` | monitor_b |
| 訊號（今日）| 30 | `/monitor/signals`、`/monitor/signals/funnel` | monitor_c |
| 訊號（歷史）| 300 | `/monitor/signals/timeline`、`/monitor/fills` | monitor_c |
| 風控遙測 | 30/60 | `/monitor/risk/metrics`(30)、`/monitor/risk/mdd-trend`(60) | monitor_d |
| 績效面板（Monitor A）| 300 | `/monitor/performance/*` | monitor_a |
| 艦隊板（live + 健康 + 退化）| 60 | `/monitor/fleet`、`/monitor/portfolio-summary` | monitor_fleet |
| 艦隊相關性（低頻）| 300 | `/monitor/correlation` | monitor_fleet |
| Home cockpit（艦隊/系統健康）| 60 | `/home/fleet`、`/home/system-health` | home_overview |
| Home cockpit（研究狀態/最近）| 300 | `/home/research-status`、`/home/recent` | home_overview |
| Trade review（run 快照不變）| 300 | `/runs/{id}/traded-symbols\|candles\|attribution\|day-context` | research_trade_review |
| 手動刷新 | — | sweep/compare 結果（使用者觸發）| research_05/06 |

### §5.2 長任務 poll 協定（submit → status → result）

重計算（real `POST /runs`、`POST /research/sweep`、`POST /system/ingest`）**非同步**：

```
POST <submit>            → 202/201  { job_id|run_id, status:"queued" }
GET  <…>/{id}/status     → 200      { status:"queued|running|done|failed", progress?, error? }
GET  <…>/{id}/<result>   → 200      終態 done 才回結果；running 回 409 或 status 物件
```

- **終態**：`done` | `failed`（前端輪詢至終態停止）。`failed` 帶 `error`（§2 形狀）。
- TTL：`queued/running` 的 status 端點 `meta.ttl` 短（2–5s）；終態後停輪詢。
- 後端 job 基礎建設見 M3.5（`jobs/` 模組）；M3.5 前 `POST /runs` 維持同步（測試以 stub executor）。

### §5.3 唯一 WebSocket：`/ws/positions/live`（M5）

整個契約**只有一個 WS**：`/ws/positions/live`（monitor_b 即時部位）。M5 才實作；M4 前 monitor_b 走 §5.1 的 60s 輪詢。訊息 schema（M5 定）：`{type:"snapshot|delta", positions:[…], ts}`。**其餘一切皆 HTTP polling**。

### §5.4 stub 慣例（Monitor 區 pending_m4）

**決策（ADR-021）**：Monitor B/C/D 無 live 資料源（無 daemon 託管 PaperBroker/CircuitBreaker；`upsert_signals/orders/fills` 是 M4 `NotImplementedError`）。在 M4 producer 完成前，`/monitor/*` 端點以 **typed 空 envelope** 上線（讓前端對著穩定 shape 建頁）：

```jsonc
{ "success": true, "data": [], "error": null,
  "meta": { "data_source": "pending_m4", "ttl": 60 } }
```

- **絕不回假數據/fixture 數字**（違反 `21 §8.8` single-truth）。
- §6 將這些端點標 `status=deferred-stub`。
- 前端據 `meta.data_source==="pending_m4"` 渲染明確空狀態「live 資料 M4 上線」，**非 0 值**。
- M4 swap-in 真 producer，**契約 shape 不變**。

---

## §6 端點 registry（全 71）

> 圖例 — **Status**：`✅shipped`（v0.6 已實作）/ `🟡partial`（已實作但需擴充）/ `⬜missing` / `🔵deferred-stub`（§5.4）。
> **就緒度**：`ready`（後端能力已存在、只缺接線）/ `needs-work`（需新後端邏輯）/ `needs-data`（需新資料源）。
> `📄`=分頁（§3）。**消費頁**回指 `web_design/pages/`。**里程碑**見 §8。

### §6.0 全域

| Method | Path | Status | Req → Resp（`data`）| 錯誤 | 里程碑 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| GET | `/health` | ✅ | — → `{status:"ok", version}` | — | — |

### §6.1 Research zone

| Method | Path | Status / 就緒 | Req → Resp（`data`）| 錯誤 | 消費頁 | 里程碑 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| GET | `/runs` 📄 | ✅ ready | `?page&limit` → `[{run_id, preset, gate_status, hypothesis, metrics, is_start, is_end}]`，`meta{total,page,limit}` | — | run_03/04 | M3.0（修 `is_start/is_end` window null bug）|
| GET | `/runs/compare` | 🟡 ready | `?baseline=&run_ids=a,b,c&metric_keys=…` → `{baseline_id, metric_keys, sign_consistent, rankings, comparisons[]}` | 404 NOT_FOUND | run_05 | M3.2（加 `run_ids` 子集 + equity）|
| GET | `/runs/{run_id}` | ✅ ready | — → 完整 ledger record dict | 404 | run_04 | — |
| POST | `/runs` | 🟡 needs-work | `RunCreateRequest{hypothesis,preset,stocks[],is_start,is_end,engine="sim"}` → record（同步）→ **async** `{run_id,status:"queued"}` | 422 | run_02 | M3.5（轉 async，§5.2）|
| GET | `/runs/{run_id}/equity` | ⬜ needs-work | — → `{returns[], equity[], drawdown[], monthly[], distribution[]}`（`run_is_returns` 持久化）| 404（舊 record 無 series）| run_04/05、mon_a(回測半) | M3.2 |
| GET | `/runs/{run_id}/trades` | ⬜ needs-work | `?symbol=`（選填，Trade review 逐股）→ `[{symbol,entry,exit,pnl,hold_days,reason,…}]`（`is_harness._trades` 持久化）| 404 | run_04、trade_review | M3.2 |
| GET | `/runs/{run_id}/log` | ⬜ needs-work | — → `{lines[], status}`（job lifecycle log）| 404 | run_04 | M3.5 |
| GET | `/runs/{run_id}/traded-symbols` | ⬜ needs-work | — → `[{symbol, trades, pnl_contrib}]`（有交易個股 + 貢獻排序）| 404 | trade_review | M3.2 |
| GET | `/runs/{run_id}/candles` | ⬜ needs-data | `?symbol=&start=&end=` → `{ohlc[], markers:[{ts,side,price}]}`（個股 K 線 + entry/exit marker；K 線需 `market_reader`）| 404 | trade_review | M4 |
| GET | `/runs/{run_id}/attribution` | ⬜ needs-work | `?symbol=` → `{factors:[{name, score}…], total}`（因子/層級歸因，**維度 N 由策略 `reason_json` 決定，不寫死層數**；four_layer 為 N=4 特例。需 harness 捕捉）| 404 | trade_review | M3.2 |
| GET | `/runs/{run_id}/day-context` | ⬜ needs-work | `?symbol=&date=` → `{factors:[{name, score}…], total, signal_reason}`（context_drawer 當日因子分數，策略無關 N 維）| 404 | trade_review | M3.2 |
| GET | `/runs/estimate` | ⬜ ready | `?<grid params>` → `{n_configs, est_minutes}`（`sweep.expand_grid`）| 422 | run_02 | M3.1 |
| POST | `/runs/tag` | ⬜ needs-work | `{run_ids[], tag, pin?}` → `{updated[]}` | **409 IS_GATE_NOT_PASSED**（pin 未過 IS）| run_03 | M3.3 |
| GET | `/runs/trials` | ⬜ needs-work | `?param_space=<hash>` → `{cumulative_trials, dsr, deflated, power}`（`dsr.py`+`trials.py` 持久化）| — | run_03/05/06 | M3.4 |
| POST | `/research/trials/increment` | ⬜ needs-work | `{param_space, n}` → `{cumulative_trials}` | — | run_05 | M3.4 |
| GET | `/research/universe-filters` | ⬜ ready | — → `{industries[], cap_buckets[], liquidity[]}`（`data/universe.py`）| — | run_02 | M3.1 |
| GET | `/research/strategies` 📄 | ⬜ needs-work | `?page&limit` → `[{strategy_id, version, best_kpi, validation_status, stage, runs_count}]`（projection over ledger）| — | run_01、mon_a(selector) | M3.3 |
| POST | `/research/strategies` | ⬜ needs-work | `{name, base_preset, …}` → `{strategy_id}` | 422 | run_01 | M3.3 |
| GET | `/research/strategies/{id}/versions` | ⬜ needs-work | — → `[{version, hypothesis, gate_status, created}]`（version timeline + hypothesis diff）| 404 | run_01 | M3.3 |
| GET | `/research/saved-views` | ⬜ needs-work | — → `[{id, name, columns[], filters}]` | — | run_03 | M3.3 |
| POST | `/research/saved-views` | ⬜ needs-work | `{name, columns[], filters}` → `{id}` | 422 | run_03 | M3.3 |
| POST | `/research/sweep` | ⬜ needs-work | `{param_space, …}` → `{job_id, status:"queued"}`（§5.2）| 422 | run_06 | M3.5 |
| GET | `/research/sweep/{id}/status` | ⬜ needs-work | — → `{status, progress}` | 404 | run_06 | M3.5 |
| GET | `/research/sweep/{id}/heatmap` | ⬜ needs-work | — → `{axes, z[][]}`（`to_heatmap` np→JSON, nan→null）| 409(running)/404 | run_06 | M3.5 |
| GET | `/gate/spec` | ✅ ready | — → `{criteria:[{key,op,threshold,kind,label}]}` | — | run_07 | — |
| POST | `/gate/evaluate` | ✅ ready | `GateEvaluateRequest{metrics:dict}` → `{status, passed, summary, results[]}` | 422 | run_07 | — |
| GET | `/research/validate/{run_id}/gate-state` | ⬜ needs-work | — → `{validation_status, stage, is, wfa, oos}`（stateful，持久化）| 404 | run_07 | M3.6 |
| POST | `/research/validate/{run_id}/is` | 🟡 needs-work | — → `{validation_status:"IS_PASS"}`（持久化 transition）| 409/422 | run_07 | M3.6 |
| POST | `/research/validate/{run_id}/oos` | ⬜ needs-work | — → `{oos_result}`（sealed unseal + access counter）| **423 OOS_VAULT_LOCKED** | run_07 | M3.6 |
| GET | `/research/validate/{run_id}/wfa` | ⬜ needs-work | — → `{folds[], scatter[]}`（per-fold via job layer）| 404 | run_07 | M3.6 |
| GET | `/research/validate/{run_id}/redline` | ⬜ needs-work | — → `{pbo, dsr_matrix[]}` | 404 | run_07 | M3.6 |
| POST | `/research/validate/{run_id}/signoff` | ⬜ needs-work | — → `{status:"APPROVED"}`（不可逆 + promotion_audit）| 409 | run_07 | M3.6 |
| GET | `/research/promote/{strategy_id}` | ⬜ needs-work | — → `{stage, history[], gates[]}`（persisted stage machine）| 404 | run_08 | M3.6 |
| POST | `/research/promote/{strategy_id}/advance` | ⬜ needs-work | — → `{stage}` | **409**（未滿足 gate）| run_08 | M3.6 |
| POST | `/research/promote/{strategy_id}/demote` | ⬜ needs-work | — → `{stage}` | 409 | run_08 | M3.6 |
| POST | `/research/promote/{strategy_id}/retire` | ⬜ needs-work | — → `{stage:"retired"}` | 409 | run_08 | M3.6 |
| GET | `/research/promote/{strategy_id}/audit` | ⬜ needs-work | — → `[{ts, from, to, actor}]`（immutable）| 404 | run_08 | M3.6 |
| GET | `/research/promote/{strategy_id}/observation` | 🔵 needs-data | — → paper equity（hosted daemon）| 🔵 stub | run_08 | M4 |

### §6.2 Monitor zone（全 `🔵 deferred-stub` 至 M4，§5.4）

> 以下端點 M3 期間以 typed 空 envelope（`meta.data_source:"pending_m4"`）上線，前端可建頁；M4 swap 真 producer，shape 不變。指標計算機 `/metrics/*` 為例外（已實作）。

| Method | Path | Status / 就緒 | Resp（`data`，M4 後）| 消費頁 | 里程碑 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| POST | `/metrics/summary` | ✅ ready | `MetricsSummaryRequest{daily_returns[],risk_free}` → `{total_return,cagr,max_drawdown,ulcer_index,downside_deviation,sharpe,sortino,calmar}` | run_04、mon_a | — |
| POST | `/metrics/trades` | ✅ ready | `TradeMetricsRequest{trades[]}` → `{win_rate,profit_factor,avg_hold,kelly_fraction}` | run_04、mon_c | — |
| GET | `/monitor/strategies` | 🔵 needs-work | strategy selector（live）| mon_a | M4 |
| GET | `/monitor/fleet` | 🔵 needs-data | 各策略 stage / 健康評分 / live KPI / 退化旗標（艦隊板）| monitor_fleet | M4 |
| GET | `/monitor/portfolio-summary` | 🔵 needs-data | 組合 equity / 曝險 / Heat / 計數 | monitor_fleet | M4 |
| GET | `/monitor/correlation` | 🔵 needs-data | 策略間報酬相關性矩陣（需多 live 策略）| monitor_fleet | M4 |
| POST | `/monitor/fleet/{strategy_id}/action` | 🔵 needs-data | `{action:demote\|retire\|replace}` → 寫 `promotion_audit`（依 M3.6 service；409/423 on gate 違反）| monitor_fleet | M4 |
| GET | `/monitor/performance/equity` | 🔵 needs-data | live 策略 equity series | mon_a | M4 |
| GET | `/monitor/performance/benchmark` | 🔵 needs-data | 0050 benchmark series（`market_reader` over daily_bars）| mon_a | M4 |
| GET | `/monitor/performance/monthly` | 🔵 needs-data | 月報酬 | mon_a | M4 |
| GET | `/monitor/performance/kpi` | 🟡 needs-data | live KPI（計算機已備，缺 live series）| mon_a | M4 |
| GET | `/monitor/positions/snapshot` | 🔵 needs-data | `PaperBroker.portfolio_snapshot`（需 daemon）| mon_b | M4 |
| GET | `/monitor/positions/prices` | 🔵 needs-data | current prices（quote/daily_bars read）| mon_b | M4 |
| GET | `/monitor/positions/kpi` | 🔵 needs-data | 部位 KPI | mon_b | M4 |
| GET | `/monitor/positions/industry-allocation` | 🔵 needs-data | 產業分布（需 universe metadata）| mon_b | M4 |
| GET | `/monitor/positions/concentration` | 🔵 needs-data | 集中度 | mon_b | M4 |
| GET | `/monitor/signals` 📄 | 🔵 needs-data | 訊號列表（`upsert_signals` M4 stub）| mon_c | M4 |
| GET | `/monitor/signals/timeline` | 🔵 needs-data | 訊號時間軸 | mon_c | M4 |
| GET | `/monitor/signals/funnel` | 🔵 needs-data | 訊號漏斗 | mon_c | M4 |
| GET | `/monitor/fills` | 🔵 needs-data | 成交（`upsert_fills` M4 stub）| mon_c | M4 |
| GET | `/monitor/risk/metrics` | 🔵 needs-data | `CircuitBreaker` RiskMetrics（需 daemon）| mon_d | M4 |
| GET | `/monitor/risk/mdd-trend` | 🔵 needs-data | MDD 趨勢 | mon_d | M4 |
| GET | `/monitor/risk/events` 📄 | 🔵 needs-data | 風控事件 | mon_d | M4 |
| GET | `/monitor/risk/events/{id}` | 🔵 needs-data | 單一事件 | mon_d | M4 |

### §6.3 System zone

| Method | Path | Status / 就緒 | Req → Resp（`data`）| 錯誤 | 消費頁 | 里程碑 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| GET | `/presets` | ✅ ready | — → `{presets[], configs{}}` | — | run_02、sys_data | — |
| GET | `/presets/{name}` | ✅ ready | — → cfg dict（M3.1 enrich bounds/desc）| 404 | run_02 | M3.1（enrich）|
| GET | `/system/risk/spec` | ⬜ ready | — → `{rules:[EX-001..012]}`（mirror gate.py）| — | mon_d(config)、sys_alerts | M3.1 |
| POST | `/system/risk/evaluate` | ⬜ ready | `{metrics}` → `{results[]}`（on-demand check）| 422 | mon_d(config) | M3.1 |
| GET | `/system/alerts/rules` | ⬜ ready | — → `[{rule}]`（static RULES catalog, read-only）| — | sys_alerts | M3.1 |
| GET | `/system/alerts/channels` | ⬜ ready | — → `{discord:{…, bot_token:"***"}}`（**遮罩**, §4）| — | sys_alerts | M3.1 |
| POST | `/system/alerts/test` | ⬜ ready | — → `{delivered:bool}`（discord_notifier test-push）| 500 | sys_alerts | M3.1 |
| PUT | `/system/alerts/channels` | ⬜ needs-work | `{discord:{…}}` → `{ok}`（secret-managed write）| 422 | sys_alerts | M4 |
| POST | `/system/alerts/rules` | ⬜ needs-work | `{rule}` → `{id}`（data-driven rule store）| 422 | sys_alerts | M4 |
| PUT | `/system/alerts/rules` | ⬜ needs-work | `{id, rule}` → `{ok}` | 404/422 | sys_alerts | M4 |
| GET | `/system/alerts/history` 📄 | 🔵 needs-data | `?page&limit` → `[{ts, rule, severity, acked}]`（alert_history store）| — | sys_alerts | M4 |
| POST | `/system/alerts/history/{id}/ack` | ⬜ needs-work | — → `{acked:true}` | 404 | sys_alerts | M4 |
| GET | `/system/bundles` 📄 | ⬜ needs-data | `?page&limit` → `[{id, range, universe, count, quality, created}]`（bundle_manifest）| — | sys_data、run_02 | M3.5 |
| GET | `/system/bundles/{id}/quality` | ⬜ needs-data | — → `{coverage, missing_days, delist_bias, look_ahead}`（DQ store）| 404 | sys_data | M3.5 |
| POST | `/system/ingest` | ⬜ needs-work | `{source, range, …}` → `{job_id, status:"queued"}`（§5.2）| 422 | sys_data | M3.5 |
| GET | `/system/ingest/{job_id}/status` | ⬜ needs-work | — → `{status, progress}` | 404 | sys_data | M3.5 |

> **Bundle 命名 reconcile**：per-page 規格曾寫 `/api/research/bundles`；契約統一為 `/system/bundles`（bundle 屬資料系統面，非研究面）。

### §6.4 Home / Cockpit zone（landing `/` 聚合，BFF 風格）

> Home（`home_overview`，route `/`）是每日進場入口，**跨三區聚合**——非新資料源，而是把 Research/Monitor/System 既有端點彙整成單畫面 cockpit。因此各端點就緒度 = 其聚合來源中最重者：研究面（research-status/recent）M3.x 可上，含 live 艦隊/系統健康者 gated 於 M4。前端可先 partial 渲染（研究半），live 半走 §5.4 stub。

| Method | Path | Status / 就緒 | Resp（`data`）聚合來源 | 消費頁 | 里程碑 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| GET | `/home/research-status` | ⬜ needs-work | active runs + IS gate blocker + power gauge + trials/DSR（聚合 `/runs`、`/gate`、`/runs/trials`）| home_overview | M3.4 |
| GET | `/home/recent` | ⬜ needs-work | 最近 run / 晉升 / saved views（聚合 `/runs`、`/research/promote`、`/research/saved-views`）| home_overview | M3.3 |
| GET | `/home/fleet` | 🔵 needs-data | live/paper 策略 + stage + 健康 + 今日 KPI + 退化旗標（聚合 `/monitor/fleet`）| home_overview | M4 |
| GET | `/home/system-health` | 🔵 needs-data | bundle 新鮮度 + 告警計數 + FinLab quota（聚合 `/system/bundles`、`/system/alerts`、Grafana quota）| home_overview | M4 |

> **聚合 vs 直連決策**：`/home/*` 採 BFF 聚合（後端一次組裝）而非前端多打——cockpit 首屏延遲敏感，且聚合邏輯（退化判定、blocker 彙整）屬後端職責。各來源端點仍獨立存在（§6.1–§6.3），`/home/*` 不取代它們。

---

## §7 型別生成 bridge（OpenAPI → TS）

- **工具（釘死）**：**`openapi-typescript`**（types-only，最輕，composes with `12 §7` 的單一 API client wrapper）；不採 orval（單人 overkill）。
- **gate（硬約束）**：型別生成**僅在本契約 union 進 FastAPI app 後**才完整——M3.0 前 `/docs` 只描述已實作 11 條，提前生成會得到缺 ~50 端點的契約。
- **流程**：FastAPI `/docs` 輸出 OpenAPI → `openapi-typescript` 生 `frontend/src/types/api.d.ts` → API client + TanStack Query hooks 強型別。
- **stub 標記**：未實作端點在本檔 §6 標 `missing/deferred-stub`；前端在型別生成補齊前，明確區分 stub vs shipped，避免對著 phantom type 寫。
- **drift 防護**：CI 對 `/docs` 生成的 OpenAPI 與本檔 §6 宣告的端點清單做 diff（§9）。

---

## §8 開發排序對映（→ 16 WBS 為狀態真相源）

> 完整里程碑見 [16_wbs_development_plan.md](./16_wbs_development_plan.md)（**單一狀態真相源**）。本節為契約視角的端點分桶；便宜（`ready`）工作 front-load，三個 CRITICAL blocker 押後。

| 里程碑 | 目標 | 端點 | 解鎖頁面 |
| :--- | :--- | :--- | :--- |
| **M3.0** | 契約合一閘（零新邏輯）| 升 `envelope.py`（error 物件）、修 `/runs` window bug、接 openapi-typescript、加 Bearer | （契約+型別 scaffold）|
| **M3.1** | 便宜 config/catalog 讀路由 | `/research/universe-filters`、`/runs/estimate`、`/system/risk/*`、`/system/alerts/{rules,channels,test}`、`/presets/{name}` enrich | run_02、sys_alerts(讀)、mon_d(config)|
| **M3.2** | 暴露已算出的 series + 逐股 review | `/runs/{id}/equity`、`/runs/{id}/trades?symbol`、compare `?run_ids`、`/runs/{id}/{traded-symbols,attribution,day-context}` | run_04/05、mon_a(回測半)、trade_review(K線除外)|
| **M3.3** | strategy registry + 側存 + Home recent | `/research/strategies*`、`/research/saved-views`、`/runs/tag`、`/home/recent` | run_01/03、home(recent)|
| **M3.4** | trials/DSR guardrail + Home 研究狀態 | `/runs/trials`、`/research/trials/increment`、`/home/research-status` | run_03/05、home(研究半)|
| **M3.5** | async job（CRITICAL #2）+ bundle/DQ | `POST /runs`(async)、`/runs/{id}/log`、`/research/sweep/*`、`/system/{bundles,ingest}*` | run_06、sys_data、run_02(async)|
| **M3.6** | validation+promotion service（CRITICAL #3）| `/research/validate/*`、`/research/promote/*` | run_07/08 |
| **M4** | live-telemetry daemon（CRITICAL #1, needs-DATA）| 全 `/monitor/*`（含 `/monitor/fleet*`）、`/home/{fleet,system-health}`、`/runs/{id}/candles`、`/research/promote/{id}/observation`、editable alerts | mon_a/b/c/d、monitor_fleet、home(live 半)、trade_review(K線)、sys_alerts(編輯)|

---

## §9 契約治理（防 drift）

> 本專案有 doc-drift 慣性病史（曾需 5 個 sweep commit、39 commits ahead）。契約**必須**靠機器檢查鎖住。

- **新增/改 API endpoint** → 同一 commit 改本檔 §6 registry + 重生 OpenAPI + 更新 `16 WBS`（**建議**在 [`code-doc-sync.md`](../.claude/rules/code-doc-sync.md) 觸發表把「新 API endpoint」列指向「25 §6 + OpenAPI」；該規則檔屬 agent 設定，需使用者自行套用）。
- **CI drift check**：比對 FastAPI `/docs` 生成的 OpenAPI 端點清單 vs 本檔 §6 宣告；不一致 → 紅燈。
- **envelope/分頁/auth/base-path** 任一變更 → 必走 ADR（如 ADR-021）+ 本檔 §1–§4 同步。
- **per-page `[DATA & API]` 路徑** 一律 by reference 指向本檔，**不再各自宣告**（附錄 A 為歷史對照，新頁不得發明路徑）。

---

## 附錄 A — per-page 路徑 reconcile 對照

per-page `[DATA & API]` 曾發明 `/api/*` 路徑（與後端裸 root 不符）。統一映射如下；**新頁面一律直接用右欄**：

| per-page 原始（廢棄）| 契約統一路徑（§6）|
| :--- | :--- |
| `/api/research/*` | `/research/*`（去 `/api`）|
| `/api/research/runs/{id}/equity` | `/runs/{id}/equity` |
| `/api/research/runs/{id}/trades` | `/runs/{id}/trades` |
| `/api/research/runs/trials` | `/runs/trials` |
| `/api/research/bundles` | `/system/bundles` |
| `/api/performance/*` | `/monitor/performance/*` |
| `/api/positions/*` | `/monitor/positions/*` |
| `/api/signals/*` | `/monitor/signals*` |
| `/api/risk/*` | `/monitor/risk/*` |
| `/api/fills` | `/monitor/fills` |
| `/api/strategies` | `/research/strategies`（research 主）/ `/monitor/strategies`（live selector）|
| `/api/system/*` | `/system/*` |
| `/api/home/*`（home_overview）| `/home/*`（去 `/api`，§6.4）|
| `/api/monitor/fleet`、`/api/monitor/portfolio-summary`、`/api/monitor/correlation`（monitor_fleet）| `/monitor/fleet`、`/monitor/portfolio-summary`、`/monitor/correlation` |
| `/api/monitor/fleet/{id}/action` | `/monitor/fleet/{strategy_id}/action` |
| `/api/research/runs/:id/{traded-symbols,candles,attribution,day-context}`（trade_review）| `/runs/{id}/{traded-symbols,candles,attribution,day-context}` |

---

> **維護**：本檔變更必同步 OpenAPI 與 16 WBS；歧異以本檔為準。對應程式碼 `backtest_platform/src/backtest_platform/api/`。
