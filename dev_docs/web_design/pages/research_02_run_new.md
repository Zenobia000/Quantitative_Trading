# Page Layer Spec — New Run 設定頁 (Research · New Run Config)

> 來源：`03_uiux_benchmark_and_reinforcement_plan.md` §4.2「設定並執行一次回測」flowchart + §6.2 parameter form/CodeEditor + §5.1 roadmap（M3）。
> 對應後端：`run_configs` schema（IS/OOS + 成本攤平 + engine + range/step + hypothesis）、CLI `backtest-run`。
> 繼承 Global v2.0（Grok 單色 dark / Geist Mono 數值 / bg-code #161616 / 白環 focus / 漲跌雙編碼）。

---

## [PAGE META]

- **page_name**: New Run 設定頁 (New Run Config)
- **route_path**: /research/runs/new
- **page_type**: form
- **primary_goal**: 讓研究者在單頁三段式表單定義「這個 run 假設了什麼」——預先註冊假設、參數化（值或 range/step）、成本+引擎+IS/OOS 區間——並在提交前估算 run 數與成本後異步提交。
- **secondary_goal**: 用「假設預先註冊」強制先承諾預期門檻，移除事後編故事空間；用提交前估算抑制暴力搜參。
- **target_users**:
  - 主要：量化研究者（正進行 ADR-017 M0 進場重設迭代）
  - 次要：風控（審查 OOS 區間是否由系統鎖死、成本假設是否攤平）
- **entry_point**: Runs Table「New Run」CTA；策略庫「新建策略 / 衍生新變體」；FirstRunEmptyState 主 CTA；Cmd-K「新建 run」。
- **expected_time_on_page**: 5–15 分鐘（填假設 → 調 13 參數 → 設成本/引擎/期間 → 估算 → 提交）

---

## [STRUCTURE: SECTIONS]

> 單頁三段式（四 sub-section）+ 提交列，由上至下共 5 個區塊。

1. **hypothesis_section**
   - section_type: form (pre-registration)
   - section_purpose: 單一論點 + 預期 Sharpe / 勝率 / 最大 DD 門檻（必填），提交 OOS 前鎖定，完成後自動對照。

2. **parameters_section**
   - section_type: form (parameter pills) + CodeEditor
   - section_purpose: 13 參數逐項 input（值 或 range/step toggle）+ universe filter；策略邏輯以 CodeEditor 唯讀/可編輯呈現，邏輯與參數分離。

3. **cost_engine_section**
   - section_type: form
   - section_purpose: 台股成本攤平（手續費 / 滑點 / 漲跌停 / T+2）+ 引擎選擇（zipline / vectorbt）+ bundle 快照 ref。

4. **period_section**
   - section_type: form
   - section_purpose: IS 區間研究者自選 / OOS 區間系統鎖死（sealed vault），明示哪段不可由使用者調整。

5. **submit_bar**
   - section_type: action / estimate
   - section_purpose: 提交前估算「will run N configs, est M min」+ 顯示累計試驗數（餵 DSR），Submit 觸發 schema 驗證與異步提交。

---

## [SECTION COMPONENT SPEC]

### Section: hypothesis_section

- **layout**: 全寬卡，2 欄（左論點 textarea，右預期門檻三欄）。
- **elements**:
  - ThesisInput: Textarea / required / 單一可測試論點（≤ 200 字），空值不可提交。
  - ExpectedSharpe: Number input / required / 預期 Sharpe 門檻（Geist Mono）。
  - ExpectedWinRate: Number input / required / 預期勝率 %。
  - ExpectedMaxDD: Number input / required / 可接受最大回撤 %（恆負，loss 色提示）。
  - PreRegNote: Caption / required / 「提交後門檻鎖定，OOS 完成自動紅/綠對照」。
- **states**:
  - default: 空表單，required 欄位標星。
  - error: 缺漏欄位逐欄紅框 + 原因文案（停留本頁不丟輸入）。
  - disabled: 衍生變體時預填 baseline 假設，可編輯。
