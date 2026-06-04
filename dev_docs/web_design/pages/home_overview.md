# Page Layer Spec — 首頁 · 控制塔 (Home · Overview Cockpit)

> 來源：補強需求（缺首頁 + 多策略艦隊總覽）；對齊 `03_uiux_benchmark_and_reinforcement_plan.md` §4.7 IA（三區）+ Cmd-K 全域。
> 平台落地頁（root `/`）：開啟即見的跨三區控制塔，回答「我現在該看什麼」。
> 繼承 Global v2.0（**Grok 單色 dark**：bg-base #0F0F0F / surface #1A1A1A / border #2A2A2A / 白環 focus / Geist Mono 數值 / 漲跌 ↑↓ 雙編碼）。
> **狀態**：M3 目標 spec（前端未實作）；artefact 僅 page 規格，assembly 隨 React 化再產出。

---

## [PAGE META]

- **page_name**: 首頁 · 控制塔 (Home · Overview Cockpit)
- **route_path**: /
- **page_type**: dashboard (landing)
- **primary_goal**: 開啟平台即在單一畫面總覽三區狀態——策略艦隊健康（live/paper）、研究迴圈進度、系統健康——並以退化示警引導下一步動作，當研究者/操盤手的每日進場入口。
- **secondary_goal**: 作為「管理多隻策略（像管理員工）」的最高層入口，退化策略一眼標紅 + 直達降級/換掉動作（深度看板在 `/monitor` Fleet）。
- **target_users**:
  - 主要：量化策略操盤手 / 研究者（單人，每日開場巡檢 + 決定今天做什麼）
  - 次要：風控視角（掃 live 策略健康與告警）
- **entry_point**: 開啟平台預設落地；側邊導覽「首頁」/ Logo；Cmd-K「回首頁」。
- **expected_time_on_page**: 30 秒–2 分鐘（掃艦隊健康 + 研究/系統狀態 → 分流到對應 zone）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 6 個功能區塊。

1. **command_hero**
   - section_type: hero / command
   - section_purpose: 常駐 Cmd-K 入口 + 全域搜尋 + 快速動作（New Run / 跳 Runs / 看艦隊）+ 一句話階段狀態（如「M0 進場重設中，IS gate FAIL」）。

2. **fleet_strip**
   - section_type: stats / roster（艦隊概覽）
   - section_purpose: 所有 live/paper 策略一列一隻——stage badge + 健康 badge + 今日 P&L / Sharpe / MDD；退化者標紅 + 示警 → 直達 Fleet 看板降級/換掉。

3. **research_status**
   - section_type: stats
   - section_purpose: 研究迴圈進度——進行中 run（queued/running）、IS gate 卡在哪條、power gauge 三軸、累計試驗數 / DSR。

4. **system_health**
   - section_type: stats
   - section_purpose: 系統健康——資料新鮮度（最新 bundle / ingest）、近期 Discord 告警（三級計數）、FinLab API quota 剩餘、Grafana F–I 連結。

5. **recent_activity**
   - section_type: list
   - section_purpose: 最近 run / 最近晉升 / saved views，一鍵回到上次深度檢視脈絡。

6. **empty_state**
   - section_type: empty (FirstRunEmptyState)
   - section_purpose: 全新平台（零策略零 run）→ 置中引導卡 + CLI 指令 + 單一 CTA「建立第一個策略」。

---

## [SECTION COMPONENT SPEC]

### Section: command_hero

- **layout**: 全寬 hero 列，左階段狀態、中 Cmd-K 搜尋框、右快速動作。
- **elements**:
  - StageStatusLabel: Text / required / 一句話當前階段（讀 WBS milestone + gate 狀態），text-secondary。
  - CommandKBox: SearchBar（⌘K）/ required / 點擊或 ⌘K 開全域命令列（切策略/跳 run/開比較/新建/跳監控）。
  - QuickActions: Button row / required / 「New Run」（白 pill → `/research/runs/new`）+「Runs」+「艦隊」ghost。
- **states**:
  - default: 顯示階段 + Cmd-K + 動作。
  - loading: 階段標 skeleton。
  - error: 階段「狀態不可用」inline，Cmd-K 仍可用。
- **copy_constraints**: 階段一句話 ≤ 28 字；按鈕 ≤ 6 字。

### Section: fleet_strip

- **layout**: 橫向卡列（每策略一卡，可橫向捲動）；Desktop 顯 4–6 卡。
- **elements**:
  - StrategyCard.Name: H4 + strategy_id（mono caption）/ required。
  - StrategyCard.StageBadge: Badge / required / live / paper / draft（色+文字雙編碼）。
  - StrategyCard.HealthBadge: StatusBadge / required / 健康 / 觀察中 / **退化**（退化用 loss + 文字，醒目）。
  - StrategyCard.LiveKpi: Mini KPI / required / 今日 P&L%（漲跌雙編碼）+ Sharpe + MDD（Geist Mono）。
  - DegradeCta: Button Ghost / optional / 退化卡顯「處置」→ `/monitor`（Fleet）對應列。
  - SeeFleetLink: Link / required / 「看完整艦隊」→ `/monitor`。
- **states**:
  - default: live/paper 策略卡列；退化者排前並標紅。
  - loading: skeleton 卡列。
  - empty: 無 live/paper（僅 draft）→ 「尚無已部署策略，先完成驗證與晉升」+ 跳 Validate/Promote。
  - error: 「艦隊狀態載入失敗」+ 重試。
- **copy_constraints**: 策略名 ≤ 16 字；健康文字 ≤ 6 字。

### Section: research_status

