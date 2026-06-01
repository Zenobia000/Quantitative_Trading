# 系統級文件規格模板 (System Document Specification)

> 想把 UI/UX 做到「工業化」— 你要先把「設計怎麼被複製」寫成系統文件。
> 本模板對應 `prereq_document_checklist.md` 的所有文件項目。

---

## 使用方式

1. 複製本模板，改名為 `XX_brand_system_doc.md`
2. 逐層填寫（至少完成 P0 標記的區塊）
3. 填完後，將內容遷移到 `global/BASE_DESIGN_SYSTEM.md` 對應的 LAYER

---

# A. 策略層 (Strategy Layer) — P0

## A1. Design Principles（設計原則）

> 3-7 條可操作的原則，用來統一取捨。

| # | 原則名稱 | 說明 | 當衝突時... |
|---|---------|------|------------|
| 1 | [例：資訊優先] | [例：內容的清晰度永遠優先於裝飾] | [例：砍動畫保可讀性] |
| 2 | [例：低認知負擔] | [例：用戶不需要學習就能操作] | [例：用預設值取代設定項] |
| 3 | | | |
| 4 | | | |
| 5 | | | |

## A2. Brand & Tone Guidelines（品牌與語氣）

### 品牌性格

| 維度 | 我們是 | 我們不是 |
|------|--------|---------|
| 語氣 | [例：專業但親切] | [例：冷冰冰的企業腔] |
| 視覺 | [例：簡潔乾淨] | [例：華麗花俏] |
| 態度 | [例：鼓勵嘗試] | [例：高高在上] |

### 文案語氣規則

- 稱呼用戶：[例：「你」而非「您」]
- 按鈕動詞：[例：用主動語態 — 「開始學習」而非「學習開始」]
- 錯誤訊息：[例：先說發生什麼，再說怎麼修 — 「上傳失敗，請檢查檔案大小是否小於 10MB」]
- 空狀態：[例：鼓勵行動 — 「還沒有任何課程，立即探索」]

---

# B. 系統層 (System Layer) — P0 核心

## B1. Design Tokens（設計代碼化）

### Color Tokens

| Token 名稱 | 色值 | 用途 |
|-----------|------|------|
| `color.primary` | #______ | 主要品牌色、CTA 按鈕 |
| `color.primary.hover` | #______ | 主色 hover 狀態 |
| `color.secondary` | #______ | 輔助色、次要元素 |
| `color.accent` | #______ | 強調色、標籤、徽章 |
| `color.bg.page` | #______ | 頁面底色 |
| `color.bg.surface` | #______ | 卡片/容器底色 |
| `color.bg.elevated` | #______ | 浮層/Modal 底色 |
| `color.text.primary` | #______ | 主要文字 |
| `color.text.secondary` | #______ | 次要文字/說明 |
| `color.text.disabled` | #______ | 停用狀態文字 |
| `color.border.default` | #______ | 預設邊框 |
| `color.border.focus` | #______ | Focus 邊框 |
| `color.success` | #______ | 成功 |
| `color.warning` | #______ | 警告 |
| `color.error` | #______ | 錯誤 |
| `color.info` | #______ | 資訊 |

### Spacing Scale

| Token | 值 | 用途 |
|-------|-----|------|
| `space.1` | 4px | 元素內微間距 |
| `space.2` | 8px | 元素內標準間距 |
| `space.3` | 12px | 標籤與文字間距 |
| `space.4` | 16px | 元件間距 |
| `space.6` | 24px | 區塊間距 |
| `space.8` | 32px | 大區塊間距 |
| `space.12` | 48px | Section 間距 |
| `space.16` | 64px | 頁面級間距 |

### Typography

| Token | 字級 | 行高 | 字重 | 用途 |
|-------|------|------|------|------|
| `text.display` | ___px | ___  | 700 | 大標題 / Hero |
| `text.heading.xl` | ___px | ___ | 700 | H1 |
| `text.heading.lg` | ___px | ___ | 600 | H2 |
| `text.heading.md` | ___px | ___ | 600 | H3 |
| `text.heading.sm` | ___px | ___ | 600 | H4 |
| `text.body.lg` | ___px | ___ | 400 | 大段落 |
| `text.body.md` | ___px | ___ | 400 | 標準段落 |
| `text.body.sm` | ___px | ___ | 400 | 小字說明 |
| `text.caption` | ___px | ___ | 400 | 標註/時間戳 |

