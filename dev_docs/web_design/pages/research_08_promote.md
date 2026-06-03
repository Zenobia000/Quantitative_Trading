# Page Layer Spec — Promotion stepper 晉升 (Research · Promote)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.5 晉升 gate 狀態機（backtest→paper→live）+ 附錄 A §1.8 Promote + §5.1 roadmap（M5）。
> 把 ADR-016/017 散落在 ADR 文字裡的人工 gate，升格為系統內可重複、可審計的不可逆狀態機 + 明確降級路徑。
> 繼承 Global v2.0（Grok 單色 dark / Geist Mono 數值 / 白環 focus / 漲跌 ↑↓ + PASS/FAIL 雙編碼）。

---

## [PAGE META]

- **page_name**: Promotion stepper 晉升 (Promote)
- **route_path**: /research/promote/:strategy_id
- **page_type**: workflow (stepper state machine)
- **primary_goal**: 以不可逆狀態機 Draft→Backtested→Validated→Paper→Live→Retired 管理晉升，每個轉換有硬門檻 checklist、試驗次數、OOS sealed vault，每階段綠燈才解鎖下一階段主 CTA。
- **secondary_goal**: 明確降級路徑（gate FAIL 回 Draft、paper 表現差回 Draft、live 退化回 Paper）；強制 paper 觀察期取代真錢後果；immutable snapshot + audit log。
- **target_users**:
  - 主要：量化研究者（晉升自己已驗證的策略）
  - 次要：風控（簽核不可逆轉換、審計 audit log）
- **entry_point**: Validate gate 核准後解鎖；策略庫策略詳情「晉升」；側邊導覽「Research → Promote」。
- **expected_time_on_page**: 3–10 分鐘（讀 stepper → 檢視當前階段 checklist → 解鎖 CTA / 看 audit）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 5 個功能區塊。

1. **promotion_stepper**
   - section_type: stepper (state machine)
   - section_purpose: Draft→Backtested→Validated→Paper→Live→Retired 視覺化；已過綠 / 當前 accent / 未解鎖灰 + 降級回退邊。

2. **current_stage_checklist**
   - section_type: checklist
   - section_purpose: 當前階段的晉升前置硬門檻逐條綠/紅（解鎖下一階段主 CTA 的條件）。

3. **paper_observation**
   - section_type: chart + status（Paper 階段）
   - section_purpose: 強制 paper 觀察期（如 60 交易日）進度 + 同圖標 live_start_date 邊界 + 退化判定（cone/勝率）。

4. **promote_action**
   - section_type: action（解鎖式 CTA）
   - section_purpose: 全綠才亮的單一晉升 CTA + 降級/退役動作；不可逆轉換二次確認。

5. **audit_log**
   - section_type: table
   - section_purpose: promotion_audit 不可竄改紀錄（誰/何時/憑哪組 metrics/哪個 run snapshot）。

---

## [SECTION COMPONENT SPEC]

### Section: promotion_stepper

- **layout**: 全寬水平 stepper（含回退邊註記）。
- **elements**:
  - StageNodes: Stepper node ×6 / required / Draft/Backtested/Validated/Paper/Live/Retired；已過 gain✓、當前 accent(白)、未解鎖灰（色+文字雙編碼）。
  - RollbackEdges: Edge label / required / 標降級路徑（isGate/wfaGate/oosGate FAIL→Draft、paperGate 差→Draft、liveGate 退化→Paper）。
  - ImmutableBadge: Badge / required / 各已過階段標 immutable snapshot ref。
- **states**:
  - default: stepper 反映 validation_status / stage。
  - loading: stepper skeleton。
  - empty: 策略未達 Validated → 「需先通過 Validate gate」+ 跳 Validate CTA。
  - error: 狀態載入失敗 → inline error + 重試。
- **copy_constraints**: 階段標籤 ≤ 8 字；回退邊註記 ≤ 16 字。

### Section: current_stage_checklist

- **layout**: 逐條 checklist（門檻 / 實際 / 綠紅）。
- **elements**:
  - GateRows: Checklist row ×N / required / 當前轉換的硬門檻（如 Validated→Paper：OOS pass + 承諾達標 + 風控核准；Paper→Live：觀察期綠燈 + 勝率/cone 達標）。
  - BlockReason: Inline / required（未過時）/ 列出阻擋項與差距。
  - PreReqNote: Caption / required / 「全綠才解鎖下一階段主 CTA」。
- **states**:
  - default: 逐條綠/紅。
  - loading: 列 skeleton。
  - empty: 無待辦 → 「當前階段無前置門檻」。
  - error: inline error + 重試。
- **copy_constraints**: 條件名 ≤ 20 字。

### Section: paper_observation（Paper 階段顯示）

- **layout**: 進度條 + equity 圖（標 live_start_date 邊界）。
- **elements**:
  - ObservationProgress: ProgressBar / required / 觀察期進度（已觀察 X / 目標 60 交易日）。
  - PaperEquity: Line + boundary / required / paper 期 equity，標 paper 起點邊界 + 預期 cone。
  - DegradeVerdict: Inline / required / 退化判定（退出 cone / 勝率退化 → 打回 Draft 提示，雙編碼）。
- **states**:
  - default: 進度 + equity + 判定（僅 Paper 階段）。
  - loading: skeleton。
  - empty: 未進 Paper → 隱藏該 section。
  - error: inline error + 重試。
- **copy_constraints**: 進度文案 ≤ 16 字；邊界標籤 ≤ 8 字。

### Section: promote_action