- **layout**: 3–4 up KPI grid。
- **elements**:
  - ActiveRuns: KPI Card / required / 進行中 run 數（queued/running，點跳 Runs Table 篩選）。
  - IsGateBlocker: KPI Card / required / 當前 candidate 卡在哪條 IS gate（K1/K2/K3…）+ 差距。
  - PowerGauge: 三軸量表 / required / 回測次數 / 參數數 / 研究天數（紅黃綠 + 文字分級）。
  - TrialsDsr: KPI Card / required / 累計試驗數 + 當前 DSR（< 1.0 warning）。
- **states**:
  - default: 4 指標。
  - loading: skeleton。
  - empty: 無研究活動 → 「尚無 run，開始第一次回測」+ New Run CTA。
  - error: inline error + 重試。
- **copy_constraints**: 標籤 ≤ 12 字。

### Section: system_health

- **layout**: 4-up 狀態卡。
- **elements**:
  - DataFreshness: KPI Card / required / 最新 bundle 日期 + ingest 狀態（stale 標 warning）→ `/system/data`。
  - AlertCounts: KPI Card / required / 近 24h Discord 告警三級計數（Critical/High/Info，色+文字）→ `/system/alerts`。
  - FinlabQuota: KPI Card / required / FinLab 月流量剩餘 %（< 閾值 warning，對應 Grafana 面板 G）。
  - GrafanaLink: Link card / optional / Grafana F–I 系統健康外連。
- **states**:
  - default: 4 卡。
  - loading: skeleton。
  - empty: 「系統指標尚未就緒」。
  - error: 單卡 inline 失敗不阻塞其他。
- **copy_constraints**: 標籤 ≤ 14 字；日期 ISO。

### Section: recent_activity

- **layout**: 全寬列表（最多 5–8 列）。
- **elements**:
  - RecentRow: List row / required / 類型 icon（run / 晉升 / view）+ 摘要 + 時間（mono ISO）+ 點跳對應頁。
  - SavedViewsChips: Chip row / optional / 釘選的 saved views 一鍵進入。
- **states**:
  - default: 由新到舊。
  - loading: 列 skeleton。
  - empty: 「尚無近期活動」。
  - error: inline error + 重試。
- **copy_constraints**: 摘要單行 ≤ 40 字。

### Section: empty_state（FirstRunEmptyState）

- **layout**: 全新平台時取代上述內容，置中大圓角卡 + 1px border 無陰影。
- **elements**:
  - Headline: H2 / required / 「歡迎——從第一個策略開始」。
  - CliBox: Code block（Geist Mono / bg-code #161616 / 可複製）/ required / 真實 `backtest-run` 指令。
  - PrimaryCta: Button Primary（白 pill）/ required / 「建立第一個策略」→ `/research/runs/new`。
- **states**:
  - default: 引導卡（無 loading/error）。
- **copy_constraints**: Headline ≤ 18 字；CLI 為真實可執行指令。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 載入 → 並行查艦隊 / 研究狀態 / 系統健康 / 最近活動 → 四區渲染；全新平台渲染 empty_state。
2. fleet_strip 退化卡標紅 + 示警 → 點「處置」跳 `/monitor` Fleet 對應策略列（降級/退役/換掉）。
3. research_status 點 ActiveRuns / IsGateBlocker → 跳 Runs Table / Validate gate。
4. system_health 點 → 跳 `/system/data` 或 `/system/alerts`。
5. Cmd-K（command_hero）→ 全域跳任一頁 / type-to-run by id。
6. recent_activity / saved views → 一鍵回上次脈絡。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | hero 單列；fleet 橫向卡列；research/system 各 4-up | 側邊導覽展開 |
| Tablet (768–1279px) | fleet 橫向捲動；KPI 2-up | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | 全部單欄堆疊；fleet 卡縱向 | hero 動作收 overflow |

### 資料更新策略

- 艦隊 / 系統健康於交易時段 TTL 60s 輪詢；研究狀態 TTL 300s。
- 即時數據無進場動畫；退化偵測由後端推導，前端標紅。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs`（research 狀態）+ `equity_snapshots`（艦隊績效）+ `promotion_audit`（stage）+ `risk_metrics`（健康）+ bundle/alert 記錄。
- **endpoints**:
  - GET `/api/home/fleet` — live/paper 策略清單 + stage + 健康 + 今日 KPI + 退化旗標。
  - GET `/api/home/research-status` — active runs + IS gate blocker + power gauge + trials/DSR。
  - GET `/api/home/system-health` — bundle 新鮮度 + 告警計數 + FinLab quota。
  - GET `/api/home/recent` — 最近 run / 晉升 / saved views。
- **error_cases**:
  - 網路錯誤：section 級 inline error + 重試，不整頁崩潰。
  - 全新平台（全空）：渲染 empty_state（非 error）。
  - 權限不足：導向登入。

---

## [EXCEPTION TO GLOBAL RULES]

無特殊例外，完全遵循 Global v2.0（Grok 單色 dark、flat 1px border #2A2A2A、Geist Mono 數值、白環 focus、漲跌/健康雙編碼）。

---

## [ACCEPTANCE CRITERIA]

- [ ] 6 個 section（command_hero / fleet_strip / research_status / system_health / recent_activity / empty_state）功能正常。
- [ ] 開啟平台預設落地本頁；Cmd-K 常駐可達任一頁。
- [ ] fleet_strip 顯示 live/paper 策略健康，退化者標紅 + 示警 + 直達 Fleet 處置。
- [ ] research_status 反映 active runs / IS gate blocker / power gauge / trials-DSR。
- [ ] system_health 顯示資料新鮮度 / 告警計數 / FinLab quota。
- [ ] 全新平台渲染 empty_state（可複製真實 CLI + 單一 CTA）。
- [ ] 每 section 四態完備（default / loading / empty / error）。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；fleet 橫向捲動）。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環。
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影、即時數據無進場動畫。
