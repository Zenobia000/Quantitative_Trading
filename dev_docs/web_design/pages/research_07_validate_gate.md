# Page Layer Spec — Validate gate 驗證守門 (Research · Validate Gate)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.4 驗證/防過擬合 gate flowchart + 附錄 A §1.7 Validate + §3 防過擬合五層 + §5.1 roadmap（M3，**Panel E 從 `/dashboard/validation` 升級/重定位**）。
> 把唯讀的 Panel E 升級為「研究迴圈中段的不可逆 gate 工作流」。對應後端：`gate_state.py` 狀態機 + OOS sealed vault + `promotion_audit`。
> 繼承 Global v2.0（Grok 單色 dark / Geist Mono 數值 / 白環 focus / 漲跌 ↑↓ + PASS/FAIL 雙編碼）。

---

## [PAGE META]

- **page_name**: Validate gate 驗證守門 (Validate Gate)
- **route_path**: /research/validate
- **page_type**: workflow (gate state machine)
- **primary_goal**: 用不可逆狀態機證明 edge 真實——IS gate 逐條硬門檻 → IS PASS 解鎖 OOS sealed vault → WFA/CPCV → PBO/DSR（吃試驗次數 deflate）紅線自動擋晉升 → 事前承諾 vs 實際自動對照，pass/fail 寫進 promotion_audit。
- **secondary_goal**: 把 ADR-017「IS gate FAIL → 回 M0」從散落 ADR 變成 UI/系統內明確狀態轉換 + 擋關；唯讀展示升級為工作流強制（L4 流程鎖定 + L5 資料封存）。
- **target_users**:
  - 主要：量化研究者（守門自己的 candidate run）
  - 次要：風控（把關不可逆晉升、審計試驗次數）
- **entry_point**: Run Report「送驗證」；Compare/Sweep 選定候選；監控 triage 結論「結構性退化」經 Cmd-K 切入；側邊導覽「Research → Validate」。
- **expected_time_on_page**: 5–15 分鐘（讀 IS gate 逐條 → 解鎖 OOS → 看 WFA/PBO/DSR → 風控簽核）

---

## [STRUCTURE: SECTIONS]

> 由上至下，共 6 個功能區塊（依不可逆狀態機順序）。

1. **gate_status_header**
   - section_type: status / stepper
   - section_purpose: 顯示當前 candidate run 在 IS→WFA→OOS 狀態機的位置（已過綠 / 當前 / 未解鎖灰）+ 試驗次數 + power gauge。

2. **is_gate_checklist**
   - section_type: checklist
   - section_purpose: IS gate 硬門檻逐條綠/紅 + 差距值（K1 CAGR / K2 Sharpe / K3 滑點 Sharpe / min-trades / turnover / sub-period 穩健 / HHI）。

3. **oos_sealed_vault**
   - section_type: locked panel
   - section_purpose: IS 未過前 OOS 區段對 CLI/UI 皆不可讀/不可跑；每次存取計次留痕；IS PASS 才解封。

4. **wfa_fold_view**
   - section_type: chart + table（母 run 收子 fold）
   - section_purpose: WFA/CPCV 各 fold 一致性（purge/embargo）+ IS-vs-OOS scatter（沿用 Panel E 圖）。

5. **overfitting_redline**
   - section_type: stats (KPI + redline)
   - section_purpose: PBO(CSCV) / DSR（吃 trials deflate）/ Deflated & Probabilistic Sharpe；PBO>0.5 或 DSR<1.0 自動標 FAIL 擋晉升。

6. **commitment_signoff**
   - section_type: comparison + action
   - section_purpose: 事前承諾 vs 實際 OOS 自動紅/綠對照 + 風控簽核（不可逆 approved 轉換）→ 寫 promotion_audit。

---

## [SECTION COMPONENT SPEC]

### Section: gate_status_header

- **layout**: 全寬 stepper + 右側計量。
- **elements**:
  - GateStepper: Stepper / required / Draft → IS → WFA → OOS → Validated；已過 gain、當前 accent(白)、未解鎖灰（色+文字雙編碼）。
  - CandidateRef: Mono / required / candidate run_id + 策略版本 + lineage link。
  - TrialsBadge: Badge / required / 累計試驗 N + 當前 DSR。
  - PowerGauge: 三軸量表 / required / 回測次數/參數數/研究天數紅黃綠。
- **states**:
  - default: stepper 反映 gate_state。
  - loading: stepper skeleton。
  - empty: 未選 candidate → 「請自 Runs/Compare 選定 candidate run」+ CTA。
  - error: gate_state 載入失敗 → inline error + 重試。
- **copy_constraints**: 階段標籤 ≤ 8 字。

### Section: is_gate_checklist