字體：
- 英文：_______________
- 中文：_______________
- 程式碼：_______________

### Border Radius

| Token | 值 | 用途 |
|-------|-----|------|
| `radius.sm` | ___px | 小元素（Tag, Badge） |
| `radius.md` | ___px | 按鈕、輸入框 |
| `radius.lg` | ___px | 卡片、容器 |
| `radius.xl` | ___px | Modal、大容器 |
| `radius.full` | 9999px | 圓形頭像、Pill |

### Elevation (Shadow)

| Token | 值 | 用途 |
|-------|-----|------|
| `shadow.sm` | _______________ | 卡片預設 |
| `shadow.md` | _______________ | 懸浮卡片 |
| `shadow.lg` | _______________ | Modal / Dropdown |

---

## B2. Layout / Grid / RWD

### Grid System

| 屬性 | 值 |
|------|-----|
| 最大寬度 | ___px |
| 欄數 | ___ |
| 欄間距 | ___px |
| 左右 Padding | ___px |

### Breakpoints

| 名稱 | 寬度 | 欄數 | 說明 |
|------|------|------|------|
| Mobile | < ___px | ___ | |
| Tablet | ___px - ___px | ___ | |
| Desktop | > ___px | ___ | |

---

## B3. Component Library（基礎元件規格）

### 元件清單（P0 必做）

每個元件需定義：**Variants × States × Sizes**

| 元件 | Variants | States | Sizes |
|------|----------|--------|-------|
| Button | Primary / Secondary / Ghost / Danger | Default / Hover / Active / Disabled / Loading | sm / md / lg |
| Input | Text / Password / Search / Textarea | Default / Focus / Error / Disabled | sm / md / lg |
| Select | Single / Multi | Default / Focus / Open / Disabled | sm / md / lg |
| Card | Default / Clickable / Selected | Default / Hover / Active | — |
| Modal | Default / Destructive | Open / Closing | sm / md / lg |
| Toast | Success / Warning / Error / Info | Entering / Visible / Exiting | — |
| Table | Default / Sortable / Selectable | Default / Loading / Empty | — |
| Badge | Default / Dot | — | sm / md |
| Avatar | Image / Initial / Icon | Default / Loading | sm / md / lg |
| Tabs | Default / Underline / Pill | Default / Active / Disabled | — |

---

# C. 產品層 (Product Layer) — P1

## C1. 資訊架構 (IA)

```
[網站名稱]
├── 首頁 (/)
├── [頁面群組 A]
│   ├── [子頁面 1]
│   └── [子頁面 2]
├── [頁面群組 B]
│   └── ...
├── 登入/註冊
└── 後台 (/admin)
    ├── ...
    └── ...
```

## C2. User Flow（核心任務流程）

```
[任務名稱]：[描述]

入口 → 步驟 1 → 步驟 2 → ... → 完成

分支：
- 如果 [條件 A] → [路徑 A]
- 如果 [條件 B] → [路徑 B]
```

## C3. Content Spec（文案規格）

| 場景 | 文案模板 | 範例 |
|------|---------|------|
| 成功 | [動作] 成功 | 「課程已加入購物車」 |
| 錯誤 | [問題描述]。[建議動作]。 | 「上傳失敗。請確認檔案小於 10MB。」 |
| 空狀態 | 還沒有 [內容]，[鼓勵動作] | 「還沒有任何課程，立即探索」 |
| 載入中 | 正在 [動作]... | 「正在載入課程列表...」 |
| 確認操作 | 確定要 [動作] 嗎？[後果說明] | 「確定要刪除此課程嗎？此操作無法復原。」 |

---

# D. 交付層 (Delivery Layer) — P1

## D1. Handoff Spec 模板

每個頁面交付時需包含：

- [ ] 所有狀態已標註（default / hover / active / disabled / loading / error / empty）
- [ ] 間距已標註（使用 spacing token）
- [ ] RWD 行為已描述（每個斷點的差異）
- [ ] 動效已描述（duration / easing / trigger）
- [ ] API 對應已標註

## D2. QA Checklist

→ 詳見 `guides/quality_checklist.md`

## D3. Change Log 格式

```markdown
## [版本號] - YYYY-MM-DD

### Added
- [新增內容]

### Changed
- [變更內容]

### Fixed
- [修復內容]

### Breaking
- [破壞性變更 + 遷移指引]
```
