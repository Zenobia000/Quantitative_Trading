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

截至 v0.6，後端 FastAPI 只落地 **11 條路由**（`/runs`、`/gate`、`/metrics`、`/presets`〔後由 `/strategies` 取代，[ADR-028](./adrs/ADR-028-strategy-dispatch-contract.md)〕 + `/health`），而 `web_design/` 的 **17 個頁面**（Research 8 + Monitor 4 + System 2 + Home cockpit `/` + Monitor fleet `/monitor` + Trade review `/research/runs/:id/trades` 3 新，2026-06-04）共需要約 **83 條端點**。在本檔之前，契約**分裂於三處且互相衝突**：

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

**v0.6 → v1.0 唯一變更**：`error` 由「裸字串」**升級為結構化物件** `{code, message, detail}`（§2）。✅ **已實作（8.H.1，PR feat/contract-gate）**，向後相容的擴充：

- `ok(data, meta)` → `success=true, error=null`（簽章不變）。
- `fail(message, code="INTERNAL", detail=None)` → 內部包成 `ApiError{code, message, detail}`；舊呼叫 `fail("xxx")` 自動帶 `code=INTERNAL`，**呼叫端不需改**。
- `app.py` 三個 exception handler：`HTTPException`（status→code 映 `_STATUS_TO_CODE`，dict detail 透傳）、`RequestValidationError`（`VALIDATION_ERROR` + `detail=[{loc,msg}]`）、新增 `Exception` 全域 fallback（`INTERNAL`，不洩漏 stack）。
- **行為不變，只有 error 子形狀變**；regression test `tests/api/test_contract_envelope.py` 釘死 code 映射 + per-field detail；OpenAPI 重生 → `frontend/src/types/api.gen.ts` 含 `ApiError`。

> 鐵律：永不回裸 `{"detail": ...}`；404／422／500 都長得跟成功回應同一個信封形狀。

### §1.2 base-path 慣例（裸 root + 五區）

**無 `/api` 前綴、無 `/v1` 路徑版本**（版本走 OpenAPI metadata，見 §1.4）。所有路由掛在裸 root，依 IA 三區 + 共用分五個前綴：

| 前綴 | 區 | 內容 |
| :--- | :--- | :--- |
| `/runs`、`/gate`、`/metrics`、`/strategies` | Research（已實作） | run 帳本、IS gate、指標計算機、策略 catalog（`/strategies` **取代 v0.6 的 `/presets`**，[ADR-028](./adrs/ADR-028-strategy-dispatch-contract.md)）；run 子資源含 equity/trades/log/traded-symbols/candles/attribution/day-context（Trade review）|
| `/research/*` | Research（新增） | strategies、saved-views、trials、sweep、validate、promote |
| `/monitor/*` | Monitor | performance、positions、signals、risk（**全 stub 至 M4**，§5.4）；`/monitor/fleet*` 艦隊板；`/monitor/board` 運行看板（**已 LIVE**：runs 表生命週期 + 審判庭 verdict，A2）|
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
| 404 | `NOT_FOUND` | 資源不存在 | `{resource, id}` | `/runs/{id}`、`/research/promote/{strategy_id}`、compare baseline |
| 400 | `BAD_REQUEST` | 請求語意錯（如 trade record 缺 key）| `{hint}` | `/metrics/trades` |
| 401 | `UNAUTHORIZED` | 缺/錯 Bearer（§4）| `null` | 全端點（單人防呆）|
| 504 | `QUERY_TIMEOUT` | 後端查詢/計算逾時 | `{op}` | 重查詢（sweep heatmap、telemetry）|
| 500 | `INTERNAL` | 未預期錯誤 | `null`（**不洩漏 stack/秘密**，`rules/security.md`）| 全域 fallback |

> ✅ **已實作（8.H.1）**：handler 依 status 對映上表 `code`（`_STATUS_TO_CODE`），422 填 `detail=[{loc,msg}]` 陣列（保留人類可讀 `message`），dict `HTTPException.detail` 透傳為結構化 `detail`，未映 status 落 `INTERNAL`。