- **layout**: 逐條 checklist 列（條件名 / 門檻 / 實際 / 差距 / 綠紅）。
- **elements**:
  - GateRows: Checklist row ×N / required / K1 CAGR>18% / K2 Sharpe>1.0 / K3 滑點 Sharpe>1.0 / min-trades / turnover 範圍 / sub-period 穩健 / HHI 集中度；每列 PASS gain✓ / FAIL loss✗ + 差距值（雙編碼）。
  - FailHint: Inline / required（FAIL 時）/ 「卡在哪、往哪改」差距導引（直接服務 M0 重設）。
  - BackToM0Button: Button / required（FAIL 時）/ 「回 M0 重設進場」→ New Run 帶差距 context。
- **states**:
  - default: 逐條綠/紅 + 差距。
  - loading: 列 skeleton。
  - empty: IS 未跑 → 「執行 validate is」CTA（橋接 CLI）。
  - error: inline error + 重試。
- **copy_constraints**: 條件名 ≤ 16 字；差距含正負號 + 單位。

### Section: oos_sealed_vault

- **layout**: 鎖定面板（IS 未過時整段上鎖 + lock icon）。
- **elements**:
  - LockState: Locked panel / required / IS 未過 → 灰鎖 + 「OOS sealed：前置 gate 未過前不可讀/不可跑」。
  - AccessLogNote: Caption / required / 「每次存取 OOS 計次留痕，反映到 DSR/晉升資格」。
  - UnsealCta: Button / required（IS PASS 時）/ 「解封並執行 validate oos（僅一次）」。
  - ThrottleNote: Inline warning / optional / 提交次數/試驗預算超限 → 擋關「已試 N 次，DSR 扣到剩餘顯著性」。
- **states**:
  - locked(default): IS 未過 → 上鎖、CTA disabled。
  - unlocked: IS PASS → 解封 CTA 可點。
  - throttled: 超限 → 擋關 + 回 M0。
  - error: inline error + 重試。
- **copy_constraints**: 鎖定說明 ≤ 40 字。

### Section: wfa_fold_view

- **layout**: 上 IS-vs-OOS scatter，下 fold 一致性表（母 run 收子 fold）。
- **elements**:
  - IsOosScatter: ScatterChart / required / X=IS Sharpe、Y=OOS Sharpe + y=x 對角線；上方=穩健（沿用 Panel E）。
  - FoldTable: DataTable / required / 各 fold 的 IS/OOS Sharpe + purge/embargo gap + 一致性（Geist Mono）。
  - RobustLegend: Legend / required / 穩健（上方 gain）/ 衰退（下方 loss）色+文字雙編碼。
- **states**:
  - default: scatter + fold 表。
  - loading: skeleton。
  - empty: OOS 未跑 → 鎖定提示（隸屬 vault）。
  - error: inline error + 重試。
- **copy_constraints**: 軸標 ≤ 20 字；fold 列 Geist Mono。

### Section: overfitting_redline

- **layout**: 3-up KPI（PBO / DSR / MTRL）+ 紅線判定。
- **elements**:
  - PboKpi: KPI Card / required / PBO 值；> 0.5 → 卡轉 error 色 + 文字「過擬合風險」（雙編碼）。
  - DsrKpi: KPI Card / required / DSR（吃 trials deflate）；< 1.0 → warning/error + 文字。
  - MtrlKpi: KPI Card / required / Min Track Record Length（月）。
  - RedlineVerdict: Banner / required / 「PBO>0.5 或 DSR<1.0 或 OOS<預登記門檻 → 自動 FAIL 擋 approved」。
- **states**:
  - default: 三 KPI + 判定。
  - loading: KPI skeleton。
  - empty: 未算 → 「待 OOS/WFA 完成」。
  - error: inline error + 重試。
- **copy_constraints**: KPI 標籤 ≤ 32 字；註記 ≤ 8 字。

### Section: commitment_signoff

- **layout**: 上承諾對照、下簽核 action。
- **elements**:
  - ExpectedVsActual ×3: Comparison / required / 預期 Sharpe/勝率/MDD vs 實際 OOS，達標 gain / 未達 loss + 文字。
  - RiskSignoff: Button Primary（白 pill）/ required / 風控核准（不可逆 approved 轉換）；退回 → 回 M0。
  - AuditNote: Caption / required / 「核准寫 promotion_audit：誰/何時/憑哪組 metrics/哪個 run snapshot」。
- **states**:
  - default: 紅線全綠時簽核可點。
  - disabled: 任一 gate 未過 → 簽核 disabled + tooltip 列阻擋原因。
  - loading: 簽核轉 spinner。
  - error: inline error + 重試。
