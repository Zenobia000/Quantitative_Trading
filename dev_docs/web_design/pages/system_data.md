# Page Layer Spec — 資料管理 (System · Data Management)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.7 sitemap 系統區（`/system/data` bundle/ingest/品質檢查）+ §5.2 IA。
> 系統區第一頁。bundle_ref 快照回饋 New Run（§4.7 `data -.->|bundle_ref 快照| newrun`）。
> 繼承 Global v2.0（**Grok 單色 dark**：bg-base #0F0F0F / surface #1A1A1A / code #161616 / border #2A2A2A / 白環 focus / Geist Mono 數值 / 漲跌 ↑↓ 雙編碼）。

---

## [PAGE META]

- **page_name**: 資料管理 (Data Management)
- **route_path**: /system/data
- **page_type**: list + status
- **primary_goal**: 讓研究者管理資料 bundle 快照與 ingest（ETL）任務，掌握每個 bundle 的覆蓋範圍與品質狀態，作為 New Run「鎖資料快照 ref」的來源真相。
- **secondary_goal**: 暴露資料品質風險（缺漏 / 下市偏差 / look-ahead / 覆蓋率），在進回測前攔截污染來源。
- **target_users**:
  - 主要：量化研究者（選 bundle 餵 New Run）
  - 次要：運維者（盯 ETL/ingest 健康，對照 Grafana F–I）
- **entry_point**: 側邊導覽「系統 → 資料管理」；New Run 的 bundle 選單「管理 bundle」；Cmd-K「跳資料」。
- **expected_time_on_page**: 1–3 分鐘（掃 bundle 狀態 / 觸發 ingest / 看品質紅旗）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 5 個功能區塊。

1. **toolbar**
   - section_type: toolbar / action
   - section_purpose: 觸發 ingest、bundle 篩選/搜尋、手動 refresh。

2. **bundle_list**
   - section_type: data_table
   - section_purpose: 每列一個 bundle 快照（id / 日期範圍 / universe / 筆數 / 品質狀態 / 建立時間），供 New Run 引用。

3. **ingest_status**
   - section_type: status / progress
   - section_purpose: 進行中 / 最近 ingest（ETL）任務狀態、進度 banner 與 execution log。

4. **data_quality**
   - section_type: stats_cards + table
   - section_purpose: 選定 bundle 的品質檢查（覆蓋率 / 缺漏日 / 下市偏差 / look-ahead 防護 / 重複），紅旗以色+文字雙編碼。

5. **empty_state**
   - section_type: empty (FirstRunEmptyState 變體)
   - section_purpose: 零 bundle 時提供可複製 CLI ingest 指令 + 單一 CTA。

---

## [SECTION COMPONENT SPEC]

### Section: toolbar

- **layout**: 1-row horizontal toolbar，sticky top。
- **elements**:
  - IngestButton: Button Primary（白底 pill）/ required / 觸發新 ingest（開 config drawer：universe / 期間 / 來源）。
  - SearchInput: Input / optional / 依 bundle id / universe 過濾。
  - StatusFilter: SegmentedControl / optional / 全部 / ready / ingesting / failed / stale。
  - RefreshButton: IconButton / optional / 清快取重查。
- **states**:
  - default: 顯示全部 bundle；filter 全選。
  - loading: toolbar 可見，bundle_list 進 skeleton。
  - empty: filter 命中 0 → list 顯示「無符合條件的 bundle」（與全空 empty_state 區分）。
  - error: bundle 清單載入失敗 → inline error + 重試。
- **copy_constraints**: 按鈕 ≤ 6 字（「觸發 ingest」）；filter chip ≤ 6 字。

### Section: bundle_list

- **layout**: 全寬 DataTable，frozen first column（bundle id）；橫向捲動保欄位密度。
- **elements**:
  - BundleIdCell: Mono link / required / 點選展開 data_quality（同頁）。
  - DateRangeCell: Mono / required / 資料涵蓋起訖（ISO）。
  - UniverseCell: Text / required / universe 名稱 + 標的數。
  - RowCountCell: Mono number / required / 筆數（tabular-nums）。
  - QualityBadge: StatusBadge / required / ready / warning / stale（色 + 文字雙編碼）。
  - UseInRunButton: Button Ghost / optional / 「用於 New Run」→ `/research/runs/new?bundle=`。
- **states**:
  - default: 依建立時間倒序；ready bundle 可引用。
  - loading: 列 skeleton。
  - empty: 交由 empty_state（全空）。
  - error: 「bundle 載入失敗」+ 重試。
- **copy_constraints**: 欄標 ≤ 12 字；日期 ISO `YYYY-MM-DD`。

### Section: ingest_status

- **layout**: 全寬卡（進行中時顯示進度 banner，否則列最近任務）。
- **elements**:
  - JobStatusBadge: StatusBadge / required / queued / running / done / failed（色+文字雙編碼）。
  - ProgressBar: ProgressBar / required（running 時）/ 進度 + 已用時。
  - ExecutionLog: Code block（bg-code #161616 / Geist Mono / 可滾動）/ required（failed 時攤開）/ 錯誤定位。
  - RetryButton: Button / optional（failed 時）/ 重試 ingest。