- **copy_constraints**: 論點 ≤ 200 字；門檻數值含單位。

### Section: parameters_section

- **layout**: 上 parameter pill grid（Desktop 3–4 欄），下 CodeEditor（可摺疊）。
- **elements**:
  - ParamPill ×13: Input pill / required / 每參數含「值 / range-step」toggle；range 模式顯示 start/stop/step 三欄。
  - UniverseFilter: Multi-select / required / 台股 universe 篩選（產業 / 市值 / 流動性）。
  - CodeEditor: Monaco（bg-code #161616 / Geist Mono / 單色語法高亮微調 / 唯讀 diff 模式）/ optional / 策略邏輯，邏輯與參數分離；直接用 Monaco 預設 dark 微調。
  - ParamDiffNote: Caption / optional / 衍生變體時標「相對 baseline 改了哪幾個輸入」。
- **states**:
  - default: 13 參數預填預設值（或 baseline）。
  - error: 參數越界 / range 非法（start>stop）逐欄紅框。
  - loading: CodeEditor 載入 skeleton。
- **copy_constraints**: 參數 label ≤ 16 字；range 三欄為數值。

### Section: cost_engine_section

- **layout**: 全寬卡，2 欄（左成本攤平，右引擎 + bundle）。
- **elements**:
  - Commission: Number input / required / 手續費率。
  - Slippage: Number input / required / 滑點假設。
  - PriceLimitToggle: Switch / required / 漲跌停限制（台股特有）。
  - SettlementNote: Label / required / T+2 交割（系統固定，唯讀說明）。
  - EngineSelect: SegmentedControl / required / zipline / vectorbt（雙引擎對拍）。
  - BundleRef: Select / required / 資料快照 bundle ref（鎖版本，供 reproduce）。
- **states**:
  - default: 預填台股標準成本假設。
  - error: 成本為負 / bundle 不存在 → inline error。
- **copy_constraints**: 成本 label ≤ 12 字；引擎選項固定「zipline / vectorbt」。

### Section: period_section

- **layout**: 全寬卡，2 欄（左 IS 可選，右 OOS 鎖死）。
- **elements**:
  - IsRangePicker: DateRange / required / IS 區間研究者自選；不可選未來日。
  - OosLockedRange: Read-only range + lock icon / required / OOS 由系統依協定鎖死，明示「sealed vault：前置 gate 未過前不可讀/不可跑」。
  - OosExplainNote: Caption / required / 解釋為何 OOS 不可手動設（防偷看調參）。
- **states**:
  - default: IS 可編輯、OOS 鎖定 + lock icon。
  - error: IS start>end / 與 OOS 重疊 → inline error。
- **copy_constraints**: 說明文案 ≤ 40 字；日期 ISO `YYYY-MM-DD`。

### Section: submit_bar

- **layout**: sticky bottom action bar，左估算文字、右 Submit。
- **elements**:
  - EstimateLabel: Text (Geist Mono) / required / 「will run N configs, est M min」，sweep 模式 N>1。
  - TrialsBadge: Badge / required / 「此參數空間累計試驗 N 次｜當前 DSR x.xx」（餵防過擬合）。
  - SubmitButton: Button Primary（白 pill）/ required / 觸發 RunConfig schema 驗證 → 異步提交。
  - SubmitGuard: Inline warning / optional / N 過大時警示「config 數過多，建議收窄 range」。
- **states**:
  - default: 估算即時更新，Submit 可點。
  - loading: Submit 轉 spinner，禁重複提交。
  - error: schema 驗證失敗 → 滾到對應紅框 section。
  - disabled: required 未齊時 Submit disabled + tooltip 列缺項。
