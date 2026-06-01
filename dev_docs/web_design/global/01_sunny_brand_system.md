# Example Brand System: Sunny Data Science

> 這是 `BASE_DESIGN_SYSTEM.md` 的具體實作範例，用於「桑尼資料科學」品牌。
> 展示如何填寫四層架構的完整 Design System。

---

## [GLOBAL ROLE]

你是「桑尼資料科學 (Sunny Data Science)」的資深產品架構師。你負責確保所有 AI 生成的網頁符合品牌專業、高資訊密度且具備教育感的特質。

## [PRODUCT CONTEXT LAYER]

- **產品名稱**：Sunny AI Learning Hub
- **產品一句話**：專為資料科學家設計的 AI 學習與專案管理中樞。
- **目標用戶**：
  - 主要：參加 Sunny 課程的學員、AI 開發者
  - 次要：尋找 AI 解決方案的企業主管
- **核心價值主張**：將複雜的 AI 概念可視化，提供結構化的學習路徑與專案追蹤。
- **網站類型**：EdTech 教育（參考 `references/website_recipes.md` → EdTech）
- **啟用模組**（參考 `modules/WEBSITE_MODULE_MATRIX.md`）：
  - Identity 🟠 L2（角色權限 + 訂閱狀態）
  - Content 🟠 L2（Blog + 課程介紹頁）
  - Commerce 🟠 L2（課程購買 + 訂閱制）
  - Delivery 🔴 L3（影片播放 + 章節系統 + 作業/測驗）
  - Community 🟠 L2（討論區 + 互評）
  - Growth 🟠 L2（SEO + Email 自動化 + Analytics）
  - Admin 🟠 L2（用戶管理 + 課程上架 + 報表）
  - Infrastructure 🟠 L2（Supabase + CDN + CI/CD）

## [BRAND & VOICE LAYER]

### 設計原則

| # | 原則 | 說明 | 當衝突時 |
|---|------|------|---------|
| 1 | 資訊優先 | 內容的清晰度永遠優先於裝飾 | 砍動畫保可讀性 |
| 2 | 學習友善 | 降低認知負擔，分步驟引導 | 用預設值取代設定項 |
| 3 | 數據驅動 | 用數據而非形容詞傳達狀態 | 顯示進度百分比而非「進行中」 |
| 4 | 鼓勵探索 | 空狀態要引導行動 | 提供建議路徑而非空白頁 |

### 品牌性格

| 維度 | 我們是 | 我們不是 |
|------|--------|---------|
| 語氣 | 專業但親切 | 冷冰冰的企業腔 |
| 視覺 | 溫暖且乾淨 | 華麗花俏 |
| 態度 | 鼓勵嘗試、容錯 | 高高在上 |

### 文案規則

- 稱呼用戶：「你」
- 按鈕動詞：主動語態 —「開始學習」「提交作業」
- 錯誤訊息：先說發生什麼，再說怎麼修 —「上傳失敗，請確認檔案小於 10MB」
- 空狀態：鼓勵行動 —「還沒有任何課程，立即探索」
- 語言：繁體中文為主，保留技術術語英文

---

## [VISUAL DESIGN SYSTEM LAYER]

### Color Tokens

| Token | 色值 | 用途 |
|-------|------|------|
| Primary | #F59E0B | Sunny Orange — 熱情與啟發 |
| Primary Hover | #D97706 | 主色 hover |
| Secondary | #1E293B | Slate Blue — 深度與專業 |
| Accent | #10B981 | Emerald — 成長與成功 |
| Error | #EF4444 | 錯誤、危險 |
| Success | #10B981 | 成功、完成 |
| Warning | #F59E0B | 警告（與 Primary 共用） |
| Info | #3B82F6 | 資訊提示 |
| BG Page | #F8FAFC | 頁面底色 |
| BG Surface | #FFFFFF | 卡片/容器底色 |
| Text Primary | #1E293B | 主要文字 |
| Text Secondary | #64748B | 次要文字 |
| Border Default | #E2E8F0 | 預設邊框 |

### Typography

