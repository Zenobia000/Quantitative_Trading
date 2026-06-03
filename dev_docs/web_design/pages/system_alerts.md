# Page Layer Spec — 告警設定 (System · Alerts)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.7 sitemap 系統區（`/system/alerts` Discord 三級 Critical/High/Info）+ §4.6 告警 triage flowchart + §5.2 IA。
> 接收 Grafana F–I 與 Panel D（風控）事件（§4.7 `graf -.-> alert`、`risk -.-> alert`）。
> 繼承 Global v2.0（**Grok 單色 dark**：bg-base #0F0F0F / surface #1A1A1A / code #161616 / border #2A2A2A / 白環 focus / Geist Mono 數值 / 狀態色+文字雙編碼）。

---

## [PAGE META]

- **page_name**: 告警設定 (Alerts)
- **route_path**: /system/alerts
- **page_type**: list + form
- **primary_goal**: 讓使用者設定 Discord 三級告警（Critical / High / Info）通道與規則，並檢視近期觸發紀錄與 ack 狀態，作為監控 triage（§4.6）的推播來源真相。
- **secondary_goal**: 接收 Grafana F–I 系統事件與 Panel D 風控/熔斷事件，集中管理 rule_id ↔ runbook ↔ 通道對應。
- **target_users**:
  - 主要：運維者 / 操盤手（設定與 ack 告警）
  - 次要：研究者（確認策略面告警如部位偏離）
- **entry_point**: 側邊導覽「系統 → 告警設定」；Discord 告警卡「設定」連結；Grafana / Panel D 事件「告警規則」。
- **expected_time_on_page**: 2–5 分鐘（設通道 / 調規則 / 測試推播 / ack 歷史）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 5 個功能區塊。

1. **toolbar**
   - section_type: toolbar / action
   - section_purpose: 新增規則、依 tier / 來源篩選、手動 refresh。

2. **channel_config**
   - section_type: form
   - section_purpose: Discord 三級通道（Critical / High / Info）webhook 設定與啟用開關。

3. **alert_rules**
   - section_type: data_table
   - section_purpose: 規則表（rule_id / tier / 來源 / 條件 / runbook / 啟用），對映 Grafana 與 Panel D 事件。

4. **alert_history**
   - section_type: data_table
   - section_purpose: 近期觸發紀錄（時間 / rule_id / tier / 摘要 / ack 狀態），列可 ack 與下鑽。

5. **test_delivery**
   - section_type: action
   - section_purpose: 對選定通道發測試推播，驗證 webhook 連通。

---

## [SECTION COMPONENT SPEC]

### Section: toolbar

- **layout**: 1-row horizontal toolbar，sticky top。
- **elements**:
  - NewRuleButton: Button Primary（白底 pill）/ required / 開規則編輯 drawer。
  - TierFilter: SegmentedControl / optional / 全部 / Critical / High / Info（色+文字雙編碼）。
  - SourceFilter: Select / optional / 來源（Grafana / 風控 Panel D / ETL / quota）。
  - RefreshButton: IconButton / optional / 清快取重查。
- **states**:
  - default: 顯示全部規則；filter 全選。
  - loading: toolbar 可見，下游 list 進 skeleton。
  - empty: filter 命中 0 → 「無符合條件的規則」。
  - error: inline error + 重試。
- **copy_constraints**: 按鈕 ≤ 6 字（「新增規則」）；tier chip ≤ 8 字。

### Section: channel_config

