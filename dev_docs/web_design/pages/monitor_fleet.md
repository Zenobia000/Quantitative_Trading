# Page Layer Spec — 策略艦隊總控 (Monitor · Fleet)

> 來源：補強需求（多策略 live 監控 + 退化示警換掉）；Monitor 區 zone home（`/monitor`），下鑽單策略 Panel A–D。
> **範圍註記**：本頁是 `03` §5.3 原**刻意延後**的「champion/challenger 艦隊營運」——03 為單人縮小成「一次研究一隻 → 晉升 → 監控那一隻」。使用者明確要「管理多隻策略像員工、退化換掉」，故補回，**範圍已由 [ADR-022](../../adrs/ADR-022-multi-strategy-fleet-operations.md) 正式裁定**（營運層多策略艦隊 lite；研究層仍單策略；仍排除跨人 leaderboard/staking/完整 registry/多人簽核）。對應 03 §5.3「有多策略候選池再加 correlation gate / 跨策略比較」；端點見 `25 §6.2`（M4、gated 於 ≥1 可部署策略）。
> 繼承 Global v2.0（**Grok 單色 dark** / Geist Mono 數值 / 白環 focus / 漲跌 ↑↓ 雙編碼）。
> **狀態**：M3 設計 spec / live 看板資料 M4-M5；assembly 隨 React 化再產出。

---

## [PAGE META]

- **page_name**: 策略艦隊總控 (Monitor · Fleet)
- **route_path**: /monitor
- **page_type**: dashboard (fleet board)
- **primary_goal**: 把所有 live/paper 策略當「一支團隊」並排監控——每隻策略的健康評分、live 績效、退化偵測一覽，退化者示警並提供降級/退役/換掉（晉升 challenger）的處置 workflow。
- **secondary_goal**: 揭露組合層風險（總曝險 / 總 Heat / 策略間相關性），避免高相關策略塞滿資金（correlation gate 雛形）。
- **target_users**:
  - 主要：操盤手（同時管理多隻已部署策略，像管理員工）
  - 次要：風控（盯組合層集中度與退化）
- **entry_point**: 側邊導覽「Monitor → 艦隊總控」（Monitor zone home）；首頁 fleet_strip「看完整艦隊」/「處置」；Cmd-K「跳艦隊」。
- **expected_time_on_page**: 1–3 分鐘（掃健康榜 → 對退化者下鑽/處置；或進單策略 Panel A）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 6 個功能區塊。

1. **fleet_toolbar**
   - section_type: toolbar / filter
   - section_purpose: 依 stage（live/paper/all）篩選、依健康/Sharpe/今日 P&L 排序、手動 refresh。

2. **portfolio_summary**
   - section_type: stats（組合層彙總）
   - section_purpose: 跨策略合併視角——組合 equity、總曝險、總 Portfolio Heat、live 策略數 / 退化數。

3. **fleet_table**
   - section_type: data_table（一列一策略）
   - section_purpose: 每策略 stage + 健康評分 + live KPI（今日/MTD P&L、Sharpe、MDD、部位數、Heat）+ 退化偵測 + 處置動作；點列下鑽單策略 Panel A。

4. **degradation_panel**
   - section_type: list / alert
   - section_purpose: 退化策略專區——退化原因（退出 cone / 勝率退化 / DD 超標）+ 示警 + swap workflow（降級回 paper/draft、退役、晉升 challenger 替補）。

5. **correlation_matrix**
   - section_type: chart (heatmap)
   - section_purpose: 策略間報酬相關性 heatmap，揪出高相關（換湯不換藥）策略，支援資金分散決策。

6. **empty_state**
   - section_type: empty
   - section_purpose: 無 live/paper 策略 → 引導先完成 Validate → Promote。

---

## [SECTION COMPONENT SPEC]

### Section: fleet_toolbar

- **layout**: 1-row toolbar，sticky top。
- **elements**:
  - StageFilter: SegmentedControl / required / all / live / paper（色+文字）。
  - SortSelect: Select / required / 健康評分 / 今日 P&L / Sharpe / 退化優先。
  - RefreshButton: IconButton / optional / 清快取重查。
  - LastUpdated: Caption / optional / 「as of HH:mm:ss TWT」。
