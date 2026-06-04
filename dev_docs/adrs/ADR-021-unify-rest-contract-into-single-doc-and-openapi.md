# ADR-021: 前後端 REST 契約合一（單一契約文件 25 + OpenAPI 為機器真相）

> **狀態：** 已接受 | **日期：** 2026-06-04 | **決策者：** Self
> **相關：**
> - [ADR-015](./ADR-015-dashboard-design-system-and-react-upgrade.md) §4/§5（儀表板 React 升級「新增 REST API 契約」行動項）— 本 ADR **supersede** 其「契約落 21」的指派。
> - [ADR-018](./ADR-018-monitoring-to-research-loop-pivot.md) §影響範圍（「`21_data_contract.md` 新增 runs/validation API 契約」「`06` 新增 endpoints」）— 本 ADR **supersede** 其契約落點分裂的隱含結果。
> - 落地真相源：**`25_fe_be_rest_contract.md`**（新建，契約唯一真相源）；`12_frontend_architecture_specification.md` §7（型別生成 bridge）；`backtest_platform/src/backtest_platform/api/`（FastAPI 實作）。
> - 治理規則：[`.claude/rules/code-doc-sync.md`](../../.claude/rules/code-doc-sync.md)（觸發表新增「新 endpoint → 25 + OpenAPI」）。

---

## 1. 背景與問題

- **上下文**：v0.6 後端 FastAPI 已落地 **11 條路由**（`/runs`、`/gate`、`/metrics`、`/presets` + `/health`），envelope `{success,data,error,meta}` 已就位。`web_design/` 的 **14 頁**（Research 8 / Monitor 4 / System 2）各帶 `[DATA & API]` 端點需求，共需約 **71 條端點**。前端（React，M3 目標）尚未實作。
- **問題**：前後端之間**沒有單一、已對齊的 REST 契約**。契約**分裂於三處，且四項慣例互相衝突**：

  | 衝突項 | `06 §9`（已實作研究面）| `21 §8`（Monitor A–E）| per-page `[DATA & API]` |
  | :--- | :--- | :--- | :--- |
  | base-path | 裸 root `/runs` | `/api/dashboard` | 發明 `/api/research/*`、`/api/performance/*` |
  | envelope.error | 字串 | 物件 `{code,message,detail}` | — |
  | 分頁 | offset `page/limit` | keyset `cursor` | — |
  | auth | 無（延 M5）| Bearer | 單人防呆 401/403 |

- **分裂成因（非設計，是 org/ADR 縫）**：ADR-015 把 A–E 儀表板契約指派落 `21 §8`，ADR-018 的研究迴圈契約半邊卻隨 v0.6 程式碼落在 `06 §9`，兩者沿 ADR 邊界各長一半，**沒有任何文件把兩者調和**。per-page 規格則由前端視角各自發明路徑。
- **觸發事件**：2026-06-04 透過 workflow 做契約優先盤點（FE 頁面需求 ↔ FastAPI 供給 ↔ 既有契約），對抗式驗證 **12/12 確認缺口為真**，並一致揪出最高風險：**前端一旦照 per-page 路徑生成（Lovable/React），會對著後端不存在、彼此也不一致的端點寫**。54 條端點未實作、4 條 partial。

## 2. 核心結論（盤點摘要）

1. **缺口三分決定排序**：`ready`（後端能力已存在、只缺接線，如 config catalog、已算出但未持久化的 `run_is_returns`/per-trade）／`needs-work`（需新後端邏輯，如 strategy registry、async job、validation+promotion service）／`needs-data`（需新資料源，整個 Monitor 區無 live 遙測 producer，`upsert_signals/orders/fills` 是 M4 `NotImplementedError`）。
2. **裸 root 已是既成事實**：11 條已實作路由掛在裸 root，無 `/api` 前綴。沿用 = 零遷移；改前綴 = 破壞 userspace。
3. **OpenAPI 已免費存在**：FastAPI 於 `/docs` 自動輸出 OpenAPI，可作機器可驗證的契約對應真相——但只描述已實作的 11 條，**不能取代宣告 71 條意圖的規劃文件**。