- **layout**: 3-up 通道卡（Critical / High / Info），Desktop 並排 / Mobile 堆疊。
- **elements**:
  - WebhookInput ×3: Input（masked）/ required / 各 tier 的 Discord webhook URL（不明碼顯示，避免洩露）。
  - EnableToggle ×3: Switch / required / 各通道啟用/停用。
  - TierBadge ×3: Badge / required / Critical(error #EF4444) / High(warning #E9A60C) / Info(text-muted)，色+文字雙編碼。
  - SaveButton: Button / required / 儲存通道設定（驗證 webhook 格式）。
- **states**:
  - default: 顯示三通道狀態（已設定/未設定）。
  - error: webhook 格式錯誤 → inline error；缺秘密 → 提示用環境變數，不硬編碼。
  - disabled: 停用通道 webhook 輸入轉灰。
- **copy_constraints**: 通道名固定 Critical/High/Info；webhook 一律 masked 顯示。

### Section: alert_rules

- **layout**: 全寬 DataTable，frozen first column（rule_id）。
- **elements**:
  - RuleIdCell: Mono / required / rule_id。
  - TierBadgeCell: Badge / required / Critical/High/Info（色+文字雙編碼）。
  - SourceCell: Tag / required / 來源（Grafana F–I / 風控 Panel D / ETL / quota / 偏離）。
  - ConditionCell: Text (truncate) / required / 觸發條件摘要（溢出 tooltip）。
  - RunbookLink: Link / optional / 對應 runbook（dev_docs/14）。
  - EnableToggle: Switch / required / 規則啟用/停用。
  - EditRow: 互動 / required / 點列開編輯 drawer。
- **states**:
  - default: 依 tier 排序；停用規則淡化。
  - loading: 列 skeleton。
  - empty: 「尚無告警規則」+ 新增 CTA。
  - error: 「規則載入失敗」+ 重試。
- **copy_constraints**: 欄標 ≤ 12 字；條件摘要單行 ≤ 40 字。

### Section: alert_history

- **layout**: 全寬 DataTable，依時間倒序。
- **elements**:
  - TimeCell: Mono / required / 觸發時間（ISO `YYYY-MM-DD HH:mm`，tabular-nums）。
  - RuleIdCell: Mono link / required / 點跳對應規則。
  - TierBadgeCell: Badge / required / 色+文字雙編碼。
  - SummaryCell: Text / required / 觸發摘要（指標值 / 偏離 %）。
  - AckBadge: StatusBadge / required / acked / unacked（色+文字雙編碼）。
  - AckButton: Button Ghost / required / 未 ack 列可一鍵 ack（留痕誰/何時）。
  - DrillRow: 互動 / optional / Critical 列 deep-link 跳對應 panel（熔斷→Panel D、訊號→Panel C）。
- **states**:
  - default: 倒序列出近期觸發。
  - loading: 列 skeleton。
  - empty: 「近期無告警觸發」（正向訊號）。
  - error: inline error + 重試。
- **copy_constraints**: 摘要 ≤ 40 字；時間 ISO。

### Section: test_delivery

- **layout**: 全寬列，左通道選擇、右送出。
- **elements**:
  - ChannelSelect: SegmentedControl / required / 選 Critical / High / Info 通道。
  - TestButton: Button / required / 發測試推播 → 顯示送達/失敗結果。
  - ResultNote: Inline / required / 成功（綠+✓）/ 失敗（error + 文字，攤連線錯誤）。
- **states**:
  - default: 可選通道送測試。
  - loading: 送出中 spinner。
  - error: webhook 未設定 / 連線失敗 → inline error。
- **copy_constraints**: 按鈕 ≤ 6 字（「測試推播」）。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 載入 → 並行查通道設定 / 規則 / 近期歷史 → 渲染各 section。
2. 設定/啟用通道 webhook → SaveButton 驗證格式後寫入（webhook 以環境變數/secret 管理，不硬編碼）。
3. 新增/編輯規則 → drawer 設 tier / 來源 / 條件 / runbook → 儲存後 alert_rules 更新。
4. 規則被 Grafana F–I 或 Panel D 事件觸發 → 寫 alert_history、依 tier 推 Discord 對應通道。
5. alert_history 未 ack 列點 AckButton → 標 acked 留痕；Critical 列 deep-link 跳對應監控 panel（接 §4.6 triage）。
6. test_delivery 選通道送測試 → 驗證 webhook 連通。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | toolbar 單列；通道 3 欄並排；rules/history 全寬 | sidebar 展開 |
| Tablet (768–1279px) | 通道堆疊；table 橫向捲動 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | 全部單欄堆疊；table 橫向捲動保密度 | test_delivery 固定底部 |

### 資料更新策略

- 規則 / 通道設定為低頻變動 → 快取 TTL 300s；變更後即時寫入並刷新。
- alert_history 交易時段 TTL 60s 輪詢；新觸發頂部插入（無進場動畫）。
- 通道 webhook 為敏感資料，僅 masked 顯示，後端以 secret 管理。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: 告警規則表 + 通道設定 + 觸發歷史 + ack 記錄。
- **endpoints**:
  - GET `/api/system/alerts/channels` / PUT `/api/system/alerts/channels` — 三級通道設定讀寫（webhook masked）。
  - GET `/api/system/alerts/rules` / POST / PUT `/api/system/alerts/rules` — 規則 CRUD。
  - GET `/api/system/alerts/history?tier=&window=` — 觸發歷史。
  - POST `/api/system/alerts/history/{id}/ack` — ack 告警（留痕）。
  - POST `/api/system/alerts/test` — 對選定通道發測試推播。
- **error_cases**:
  - webhook 格式錯誤（422）：channel_config inline error。
  - 缺秘密 / 連線失敗：test_delivery / 推播顯示連線錯誤，提示用環境變數管理。
  - 網路錯誤：section 級 inline error + 重試。
  - 權限不足：導向登入（告警設定屬運維權限）。

---

## [EXCEPTION TO GLOBAL RULES]

- 告警 tier 沿用功能色（Critical error #EF4444 / High warning #E9A60C / Info text-muted），皆配文字標籤雙編碼，非新增彩色語彙。
- webhook URL 一律 masked 顯示（安全要求），不在 UI 明碼或硬編碼。
- 其餘完全遵循 Global v2.0（Grok 單色 dark、flat 1px border #2A2A2A、Geist Mono、白環 focus）。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（toolbar / channel_config / alert_rules / alert_history / test_delivery）功能正常。
- [ ] channel_config 三級 Discord 通道（Critical/High/Info）webhook 設定 + 啟用開關；webhook masked 顯示、以 secret 管理不硬編碼。
- [ ] alert_rules 對映 Grafana F–I 與 Panel D 事件，含 rule_id / tier / 來源 / 條件 / runbook / 啟用。
- [ ] tier 一律色+文字雙編碼（Critical/High/Info），不只靠顏色。
- [ ] alert_history 可 ack（留痕）；Critical 列 deep-link 跳對應監控 panel（接 §4.6 triage）。
- [ ] test_delivery 可對選定通道發測試並回報送達/失敗。
- [ ] 每 section 四態完備（default / loading / empty / error）。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；table 橫向捲動）。
- [ ] 數值/時間 Geist Mono tabular-nums；文字 AA；focus 白環 rgba(245,245,245,.7)。
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影。