- **states**:
  - default: 無進行任務 → 列最近 1–3 筆結果。
  - loading(running): 進度 banner + log。
  - error(failed): 攤開 log + 重試。
  - empty: 「尚無 ingest 紀錄」。
- **copy_constraints**: 狀態文案 ≤ 12 字；log 等寬截斷。

### Section: data_quality

- **layout**: 上 4-up 品質 KPI，下缺漏明細表（選定 bundle 後）。
- **elements**:
  - CoverageKpi: KPI Card / required / 覆蓋率 %（< 門檻轉 warning + 文字）。
  - MissingDaysKpi: KPI Card / required / 缺漏交易日數。
  - DelistBiasKpi: KPI Card / required / 下市偏差檢查（pass/fail + 文字）。
  - LookaheadKpi: KPI Card / required / look-ahead 防護（pass/fail + 文字）。
  - MissingTable: DataTable / optional / 缺漏/重複明細（日期 / 標的 / 類型，Geist Mono）。
- **states**:
  - default: 4 KPI + 明細；紅旗以色+文字雙編碼。
  - loading: KPI skeleton。
  - empty: 未選 bundle → 「選一個 bundle 查看品質」。
  - error: inline error + 重試。
- **copy_constraints**: KPI 標籤 ≤ 16 字；比率 1 位小數 %。

### Section: empty_state（FirstRunEmptyState 變體）

- **layout**: 置中大圓角卡（radius 12px）+ 1px border 無陰影。
- **elements**:
  - Headline: H2 / required / 「尚無資料 bundle，先 ingest」。
  - CliBox: Code block（Geist Mono / bg-code #161616 / 可複製）/ required / 真實 `bundle-ingest --universe ... --start ... --end ...` 指令。
  - PrimaryCta: Button Primary（白 pill）/ required / 「觸發 ingest」。
- **states**:
  - default: 引導卡 + CLI + 單一 CTA（無 loading/error）。
- **copy_constraints**: Headline ≤ 18 字；CLI 為真實可執行指令。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 載入 → 查 bundle 清單 → 有資料渲染 bundle_list；零資料渲染 empty_state。
2. 點 BundleIdCell → 展開 data_quality（同頁），懶載入該 bundle 品質。
3. 點 IngestButton → 開 config drawer 設定 → 提交 → ingest_status 顯示進度 banner，輪詢至 done/failed。
4. ready bundle 點 UseInRunButton → 跳 New Run 並預填 bundle ref（§4.7 bundle_ref 快照回饋）。
5. ingest 完成 → bundle_list 新增/更新該 bundle，品質重算。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | toolbar 單列；table 全欄 + frozen col；quality 右側展開 | sidebar 展開 |
| Tablet (768–1279px) | table 橫向捲動；quality 下方展開 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | toolbar 收合；table 橫向捲動保密度 | quality KPI 1 欄堆疊 |

### 資料更新策略

- bundle 清單快取 TTL 300s；page load / filter / refresh 觸發。
- ingest job 以輪詢或 SSE 更新 status（done/failed 終態停止）。
- data_quality 點選時懶載入。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: bundle 註冊表 + ingest job 記錄 + 品質檢查結果。
- **endpoints**:
  - GET `/api/system/bundles` — bundle 清單（id / range / universe / count / quality / created）。
  - GET `/api/system/bundles/{id}/quality` — 覆蓋率 / 缺漏 / 下市偏差 / look-ahead 明細。
  - POST `/api/system/ingest` — 觸發 ingest（body: universe / 期間 / 來源）→ 回 job_id。
  - GET `/api/system/ingest/{job_id}/status` — ingest 進度 + log。
- **error_cases**:
  - 網路錯誤：section 級 inline error + 重試。
  - ingest 失敗（job failed）：ingest_status 攤 log + 重試，非整頁 error。
  - 無資料（全空）：渲染 empty_state（非 error）。
  - 權限不足：導向登入。

---

## [EXCEPTION TO GLOBAL RULES]

無特殊例外，完全遵循 Global v2.0（Grok 單色 dark、flat 1px border #2A2A2A、Geist Mono 數值、白環 focus、漲跌/狀態雙編碼）。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（toolbar / bundle_list / ingest_status / data_quality / empty_state）功能正常。
- [ ] bundle_list 四態完備：default / loading / empty(filter 命中 0) / error；在 @<1024px 橫向捲動不轉 card。
- [ ] ingest_status 承接 queued/running/done/failed，failed 攤開 execution log 可重試。
- [ ] data_quality 4 KPI（覆蓋率/缺漏/下市偏差/look-ahead）以色+文字雙編碼標紅旗。
- [ ] ready bundle 可「用於 New Run」帶 bundle ref 跳轉（bundle_ref 快照回饋研究區）。
- [ ] 零 bundle 渲染 empty_state（可複製真實 CLI ingest 指令 + 單一 CTA）。
- [ ] StatusBadge 色+文字雙編碼；ingest 輪詢至終態。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環 rgba(245,245,245,.7)。
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影。