## 3. 考量的選項

### 選項一：硬併進 `06 §9` 或 `21 §8`
- **描述**：把三處契約全併入既有某一份。
- **缺點**：`06` 本質是後端 CLI + Python API spec（HTTP 只是其中一節）；`21` 本質是資料層 DDL 契約（REST 是 §8 bolt-on）。併入任一者都把「契約」綁在錯誤的抽象層，分裂縫只是換位置，未消除。**拒絕**。

### 選項二：純 code-first，OpenAPI 即唯一契約
- **描述**：不寫散文契約，FastAPI `/docs` 即真相。
- **缺點**：54 條端點還沒 code，`/docs` 只描述已實作 11 條；前端會對著缺 ~50 端點的 phantom 型別寫。團隊的 dev_docs 是規劃真相源，純 code-first 失去「先訂契約再實作」的能力。**拒絕**。

### 選項三：新建單一契約文件 25 + ADR + OpenAPI 機器真相 ★採納
- **描述**：建 `25_fe_be_rest_contract.md` 為契約唯一真相源，釘死單一 envelope / 單一錯誤碼 enum / 單一分頁 / 單一 base-path / 單一 auth / realtime 協定 / 71 端點 registry / 型別生成 bridge。`06 §9`、`21 §8`、`20`、`12` 加 banner 降為 feeder by reference。FastAPI `/docs` 的 OpenAPI 為機器可驗證對應，CI diff 對齊。
- **優點**：尊重既有編號文化（25 接續 24）；滿足 code-doc-sync「新 endpoint → 契約文件」觸發；`06 §9`/`21 §8` 降級不刪除（never break userspace）；OpenAPI 落地驗證鎖 drift。
- **成本**：新增一份大文件 + 4 份 banner 編輯 + 觸發表更新。一次性，可控。

## 4. 決策

**選擇：選項三。** 確立六項決策（細節落 `25_fe_be_rest_contract.md`）：

1. **契約家** = 新建 `25_fe_be_rest_contract.md`，為前後端 REST 契約**唯一真相源**；FastAPI `/docs` OpenAPI 為機器可驗證對應真相。`06 §9` / `21 §8` / `20` / `12` 降為 feeder by reference。
2. **envelope** = 沿用已實作 `{success,data,error,meta}`，**`error` 由裸字串升級為結構化 `{code,message,detail}`**（向後相容：`fail()` 簽章不變、預設 `code`；`app.py` exception handler 改一次）。
3. **錯誤碼** = 單一 enum：`VALIDATION_ERROR`(422)、`IS_GATE_NOT_PASSED`(409)、`OOS_VAULT_LOCKED`(423)、`NOT_FOUND`(404)、`BAD_REQUEST`(400)、`UNAUTHORIZED`(401)、`QUERY_TIMEOUT`(504)、`INTERNAL`(500)。HTTP status 與 code 一對一。
4. **分頁** = **offset `page/limit`**（沿用 v0.6，零遷移）。**不全站雙軌**；日後 telemetry 大表若需 keyset，per-endpoint 再加。
5. **base-path** = **裸 root 無 `/api`、無 `/v1` 路徑版本**；五前綴：`/runs|/gate|/metrics|/presets`（已實作）、`/research/*`、`/monitor/*`、`/system/*`、`/health|/ws/*`。per-page 發明路徑全 reconcile（25 附錄 A）。
6. **auth** = **單人 static Bearer**（day-one 預留 header slot），秘密僅後端持有、回應遮罩；`/health` 永遠開放。**realtime** = HTTP polling + `meta.ttl`，長任務 poll-status（終態 done/failed），**唯一 WS** `/ws/positions/live`（M5）；Monitor 區 M4 前以 typed 空 envelope（`data_source:"pending_m4"`）stub，**絕不假數據**。**型別生成** = `openapi-typescript`，gate 在契約 union 進 app 之後。