> **🔧 錯誤語意統一（2026-07-03，contract-standardization WP／A4）**：
>
> - **未知資源 → 404 everywhere**：`GET /system/bundles/{id}/quality`（先前 `200+data:null`）、job 輪詢 `GET /system/ingest/{job_id}/status`、`GET /research/sweep/{id}/status`、`GET /runs/{job_id}/log`、`GET /system/universe/build/{job_id}/status`（先前 `200+pending`——§5.2 早已要求 404）皆改回 **404**。前端 job pollers 於 error 態停止輪詢並顯示錯誤，不再無限 pending。
> - **未知具名資源 → 404**：`/gate/spec?strategy=`、`POST /gate/evaluate`（未知 strategy，先前 400）與 `POST /research/workflows/{workflow}`（未知 workflow）統一為 **404**。
> - **domain `ValueError` → 400**：`POST /research/promote/{id}`（非法 skip/regress/未知 stage，先前 422）改為 **400 BAD_REQUEST**（422 專留 schema 驗證）。`promote` 為純 ordered stage machine，所有 `ValueError` 皆屬非法轉移。**409 `IS_GATE_NOT_PASSED`** 為 gate-blocked advance 之保留 backstop（目前 stage machine 不做 IS-gate 檢查故未觸發；前端已用 `validation_status` 先行 gate）。
> - **結構化 404 `detail`**：主要 404 raiser（runs / runs candles / workflows / gate / bundles quality / job polls）一律回 `detail={"resource": "...", "id": ...}`（§2 承諾落地）。

### §2.1 domain 狀態詞彙（非 HTTP 錯誤碼）

回應 `data` 內的 domain 狀態字串（前端 switch/badge 用），與 §2 的 HTTP `error.code` 正交：

| 詞彙 | 值 | 出現處 |
| :--- | :--- | :--- |
| **GateStatus**（審判庭 verdict）| `PASS` / `FAIL` / `INCOMPLETE` | `POST /gate/evaluate`、run record `gate_status` |
| **validation_status**（IS 驗證）| `draft` / `is_pass` / `is_fail` | `/research/strategies`、`/research/validate/{id}/gate-state` |
| **promotion stage**（晉升階）| `draft` / `paper` / `live` | `/research/promote/{id}` |
| **TruthVerdict**（真相閘 band，A5）| `REAL` / `PAPER_WATCH` / `REJECTED` / `INCOMPLETE` | `/runs/{id}/report` 的 `verdict.truth_gate.band`（觀察艙 DSR band；非新端點）|

---

## §3 分頁（offset，單一）

**全系統唯一分頁方案 = offset**（沿用 v0.6 `/runs`，零遷移）：

- Query：`?page=<int ge1, default 1>&limit=<int 1..500, default 50>`（1-based）。
- 切片：`start = (page-1)*limit; items = records[start:start+limit]`。
- Meta：`meta = {"total": <int>, "page": <int>, "limit": <int>}`。
- **不提供 cursor/keyset**；若日後 telemetry 大表證明 offset 痛，**per-endpoint** 再加 keyset，**不全站雙軌**（ADR-021）。

需分頁的端點（§6 標 `📄`，共 8 條）：`GET /runs`、`GET /research/strategies`、`GET /monitor/board`、`GET /monitor/signals`、`GET /monitor/fills`、`GET /monitor/risk/events`、`GET /system/alerts/history`、`GET /system/bundles`。其餘為固定/小集合，不分頁。

> **統一標準（2026-07-03，contract-standardization WP／A3）**：所有 list 端點簽章一律 `page: int = Query(1, ge=1)` + `limit: int = Query(50, ge=1, le=500)`，回 `envelope.page_meta()`（`{total, page, limit}` 回填**呼叫端實際值**，不再硬編 `{1,50}`）。`GET /monitor/signals` 與 `GET /monitor/risk/events` 先前「接受 `page` 但忽略」的 bug 已改為真正 offset 切片；`GET /monitor/board`、`GET /monitor/fills` 補上 `page`。所有 `le=200` 上限升為 `le=500`。

