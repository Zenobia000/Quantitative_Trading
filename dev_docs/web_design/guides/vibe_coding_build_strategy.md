# Vibe Coding 網站建置策略

> 先分層，不要先做頁面。模組解耦，才能長大。類型只是比例差異。

---

## 一、建置前的三個必答題

在打開任何 AI 工具之前，先回答這三個問題：

### Q1：這個網站的商業目標是什麼？

→ 查 [`references/website_recipes.md`](../references/website_recipes.md) 選定你的網站原型

不要從「我想做什麼頁面」開始，要從「這個網站要幫我達成什麼」開始。

### Q2：需要哪些積木模組？

→ 查 [`modules/WEBSITE_MODULE_MATRIX.md`](../modules/WEBSITE_MODULE_MATRIX.md) 確認模組組合

找到你的網站類型，看哪些模組亮燈、各要做到什麼深度。

### Q3：前置規範文件準備到什麼程度？

→ 查 [`references/prereq_document_checklist.md`](../references/prereq_document_checklist.md) 打勾確認

至少 P0 文件要備齊才開工。沒有 Design Tokens 就直接做，等於沒有尺規就畫建築圖。

---

## 二、Vibe Coding 建置 SOP（7 步驟）

```
Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6 → Step 7
選原型    確認模組   準備文件   初始化     定義頁面   組裝 Prompt  執行+QA
                    (P0)    Design     Page      Assembly
                           System     Spec      Prompt
```

### Step 1：選定網站原型

**輸入：** 你的商業想法
**工具：** [`references/website_recipes.md`](../references/website_recipes.md)
**產出：** 確定的網站類型 + 商業目標 + 參考網站

做什麼：
1. 瀏覽 10 種網站原型，選最接近的
2. 打開 Reference 網站，截圖你喜歡的部分
3. 記下商業目標和 MVP 最小集合

### Step 2：確認模組組合

**輸入：** 選定的網站類型
**工具：** [`modules/WEBSITE_MODULE_MATRIX.md`](../modules/WEBSITE_MODULE_MATRIX.md) + [`modules/MODULE_REGISTRY.md`](../modules/MODULE_REGISTRY.md)
**產出：** 模組清單 + 每個模組的深度等級 + 具體功能清單

做什麼：
1. 在矩陣中找到你的網站類型，看哪些模組亮燈
2. 到 MODULE_REGISTRY 查每個模組的功能細項
3. 決定 MVP 範圍：先做哪些、後做哪些

### Step 3：準備前置文件（P0）

**輸入：** 你的品牌資訊
**工具：** [`references/prereq_document_checklist.md`](../references/prereq_document_checklist.md) + [`global/SYSTEM_DOCUMENT_SPEC.md`](../global/SYSTEM_DOCUMENT_SPEC.md)
**產出：** 填寫完成的 P0 文件（品牌原則 + Design Tokens + Layout Spec + 基礎元件定義）

做什麼：
1. 複製 `SYSTEM_DOCUMENT_SPEC.md`，填入你的品牌資訊
2. 至少完成：Color Tokens + Typography + Spacing + Grid + Breakpoints
3. 對照 `prereq_document_checklist.md` 的 P0 打勾

### Step 4：初始化 Global Design System

**輸入：** Step 3 的 P0 文件
**工具：** [`global/BASE_DESIGN_SYSTEM.md`](../global/BASE_DESIGN_SYSTEM.md)
**產出：** 你的品牌專屬 Design System 文件（如 `global/01_sunny_brand_system.md`）

做什麼：
1. 複製 `BASE_DESIGN_SYSTEM.md`，改名為 `XX_brand_system.md`
2. 將 Step 3 的 Design Tokens 填入對應的 LAYER
3. 定義 UX Pattern（基於 MODULE_REGISTRY 選定的模組）

### Step 5：逐頁定義 Page Spec

**輸入：** Step 1 的頁面清單 + Step 4 的 Design System
**工具：** [`pages/page_template.md`](../pages/page_template.md)
**產出：** 每個頁面的規格文件（如 `pages/01_homepage.md`）

做什麼：
1. 從 `website_recipes.md` 的「推薦頁面」清單開始
2. 為每個頁面複製 `page_template.md`，填入：
   - PAGE META（名稱、路由、目標）
   - SECTIONS（功能區塊拆解）
   - COMPONENT SPEC（每個區塊的元件、狀態、佈局）
   - DATA & API（資料來源）
3. **MVP 優先**：先做核心頁面，次要頁面後補

### Step 6：組裝 Assembly Prompt

**輸入：** Step 4 的 Design System + Step 5 的 Page Spec
**工具：** [`assembly/PIPELINE_ORCHESTRATOR.md`](../assembly/PIPELINE_ORCHESTRATOR.md)
**產出：** 可直接餵給 AI 的完整 Prompt

做什麼：
1. 複製 `PIPELINE_ORCHESTRATOR.md`
2. 填入 Global Design System（壓縮版）
3. 填入當前要做的 Page Spec
4. 填入 Exception Rules（這個頁面的特殊規則）
5. 確認 Output Requirements

### Step 7：執行 + QA

**輸入：** Step 6 的 Assembly Prompt
**工具：** Lovable / Claude + [`guides/quality_checklist.md`](quality_checklist.md)
**產出：** 可運行的頁面