**落地節奏（鐵律：契約合一閘 M3.0 是後續一切的前置）**：便宜 `ready` 工作 front-load（M3.1–M3.4），三個 CRITICAL blocker（async job M3.5、validation/promotion M3.6、live-telemetry M4）押後；Monitor 區因 ADR-018 已降級，排最後。詳見 `25 §8` + `16 WBS`。

## 5. 後果

### 正面
- 前端可對著**單一、穩定、機器可驗證**的契約生成型別與頁面，消除最高 drift 風險。
- 11 條已實作路由零遷移；envelope error 升級向後相容，不破壞既有測試。
- OpenAPI CI diff 把契約治理從「人工紀律」升為機器強制，對症本專案 doc-drift 慣性病史。
- `06`/`21`/`20`/`12` 各守其本分（CLI spec / DDL / 面板 data-needs / 前端 stack），不再越界宣告契約。

### 負面 / 成本
- 多一份需維護的大文件（25）；每次新 endpoint 必同步 §6 registry + OpenAPI（已寫入 code-doc-sync 觸發表）。
- `error` 字串→物件需改 `envelope.py` + 兩個 exception handler + 加 regression test（M3.0）。

### 影響範圍
- **新增**：`25_fe_be_rest_contract.md`、本 ADR。
- **banner 降級（不改內容）**：`06 §9`（→「v0.6 已實作子集，契約見 25」）、`21 §8`（→「Monitor A–E data-source map，契約 shape 見 25」）、`20`（→「面板 data-needs，非 REST shape」）、`12 §7`（契約源 21→25、envelope 標籤 `pagination`→`meta`、釘 openapi-typescript）。
- **治理（建議，待使用者套用）**：`.claude/rules/code-doc-sync.md` 觸發表「新 API endpoint」→ 加「25 §6 registry + 重生 OpenAPI」（規則檔屬 agent 設定，本批未自動改）。
- **狀態真相源**：`16_wbs_development_plan.md` 加 M3.0–M4 契約落地里程碑。
- **程式碼（後續 M3.0）**：`api/envelope.py`（error 物件）、`api/app.py`（handler + Bearer dep）、`api/routers/runs.py`（修 `is_start/is_end` window null bug）。

### 重新評估觸發
- 若 offset 分頁在 telemetry 大表證明痛 → per-endpoint 加 keyset（不全站改）。
- 若單人 + 內網使 Bearer 成純負擔 → 降為 reverse-proxy guard，但 header slot 保留。
- 若 OpenAPI CI diff 維護成本過高 → 退為 PR checklist 人工核對（但 25 §6 仍為真相源）。

## 6. 執行計畫

1. ✅ 本 ADR 記錄合一決策 + 盤點證據（workflow `wf_e27bec66-9c6`）
2. ✅ 新建 `25_fe_be_rest_contract.md`（§1–§9 + 附錄 A）
3. ✅ `06 §9` / `21 §8` / `20` / `12 §7` 加降級 banner
4. ✅ `16 WBS` 加里程碑；`INDEX.md` 加 25 + ADR-021（⏳ `code-doc-sync.md` 觸發表更新待使用者套用，§5 影響範圍）
5. ⏳ M3.0（契約合一閘，後續 PR）：`envelope.py` error 物件 + `app.py` handler/Bearer + 修 `/runs` window bug + 接 openapi-typescript + regression test

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-04 | Self | 初版 — 三處分裂 REST 契約合一至 doc 25 + OpenAPI 機器真相；envelope error 字串→物件、offset 分頁、裸 root、single-user Bearer、polling+單一 WS、Monitor stub；supersede ADR-015/018 契約落點指派 |