---

## §4 認證（standalone = localhost-only 綁定，[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)）

> **🔧 2026-07-02 裁決（[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)，審查缺陷 #20）**：本節原承諾「M3.0 起全端點 static Bearer」為**三方矛盾**——後端 `api/` 零實作、前端 `http.ts` 硬編碼 `?? 'dev-token'`。依 [PRD v4.0](./02_project_brief_and_prd.md) §2.3 standalone 假設（單機、內網 localhost、無多人協作）裁決：**採 localhost-only 綁定為唯一安全邊界，移除 Bearer 承諾**（降為 M5 遠端存取時重議）。理由：20 行 static Bearer 對 localhost 威脅模型不增實質安全（能存取 `127.0.0.1` 者已擁有這台機器）、卻增加每個 client 的摩擦；loopback bind 才是真正的邊界。

**standalone 現行機制（ADR-031）：**

- **邊界**：後端 API **MUST 綁 `127.0.0.1`**（loopback），前端走 vite proxy 同機存取，無公網暴露。綁定本身即安全邊界，**無 app 層 auth**。
- **前端**：`http.ts` 的 `?? 'dev-token'` 為**無害殘留**（後端不檢查、不授予任何權限）；header slot 保留與否為前端清理 follow-up，非 auth 前置。
- **秘密（不放鬆）**：`FINLAB_API_TOKEN`、`DISCORD_*`、`INFLUX_*` **僅後端持有，絕不出現在任何回應或前端 bundle**（`rules/security.md`）；`/system/alerts/channels` 回傳一律 **遮罩**（`bot_token` → `"***"`）。
- **`401 UNAUTHORIZED`（§2）**：保留於錯誤碼 enum，供 M5 遠端存取啟用 auth 時使用；standalone 期不觸發。

> **M5 遠端存取重議項**：若需跨機/遠端存取，於 M5 重開 auth 決策——reverse-proxy guard 或 static Bearer dependency（+ 環境變數 + CORS）。本節不預先實作，避免 gold-plating（ADR-031 §4 follow-up）。
>
> **~~原承諾（已由 ADR-031 移除，保留為脈絡）~~**：~~M3.0 加 Bearer dependency + 環境變數，所有非 `/health` 端點要求 Bearer。~~

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
| 運行看板 | 5 | `/monitor/board`（runs 表；`meta.ttl=5` 驅動 staleTime，FE 另以 10s `refetchInterval` 輪詢）| monitor_board |
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

### §5.4 stub 慣例 + `data_source` 詞彙（單一 enum）

**決策（ADR-021）**：Monitor B/C/D 無 live 資料源（無 daemon 託管 PaperBroker/CircuitBreaker；`upsert_signals/orders/fills` 是 M4 `NotImplementedError`）。在 M4 producer 完成前，`/monitor/*` 端點以 **typed 空 envelope** 上線（讓前端對著穩定 shape 建頁）：

```jsonc
{ "success": true, "data": [], "error": null,
  "meta": { "data_source": "pending", "ttl": 300 } }
```

- **絕不回假數據/fixture 數字**（違反 `21 §8.8` single-truth）。
- 前端據 `meta.data_source==="pending"` 渲染明確空狀態，**非 0 值**（`isPending` 精確比對）。
- M4 swap-in 真 producer，**契約 shape 不變**。

**`data_source` 詞彙表（2026-07-03，contract-standardization WP／A1）**：後端把先前散落的 7 個 uncoordinated 字面量（含已淘汰的 `pending_m4`）收斂成 `api/envelope.py::DataSource` 單一 enum；drift-gate Check D（§9）static-scan 每個 `data_source` 賦值必為 enum 成員。