- **layout**: sticky action bar（單一主 CTA + 降級/退役次要動作）。
- **elements**:
  - PromoteButton: Button Primary（白 pill）/ required / 全綠才亮的單一晉升 CTA（如「晉升 Paper」/「部署 Live」）；含不可逆二次確認 modal。
  - DemoteButton: Button Ghost / optional / 降級（Live→Paper）。
  - RetireButton: Button Ghost / optional / 退役（→Retired，凍結唯讀 run report）。
  - DeriveButton: Button Ghost / optional（Retired 時）/ 以舊版為 baseline 衍生新變體 → New Run。
- **states**:
  - default: 全綠時 PromoteButton 亮。
  - disabled: 未過門檻 → PromoteButton disabled + tooltip 列阻擋原因。
  - loading: 轉換中 spinner，禁重複。
  - error: 轉換失敗 inline error + 重試。
- **copy_constraints**: 按鈕 ≤ 8 字；二次確認文案明示不可逆。

### Section: audit_log

- **layout**: DataTable，列=轉換事件。
- **elements**:
  - AuditRows: Table row / required / 時間 / 動作（promote/demote/retire/FAIL）/ 操作者 / metrics 快照 / run snapshot ref（Geist Mono）。
  - SnapshotLink: Link / optional / 跳對應 immutable run report。
  - ImmutableNote: Caption / required / 「紀錄不可竄改，供 audit 追溯」。
- **states**:
  - default: 由新到舊列出。
  - loading: 列 skeleton。
  - empty: 「尚無晉升紀錄」。
  - error: inline error + 重試。
- **copy_constraints**: 動作 ≤ 8 字；時間 ISO `YYYY-MM-DD HH:mm`。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 載入策略 → promotion_stepper 反映 validation_status；未達 Validated → empty 導回 Validate gate。
2. current_stage_checklist 逐條判定 → 全綠才解鎖 promote_action 主 CTA。
3. Validated → 晉升 Paper（不可逆二次確認）→ 進 paper_observation 強制觀察期。
4. 觀察期內退化（退出 cone/勝率退化）→ DegradeVerdict 提示 → 可降級回 Draft。
5. 觀察期綠燈 → 部署 Live（immutable snapshot + audit）→ 交監控 A–E 子視圖接管。
6. Live 退化 → 降級回 Paper；策略失效 → 退役 Retired（凍結唯讀，可衍生新變體回 Draft）。
7. 每次轉換寫 promotion_audit（誰/何時/metrics/run snapshot）。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | stepper 水平全寬；checklist + paper 兩欄；audit 全寬 | sidebar 展開 |
| Tablet (768–1279px) | stepper 水平捲動；單欄堆疊 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | stepper 改垂直；audit 表橫向捲動 | promote_action 固定底部；二次確認全屏 modal |

### 資料更新策略

- stage/狀態為不可逆後端寫入，前端反映後鎖定；快取 TTL 300s。
- paper_observation 進度依交易日更新（每日批次），equity 隨 paper run 更新。
- 轉換動作為後端不可逆操作，成功後 stepper + audit 即時刷新。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs`（validation_status / stage）+ `promotion_audit` + `equity_snapshots`（paper-scoped）。
- **endpoints**:
  - GET `/api/research/promote/:strategy_id` — 當前 stage + stepper 狀態 + 當前階段 checklist。
  - POST `/api/research/promote/:strategy_id/advance` — 晉升下一階段（後端驗門檻；未過回 409，含阻擋原因）。
  - POST `/api/research/promote/:strategy_id/demote` — 降級（Live→Paper / Paper→Draft）。
  - POST `/api/research/promote/:strategy_id/retire` — 退役 → Retired。
  - GET `/api/research/promote/:strategy_id/observation` — paper 觀察期進度 + equity + cone。
  - GET `/api/research/promote/:strategy_id/audit` — promotion_audit 紀錄。
- **error_cases**:
  - 未達 Validated（前置未過）：stepper empty + 導回 Validate gate。
  - 門檻未過（409）：promote_action disabled + 列阻擋原因。
  - 轉換衝突（已被他處推進）：提示重載最新狀態。
  - 網路錯誤：section 級 inline error + 重試。

---

## [EXCEPTION TO GLOBAL RULES]

- paper_observation 的 equity cone band 沿用既有漲跌語義（gain/loss + 邊界文字標籤），不引入新彩色。
- 其餘完全遵循 Global v2.0（Grok 單色 dark、flat 1px border、Geist Mono、白環 focus）。
- 刻意不做（§4.5）：跨人競賽 leaderboard、多人簽核、champion/challenger registry、staking 真錢——用三狀態 + 不可逆 gate + 強制 paper 觀察期替代。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（stepper / checklist / paper_observation / promote_action / audit_log）功能正常。
- [ ] promotion_stepper 反映 Draft→Backtested→Validated→Paper→Live→Retired，含降級回退邊標註（色+文字雙編碼）。
- [ ] current_stage_checklist 全綠才解鎖 promote_action 單一主 CTA；未過列阻擋原因。
- [ ] 晉升為不可逆轉換，含二次確認 modal 明示不可逆。
- [ ] paper_observation 顯示強制觀察期進度 + live_start_date 邊界 + 退化判定。
- [ ] 降級路徑可用（Live→Paper、Paper→Draft）；Retired 可衍生新變體回 Draft。
- [ ] 每次轉換寫 promotion_audit（誰/何時/metrics/run snapshot），不可竄改。
- [ ] Live 階段交監控 A–E 子視圖接管（cross-link）。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；stepper 垂直化；表格橫向捲動）。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影。