- **states**:
  - default: 全選；退化優先排序預設。
  - loading: toolbar 可見，table skeleton。
  - empty: filter 命中 0 → 「無符合條件策略」。
  - error: inline error + 重試。
- **copy_constraints**: filter chip ≤ 6 字。

### Section: portfolio_summary

- **layout**: 4–5 up KPI 列。
- **elements**:
  - PortfolioEquity: KPI Card / required / 跨策略合併 equity（今日變化漲跌雙編碼）。
  - TotalExposure: KPI Card / required / 總曝險（市值 / 資金 %）。
  - TotalHeat: KPI Card / required / 組合層 Portfolio Heat（接近上限 warning + 文字）。
  - LiveCount: KPI Card / required / live 策略數 / 上限。
  - DegradedCount: KPI Card / required / 退化策略數（> 0 標 loss + 文字）。
- **states**:
  - default: 彙總指標。
  - loading: skeleton。
  - empty: 「無已部署策略」。
  - error: inline error。
- **copy_constraints**: 標籤 ≤ 14 字；金額 NT$ 千分位。

### Section: fleet_table

- **layout**: 全寬 DataTable，frozen first column（策略名）；橫向捲動保欄位密度（不轉 card）。
- **elements**:
  - NameCell: Mono link / required / 策略名 + id；點跳 `/monitor/performance?strategy_id=`（Panel A 單策略）。
  - StageBadge: Badge / required / live / paper（色+文字）。
  - HealthScore: Gauge cell / required / 健康評分（0–100，紅黃綠 + 文字 健康/觀察/退化）。
  - LiveKpiCells: Mono number / required / 今日 P&L% / MTD P&L% / Sharpe / MDD / 部位數 / Heat（tabular-nums，漲跌雙編碼）。
  - DegradeFlag: Badge / required / 退化偵測（退出 cone / 勝率退化 / DD 超標，色+文字）。
  - ActionMenu: Overflow menu / required / 處置：下鑽 Panel A / 降級 / 退役 / 換掉（→ degradation_panel workflow）。
  - SparklineCell: inline sparkline / optional / 該策略近 N 日 equity 縮圖（單色）。
- **states**:
  - default: 退化優先；健康評分著色 + 文字。
  - loading: 列 skeleton。
  - empty: 交由 empty_state。
  - error: 「艦隊載入失敗」+ 重試。
- **copy_constraints**: 欄標 ≤ 10 字；比率 2 位小數。

### Section: degradation_panel

- **layout**: 退化策略卡列（無退化時收合為「全員健康」）。
- **elements**:
  - DegradeCard: Card / required / 策略名 + 退化原因（具體指標 vs 門檻）+ 自 live_start 多久退化。
  - EvidenceLink: Link / required / 「看證據」→ Panel A（標 live_start_date + cone 退化段）。
  - SwapWorkflow: Action group / required / 降級回 paper/draft / 退役（凍結唯讀 run report）/ **晉升 challenger 替補**（→ Promote 對應策略）。
  - AuditNote: Caption / required / 處置寫 promotion_audit（誰/何時/憑哪組退化證據）。
- **states**:
  - default: 列出退化者 + 處置。
  - empty: 「目前全員健康，無退化」（正向）。
  - loading: skeleton。
  - error: inline error + 重試。
- **copy_constraints**: 退化原因單行 ≤ 40 字。

### Section: correlation_matrix

- **layout**: 全寬 heatmap（策略 × 策略）。
- **elements**:
  - CorrHeatmap: Heatmap / required / 策略間報酬相關性，**Diverging 色階**（高相關 ↔ 中性 ↔ 負相關，沿用漲跌語義）。
  - HighCorrFlag: Inline / required / self-correlation > 0.7 標警示（換湯不換藥 / 資金過度集中）。
  - CellTooltip: Tooltip / required / hover 顯示策略對 + 相關係數。
- **states**:
  - default: 完整矩陣。
  - loading: skeleton grid。
  - empty: 「需 ≥2 已部署策略」。
  - error: inline error + 重試。
