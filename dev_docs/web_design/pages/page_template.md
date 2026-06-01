# Page Layer Template

> 每個頁面一份。對應 `guides/vibe_coding_build_strategy.md` → Step 5。
> 填完後，將此文件貼入 `assembly/PIPELINE_ORCHESTRATOR.md` 的 PAGE SPECIFICATION 區段。

---

## [PAGE META]

- **page_name**: {頁面名稱}
- **route_path**: /{path}
- **page_type**: {dashboard / list / detail / form / landing / ...}
- **primary_goal**: {這個頁面的主要目的是什麼？}
- **secondary_goal**: {次要目的（選填）}
- **target_users**:
  - 主要：{主要使用者}
  - 次要：{次要使用者}
- **entry_point**: {用戶從哪裡進入這個頁面？}
- **expected_time_on_page**: {用戶預期停留時間}

---

## [STRUCTURE: SECTIONS]

> 由上至下列出頁面的功能區塊，通常 5-7 個。

1. **{Section Name}**
   - section_type: {hero / action_cards / list / stats / form / ...}
   - section_purpose: {這個區塊要達成什麼}

2. **{Section Name}**
   - section_type: {type}
   - section_purpose: {purpose}

3. **{Section Name}**
   - section_type: {type}
   - section_purpose: {purpose}

---

## [SECTION COMPONENT SPEC]

> 每個 Section 的詳細元件規格。

### Section: {Section Name}

- **layout**: {1-column / 2-column grid / sidebar + main / ...}
- **elements**:
  - {Element 1}: {Type} / {required|optional} / {描述}
  - {Element 2}: {Type} / {required|optional} / {描述}
- **states**:
  - default: {正常顯示}
  - hover: {Hover 行為}
  - loading: {載入狀態，例：skeleton}
  - error: {錯誤狀態}
  - empty: {無資料狀態}
  - disabled: {停用狀態（如適用）}
- **copy_constraints**: {文案長度限制，例：標題最多 30 字}

### Section: {Section Name}

- **layout**: {佈局}
- **elements**: {...}
- **states**: {...}

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. {頁面載入 → 取得資料}
2. {用戶操作 A → 結果}
3. {用戶操作 B → 結果}

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop ({寬度}+) | {描述} | |
| Tablet ({寬度}) | {描述} | {例：側邊欄預設收合} |
| Mobile ({寬度}-) | {描述} | {例：改為單欄堆疊} |

### 資料更新策略

- {例：列表每 30 秒自動更新}
- {例：通知 WebSocket 即時推送}

---

## [DATA & API]

- **uses_api**: {true / false}
- **endpoints**:
  - GET `{endpoint}` — {用途}
  - POST `{endpoint}` — {用途}
- **error_cases**:
  - 網路錯誤：{處理方式}
  - API 錯誤：{處理方式}
  - 權限不足：{處理方式}

---

## [EXCEPTION TO GLOBAL RULES]

> 這個頁面需要違反 Global Design System 的地方。盡量最小化。

- {例：此頁面使用全寬 Hero，不受 Grid 最大寬度限制}
- 若無例外：「無特殊例外，完全遵循 Global System Prompt 規範。」

---

## [ACCEPTANCE CRITERIA]

> 驗收條件，對照 `guides/quality_checklist.md`。

- [ ] 所有 Section 功能正常
- [ ] 所有狀態已實作（default / hover / loading / error / empty）
- [ ] RWD 行為符合上方定義
- [ ] 符合 Design System 視覺規範
- [ ] 效能指標達標
- [ ] {其他專案特定條件}
