# 網站複製工作流戰法 (Website Cloning Playbook)

> 把任意網站變成可消化的規格書，餵進 Prompt Architect Pipeline。
> 不是抄襲，是結構化吸收 + 差異化重建。

---

## 核心信條

> **「目的不是複製別人的 Figma 檔案，而是萃取設計決策、產出更好的產品。」**

| 做什麼 | 不做什麼 |
|--------|----------|
| 抽取 Token / 元件 / 模式的**結構** | 直接搬運品牌資產（logo、文案、商標色） |
| 學習設計**決策的理由** | 像素級複製 |
| 對齊既有四層 spec | 另起一套規格體系 |
| 標註「inspired by」來源 | 假裝是原創 |

---

## 六階段流水線

```
[1.Capture] → [2.Extract] → [3.Analyze] → [4.Differentiate] → [5.Specify] → [6.Validate]
   擷取        抽取          分析         差異化           規格化       驗收
```

| 階段 | 輸入 | 輸出位置 | 主要工具 | 驗收門檻 |
|------|------|----------|----------|----------|
| 1. Capture | URL | `clones/{slug}/raw/` | Playwright / browser MCP | 三斷點截圖完整 |
| 2. Extract | raw | `clones/{slug}/extracted/` | Claude + extract prompt | DOM 樹 + CSS 變數齊全 |
| 3. Analyze | extracted | `clones/{slug}/analysis/` | Claude + L0–L4 prompts | 五個分析檔產出 |
| 4. Differentiate | analysis | `clones/{slug}/differentiation.md` | Claude + 人類決策 | 標註保留/拋棄/改進 |
| 5. Specify | differentiation | `clones/{slug}/spec/` | Claude + specify prompt | 對齊 BASE_DESIGN_SYSTEM |
| 6. Validate | spec | `clones/{slug}/validation.md` | Checklist + sunnydata-code-review | 全項通過 |

---

## 1. Capture — 擷取原料

### 1.1 必收清單

| 項目 | 規格 | 為什麼 |
|------|------|--------|
| 全頁截圖 × 3 斷點 | 375 / 768 / 1440 px | 看 responsive 行為 |
| 渲染後 DOM | `document.documentElement.outerHTML` | 真實的 class / 結構 |
| Computed CSS | 關鍵元素的 `getComputedStyle` | 真實生效的數值，不是 source CSS |
| `:root` CSS Variables | 全部 | 設計 token 的金礦 |
| 字型清單 | `document.fonts` | typography system |
| Media queries 斷點 | 從 stylesheet 抽出 | 對齊 grid system |

### 1.2 工具選擇

| 場景 | 工具 | 命令 |
|------|------|------|
| 互動式探索 | browser-automation-expert agent | 對話式擷取 |
| 大量自動化 | Playwright 腳本 | `node capture.js <url>` |
| 簡單頁面 | WebFetch + 手動 DevTools | 快速但不完整 |

### 1.3 法律與倫理紅線

- ❌ 不擷取登入後內容（除非有明示授權）
- ❌ 不下載受版權保護的圖片素材
- ❌ 不保留 PII（網站上的真實使用者資料）
- ✅ 只擷取公開首頁與行銷頁
- ✅ robots.txt 拒絕的路徑直接跳過

---

## 2. Extract — 結構化抽取

把 raw HTML/CSS 轉成 AI 易讀的中繼格式。**這階段不做判斷，只結構化。**

### 產出檔案

| 檔名 | 內容 |
|------|------|
| `dom-tree.md` | 簡化 DOM 樹，標註語意角色（header/nav/hero/card...） |
| `css-vars.json` | `:root` 變數 + 所有用到的色票/字型/間距值的頻率統計 |
| `media-queries.json` | 斷點清單與觸發的樣式變化 |
| `assets-inventory.md` | 字型、icon set、圖片風格清單 |

使用 prompt：[`prompts/02_extract.md`](prompts/02_extract.md)

---

## 3. Analyze — 對齊四層

**核心動作**：把 extracted 結果映射到既有 `00–03` spec 結構。