做什麼：
1. 將 Assembly Prompt 貼入 Lovable / Claude
2. 檢查產出是否符合 Design System
3. 用 `quality_checklist.md` 逐項驗收
4. 迭代修改直到通過

---

## 三、文件依賴關係圖

```
references/website_recipes.md ←── 選原型，拿配方+提示詞
    ↓
modules/WEBSITE_MODULE_MATRIX.md ←── 確認模組組合
    ↓
modules/MODULE_REGISTRY.md ←── 查模組功能細項
    ↓
references/prereq_document_checklist.md ←── 確認文件準備度
    ↓
global/SYSTEM_DOCUMENT_SPEC.md ←── 填寫前置文件（模板）
    ↓
global/BASE_DESIGN_SYSTEM.md ←── 初始化 Design System
    ↓
pages/page_template.md ←── 逐頁定義
    ↓
assembly/PIPELINE_ORCHESTRATOR.md ←── 組裝 Prompt
    ↓
guides/quality_checklist.md ←── 驗收
```

---

## 四、Vibe Coding 心法 — 與傳統開發的差異

### 傳統開發

```
需求文件 → 設計稿 → 切版 → 前端開發 → 後端開發 → 整合 → 測試 → 部署
（2-6 個月）
```

### Vibe Coding

```
選原型 → 查模組 → 準備 Tokens → 組裝 Prompt → AI 生成 → 驗收迭代
（1-7 天）
```

### 關鍵差異

| 維度 | 傳統 | Vibe Coding |
|------|------|-------------|
| 瓶頸 | 寫程式 | 描述清楚你要什麼 |
| 核心能力 | Coding | Prompting + 審美 + 商業判斷 |
| 速度 | 月計 | 天計 |
| 品質控制 | Code Review | Design System + QA Checklist |
| 擴展性 | 高（如果架構好） | 中（依賴 AI 一致性） |
| 適用場景 | 大型系統 | MVP / Landing / 行銷頁 / 中小型產品 |

### 五條心法

1. **先定規則再動手** — Design Tokens 是你的「工業模具」，沒有模具就是手工藝
2. **先看得到再看不到** — Public Layer → Conversion → Product → Infra
3. **一次做一頁** — 每次 Prompt 只做一個頁面，不要一次丟整個網站
4. **積木思維** — 不同網站只是不同模組的深度加權
5. **迭代取代完美** — 先出第一版，再用提示詞微調

---

## 五、常見陷阱與避坑指南

| # | 陷阱 | 為什麼會踩 | 怎麼避 |
|---|------|-----------|--------|
| 1 | 沒有 Design System 就直接做 | 急著看到結果 | 花 30 分鐘填 SYSTEM_DOCUMENT_SPEC，省 3 天改色改字 |
| 2 | 一次 Prompt 做整個網站 | 覺得 AI 萬能 | 一次一頁，用 Pipeline Orchestrator |
| 3 | 只做 Desktop 忘記 Mobile | 開發時只看大螢幕 | Breakpoints 在 P0 就要定義 |
| 4 | 沒有定義狀態 | 只想到 happy path | 每個元件都問：Loading? Error? Empty? Disabled? |
| 5 | 模組耦合 | 急著做完不管架構 | 按模組分開做，用 API/接口連接 |
| 6 | 不做 QA | 覺得 AI 做的一定對 | 每頁交付都走 quality_checklist.md |
| 7 | 忽略 Growth 模組 | 只想做功能 | SEO/Analytics 從第一天就要埋 |
| 8 | 複製整段 Design System 到每個 Prompt | Token 太多爆 context | 壓縮版：只放色值+字級+間距，不放解釋 |

---

## 六、Pipeline 完整目錄結構

```
prompt_architect_pipeline/
├── README.md                               ← 入口導覽
├── lovable_組裝.md                         ← Lovable 實作手冊
│
├── global/                                 ← 靈魂層（全域設計系統）
│   ├── BASE_DESIGN_SYSTEM.md              ← 設計系統模板
│   ├── SYSTEM_DOCUMENT_SPEC.md            ← 🆕 四層系統文件模板
│   └── 01_sunny_brand_system.md           ← 範例：Sunny 品牌
│
├── pages/                                  ← 骨架層（頁面規格）
│   ├── page_template.md                   ← 頁面規格模板
│   └── 01_dashboard.md                    ← 範例：Dashboard
│
├── assembly/                               ← 心臟層（組裝器）
│   ├── PIPELINE_ORCHESTRATOR.md           ← 組裝模板
│   └── 01_dashboard_integrated.md         ← 範例：完整 Prompt
│
├── modules/                                ← 🆕 積木層（模組系統）
│   ├── MODULE_REGISTRY.md                 ← 8 大模組定義
│   └── WEBSITE_MODULE_MATRIX.md           ← 模組 × 網站檢索表
│
├── references/                             ← 🆕 參考層（配方與檢核）
│   ├── website_recipes.md                 ← 10 種網站配方 + Reference
│   └── prereq_document_checklist.md       ← 前置文件檢核清單
│
└── guides/                                 ← 指南層
    ├── implementation_guide.md            ← 實作指南
    ├── quality_checklist.md               ← QA 清單
    └── vibe_coding_build_strategy.md      ← 🆕 建置策略（你在這裡）
```
