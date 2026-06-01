# Prompt Architect Pipeline - 實施指南

> 完整的 Pipeline 使用說明。新手建議先讀 `vibe_coding_build_strategy.md`。

---

## 一、快速開始

### 1.1 文檔結構概覽

```
prompt_architect_pipeline/
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
│   ├── website_recipes.md                 ← 10 種網站配方 + Reference + 提示詞
│   └── prereq_document_checklist.md       ← 前置文件檢核清單（P0/P1/P2）
│
└── guides/                                 ← 指南層
    ├── implementation_guide.md            ← 本文件
    ├── quality_checklist.md               ← QA 清單
    └── vibe_coding_build_strategy.md      ← 建置策略（新手起點）
```

### 1.2 架構說明

Pipeline 由兩個維度構成：

**縱向：三層組裝架構**
1. **Global Layer (靈魂層)**：定義 Design Tokens、通用元件行為與品牌規範
2. **Page Layer (骨架層)**：定義特定路由的功能區塊、資料需求與頁面邏輯
3. **Assembly Layer (心臟層)**：將 Global + Page 組裝為可執行的 AI Prompt

**橫向：積木模組系統**
- 8 大模組（Identity / Content / Commerce / Delivery / Community / Growth / Admin / Infrastructure）
- 每個模組有 L1-L3 深度分級
- 不同網站類型 = 不同模組的深度加權

---

## 二、實施流程 SOP

> 完整 7 步驟 SOP 詳見 `vibe_coding_build_strategy.md`，以下為精簡版。

### Step 1: 選定網站原型
- 查 `references/website_recipes.md` 選定類型
- 確認商業目標與 MVP 範圍

### Step 2: 確認模組組合
- 查 `modules/WEBSITE_MODULE_MATRIX.md` 看哪些模組亮燈
- 查 `modules/MODULE_REGISTRY.md` 看功能細項

### Step 3: 準備前置文件（P0）
- 查 `references/prereq_document_checklist.md` 確認文件備齊
- 用 `global/SYSTEM_DOCUMENT_SPEC.md` 填寫四層系統文件

### Step 4: 初始化 Design System
- 複製 `global/BASE_DESIGN_SYSTEM.md`，改名為 `XX_brand_system.md`
- 填入 Step 3 準備的 Design Tokens
- 參考 `global/01_sunny_brand_system.md` 看範例

### Step 5: 定義頁面規格
- 複製 `pages/page_template.md`，為每個頁面建立規格
- 參考 `pages/01_dashboard.md` 看範例
- MVP 優先：先做核心頁面

### Step 6: 組裝 Assembly Prompt
- 開啟 `assembly/PIPELINE_ORCHESTRATOR.md`
- 填入 Global Design System（壓縮版）
- 填入 Page Spec
- 參考 `assembly/01_dashboard_integrated.md` 看範例

### Step 7: 執行 + QA
- 將組裝後的 Prompt 貼入 Lovable / Claude
- 用 `guides/quality_checklist.md` 逐項驗收
- 迭代修改直到通過

---

## 三、最佳實踐

### 3.1 Prompt 撰寫準則

**DO**
- **層級明確**：讓 AI 知道 Global 的優先級高於 Page
- **具體而非抽象**：使用 Hex Code (#F59E0B) 而非描述色 (橘色)
- **定義狀態**：每個元件都要問 — Loading? Error? Empty? Disabled?
- **壓縮 Global**：Assembly 中只放當前頁面需要的 Tokens，不要整份複製

**DON'T**
- **冗餘描述**：Page 層不應重複 Global 已定義的內容，除非是 Exception
- **模糊語義**：避免「漂亮的」「現代的」，改用具體 UI Pattern 名稱
- **一次做整站**：一次 Prompt 只做一頁，不要一次丟整個網站
- **跳過 P0**：沒有 Design Tokens 就直接做 = 沒有尺規就畫建築圖

### 3.2 協作與維護

- **Single Source of Truth**：所有視覺改動從 `BASE_DESIGN_SYSTEM.md` 發起
- **Component Feedback Loop**：AI 生成了優秀的客製化元件 → 記錄回 Global
- **版本號同步**：Global 變更時更新版本號，Page 註記使用的 Global 版本

---

## 四、常見問題處理

### Q: AI 輸出的樣式跑掉了？
**A**: 檢查 Assembly Prompt 是否過長導致 AI 遺失細節。壓縮 Global 內容至當前頁面相關的 Tokens。

### Q: 如何處理跨專案的設計？
**A**: 複製整個 `prompt_architect_pipeline` 目錄，只需修改 `global/` 層級。模組系統和參考資料可以共用。

### Q: 我的網站類型不在 10 種原型中？
**A**: 找最接近的原型作為起點，然後在 `WEBSITE_MODULE_MATRIX.md` 基礎上調整模組深度。大部分網站是多種原型的混合。

### Q: P0 文件太多了，可以先跳過嗎？
**A**: 至少完成 Color Tokens + Typography + Spacing + Breakpoints。這四項是最小 P0，沒有它們 AI 產出的視覺一致性無法保證。

---

**最後更新**：2025-03-02
**維護者**：Prompt Architect Team
