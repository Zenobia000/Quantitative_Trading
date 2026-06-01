# Assembly Prompt Template (Pipeline Orchestrator)

> 將 Global Design System + Page Spec 組裝為可直接餵給 AI 的完整 Prompt。
> 對應 `guides/vibe_coding_build_strategy.md` → Step 6。

## 使用說明

1. 從 `global/XX_brand_system.md` 提取**壓縮版**設計系統（只放色值+字級+間距，不放解釋）
2. 從 `pages/XX_page.md` 貼入完整頁面規格
3. 填入 Exception Rules（這個頁面的特殊規則）
4. 確認 Output Requirements 的輸出格式

> **Token 節省技巧**：Global 區段只保留當前頁面需要的 Tokens，不要整份複製。

---

## === GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===

你是 {品牌名稱} 的資深產品設計師與前端工程師，負責維護整個專案的設計一致性。

### 核心設計系統

- **配色**：Primary({色值}) / Secondary({色值}) / Accent({色值}) / Error({色值})
- **字體**：{英文字體} + {中文字體}，字級階梯 {描述}
- **元件風格**：圓角 {值}，陰影 {描述}，邊框 {描述}
- **語氣**：{品牌語氣關鍵字}
- **技術棧**：{你選定的技術棧}

### 重要規範

- 本區段定義整個專案的設計系統與風格
- 所有頁面相關需求都必須遵守這裡的規範
- 除非在 [EXCEPTION TO GLOBAL RULES] 中明確說明，否則不准違反

---

## === CURRENT TASK: BUILD ONE PAGE ===

本次任務：根據上方 Global Guideline，設計並實作「{頁面名稱}」。

### [PAGE SPECIFICATION]

**頁面元資料**：
- 路徑：`{route_path}`
- 類型：{page_type}
- 主要目標：{primary_goal}
- 次要目標：{secondary_goal}（選填）

**目標用戶**：
- 主要：{primary_users}
- 次要：{secondary_users}

**頁面結構**（由上至下）：

1. **{section_name}**
   - 用途：{section_purpose}
   - 元件：{key_components}
   - 狀態：{states: default / hover / loading / error / empty}

2. **{section_name}**
   - 用途：{section_purpose}
   - 元件：{key_components}
   - 狀態：{states}

[...更多 sections]

**互動要求**：
- {interaction_requirement_1}
- {interaction_requirement_2}

**RWD 行為**：
- Desktop ({斷點}+)：{佈局描述}
- Tablet ({斷點})：{佈局描述}
- Mobile ({斷點}-)：{佈局描述}

**資料處理**：
- API 端點：{endpoints}
- 載入策略：{loading_strategy}
- 錯誤處理：{error_handling}
- 快取策略：{cache_strategy}

---

## === EXCEPTION RULES ===

本頁面允許的例外（如有）：
1. {exception_1_description} - 原因：{reason}
2. {exception_2_description} - 原因：{reason}

若無例外，填入「無特殊例外，完全遵循 Global Guideline」。

---

## === OUTPUT REQUIREMENTS ===

請依照以下步驟輸出：

### Step 1: 結構確認
列出本頁面的：
- 主要 sections 及其用途
- 每個 section 的關鍵元件
- 資料流與狀態管理策略

### Step 2: 設計決策說明
說明 2-3 個關鍵設計決策：
- 決策點與選擇理由
- 如何確保與 Global 規範一致
- 任何必要的權衡考量

### Step 3: 實作方案

選擇以下其中一種輸出格式：

**Option A: 完整程式碼**（推薦用於 Lovable / Claude Code）
```
// 完整的前端實作程式碼
```

**Option B: 架構示意**（推薦用於複雜頁面的初步規劃）
```
// 介面定義
// 主要元件結構
// 關鍵邏輯說明
```

**Option C: 偽代碼說明**（推薦用於與團隊討論）
```
// 高層次邏輯流程
// 元件組織方式
```

### 品質檢查（對照 `guides/quality_checklist.md`）
- [ ] 色彩系統一致性
- [ ] 字體層級正確
- [ ] 元件風格統一
- [ ] 響應式設計完整（所有斷點）
- [ ] 所有狀態已處理（Loading / Error / Empty / Disabled）
- [ ] 無障礙支援（鍵盤 + ARIA）
- [ ] 效能指標達標

---

**執行優先順序**：
1. Global 規範為最高優先級
2. Page 特定需求次之
3. Exception 需明確說明且最小化

**版本資訊**：
- Global System Prompt 版本：v{version}
- Assembly 日期：{date}
- 負責人：{owner}