| 分析檔 | 對應 spec | 抽取重點 |
|--------|-----------|----------|
| `L0_foundations.md` | `00_foundations_spec.md` | Color / Typo / Spacing / Grid / Radius / Shadow / Motion |
| `L1_components.md` | `01_components_spec.md` | Button / Input / Card / Modal / Badge 等 + 變體與狀態 |
| `L2_patterns.md` | `02_patterns_spec.md` | Form 流程 / Nav 結構 / Table / Feedback / Empty State |
| `L3_templates.md` | `03_templates_spec.md` | Page-level 區塊組合（Hero / Feature Grid / CTA / Footer） |
| `L4_sitemap.md` | （新增層）| 頁面層級 + 路由 + 功能分區（Mermaid） |

每個 L 檔有對應 prompt：`prompts/03_analyze_L{0–4}_*.md`

### 3.1 黃金法則

- **頻率即重點**：CSS 變數出現越多次，越是核心 token
- **變體歸類**：同一按鈕的 hover/disabled/loading 視為一個 component 的 states，不是不同 component
- **語意命名**：抽取時直接用 `color.brand.primary` 而非 `--blue-500`
- **不知道就空白**：抽不到的欄位留 `TBD`，不要瞎猜

---

## 4. Differentiate — 差異化決策

**這階段是價值核心。** 沒有差異化，複製就是抄襲。

### 產出：`differentiation.md`

```markdown
## ✅ 值得學的（KEEP）
- 設計決策 + 為什麼好 + 如何納入

## ⚠️ 不適合的（DROP）
- 元素 + 為什麼不適合你的品牌/受眾

## 🎨 品牌覆蓋（OVERRIDE）
- 來源 token → 你的 token 對照表
- 主色從 #2563EB 改為 #7C3AED 等

## 💡 改進機會（IMPROVE）
- 你能做得更好的地方（accessibility、效能、互動）
```

使用 prompt：[`prompts/04_differentiate.md`](prompts/04_differentiate.md)

---

## 5. Specify — 規格化輸出

把 analysis + differentiation 合成一份**可直接交給 Lovable / Claude Code 的規格書**。

### 產出：`spec/inspired-design-system.md`

- 結構**完全對齊** `global/BASE_DESIGN_SYSTEM.md`
- 每個 token 標註 `[inspired by: stripe.com]` 或 `[original]`
- 與既有 `00_foundations_spec.md` 的衝突已在 differentiation 階段解決

使用 prompt：[`prompts/05_specify.md`](prompts/05_specify.md)

---

## 6. Validate — 驗收

執行 [`checklists/validation_checklist.md`](checklists/validation_checklist.md)：

- [ ] 顏色對比度 WCAG AA 通過
- [ ] Token 完整度 ≥ 80%（vs `00_foundations_spec.md` 條目數）
- [ ] 無直接複製商標 / 文案 / logo
- [ ] 與既有 design system 衝突已解決
- [ ] Sitemap 可對應到 `WEBSITE_MODULE_MATRIX.md` 某個原型
- [ ] differentiation.md 至少 3 條 IMPROVE 項目

未通過 → 回到對應階段修正。全通過 → spec 可被 Pipeline Orchestrator 引用。

---

## 與既有 Pipeline 的接口

```
[Clone Workflow]                    [Prompt Architect Pipeline]
clones/{slug}/spec/              ──→  global/sample/{slug}_brand.md
clones/{slug}/analysis/L4         ──→  references/website_recipes.md (新原型)
clones/{slug}/analysis/L3         ──→  pages/sample/{slug}_*.md
```

複製產物**不取代**既有 Base Design System，而是作為**靈感來源**被 Orchestrator 引用。

---

## 快速啟動

```bash
# 1. 為新目標建立工作目錄
SLUG=stripe
mkdir -p design-system-specs/cloning/clones/$SLUG/{raw,extracted,analysis,spec}

# 2. 從 templates/clone_target_template.md 複製 metadata
cp design-system-specs/cloning/templates/clone_target_template.md \
   design-system-specs/cloning/clones/$SLUG/README.md

# 3. 依序執行六階段（每階段對應一份 prompt）
```

---

## 目錄總覽

```
cloning/
├── CLONE_WORKFLOW_PLAYBOOK.md     ← 你在這裡
├── prompts/                        ← 每階段固定 prompt
├── templates/                      ← 輸出範本
├── checklists/                     ← 驗收清單
└── clones/                         ← 每個複製專案
    └── _example_stripe/            ← 範例骨架
```

---

最後更新：2026-04-07