| token | 語意 | FE `isPending`/`isPartial` |
| :--- | :--- | :--- |
| `pending` | 端點尚無 producer（typed 空 envelope；**取代舊 `pending_m4`**，一個概念一個 token）| `isPending` |
| `partial` | 真實資料帶已揭露缺口（如 WFA folds 已出、per-fold scatter 仍 parquet-gated）| `isPartial`（照常渲染 live，另標缺口）|
| `timescaledb` | live paper/live 遙測（TimescaleDB）| live |
| `watch_registry` | event-sourced 觀察艙 berth（JSONL registry）| live |
| `parquet_scan` | bundle manifest 掃描（parquet 快取）| live |
| `ledger` | runs 帳本投影（`/home/research-status`、`/home/recent`）| live |
| `catalog` | curated FinLab dataset 字典（`/system/datasets`）| live |

- **pending 預設 ttl 統一為 300**（`envelope.pending()` 與 monitor/system `_stub` 同一預設；A2）——一個概念一個預設值。
- **已移除的 `not_found` token**：`GET /system/bundles/{id}/quality` 未知 id 先前回 `200 + data:null + data_source="not_found"`，A4 改為 **404**（§2）。

---

## §6 端點 registry（machine-checkable，全 83 operations / 77 paths）

> **🔧 2026-07-03 全面 reconcile（contract-standardization WP／A6）**：§6 重寫為**機讀 inventory**——下表由 live OpenAPI 逐條列出，drift-gate **Check C**（§9）以 `<!-- drift:endpoint-inventory -->` sentinel 解析本表並與 live spec 逐 `{method, path}` 比對，不一致即紅燈。修正歷史 rot：`preset`→`strategy` 欄位、phantom 端點（validate is/oos/signoff、promote advance/demote/retire/observation、sweep heatmap、traded-symbols/attribution/day-context、runs/trials、`POST /research/strategies`）已移除；補上真實存在但先前漏列者（`/runs/async`、`/runs/{id}/log`、`/runs/{id}/report`、`/runs/{id}/notebook`、`/system/datasets`、`/system/universe/build*` 等）。**逐端點 request/response shape 一律以 OpenAPI 為機器真相（§7）**，本表只釘死「哪些 operation 存在」——移除先前 drift 成災的 per-endpoint req→resp 欄。

> **歷史決策（保留脈絡）**：`/presets`→`/strategies`（[ADR-028](./adrs/ADR-028-strategy-dispatch-contract.md)）；研究工作流 dispatch（[ADR-029](./adrs/ADR-029-research-workflow-standardization.md)）；Paper-Watch 觀察艙 GUI（[ADR-033](./adrs/ADR-033-paper-watch-tier.md)，已 LIVE，讀 event-sourced JSONL 非 daemon telemetry）；Run-Report v1 一次聚合（`/runs/{id}/report`＋`/notebook`，純函式 `validation/report.py`／`research/notebook_export.py`）。

> **圖例**：`📄` = 分頁（§3 標準）。`⚠️` no-FE = 後端已上線但目前**尚無前端消費者**——這些是**功能**（如 `/metrics/*`、`/gate/evaluate`、editable alerts、`/runs/{id}/report`），**不刪**，只誠實標記等待接線。共 43 條已接前端、40 條 no-FE。逐頁 `[DATA & API]` 需求見 `web_design/pages/*`；里程碑見 §8 → 16 WBS。

