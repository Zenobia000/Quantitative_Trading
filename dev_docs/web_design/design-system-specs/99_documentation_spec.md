# 99_Documentation — 治理、交付、變更管理

> 設計系統如果沒有治理，只會越來越胖、越來越亂，最後死掉。
> 這區是「工廠規章 + 變更公告」。

---

## 目錄

1. [Do / Don't 規範](#1-do--dont-規範)
2. [元件貢獻規範](#2-元件貢獻規範)
3. [Handoff Spec（交付規格）](#3-handoff-spec交付規格)
4. [Design QA Checklist](#4-design-qa-checklist)
5. [Change Log 規範](#5-change-log-規範)
6. [Version 策略](#6-version-策略)
7. [Ownership & Review](#7-ownership--review)
8. [Deprecation 流程](#8-deprecation-流程)
9. [Design ↔ Dev 同步機制](#9-design--dev-同步機制)

---

## 1. Do / Don't 規範

### 全域規則（適用所有元件）

| ✅ Do | ❌ Don't |
|-------|---------|
| 使用 Design Token，不寫 magic number | 直接寫 `#3B82F6` 或 `padding: 13px` |
| 遵循 Spacing Scale（4px 倍數） | 用 5px、7px、13px 這種非系統值 |
| 每個互動元素都有 hover + focus 狀態 | 只做 default 狀態就交付 |
| 空狀態、錯誤狀態、Loading 都要設計 | 只設計 happy path |
| 文案簡潔、動詞開頭 | 按鈕寫「確定」「提交」這種模糊詞 |
| 一頁只有一個 Primary CTA | 放 3 個 Primary Button 搶注意力 |
| 使用語意色（success/error） | 用品牌色表示錯誤 |
| Icon + Text 配對（非 icon-only 優先） | 只用 icon 沒有任何文字提示 |
| Mobile 先設計，再往上擴展 | 只做 Desktop，Mobile 用縮小版 |
| 圖片有 alt text / aria-label | 純裝飾圖片佔用 screen reader |

### 元件級 Do / Don't

→ 詳見 `01_components_spec.md` 第 8 節

---

## 2. 元件貢獻規範

### 2.1 新增元件流程

```
Step 1: 提案
  ├── 填寫「元件提案表」（見下方）
  ├── 確認不與現有元件重複
  └── 確認至少有 2 個以上使用場景

Step 2: 設計
  ├── 遵循命名規範（01_components_spec.md §6）
  ├── 完成所有 variants × states × sizes
  ├── 撰寫 Do / Don't
  └── 使用 Foundation tokens（不造新 token）

Step 3: 審核
  ├── Design review（設計負責人）
  ├── Dev review（工程確認可實作）
  └── Accessibility check（對比度、鍵盤操作）

Step 4: 發布
  ├── 加入 Figma Component Library
  ├── 更新 Component Inventory
  ├── 撰寫 Change Log
  └── 通知相關人員
```

### 2.2 元件提案表

```markdown
## 元件提案

**元件名稱**：
**類別**：（Action / Input / Data Display / Feedback / Navigation）
**提案人**：
**日期**：

### 為什麼需要？
（描述使用場景，至少 2 個）

### 與現有元件的差異
（為什麼不能用現有元件解決？）

### 初步規格
- Variants：
- States：
- Sizes：

### 參考
（Figma link / Screenshot / 競品參考）
```

### 2.3 Breaking Changes 規則

```
Breaking Change 定義：
  - 刪除元件
  - 刪除 variant / prop
  - 改變預設行為
  - 改變 token 名稱
  - 改變元件 API（prop 名稱、type）

Breaking Change 處理：
  1. 標記為 @deprecated（至少 1 個版本週期）
  2. 提供遷移指引
  3. 在 Change Log 中標記 [BREAKING]
  4. 主動通知受影響的專案/頁面
```

---

## 3. Handoff Spec（交付規格）

### 3.1 每個設計交付時必須包含

```
✅ 基本規格
  □ 所有尺寸使用 Design Token（不是 pixel 值）
  □ 間距使用 Spacing Token
  □ 色彩使用 Color Token
  □ 字型使用 Typography Token

✅ 狀態覆蓋
  □ Default 狀態
  □ Hover 狀態
  □ Focus 狀態
  □ Active / Pressed 狀態
  □ Disabled 狀態
  □ Loading 狀態
  □ Error 狀態
  □ Empty 狀態
  □ Success 狀態（若適用）

✅ RWD 行為
  □ Desktop 版面（> 1024px）
  □ Tablet 版面（640px - 1024px）
  □ Mobile 版面（< 640px）
  □ 斷點轉換行為描述

✅ 互動與動效
  □ 動效 trigger（什麼操作觸發）
  □ Duration + Easing（使用 Motion Token）
  □ 動效方向（from where to where）

✅ 文案
  □ 所有文案已定稿（非 Lorem ipsum）
  □ 錯誤訊息已定義
  □ 空狀態文案已定義
  □ Loading 文案已定義（若需要）

✅ 可及性
  □ 對比度檢查通過（AA 標準）
  □ Focus 順序已標示
  □ ARIA labels 已標示（icon-only buttons、images）
  □ 表單 error 關聯已標示
```

### 3.2 Handoff 交付格式

```
推薦工具：
  - Figma Dev Mode（內建）
  - Figma MCP Server（AI 讀取 → 直接生程式碼）
  - Zeplin / Storybook（若團隊已有）

Figma 標註規範：
  - 使用 Auto Layout（不要用絕對定位）
  - 使用 Variables（不要用 hard-coded 值）
  - Frame 命名有語意（不要用 Frame 432）
  - 元件使用 Library instances（不要 detach）
```

---

## 4. Design QA Checklist

### 4.1 新元件 QA

| # | 檢查項 | 通過 |
|---|--------|------|
| 1 | 所有 variants 完整 | ☐ |
| 2 | 所有 states 完整（default/hover/focus/active/disabled/loading/error） | ☐ |
| 3 | 所有 sizes 完整 | ☐ |
| 4 | Token 使用正確（無 hard-coded 值） | ☐ |
| 5 | Auto Layout 設定正確（拉伸不爆版） | ☐ |
| 6 | 命名符合規範（Category / Name / Variant） | ☐ |
| 7 | Accessibility 對比度 >= 4.5:1（一般文字） | ☐ |
| 8 | Focus state 有 visible focus ring | ☐ |
| 9 | Do / Don't 已撰寫 | ☐ |
| 10 | 已加入 Component Library | ☐ |

### 4.2 新頁面 QA

| # | 檢查項 | 通過 |
|---|--------|------|
| 1 | 字級、間距符合 Foundation tokens | ☐ |
| 2 | 所有元件使用 Library instance（非 detach） | ☐ |
| 3 | RWD 三個斷點都有設計 | ☐ |
| 4 | 空狀態、錯誤狀態、Loading 狀態齊全 | ☐ |
| 5 | 所有互動元素有 hover/focus 狀態 | ☐ |
| 6 | 文案已定稿（非 placeholder） | ☐ |
| 7 | 對比度通過 AA 標準 | ☐ |
| 8 | Tab 順序合理 | ☐ |
| 9 | 使用正確的 Template 結構 | ☐ |
| 10 | Handoff spec 已完成 | ☐ |

### 4.3 工程實作驗收

| # | 檢查項 | 通過 |
|---|--------|------|
| 1 | 視覺與設計稿一致（pixel-level） | ☐ |
| 2 | Token 對應正確（非 hard-coded） | ☐ |
| 3 | RWD 行為正確 | ☐ |
| 4 | 所有狀態可操作（hover/focus/disabled/error） | ☐ |
| 5 | 鍵盤操作可用（Tab/Enter/Esc） | ☐ |
| 6 | 動效正確（duration/easing/trigger） | ☐ |
| 7 | Empty/Error/Loading 狀態正確 | ☐ |
| 8 | 效能合格（LCP < 2.5s, CLS < 0.1） | ☐ |

---

## 5. Change Log 規範

### 格式

```markdown
## [v1.2.0] - 2026-03-17

### Added
- 新增 DatePicker 元件（single / range mode）
- 新增 Empty State pattern for search results

### Changed
- Button: hover 透明度從 0.9 改為 0.85
- Card: 預設 padding 從 16px 改為 20px

### Fixed
- Toast: 修正 mobile 上位置偏移問題
- Select: 修正 keyboard navigation 在 Chrome 上的問題

### Deprecated
- Badge variant "outline" → 請改用 "outlined"（將在 v2.0 移除）

### Breaking ⚠️
- [BREAKING] Token 重新命名：color.bg.card → color.bg.surface
  - 遷移：全域搜尋替換
  - 影響範圍：所有使用 Card 背景色的頁面
```

### 紀錄規則

```
1. 每次發布都寫 Change Log（不管多小）
2. 按 Added / Changed / Fixed / Deprecated / Breaking 分類
3. Breaking changes 必須有遷移指引
4. 標注影響範圍（哪些頁面/元件受影響）
5. Change Log 保持時間倒序（最新在最上）
```

---

## 6. Version 策略

### Semantic Versioning

```
v{MAJOR}.{MINOR}.{PATCH}

MAJOR：Breaking changes（token 改名、元件刪除、API 改變）
MINOR：新增功能（新元件、新 variant、新 pattern）
PATCH：修復（Bug fix、微調、文案修正）

範例：
  v1.0.0 → 初始發布
  v1.1.0 → 新增 DatePicker
  v1.1.1 → 修正 DatePicker 在 Safari 的 bug
  v2.0.0 → Token 大規模重新命名
```

### 發布節奏

```
建議：
  - PATCH：隨時（修復即發布）
  - MINOR：每 2 週一次（sprint 結束時）
  - MAJOR：每季一次（需要遷移計畫）
```

---

## 7. Ownership & Review

### 7.1 角色定義

| 角色 | 職責 |
|------|------|
| Design System Lead | 整體方向、Breaking changes 審核、版本策略 |
| Component Owner | 負責特定元件的設計與維護 |
| Token Owner | 維護 Foundation tokens、確保一致性 |
| Documentation Owner | 維護文件、Change Log、Do/Don't |
| Engineering Liaison | 確保設計 ↔ 工程同步 |

### 7.2 Review 流程

```
新元件 / Breaking Change：
  → Component Owner 提案
  → Design System Lead 審核
  → Engineering Liaison 確認可行性
  → Design QA
  → 發布

Minor Change（新 variant、修正）：
  → Component Owner 直接修改
  → Peer review（另一位 designer）
  → 發布

Patch（Bug fix）：
  → 直接修復
  → 記錄在 Change Log
```

---

## 8. Deprecation 流程

```
Step 1: 標記 @deprecated
  - 在 Figma 元件加上 [DEPRECATED] prefix
  - 在文件中標記 Deprecated 並說明替代方案

Step 2: 通知
  - 在 Change Log 中記錄
  - 通知受影響的團隊/專案

Step 3: 緩衝期
  - 至少保留 1 個 MINOR 版本週期
  - 大範圍影響的：保留 1 個 MAJOR 版本週期

Step 4: 移除
  - 在下一個 MAJOR 版本中移除
  - 確認所有使用方已遷移
```

---

## 9. Design ↔ Dev 同步機制

### 9.1 同步工具鏈

```
Token 同步：
  Figma Variables
    ↓ Tokens Studio (plugin)
  tokens.json (W3C Design Token 格式)
    ↓ Style Dictionary
  CSS Variables / Tailwind Config / iOS / Android
    ↓ Git PR
  Code Review → Merge → 自動部署

元件同步：
  Figma Component（設計）
    ↓ Figma MCP Server
  AI 讀取設計結構
    ↓ Claude Code / Cursor
  React Component（程式碼）
    ↓ Storybook
  視覺驗證

Code Connect（Figma 官方）：
  Figma Node ↔ Code Component 建立 mapping
    → 在 Figma Dev Mode 中直接顯示對應的程式碼
```

### 9.2 同步頻率

| 內容 | 頻率 | 方式 |
|------|------|------|
| Token 變更 | 即時 | Token Studio auto-sync |
| 新元件 | Sprint 結束 | PR + Code Review |
| Pattern 更新 | 月度 | Design Review Meeting |
| Breaking Changes | 季度 | Migration Plan |

### 9.3 衝突解決

```
設計領先（設計好了，工程還沒做）：
  → 記錄在 Backlog，標記優先級
  → 工程在下個 sprint 追上

工程領先（工程改了，設計沒更新）：
  → Code-to-Canvas（Figma MCP）同步回 Figma
  → 設計審核後更新 Library

Token 衝突（設計改了 token，工程用舊值）：
  → Token pipeline 自動偵測 diff
  → CI 警告 + PR review
```

---

## Figma 結構建議

```
📁 99_Documentation（Figma Page）
├── 📄 Do / Don't
│   ├── 全域規則
│   ├── 元件級（每個 P0 元件）
│   └── Pattern 級（Form / Table / Navigation）
├── 📄 Contribution Guide
│   ├── 新增元件流程圖
│   ├── 提案表模板
│   └── Naming Convention 速查
├── 📄 Handoff Spec
│   ├── Handoff Checklist
│   └── 標註範例
├── 📄 QA Checklist
│   ├── 元件 QA
│   ├── 頁面 QA
│   └── 工程驗收
├── 📄 Change Log
│   └── 按版本倒序排列
└── 📄 Governance
    ├── Ownership 表
    ├── Review 流程
    └── Deprecation 流程
```

---

**版本**：v1.0
**最後更新**：2026-03-17
**相關文件**：`guides/quality_checklist.md`（QA 詳細清單）
