# 📚 Prompt Architect Pipeline - AI 網頁開發流水線

## 🎯 專案概述

本系統採用模組化架構，將模糊的 PRD 或想法轉化為可執行、一致性高的 AI 開發指令集。核心流程：**選原型 → 查模組 → 準備 Tokens → 組裝 Prompt → AI 生成 → 驗收迭代**。

### 核心目標
- 縮短 AI 輔助開發迭代週期 30% 以上
- 建立可跨專案複用的 Base Design System
- 透過積木模組系統支援 10 種網站原型
- 透過 Pipeline Orchestrator 實現動態 Prompt 組裝
- 提供結構化的開發審查流程

## 📁 文檔結構

```
prompt_architect_pipeline/
├── README.md                               ← 入口導覽（你在這裡）
│
├── global/                                 ← 靈魂層（全域設計系統）
│   ├── BASE_DESIGN_SYSTEM.md              ← [Template] 設計基準範本
│   ├── SYSTEM_DOCUMENT_SPEC.md            ← [Template] 四層系統文件模板
│   └── 01_sunny_brand_system.md           ← [Example] 桑尼品牌實施範例
│
├── pages/                                  ← 骨架層（頁面規格）
│   ├── page_template.md                   ← [Template] 頁面規格範本
│   └── 01_dashboard.md                    ← [Example] 儀表板規格範例
│
├── assembly/                               ← 心臟層（組裝器）
│   ├── PIPELINE_ORCHESTRATOR.md           ← [Template] 組裝調度範本
│   └── 01_dashboard_integrated.md         ← [Example] 完整組裝 Prompt 範例
│
├── modules/                                ← 積木層（模組系統）
│   ├── MODULE_REGISTRY.md                 ← 8 大模組定義 + 功能清單 + 深度分級
│   └── WEBSITE_MODULE_MATRIX.md           ← 模組 × 網站類型檢索矩陣
│
├── references/                             ← 參考層（配方與檢核）
│   ├── website_recipes.md                 ← 10 種網站配方 + Reference + Lovable 提示詞
│   └── prereq_document_checklist.md       ← 前置文件檢核清單（P0/P1/P2）
│
├── guides/                                 ← 指南層
│   ├── implementation_guide.md            ← 實施指南
│   ├── quality_checklist.md               ← QA 清單
│   └── vibe_coding_build_strategy.md      ← 建置策略（新手從這裡開始）
│
└── design-system-specs/                   ← 工業化設計系統規格（Figma 對應）
    ├── AI_DESIGN_INDUSTRIAL_PLAYBOOK.md  ← 完整戰法：Pencil + Figma MCP + Claude Code
    ├── 00_foundations_spec.md             ← Grid / Color / Typo / Spacing / Tokens
    ├── 01_components_spec.md             ← Button / Input / Table / Modal 元件庫規格
    ├── 02_patterns_spec.md               ← Form / Table / Nav / Feedback 互動模式
    ├── 03_templates_spec.md              ← Dashboard / List / Detail / Settings 頁面模板
    └── 99_documentation_spec.md          ← Do/Don't / QA / Change Log / 治理規範
```

## 快速上手

### 路徑 A：我要從零建一個網站（推薦新手）

1. 讀 [`guides/vibe_coding_build_strategy.md`](guides/vibe_coding_build_strategy.md) — 了解 7 步驟建置 SOP
2. 查 [`references/website_recipes.md`](references/website_recipes.md) — 選定你的網站原型
3. 查 [`modules/WEBSITE_MODULE_MATRIX.md`](modules/WEBSITE_MODULE_MATRIX.md) — 確認需要哪些模組
4. 查 [`references/prereq_document_checklist.md`](references/prereq_document_checklist.md) — 確認 P0 文件備齊
5. 填 [`global/SYSTEM_DOCUMENT_SPEC.md`](global/SYSTEM_DOCUMENT_SPEC.md) — 建立你的 Design Tokens
6. 按 SOP Step 4-7 執行

### 路徑 C：我要用 AI 工業化設計流程（Pencil + Figma MCP + Claude Code）

1. 讀 [`design-system-specs/AI_DESIGN_INDUSTRIAL_PLAYBOOK.md`](design-system-specs/AI_DESIGN_INDUSTRIAL_PLAYBOOK.md) — 完整戰法
2. 依序建立 [`00_foundations`](design-system-specs/00_foundations_spec.md) → [`01_components`](design-system-specs/01_components_spec.md) → [`02_patterns`](design-system-specs/02_patterns_spec.md)
3. 設定 Figma MCP + Pencil MCP 環境
4. 用 Claude Code 讀設計檔 + 規格文件 → 產出程式碼

### 路徑 B：我已經有 Design System，要做一頁

1. 看範例 `global/01_sunny_brand_system.md` → `pages/01_dashboard.md` → `assembly/01_dashboard_integrated.md`
2. 拷貝 `pages/page_template.md` 定義你的頁面
3. 填入 `assembly/PIPELINE_ORCHESTRATOR.md` 組裝
4. 將結果貼到 Lovable / Claude 執行

---
最後更新：2026-03-17 | 維護：Prompt Architect Team