<!-- drift:endpoint-inventory:begin -->
| Method | Path | Zone | 📄 | no-FE |
| :--- | :--- | :--- | :---: | :---: |
| GET | `/health` | Global |  | ⚠️ |
| POST | `/gate/evaluate` | Research |  | ⚠️ |
| GET | `/gate/spec` | Research |  |  |
| POST | `/metrics/summary` | Research |  | ⚠️ |
| POST | `/metrics/trades` | Research |  | ⚠️ |
| GET | `/research/candidates` | Research |  | ⚠️ |
| GET | `/research/candidates/{candidate_id}` | Research |  | ⚠️ |
| POST | `/research/candidates/{candidate_id}/decision` | Research |  | ⚠️ |
| POST | `/research/candidates/{candidate_id}/select-live-oos` | Research |  | ⚠️ |
| GET | `/research/evaluations/{evaluation_id}` | Research |  | ⚠️ |
| GET | `/research/evaluations/{evaluation_id}/report` | Research |  | ⚠️ |
| GET | `/research/live-oos/queue` | Research |  | ⚠️ |
| GET | `/research/profiles` | Research |  | ⚠️ |
| GET | `/research/profiles/{name}` | Research |  | ⚠️ |
| GET | `/research/promote/{strategy_id}` | Research |  |  |
| POST | `/research/promote/{strategy_id}` | Research |  |  |
| GET | `/research/promote/{strategy_id}/audit` | Research |  |  |
| GET | `/research/saved-views` | Research |  | ⚠️ |
| POST | `/research/saved-views` | Research |  | ⚠️ |
| GET | `/research/strategies` | Research | 📄 |  |
| GET | `/research/strategies/{strategy_id}/versions` | Research |  | ⚠️ |
| POST | `/research/sweep` | Research |  |  |
| GET | `/research/sweep/{job_id}/status` | Research |  |  |
| POST | `/research/trials/increment` | Research |  | ⚠️ |
| GET | `/research/universe-filters` | Research |  | ⚠️ |
| GET | `/research/validate/{run_id}/gate-state` | Research |  |  |
| GET | `/research/validate/{run_id}/health` | Research |  | ⚠️ |
| GET | `/research/validate/{run_id}/redline` | Research |  | ⚠️ |
| GET | `/research/validate/{run_id}/wfa` | Research |  |  |
| GET | `/research/workflows/{strategy}` | Research |  | ⚠️ |
| POST | `/research/workflows/{workflow}` | Research |  | ⚠️ |
| GET | `/runs` | Research | 📄 |  |
| POST | `/runs` | Research |  |  |
| POST | `/runs/async` | Research |  | ⚠️ |
| GET | `/runs/compare` | Research |  |  |
| GET | `/runs/estimate` | Research |  |  |
| POST | `/runs/tag` | Research |  | ⚠️ |
| GET | `/runs/{job_id}/log` | Research |  | ⚠️ |
| GET | `/runs/{run_id}` | Research |  |  |
| GET | `/runs/{run_id}/candles` | Research |  |  |
| GET | `/runs/{run_id}/equity` | Research |  |  |
| GET | `/runs/{run_id}/notebook` | Research |  | ⚠️ |
| GET | `/runs/{run_id}/report` | Research |  | ⚠️ |
| GET | `/runs/{run_id}/trades` | Research |  |  |
| GET | `/strategies` | Research |  |  |
| GET | `/monitor/board` | Monitor | 📄 |  |
| GET | `/monitor/correlation` | Monitor |  | ⚠️ |
| GET | `/monitor/fills` | Monitor | 📄 |  |
| GET | `/monitor/fleet` | Monitor |  |  |
| POST | `/monitor/fleet/{strategy_id}/action` | Monitor |  | ⚠️ |
| GET | `/monitor/performance/benchmark` | Monitor |  | ⚠️ |
| GET | `/monitor/performance/equity` | Monitor |  |  |
| GET | `/monitor/performance/kpi` | Monitor |  |  |
| GET | `/monitor/performance/monthly` | Monitor |  | ⚠️ |
| GET | `/monitor/portfolio-summary` | Monitor |  |  |
| GET | `/monitor/positions/concentration` | Monitor |  | ⚠️ |
| GET | `/monitor/positions/industry-allocation` | Monitor |  | ⚠️ |
| GET | `/monitor/positions/kpi` | Monitor |  | ⚠️ |
| GET | `/monitor/positions/prices` | Monitor |  | ⚠️ |
| GET | `/monitor/positions/snapshot` | Monitor |  |  |
| GET | `/monitor/risk/events` | Monitor | 📄 | ⚠️ |
| GET | `/monitor/risk/events/{event_id}` | Monitor |  | ⚠️ |
| GET | `/monitor/risk/mdd-trend` | Monitor |  | ⚠️ |
| GET | `/monitor/risk/metrics` | Monitor |  |  |
| GET | `/monitor/signals` | Monitor | 📄 |  |
| GET | `/monitor/signals/funnel` | Monitor |  | ⚠️ |
| GET | `/monitor/signals/timeline` | Monitor |  | ⚠️ |
| GET | `/monitor/strategies` | Monitor |  |  |
| GET | `/monitor/watch` | Monitor |  |  |
| POST | `/monitor/watch/{strategy}/pause` | Monitor |  |  |
| POST | `/monitor/watch/{strategy}/resume` | Monitor |  |  |
| GET | `/system/alerts/channels` | System |  |  |
| PUT | `/system/alerts/channels` | System |  | ⚠️ |
| GET | `/system/alerts/history` | System | 📄 | ⚠️ |
| POST | `/system/alerts/history/{event_id}/ack` | System |  | ⚠️ |
| GET | `/system/alerts/rules` | System |  |  |
| POST | `/system/alerts/rules` | System |  | ⚠️ |
| PUT | `/system/alerts/rules` | System |  | ⚠️ |
| POST | `/system/alerts/test` | System |  | ⚠️ |
| GET | `/system/bundles` | System | 📄 |  |
| GET | `/system/bundles/{bundle_id}/quality` | System |  | ⚠️ |
| GET | `/system/datasets` | System |  | ⚠️ |
| POST | `/system/ingest` | System |  |  |
| GET | `/system/ingest/{job_id}/status` | System |  |  |
| POST | `/system/risk/evaluate` | System |  | ⚠️ |
| GET | `/system/risk/spec` | System |  |  |
| POST | `/system/universe/build` | System |  |  |
| GET | `/system/universe/build/{job_id}/status` | System |  |  |
| GET | `/home/fleet` | Home |  |  |
| GET | `/home/recent` | Home |  |  |
| GET | `/home/research-status` | Home |  |  |
| GET | `/home/system-health` | Home |  |  |
<!-- drift:endpoint-inventory:end -->

