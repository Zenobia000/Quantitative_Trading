# 前置規範文件檢核清單 (Prerequisite Document Checklist)

> 先定規則，再做模具，最後可驗收。

本清單按四層架構（策略→系統→產品→交付）列出所有前置文件，並標注優先級。

---

## 優先級說明

| 等級 | 意涵 | 時機 |
|------|------|------|
| **P0** | 必須有才能開工 | 動手寫提示詞之前 |
| **P1** | 沒有會痛但可以邊做邊補 | 第一版做完後立即補齊 |
| **P2** | 規模化時需要 | 多頁面 / 多人協作 / 多品牌時 |

---

## A. 策略層（決定你「為什麼長這樣」）

| 優先級 | 文件 | 內容 | 沒有會怎樣 | Pipeline 對應檔案 |
|--------|------|------|-----------|-----------------|
| **P0** | Design Principles | 3-7 條可操作的設計原則 | 每個人審美不同，吵不完 | `global/BASE_DESIGN_SYSTEM.md` → [BRAND & VOICE LAYER] |
| **P0** | Brand & Tone Guidelines | 品牌性格、視覺語言、文案語氣 | UI 的「感覺」靠設計師個人風格 | `global/BASE_DESIGN_SYSTEM.md` → [BRAND & VOICE LAYER] |
| **P1** | 商業目標定義 | 網站要解決什麼問題、服務誰 | 功能做了一堆但不知道為誰做 | `references/website_recipes.md` |

### P0 交付物檢查

- [ ] 設計原則已定義（3-7 條）
- [ ] 品牌色彩已確定（主色/輔色/強調色）
- [ ] 語氣定位已確定（正式/親切/幽默的尺度）
- [ ] 目標受眾已明確

---

## B. 系統層（工業化核心：把「模具」做出來）

| 優先級 | 文件 | 內容 | 沒有會怎樣 | Pipeline 對應檔案 |
|--------|------|------|-----------|-----------------|
| **P0** | Design Tokens + Naming | color / spacing / typography / radius / shadow 的代碼化命名 | UI 變成手刻，越改越散 | `global/BASE_DESIGN_SYSTEM.md` → [VISUAL DESIGN SYSTEM LAYER] |
| **P0** | Layout / Grid / RWD Spec | 欄位、邊距、容器寬度、斷點策略 | RWD 永遠在救火 | `global/BASE_DESIGN_SYSTEM.md` → [VISUAL DESIGN SYSTEM LAYER] |
| **P0** | Component Library（基礎版）| 按鈕、輸入框、卡片、Modal 等核心元件 + states/variants | 每頁都重畫，狀態漏一堆 | `global/BASE_DESIGN_SYSTEM.md` → [VISUAL DESIGN SYSTEM LAYER] |
| **P1** | Pattern Library | 表單/表格/導覽/回饋等互動模式 | 每個人都用自己的習慣 | `global/BASE_DESIGN_SYSTEM.md` → [UX PATTERN LAYER] |
| **P1** | Accessibility Spec | 對比、鍵盤操作、Focus state、螢幕閱讀器 | 後期補可及性很痛 | `global/BASE_DESIGN_SYSTEM.md` → [INTERACTION & ACCESSIBILITY] |
| **P2** | 多品牌/Skin Token 規則 | 白標、Dark mode、客戶 skin | 規模化時全部重做 | — |

### P0 交付物檢查

- [ ] Color Tokens 已定義（Primary / Secondary / Accent / Neutral / Error / Success / Warning / Info）
- [ ] Typography 已定義（字級階梯、字重、行高）
- [ ] Spacing Scale 已定義（4/8/12/16/24/32/48/64）
- [ ] Border Radius 已定義（sm/md/lg/full）
- [ ] Grid 已定義（最大寬度、欄數、間距）
- [ ] Breakpoints 已定義（Mobile / Tablet / Desktop）
- [ ] 核心元件已定義（Button / Input / Card / Modal / Toast / Table）
- [ ] 元件 States 已定義（default / hover / active / disabled / loading / error）

---

## C. 產品層（讓每個功能不會自己長歪）

| 優先級 | 文件 | 內容 | 沒有會怎樣 | Pipeline 對應檔案 |
|--------|------|------|-----------|-----------------|
| **P1** | IA 資訊架構 | Sitemap / Navigation Map | 頁面越多越亂 | `pages/page_template.md` → [PAGE META] |
| **P1** | User Flow | 從入口到完成任務的最短路徑 | 流程斷裂、用戶迷路 | `pages/page_template.md` → [INTERACTION & STATE FLOW] |
| **P1** | Content Spec / UX Writing | 按鈕文案、錯誤訊息模板、空狀態文案 | 同一種情境不同語氣 | `pages/page_template.md` → [SECTION COMPONENT SPEC] |
| **P2** | Wireframe 低保真骨架 | 資訊排序與互動順序 | 開發後才發現排版不對 | — |

### P1 交付物檢查

- [ ] Sitemap 已繪製（含主導覽和次導覽）
- [ ] 核心任務的 User Flow 已定義
- [ ] 通用文案已統一（確認按鈕叫「確認」還是「送出」還是「儲存」）
- [ ] 空狀態文案已準備
- [ ] 錯誤訊息模板已定義

---

## D. 交付層（讓工程與 QA 能「不猜你意思」）

| 優先級 | 文件 | 內容 | 沒有會怎樣 | Pipeline 對應檔案 |
|--------|------|------|-----------|-----------------|
| **P1** | Handoff Spec | 尺寸、間距、狀態、RWD 行為、動效 | 工程猜你意思 | `assembly/PIPELINE_ORCHESTRATOR.md` |
| **P1** | Design QA Checklist | 驗收清單：字級/間距/狀態是否齊 | 改壞了不知道 | `guides/quality_checklist.md` |
| **P2** | Change Log | 設計系統版本、元件變更、breaking changes | 改壞了追不回來 | — |

### P1 交付物檢查

- [ ] QA Checklist 已建立
- [ ] 動效規格已定義（duration / easing / trigger）
- [ ] RWD 行為已描述（每個斷點的佈局差異）

---

## 快速判斷：我現在該準備什麼？

```
你在哪個階段？

├── 剛開始（MVP / 第一版）
│   └── 只做 P0：策略層全做 + 系統層 Tokens/Grid/基礎元件
│
├── 第一版做完，要迭代
│   └── 補齊 P1：Pattern Library + IA + User Flow + Content Spec + QA Checklist
│
├── 多人協作 / 多品牌 / 規模化
│   └── 補齊 P2：多品牌 Token + Change Log + Wireframe 流程
│
└── 不確定？
    └── 先去 references/website_recipes.md 選你的網站類型
        → 回來看 P0 清單打勾
        → 打完勾就可以開始寫提示詞了
```

---

## 與 Pipeline 的對應關係

```
prereq_document_checklist.md（你在這裡）
    ↓ 確認文件備齊
global/BASE_DESIGN_SYSTEM.md（填入 P0 內容）
    ↓
pages/page_template.md（填入 P1 內容）
    ↓
assembly/PIPELINE_ORCHESTRATOR.md（組裝）
    ↓
guides/quality_checklist.md（驗收 P1 交付層）
```