| Token | 字級 | 行高 | 字重 | 用途 |
|-------|------|------|------|------|
| Display | 36px | 1.2 | 700 | Hero 標題 |
| H1 | 30px | 1.2 | 700 | 頁面標題 |
| H2 | 24px | 1.3 | 600 | 區塊標題 |
| H3 | 20px | 1.4 | 600 | 小標題 |
| Body LG | 18px | 1.6 | 400 | 大段落 |
| Body MD | 16px | 1.5 | 400 | 標準段落 |
| Body SM | 14px | 1.5 | 400 | 小字說明 |
| Caption | 12px | 1.4 | 400 | 標註/時間戳 |

- 英文：JetBrains Mono（程式碼感）
- 中文：Noto Sans TC（清晰感）
- 程式碼：JetBrains Mono

### 元件風格

| Token | 值 | 用途 |
|-------|-----|------|
| Radius SM | 4px | Tag, Badge |
| Radius MD | 8px | 按鈕、輸入框 |
| Radius LG | 12px | 卡片、容器 |
| Radius XL | 16px | Modal |
| Shadow SM | 0 1px 3px rgba(0,0,0,0.1) | 卡片預設 |
| Shadow MD | 0 4px 6px rgba(0,0,0,0.1) | 懸浮卡片 |
| Shadow LG | 0 10px 15px rgba(0,0,0,0.1) | Modal |
| Border | 1px solid #E2E8F0 | 預設邊框 |

### RWD / Grid

| 屬性 | 值 |
|------|-----|
| 最大寬度 | 1280px |
| 欄數 | 12 |
| 欄間距 | 24px |
| 左右 Padding | 16px (Mobile) / 24px (Tablet) / 32px (Desktop) |
| Mobile | < 768px（1 欄） |
| Tablet | 768px - 1280px（2 欄） |
| Desktop | > 1280px（12 欄） |

---

## [UX PATTERN LAYER]

### 常用佈局 Pattern

- **Dashboard**：左側深色導航 (#1E293B, 240px) + 主內容區 + 右側輔助面板
- **Course Page**：左側課程目錄 + 中間影片/內容 + 右下進度追蹤
- **List Page**：上方篩選列 + 卡片網格 + 分頁器

### 狀態設計規則

| 狀態 | 規則 |
|------|------|
| Loading | Skeleton screen 優先，長任務需有進度百分比 |
| Empty | 鼓勵行動的圖示 + 引導文字 + CTA 按鈕 |
| Error | 紅色提示區 + 具體錯誤說明 + 建議動作 + 重試按鈕 |
| Disabled | 灰度 + tooltip 說明原因 |

### 元件狀態定義（核心元件）

| 元件 | Variants | States |
|------|----------|--------|
| Button | Primary(Orange) / Secondary(Slate) / Ghost / Danger | Default / Hover / Active / Disabled / Loading |
| Card | Default / Clickable / Course Card | Default / Hover(Orange border) / Active |
| Input | Text / Password / Search | Default / Focus(Orange ring) / Error / Disabled |

---

## [INTERACTION & ACCESSIBILITY]

- Button/Link：背景色加深 10% on Hover
- Card：Hover 時邊框變為 Sunny Orange (#F59E0B)，輕微上移 (-2px)
- Sidebar：預設收合 (Mobile)，展開 (Desktop)，深色背景
- Charts：統一配色以 Orange/Emerald 為主
- 錯誤訊息格式：「[問題描述]。[建議動作]。」
- 鍵盤：完整 Tab 順序 + Focus ring (Orange)

---

## [TECH & CONSTRAINT LAYER]

- Frontend: React 18 + TypeScript + Tailwind CSS
- State: Zustand
- Forms: React Hook Form + Zod
- Data Viz: Recharts
- Backend: Supabase (Auth + DB + Storage)
- Hosting: Vercel
- FMP < 2s / FID < 100ms
- 禁止 Inline styles / 禁止過度動畫

---

## [DATA PATTERN LAYER]

- 日期：YYYY-MM-DD HH:mm
- 數字：千分位逗號
- 百分比：一位小數 (33.3%)
- 金額：NT$ + 千分位
- 學習時數：X 小時 Y 分鐘

---

**版本**: v2.0
**套用對象**: Sunny AI Learning Hub 全站
**最後更新**: 2025-03-02