### §6 zone 摘要（prose，shape 見 OpenAPI）

- **Research（`/runs`、`/gate`、`/metrics`、`/strategies`、`/research/*`）**：run 帳本（list/get/compare/trigger/async）、run 子資源（equity/trades/candles/report/notebook/log）、審判庭（gate spec/evaluate）、指標計算機、策略 catalog/roster、saved-views/trials、sweep（async job）、validate（gate-state/health/wfa/redline）、promote（stage machine + audit）、workflows（doe/go_gates/truth_gate/paper_replay/build_universe dispatch）。**canonical id = `stock_id`**（`/runs/{id}/candles?stock_id=`，A5；`?symbol=` 已淘汰）。
- **Monitor（`/monitor/*`）**：多數 M4 deferred-stub（`data_source="pending"`，§5.4）；**例外已 LIVE**：`/monitor/board`（runs 表看板）、`/monitor/watch*`（觀察艙）、`/monitor/performance/{equity,kpi}` + `/monitor/{fleet,portfolio-summary,positions/snapshot,signals,fills}`（有 telemetry 時走 `timescaledb`，否則 pending fallback）。
- **System（`/system/*`）**：risk spec/evaluate、alerts（rules/channels/history/test，含 secret 遮罩 §4）、bundles（真實 manifest 掃描）+ bundle quality（未知 id → 404，A4）、datasets（FinLab 資料字典）、ingest / universe build（async job + status poll，未知 job → 404，A4）。
- **Home（`/home/*`）**：BFF 跨區聚合（cockpit 首屏）。`research-status`／`recent` = 真實 ledger 投影（`data_source="ledger"`）；`fleet`／`system-health` = M4 pending stub。各來源端點仍獨立存在，`/home/*` 不取代它們。

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
| **M3.0** | 契約合一閘（零新邏輯）| 升 `envelope.py`（error 物件）、修 `/runs` window bug、接 openapi-typescript（~~加 Bearer~~ → 移除，[ADR-031](./adrs/ADR-031-standalone-auth-decision.md) localhost-only）| （契約+型別 scaffold）|
| **M3.1** | 便宜 config/catalog 讀路由 | `/research/universe-filters`、`/runs/estimate`、`/system/risk/*`、`/system/alerts/{rules,channels,test}`、`/strategies`（catalog + config schema，取代 `/presets` enrich）| run_02、sys_alerts(讀)、mon_d(config)|
| **M3.2** | 暴露已算出的 series + 逐股 review | `/runs/{id}/equity`、`/runs/{id}/trades?symbol`、`/runs/{id}/candles?symbol`（K 線讀 parquet + marker 重推，ADR-034）、compare `?run_ids`、`/runs/{id}/{traded-symbols,attribution,day-context}` | run_04/05、mon_a(回測半)、trade_review(K線 ✅、歸因除外)|
| **M3.3** | strategy registry + 側存 + Home recent | `/research/strategies*`、`/research/saved-views`、`/runs/tag`、`/home/recent` | run_01/03、home(recent)|
| **M3.4** | trials/DSR guardrail + Home 研究狀態 | `/runs/trials`、`/research/trials/increment`、`/home/research-status` | run_03/05、home(研究半)|
| **M3.5** | async job（CRITICAL #2）+ bundle/DQ | `POST /runs`(async)、`/runs/{id}/log`、`/research/sweep/*`、`/system/{bundles,ingest}*` | run_06、sys_data、run_02(async)|
| **M3.6** | validation+promotion service（CRITICAL #3）| `/research/validate/*`、`/research/promote/*` | run_07/08 |
| **M4** | live-telemetry daemon（CRITICAL #1, needs-DATA）| 全 `/monitor/*`（含 `/monitor/fleet*`）、`/home/{fleet,system-health}`、`/research/promote/{id}/observation`、editable alerts | mon_a/b/c/d、monitor_fleet、home(live 半)、sys_alerts(編輯)|

