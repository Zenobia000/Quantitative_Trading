# Example Clone: Stripe

> 範例骨架（未實際擷取）。展示六階段執行後的目錄該長什麼樣子。

---

## 基本資訊

| 欄位 | 值 |
|------|-----|
| Slug | `_example_stripe` |
| Target URL | `https://stripe.com` |
| 擷取日期 | 2026-04-07 |
| 操作者 | example |
| 法律檢查 | [x] robots.txt 確認 / [x] 僅公開頁面 |

## 為什麼複製這個

- **看上它什麼**：開發者導向 SaaS 的設計典範，typography 與留白處理極佳
- **想學的核心**：L0 Foundations（color/typo system）+ L3 Landing template
- **對應你的產品**：自己的開發者工具 SaaS 首頁

## 預設輸出範圍

- [x] L0 Foundations
- [x] L1 Components
- [x] L2 Patterns
- [x] L3 Templates
- [x] L4 Sitemap

## 進度追蹤

| 階段 | 狀態 | 完成日 | 備註 |
|------|------|--------|------|
| 1. Capture | ⬜ 範例 | | 實際使用時要做 |
| 2. Extract | ⬜ 範例 | | |
| 3. Analyze | ⬜ 範例 | | |
| 4. Differentiate | ⬜ 範例 | | |
| 5. Specify | ⬜ 範例 | | |
| 6. Validate | ⬜ 範例 | | |

## 你的品牌覆蓋

- 主色：`#7C3AED`（紫色，與 Stripe 的藍區隔）
- 字型：Inter（同 Stripe，因為通用）
- 受眾：中小企業開發者
- 風格定位：比 Stripe 更親切、更口語

## 必避開的設計

- 過於企業感的灰藍色
- 過長的 Hero 標題

---

## 目錄結構（執行後應有）

```
_example_stripe/
├── README.md              ← 你在這裡
├── raw/
│   ├── screenshots/
│   │   ├── mobile.png
│   │   ├── tablet.png
│   │   └── desktop.png
│   ├── dom.html
│   ├── css-vars-raw.json
│   ├── computed-styles.json
│   ├── fonts.json
│   └── media-queries.json
├── extracted/
│   ├── dom-tree.md
│   ├── css-vars.json
│   ├── media-queries.json
│   └── assets-inventory.md
├── analysis/
│   ├── L0_foundations.md
│   ├── L1_components.md
│   ├── L2_patterns.md
│   ├── L3_templates.md
│   └── L4_sitemap.md
├── differentiation.md
├── spec/
│   └── inspired-design-system.md
└── validation.md
```

執行步驟參考根目錄 [`CLONE_WORKFLOW_PLAYBOOK.md`](../../CLONE_WORKFLOW_PLAYBOOK.md)。
