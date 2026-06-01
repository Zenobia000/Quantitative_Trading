# 01_Components — 元件庫規格

> 頁面不是畫出來的，是裝出來的。
> 這區的核心不是「有元件」，而是「元件可控、可擴充、可維護」。

---

## 目錄

1. [元件分級架構](#1-元件分級架構)
2. [元件規格卡模板](#2-元件規格卡模板)
3. [P0 元件清單與規格](#3-p0-元件清單與規格)
4. [P1 元件清單](#4-p1-元件清單)
5. [P2 元件清單](#5-p2-元件清單)
6. [元件命名規範](#6-元件命名規範)
7. [元件 Inventory 總表](#7-元件-inventory-總表)
8. [Do / Don't 範例](#8-do--dont-範例)

---

## 1. 元件分級架構

採用 Atomic Design 分層，確保元件粒度清晰。

```
Atoms（原子）
  最小不可分割的 UI 單位
  例：Button, Input, Badge, Avatar, Icon, Tag, Checkbox, Radio, Switch, Divider

Molecules（分子）
  2-3 個 Atom 組合而成的功能單位
  例：Search Bar (Input + Button), Form Field (Label + Input + Error),
      Menu Item (Icon + Text + Badge), Stat Card (Number + Label + Trend)

Organisms（有機體）
  多個 Molecules 組成的完整區塊
  例：Navigation Bar, Data Table, Form Section, Card Grid,
      Comment Thread, Pricing Card

Templates（模板）
  → 歸入 03_Templates
```

---

## 2. 元件規格卡模板

每個元件都必須有一張「規格卡」，像產品說明書。

```markdown
### [元件名稱] Component Spec

#### Purpose（用途）
一句話說明這個元件「什麼時候用」。

#### Anatomy（結構）
列出元件的所有組成部分。
- [ ] Root container
- [ ] Leading element (icon / avatar)
- [ ] Content (label / text)
- [ ] Trailing element (icon / badge / action)

#### Props（可配置項）

| Prop | Type | Default | Options | 說明 |
|------|------|---------|---------|------|
| variant | enum | primary | primary / secondary / ghost / danger | 視覺變體 |
| size | enum | md | sm / md / lg | 尺寸 |
| disabled | boolean | false | — | 停用狀態 |
| loading | boolean | false | — | 載入狀態 |

#### States（狀態矩陣）

| State | 視覺變化 | 觸發方式 |
|-------|---------|---------|
| Default | 基準樣式 | 初始 |
| Hover | 背景加深 / 陰影增加 | 滑鼠移入 |
| Active/Pressed | 背景再加深 / 輕微縮小 | 滑鼠按下 |
| Focus | Focus ring (2px outline) | Tab 鍵 |
| Disabled | 降低 opacity 0.5 + cursor not-allowed | disabled=true |
| Loading | Spinner 取代 icon / 文字不變 | loading=true |

#### Interaction（互動規則）
- 鍵盤：Enter/Space 可觸發
- 動效：hover transition 150ms ease
- 回饋：click 有 ripple / scale 回饋

#### Accessibility
- Role: button
- aria-label: 若只有 icon 需提供
- aria-disabled: disabled 時設定
- Focus visible: 必須有 focus ring

#### Do / Don't
- ✅ 按鈕文案用動詞開頭（送出、取消、刪除）
- ❌ 不要在按鈕內放超過 2 行文字
- ✅ Danger 操作用 Danger variant
- ❌ 不要用顏色作為唯一的區分方式
```

---

## 3. P0 元件清單與規格

### 3.1 Button（按鈕）

| 維度 | 規格 |
|------|------|
| Variants | `primary` / `secondary` / `ghost` / `danger` / `link` |
| Sizes | `sm` (32px h) / `md` (36px h) / `lg` (40px h) |
| States | default / hover / active / focus / disabled / loading |
| Content | text-only / icon-left / icon-right / icon-only |
| Padding | sm: `px-3 py-1.5` / md: `px-4 py-2` / lg: `px-5 py-2.5` |
| Radius | `radius.md` (6px) |
| Font | `text.body.sm` (14px, 500) |
| Min Width | 64px（防止太窄） |
| Loading | Spinner 替換 leading icon，文字保留，disabled interaction |

### 3.2 Input（輸入框）

| 維度 | 規格 |
|------|------|
| Types | `text` / `password` / `email` / `number` / `search` / `textarea` |
| Sizes | `sm` (32px h) / `md` (36px h) / `lg` (40px h) |
| States | default / hover / focus / error / disabled / readonly |
| Anatomy | `Label` + `Input Container` + `Helper Text / Error Message` |
| Padding | `px-3 py-2` |
| Radius | `radius.md` (6px) |
| Border | default: `border.default` / focus: `border.focus` (2px) / error: `border.error` |
| Prefix/Suffix | 支援 icon / text / select（如幣別選擇） |
| Placeholder | `color.text.tertiary` |
| Character Count | 可選，右下角顯示 `{current}/{max}` |

### 3.3 Select（選擇器）

| 維度 | 規格 |
|------|------|
| Types | `single-select` / `multi-select` / `combobox`（可搜尋） |
| Sizes | sm / md / lg（同 Input） |
| States | default / hover / focus / open / disabled / error |
| Dropdown | shadow.lg, radius.lg, max-height 240px, overflow scroll |
| Options | text / icon+text / description / group header / divider |
| Selected | Checkmark icon 在右側 |
| Empty | 「無選項」或「無搜尋結果」文案 |
| Keyboard | Arrow ↑↓ 導航、Enter 選取、Esc 關閉 |

### 3.4 Card（卡片）

| 維度 | 規格 |
|------|------|
| Variants | `default` / `outlined` / `elevated` / `clickable` |
| Padding | `space.4` (16px) 或 `space.6` (24px) |
| Radius | `radius.lg` (8px) |
| Shadow | default: `shadow.sm` / hover (clickable): `shadow.md` |
| Border | outlined: `border.default` |
| Anatomy | `Header` (optional) + `Body` (required) + `Footer` (optional) |
| Header | Title + Subtitle + Action (icon button / menu) |
| Clickable | 整張卡片可點擊，hover 有 shadow + cursor pointer |

### 3.5 Modal / Dialog

| 維度 | 規格 |
|------|------|
| Variants | `default` / `destructive` / `form` |
| Sizes | `sm` (400px) / `md` (520px) / `lg` (640px) / `full` (mobile only) |
| Anatomy | `Overlay` + `Container` (Header + Body + Footer) |
| Overlay | `color.bg.overlay`, click 可關閉（destructive 除外） |
| Header | Title + Close button (X) |
| Footer | Action buttons（Primary 在右、Cancel 在左） |
| Animation | scale(0.95→1) + opacity, 200ms ease-out |
| Close | X 按鈕、Esc 鍵、Overlay 點擊 |
| Focus Trap | 開啟後 focus 鎖在 Modal 內 |
| Scroll | Body 可 scroll，Header/Footer 固定 |
| Mobile | < sm 斷點轉為 full-screen sheet（bottom-up slide） |

### 3.6 Toast / Notification

| 維度 | 規格 |
|------|------|
| Variants | `success` / `warning` / `error` / `info` / `neutral` |
| Position | 右上角（desktop）/ 頂部居中（mobile） |
| Duration | 5000ms auto-dismiss（error 不自動消失） |
| Anatomy | Icon + Message + Action (optional) + Close |
| Width | min 320px / max 420px |
| Animation | slide-in from right + fade, 300ms |
| Stack | 最多顯示 3 個，新的推舊的向下 |
| Accessibility | role="alert", aria-live="polite" |

### 3.7 Table（資料表格）

| 維度 | 規格 |
|------|------|
| Variants | `default` / `sortable` / `selectable` / `expandable` |
| States | default / loading (skeleton rows) / empty / error |
| Header | 固定在頂部（sticky）、可排序（↑↓ icon） |
| Rows | hover 背景色變化、selected 背景色 |
| Cell Types | text / number / badge / avatar+text / action buttons |
| Pagination | 底部分頁器（上一頁/下一頁/頁碼/每頁筆數） |
| Responsive | desktop 橫向表格 → mobile 轉 card list |
| Empty State | 插圖 + 文字 + CTA 按鈕 |
| Loading | 5 行 skeleton rows |
| Bulk Actions | Checkbox 全選 → 頂部 action bar 出現 |

### 3.8 Badge / Tag

| 維度 | 規格 |
|------|------|
| Badge Variants | `default` / `dot` (無文字，只有圓點) |
| Badge Sizes | `sm` (18px) / `md` (22px) |
| Tag Variants | `filled` / `outlined` / `subtle` |
| Tag Colors | neutral / primary / success / warning / error / info + 自訂色 |
| Tag Features | closable (X icon) / icon-left |
| Radius | Badge: `radius.full` / Tag: `radius.sm` |
| Font | `text.caption` (12px) |

### 3.9 Avatar

| 維度 | 規格 |
|------|------|
| Types | `image` / `initial` (首字母) / `icon` (fallback) |
| Sizes | `xs` (24px) / `sm` (32px) / `md` (40px) / `lg` (48px) / `xl` (64px) |
| Shape | Circle (`radius.full`) |
| Fallback | 有圖 → 顯示圖；無圖 → 顯示首字母（取背景色 hash）；無名 → User icon |
| Group | Avatar Stack，重疊 -8px，最多顯示 5 個 + "+N" |
| Status | 右下角狀態指示器（online/offline/busy） |

### 3.10 Tabs

| 維度 | 規格 |
|------|------|
| Variants | `underline` / `pill` / `outlined` |
| States | default / hover / active / disabled |
| Sizes | `sm` / `md` |
| Anatomy | Tab List (horizontal) + Tab Panel |
| Indicator | underline: 2px bottom border animate / pill: background animate |
| Overflow | 超過容器寬度時顯示左右箭頭 scroll |
| Keyboard | Arrow ← → 切換、Home/End 跳首尾 |
| Accessibility | role="tablist" + role="tab" + role="tabpanel" |

---

## 4. P1 元件清單

| 元件 | 說明 | Variants | Key States |
|------|------|----------|------------|
| Dropdown Menu | 下拉選單 | default / nested | hover / active / disabled items |
| Popover | 資訊氣泡 | default / interactive | open (click) / close |
| Tooltip | 提示框 | default | hover / focus 觸發 |
| Drawer / Sheet | 側邊滑出面板 | left / right / bottom | open / closing |
| Accordion | 摺疊面板 | single-open / multi-open | expanded / collapsed |
| Breadcrumb | 麵包屑導航 | default | current / link / separator |
| Pagination | 分頁器 | default / simple (prev/next) | active / disabled |
| Progress | 進度條/環 | bar / circle / steps | value / indeterminate |
| Skeleton | 載入佔位 | text / circle / rect | pulse animation |
| Alert / Banner | 頁面級通知 | info / success / warning / error | dismissable / persistent |
| Checkbox | 核取方塊 | default | checked / unchecked / indeterminate / disabled |
| Radio | 單選 | default | selected / unselected / disabled |
| Switch / Toggle | 開關 | default | on / off / disabled |
| Date Picker | 日期選擇器 | single / range | open / selected / disabled dates |
| File Upload | 檔案上傳 | drag-drop / button | idle / dragover / uploading / success / error |

---

## 5. P2 元件清單

| 元件 | 說明 |
|------|------|
| Color Picker | 顏色選擇器 |
| Slider / Range | 滑桿 |
| Stepper / Wizard | 步驟指示器 |
| Timeline | 時間軸 |
| Tree View | 樹狀結構 |
| Kanban Board | 看板 |
| Rich Text Editor | 富文字編輯器 |
| Code Block | 程式碼區塊（含語法高亮） |
| Chart Wrapper | 圖表容器（Bar / Line / Pie） |
| Carousel | 輪播 |
| Command Palette | 命令面板 (Cmd+K) |
| Keyboard Shortcut | 快捷鍵提示 |

---

## 6. 元件命名規範

### 6.1 Figma 命名

```
格式：[Category] / [Component Name] / [Variant]

範例：
  Actions / Button / Primary
  Actions / Button / Secondary
  Actions / Button / Ghost
  Inputs / Text Field / Default
  Inputs / Text Field / Error
  Data Display / Badge / Filled
  Data Display / Badge / Dot
  Feedback / Toast / Success
  Feedback / Toast / Error
  Navigation / Tabs / Underline
  Navigation / Breadcrumb / Default
```

### 6.2 工程命名

| Figma 名稱 | React 元件名 | CSS Class |
|------------|-------------|-----------|
| Actions / Button | `<Button>` | `.btn`, `.btn-primary` |
| Inputs / Text Field | `<TextField>` | `.text-field` |
| Data Display / Table | `<DataTable>` | `.data-table` |
| Feedback / Toast | `<Toast>` | `.toast` |
| Navigation / Tabs | `<Tabs>`, `<Tab>`, `<TabPanel>` | `.tabs` |

### 6.3 命名規則

```
規則 1：Figma 用 / 分層（Category / Name / Variant）
規則 2：React 用 PascalCase（Button、TextField、DataTable）
規則 3：CSS 用 kebab-case（.btn、.text-field、.data-table）
規則 4：Props 用 camelCase（variant、isDisabled、onClose）
規則 5：設計與工程名稱必須 1:1 對應（建立 Code Connect mapping）
```

---

## 7. 元件 Inventory 總表

| # | 元件 | 優先級 | 狀態 | Variants 數 | States 覆蓋 | 負責人 | 版本 |
|---|------|--------|------|------------|------------|--------|------|
| 1 | Button | P0 | ☐ | 5 | 6/6 | | v1.0 |
| 2 | Input / TextField | P0 | ☐ | 6 | 6/6 | | v1.0 |
| 3 | Select | P0 | ☐ | 3 | 6/6 | | v1.0 |
| 4 | Card | P0 | ☐ | 4 | 3/3 | | v1.0 |
| 5 | Modal / Dialog | P0 | ☐ | 3 | 3/3 | | v1.0 |
| 6 | Toast | P0 | ☐ | 5 | 3/3 | | v1.0 |
| 7 | Table | P0 | ☐ | 4 | 4/4 | | v1.0 |
| 8 | Badge / Tag | P0 | ☐ | 5 | 2/2 | | v1.0 |
| 9 | Avatar | P0 | ☐ | 3 | 3/3 | | v1.0 |
| 10 | Tabs | P0 | ☐ | 3 | 4/4 | | v1.0 |
| 11 | Dropdown Menu | P1 | ☐ | 2 | | | |
| 12 | Popover | P1 | ☐ | 2 | | | |
| 13 | Tooltip | P1 | ☐ | 1 | | | |
| 14 | Drawer | P1 | ☐ | 3 | | | |
| 15 | Accordion | P1 | ☐ | 2 | | | |
| ... | ... | ... | ... | ... | ... | ... | ... |

---

## 8. Do / Don't 範例

### Button

| ✅ Do | ❌ Don't |
|-------|---------|
| 一頁只有一個 Primary CTA | 放 3 個 Primary 按鈕搶注意力 |
| 按鈕文案用動詞：「建立專案」 | 模糊文案：「確定」「提交」 |
| Danger 操作用 Danger variant + 確認 Dialog | 用 Primary variant 做刪除 |
| Loading 時 disable + 顯示 spinner | Loading 時什麼都不顯示，用戶連點 |
| Icon-only 按鈕加 tooltip + aria-label | Icon-only 按鈕無任何提示 |

### Input

| ✅ Do | ❌ Don't |
|-------|---------|
| Label 在上方，永遠可見 | Label 只放在 placeholder 裡（focus 後消失） |
| Error 顯示在 Input 下方 + 紅色邊框 | 只用 toast 顯示表單錯誤 |
| 必填欄位用 * 標示 | 所有欄位都不標示必填 |
| Helper text 說明格式要求 | 完全沒有格式提示，錯了才告訴用戶 |

### Modal

| ✅ Do | ❌ Don't |
|-------|---------|
| Modal 只做一件事 | Modal 裡塞完整的表單 + 表格 + 子 Modal |
| 破壞性操作要二次確認 | 點刪除直接執行 |
| Mobile 轉 bottom sheet | Mobile 還用小 Modal（很難點） |
| 有明確的關閉方式（X, Esc, Overlay click） | 只有「確定」按鈕能關 Modal |

### Table

| ✅ Do | ❌ Don't |
|-------|---------|
| 數字右對齊、文字左對齊 | 所有內容都置中 |
| 空狀態有插圖 + CTA | 只顯示「無資料」三個字 |
| Mobile 轉 card list | Mobile 還用橫向表格（要左右滑） |
| 長文字 truncate + tooltip | 長文字把 row 撐高 |

---

## Figma 結構建議

```
📁 01_Components（Figma Page）
├── 📄 Overview（元件總覽 + Inventory 表）
├── 📄 Actions
│   ├── Button（所有 variants × states × sizes）
│   └── Icon Button
├── 📄 Inputs
│   ├── Text Field
│   ├── Select
│   ├── Checkbox / Radio / Switch
│   ├── Date Picker
│   └── File Upload
├── 📄 Data Display
│   ├── Table
│   ├── Badge / Tag
│   ├── Avatar
│   ├── Card
│   └── Tooltip
├── 📄 Feedback
│   ├── Toast / Notification
│   ├── Alert / Banner
│   ├── Modal / Dialog
│   ├── Drawer
│   └── Progress / Skeleton
├── 📄 Navigation
│   ├── Tabs
│   ├── Breadcrumb
│   ├── Pagination
│   └── Menu / Dropdown
└── 📄 Do & Don't（常見錯用案例）
```

---

**版本**：v1.0
**最後更新**：2026-03-17
**相關文件**：`SYSTEM_DOCUMENT_SPEC.md` → B3、`BASE_DESIGN_SYSTEM.md` → UX Pattern Layer