---

## §9 契約治理（防 drift）

> 本專案有 doc-drift 慣性病史（曾需 5 個 sweep commit、39 commits ahead）。契約**必須**靠機器檢查鎖住。

- **新增/改 API endpoint** → 同一 commit 改本檔 §6 registry（sentinel 表）+ 重生 OpenAPI + 更新 `16 WBS`（**建議**在 [`code-doc-sync.md`](../.claude/rules/code-doc-sync.md) 觸發表把「新 API endpoint」列指向「25 §6 + OpenAPI」；該規則檔屬 agent 設定，需使用者自行套用）。
- **CI drift check（`scripts/check_openapi_drift.py`，四檢查）**：
  - **Check A** — live FastAPI OpenAPI vs committed `frontend/openapi.json`（形狀真相）。
  - **Check B** — runs DDL vs `db_writer._RUNS_COLS`（欄位對齊）。
  - **Check C** — 本檔 §6 sentinel inventory 表 vs live OpenAPI 的 `{method, path}` 集合（**新，2026-07-03**；防 §6 宣告漂離機器真相——本專案的復發病灶）。
  - **Check D** — `api/routers/*.py` + `envelope.py` 每個 `data_source` 賦值必為 `DataSource` enum 成員（**新**；防 §5.4 的 uncoordinated 字面量重新滋生）。
  - 任一不一致 → exit 1 紅燈。
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
| `/api/research/compare`（research_05）| `/runs/compare`（**例外：非 `/research/compare`**；compare 屬 runs 子資源，泛則不適用）|
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