- **copy_constraints**: 係數 2 位小數。

### Section: empty_state

- **layout**: 置中卡 + 1px border 無陰影。
- **elements**:
  - Headline: H2 / required / 「尚無已部署策略」。
  - Guide: Text / required / 「先在研究區完成 Validate → Promote，策略上 paper/live 後在此監控艦隊」。
  - Cta: Button / required / 「去 Validate gate」→ `/research/validate`。
- **states**:
  - default: 引導卡。
- **copy_constraints**: Headline ≤ 16 字。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 載入 → 查艦隊 + 組合彙總 + 相關性 → 渲染；無 live/paper 渲染 empty_state。
2. fleet_table 退化優先排序；點列 → 下鑽 `/monitor/performance` 單策略 Panel A。
3. 退化策略 → degradation_panel 示警 + swap workflow：降級 / 退役 / 晉升 challenger 替補（跳 Promote）。
4. correlation_matrix 高相關（>0.7）標警示 → 引導資金分散 / 退掉冗餘策略。
5. 處置動作寫 promotion_audit；退化偵測由後端推導（cone/勝率/DD vs 門檻）。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | summary 5-up；table 全欄 frozen col；correlation 全寬 | 側邊導覽展開 |
| Tablet (768–1279px) | summary 2-up；table 橫向捲動；correlation 全寬 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | 全部單欄；table 橫向捲動保密度；correlation 橫向捲動 | degradation_panel 固定 |

### 資料更新策略

- 交易時段 TTL 60s 輪詢（live 績效 + 健康 + 退化）；correlation 低頻 TTL 300s。
- 即時數據無進場動畫；退化偵測即時標紅。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs`（stage）+ `equity_snapshots`（各策略 live）+ `risk_metrics` + `promotion_audit`。
- **endpoints**:
  - GET `/api/monitor/fleet` — 各策略 stage / 健康評分 / live KPI / 退化旗標。
  - GET `/api/monitor/portfolio-summary` — 組合 equity / 曝險 / Heat / 計數。
  - GET `/api/monitor/correlation` — 策略間報酬相關性矩陣。
  - POST `/api/monitor/fleet/{strategy_id}/action` — 降級 / 退役 / 換掉（寫 promotion_audit）。
- **error_cases**:
  - 網路錯誤：section 級 inline error + 重試。
  - 無已部署策略：empty_state。
  - 處置衝突（stage 已被別處推進）：提示重載最新狀態。
  - 權限不足：導向登入（艦隊處置屬操盤/風控權限）。

---

## [EXCEPTION TO GLOBAL RULES]

- correlation_matrix 用 §6.1 **Diverging 色階**（高相關 ↔ 中性 ↔ 負相關，沿用漲跌語義零新增語彙），僅限圖表內容區。
- fleet_table / correlation 在 @<1024px **橫向捲動不轉 card**（艦隊級密集表，研究表同理）。
- 其餘完全遵循 Global v2.0。

---

## [ACCEPTANCE CRITERIA]

- [ ] 6 個 section（toolbar / portfolio_summary / fleet_table / degradation_panel / correlation_matrix / empty_state）功能正常。
- [ ] fleet_table 一列一策略，健康評分紅黃綠+文字、live KPI 漲跌雙編碼、退化旗標醒目。
- [ ] degradation_panel 列退化原因 + swap workflow（降級/退役/晉升 challenger 替補），處置寫 promotion_audit。
- [ ] portfolio_summary 顯組合 equity / 曝險 / Heat / live 數 / 退化數。
- [ ] correlation_matrix Diverging 色階 + >0.7 高相關警示。
- [ ] 點列下鑽單策略 `/monitor/performance`（Panel A）。
- [ ] 無已部署策略渲染 empty_state（導向 Validate）。
- [ ] 密集表 @<1024px 橫向捲動不轉 card。
- [ ] 每 section 四態完備；數值 Geist Mono tabular-nums；文字 AA / KPI AAA；focus 白環。
- [ ] dark-first（Grok 單色）、flat 1px border #2A2A2A 無陰影。