- **copy_constraints**: 估算文案 ≤ 32 字；按鈕 ≤ 4 字（「提交」）。

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 進入頁面 → 空表單（或 baseline 預填）→ 即時估算 N=1 configs。
2. 任一參數切 range/step → 估算 N 重算（笛卡爾積），TrialsBadge 預示提交後試驗數。
3. 點 Submit → RunConfig Pydantic schema 驗證：失敗→inline 逐欄紅框留本頁；通過→寫 `run_configs`、產 run_id（git-sha+bundle+序號）、status=queued。
4. 提交成功 → 跳轉 Run Report `/research/runs/:id`（loading/queue banner 態），或返回 Runs Table 看 queue。
5. 衍生變體進入時，hypothesis/parameters/cost 預填 baseline，ParamDiffNote 標差異。

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (≥1280px) | 各 section 2 欄；submit_bar sticky bottom | sidebar 展開；CodeEditor 並排 |
| Tablet (768–1279px) | section 單欄；parameter pill 2 欄 | sidebar→drawer（@<1024px） |
| Mobile (≤767px) | 全部單欄堆疊；parameter pill 1 欄 | CodeEditor 改全寬可摺疊；submit_bar 固定底部 |

### 資料更新策略

- 估算（N configs / est min）為前端本地計算（笛卡爾積 × 單 run 估時），不打 API。
- bundle / universe 選項清單 page load 一次撈，快取 TTL 300s。
- 提交為異步：寫 run_configs 後立即回 run_id，不阻塞 UI。

---

## [DATA & API]

- **uses_api**: true
- **主要資料表**: `run_configs`（寫入）+ `runs`（產 run_id）。
- **endpoints**:
  - GET `/api/research/bundles` — 可用 bundle 快照清單。
  - GET `/api/research/universe-filters` — universe 篩選選項。
  - POST `/api/research/runs` — 提交 run config（body=RunConfig schema）→ 回 run_id + status=queued；驗證失敗回 422 逐欄錯誤。
  - GET `/api/research/runs/estimate?...` — （選用）後端精算 N configs / est min。
- **error_cases**:
  - schema 驗證失敗（422）：逐欄 inline error，停留本頁不丟輸入。
  - 網路錯誤：submit_bar inline error + 可重試，表單狀態保留。
  - bundle 不存在 / 過期：cost_engine_section inline error。
  - 權限不足：導向登入。

---

## [EXCEPTION TO GLOBAL RULES]

- CodeEditor 使用 Monaco 預設 dark 主題微調的語法高亮 — 屬「chrome 單色之上、code 區受控例外」，僅在 code 內容區，不擴散至頁面 chrome。
- 其餘完全遵循 Global v2.0（Grok 單色 dark、flat 1px border、Geist Mono 數值、白環 focus、漲跌雙編碼）。

---

## [ACCEPTANCE CRITERIA]

- [ ] 5 個 section（hypothesis / parameters / cost_engine / period / submit_bar）功能正常。
- [ ] 假設三門檻為 required，空值不可提交（強制預先註冊）。
- [ ] 13 參數支援「值 / range-step」toggle；range 非法（start>stop）即時擋。
- [ ] OOS 區間系統鎖死（lock icon + 說明），使用者不可手動編輯（sealed vault 語意）。
- [ ] 提交前估算「will run N configs, est M min」+ TrialsBadge 顯示累計試驗數與 DSR。
- [ ] Submit 觸發 RunConfig schema 驗證；失敗逐欄 inline 紅框、停留本頁不丟輸入。
- [ ] 提交成功產 run_id（git-sha+bundle+序號）、status=queued，跳 Run Report。
- [ ] CodeEditor 語法高亮例外僅限 code 區，不汙染 chrome 單色。
- [ ] RWD 三斷點正確（@<1024px sidebar→drawer；section 降欄）。
- [ ] 數值 Geist Mono tabular-nums；文字 AA、KPI/門檻數值 AAA；focus 白環。
- [ ] dark-first、flat 1px border #2A2A2A 無陰影。
