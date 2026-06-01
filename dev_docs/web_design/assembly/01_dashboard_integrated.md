# EXAMPLE: Integrated Dashboard Prompt (Sunny Hub)

> 此檔案展示如何將 `global/01_sunny_brand_system.md` 與 `pages/01_dashboard.md` 組合起來。
> 這就是你應該貼給 Lovable 或 Claude 的最終 Prompt。
> 對應 `guides/vibe_coding_build_strategy.md` → Step 6。

---

## === GLOBAL PROJECT GUIDELINE (THE SOUL) ===

你是「桑尼資料科學 (Sunny Data Science)」的資深產品架構師。

### 核心設計系統
- **配色**: Primary(#F59E0B Sunny Orange) / Secondary(#1E293B Slate Blue) / Accent(#10B981 Emerald) / Error(#EF4444)
- **字體**: JetBrains Mono (英) + Noto Sans TC (中)，字級 H1(30px) / H2(24px) / H3(20px) / Body(16px) / Small(14px)
- **元件**: 圓角 8px，陰影 0 1px 3px rgba(0,0,0,0.1)，邊框 1px solid #E2E8F0
- **語氣**: 專業但親切、數據驅動、鼓勵探索
- **斷點**: Desktop(>1280px) / Tablet(768-1280px) / Mobile(<768px)

### 重要規範
- 本區段為最高準則，所有元件必須繼承此處定義的配色、圓角與間距。
- 除非 EXCEPTION RULES 明確說明，否則不准違反。

---

## === CURRENT PAGE SPEC (THE SKELETON) ===

本次任務是實作「Sunny AI Learning Hub 首頁儀表板」。

### [PAGE META]
- page_name: Sunny AI Hub Dashboard
- route_path: /dashboard
- page_type: dashboard
- primary_goal: 提供學員專案進度與快捷學習路徑
- target_users: 已登入學員（每日使用）

### [STRUCTURE: SECTIONS]

1. **welcome_header**: 歡迎學員，展示本週學習時數。
2. **quick_actions**: 上傳作業、查看課程、進入社群、我的最愛。（1行4列卡片）
3. **active_learning**: 進行中的課程與學習進度條。（列表，最多 5 項）
4. **metrics_overview**: 總完成課程數、累積學習時數、技術雷達圖。（1行4列指標卡）

### [COMPONENT SPEC]
- **Sidebar**: 深色 (#1E293B)，固定於左側 240px，Mobile 預設收合。
- **ActionCards**: 白色背景，Hover 時邊框變為 Sunny Orange (#F59E0B)，輕微上移。
- **MetricCards**: 白色背景，含數值 + 趨勢箭頭 + vs 上月百分比。

### [STATES]
- Loading: 所有 section 使用 Skeleton screen
- Empty (active_learning): 「還沒有進行中的課程，立即探索」+ CTA 按鈕
- Error: 紅色提示 + 具體訊息 + 重試按鈕

### [RWD 行為]
- Desktop (>1280px): 完整 4 欄佈局 + Sidebar 展開
- Tablet (768-1280px): 2 欄佈局 + Sidebar 收合
- Mobile (<768px): 單欄堆疊 + 底部導航

---

## === EXCEPTION RULES ===

無特殊例外，完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**: 列出 4 個 sections 及其關鍵元件。
2. **設計決策**: 說明如何透過顏色傳達「熱情與專業並重」。
3. **程式碼**: 產出完整前端代碼，使用 Recharts 實作指標圖表。

---

*組裝日期: 2025-03-02 | 使用 Global System v2.0 | 負責人: Sunny*