- **copy_constraints**: 按鈕 ≤ 6 字；對照含正負號。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 自 candidate run 載入 gate_state → stepper 反映位置；未選 candidate → empty CTA。
2. is_gate_checklist 逐條判定：任一 FAIL → 下游全鎖、計入試驗次數、FailHint 導回 M0（ADR-017 現況）。
3. IS 全綠 PASS → oos_sealed_vault 解封（每次存取計次）；超限 → throttled 擋關回 M0。
4. 執行 validate oos（僅一次）+ WFA/CPCV → wfa_fold_view + overfitting_redline 計算。
5. 紅線命中（PBO>0.5 / DSR<1.0 / OOS<門檻）→ 自動 FAIL、擋 approved、寫 promotion_audit(FAIL)、回 M0。
6. 全數通過 → commitment_signoff 承諾對照 → 風控核准 → status=approved、寫 audit、解鎖 Promote 強制 paper 觀察期。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | stepper 全寬；checklist + vault 兩欄；scatter/redline 全寬 | sidebar 展開 |
| Tablet (768–1279px) | 單欄堆疊；KPI 3 欄或 2+1 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | 全部單欄；fold 表橫向捲動；scatter 觸控 tooltip | signoff 固定底部 |

### 資料更新策略

- gate_state / validation 為離線批次產物 → 快取 TTL 300s；手動 refresh 失效重撈。
- 狀態轉換（IS PASS / OOS unseal / approved）為後端不可逆寫入，前端反映後鎖定。
- OOS 存取計次與 trials_count 寫回後端，DSR 由後端 deflate 回算。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `runs`（gate_state / validation_status / trials_count / is_oos_sealed）+ `validation_runs` + `promotion_audit`。
- **endpoints**:
  - GET `/api/research/validate/:run_id/gate-state` — 狀態機位置 + IS gate 逐條 + trials + power gauge。
  - POST `/api/research/validate/:run_id/is` — 執行 IS gate 判定（gate_state.py）。
  - POST `/api/research/validate/:run_id/oos` — 解封並執行 OOS（僅一次，計次留痕）；前置 gate 未過回 423 Locked。
  - GET `/api/research/validate/:run_id/wfa` — WFA fold + IS-vs-OOS scatter。
  - GET `/api/research/validate/:run_id/redline` — PBO/DSR/MTRL + 紅線判定。
  - POST `/api/research/validate/:run_id/signoff` — 風控核准 → approved + 寫 promotion_audit。
- **error_cases**:
  - 未選 candidate：gate_status_header empty + CTA。
  - OOS 前置未過（423 Locked）：vault 維持鎖定，提示先過 IS/WFA。
  - 紅線 FAIL：自動擋 signoff，commitment_signoff disabled。
  - 提交超限（429）：throttled 擋關 + 回 M0。
  - 網路錯誤：section 級 inline error + 重試。

---

## [EXCEPTION TO GLOBAL RULES]

- IS-vs-OOS scatter 與 fold 表沿用既有漲跌/PASS-FAIL 雙編碼（gain/loss + ✓/✗），不引入新彩色語彙。
- 其餘完全遵循 Global v2.0（Grok 單色 dark、flat 1px border、Geist Mono、白環 focus）。
- 重定位說明：本頁取代原監控區 Panel E 統計驗證（舊 route `/dashboard/validation` 唯讀展示，對應頁已自 `pages/` 移除）。Panel E 圖型（IS-vs-OOS scatter）複用、但語意從「監控唯讀」升級為「研究迴圈 gate 工作流」；舊 teal token（#22D3EE/#243044）一併收斂為 Global v2.0 單色（§10 GAP-4）。

---

## [ACCEPTANCE CRITERIA]

- [ ] 6 個 section（status_header / is_gate / oos_vault / wfa_fold / redline / signoff）功能正常。
- [ ] gate_status_header stepper 正確反映 IS→WFA→OOS 不可逆狀態（已過/當前/未解鎖，色+文字雙編碼）。
- [ ] is_gate_checklist 逐條綠/紅 + 差距值；FAIL 導回 M0 帶 context（服務 ADR-017）。
- [ ] oos_sealed_vault 在 IS 未過前整段上鎖、CTA disabled；存取計次留痕；超限 throttled 擋關。
- [ ] wfa_fold_view 含 IS-vs-OOS scatter（y=x 對角線）+ fold 一致性表（purge/embargo）。
- [ ] overfitting_redline：PBO>0.5 或 DSR<1.0 或 OOS<門檻 → 自動 FAIL 擋 approved。
- [ ] commitment_signoff 自動承諾對照；任一 gate 未過則簽核 disabled；核准寫 promotion_audit。
- [ ] 取代 Panel E（唯讀→工作流），舊 teal token 收斂為 v2.0 單色。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；表格橫向捲動）。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI 數值 AAA；focus 白環。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影。
