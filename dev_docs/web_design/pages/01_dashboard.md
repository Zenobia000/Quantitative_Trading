# Page-Level Prompt: Sunny AI Hub 首頁儀表板

> 範例：展示如何使用 `page_template.md` 填寫一個完整的頁面規格。

---

## [PAGE META]

- **page_name**: Sunny AI Hub Dashboard
- **route_path**: `/dashboard`
- **page_type**: dashboard
- **primary_goal**: 提供學員專案進度總覽與快捷學習入口
- **secondary_goal**: 展示學習成就激勵持續使用
- **target_users**:
  - 主要：已登入的學員（每日使用）
  - 次要：講師查看學員整體進度
- **entry_point**: 登入後直接導向 / 點擊 Logo 返回
- **expected_time_on_page**: 30秒-2分鐘（快速瀏覽後進入具體功能）

---

## [STRUCTURE: SECTIONS]

1. **welcome_header**
   - section_type: hero
   - section_purpose: 個人化歡迎訊息與本週學習統計

2. **quick_actions**
   - section_type: action_cards
   - section_purpose: 提供最常用功能的快捷入口

3. **active_learning**
   - section_type: course_list
   - section_purpose: 顯示進行中的課程與學習進度

4. **metrics_overview**
   - section_type: stats_cards
   - section_purpose: 展示學習成就統計與趨勢

5. **recent_activity**
   - section_type: history_list
   - section_purpose: 最近的學習紀錄與作業提交

---

## [SECTION COMPONENT SPEC]

### Section: welcome_header

- **layout**: 全寬單欄，左對齊
- **elements**:
  - greeting_text: H1 / required / "歡迎回來，{userName}"
  - date_time: Body SM / required / 當前日期
  - quick_stats: Stats Row / required / "本週學習: {hours}小時 | 完成: {count}單元"
- **states**:
  - default: 顯示個人化資訊
  - loading: Skeleton（greeting + 數字區）
- **copy_constraints**: 用戶名稱最多 20 字元

### Section: quick_actions

- **layout**: 1行4列卡片網格（Desktop）/ 2x2（Tablet）/ 1列（Mobile）
- **elements**:
  - course_card: ActionCard / required / icon: BookOpen / "查看課程" / → `/courses`
  - homework_card: ActionCard / required / icon: Upload / "提交作業" / → `/homework`
  - community_card: ActionCard / required / icon: Users / "進入社群" / → `/community`
  - favorites_card: ActionCard / required / icon: Heart / "我的收藏" / → `/favorites`
- **states**:
  - default: 白色背景
  - hover: 邊框變為 Sunny Orange (#F59E0B)，輕微上移 (-2px)
  - loading: Skeleton card
  - disabled: 灰度顯示（功能未開放時）

### Section: active_learning

- **layout**: 單欄列表，最多顯示 5 項
- **elements**:
  - section_title: H2 / required / "進行中的課程"
  - course_items: CourseRow[] / required
    - course_name: Body MD / required
    - progress_bar: ProgressBar / required / 顯示百分比
    - last_accessed: Caption / required / "上次學習: {時間}"
    - continue_btn: Button Secondary / required / "繼續學習"
  - view_all_link: Link / required / "查看全部課程 →"
- **states**:
  - default: 顯示課程列表
  - loading: Skeleton rows
  - empty: "還沒有進行中的課程，立即探索" + CTA「瀏覽課程」
  - error: 錯誤訊息 + 重試按鈕

### Section: metrics_overview

- **layout**: 1行4列指標卡片
- **elements**:
  - total_courses: MetricCard / required / "完成課程" + 數字 + vs 上月趨勢
  - total_hours: MetricCard / required / "學習時數" + 數字 + 趨勢
  - streak_days: MetricCard / required / "連續天數" + 數字
  - skill_radar: RadarChart / optional / 技術能力雷達圖
- **states**:
  - default: 顯示數值 + 趨勢箭頭
  - loading: Skeleton
  - hover: Tooltip 顯示詳細說明

### Section: recent_activity

- **layout**: 時間軸式列表，最多 10 項
- **elements**:
  - section_title: H2 / required / "最近活動"
  - activity_items: ActivityRow[] / required
    - timestamp: Caption / required
    - activity_type: Badge / required (完成課程/提交作業/社群發言)
    - summary: Body SM / required / 最多 80 字
- **states**:
  - default: 顯示活動列表
  - loading: Skeleton
  - empty: "還沒有活動紀錄"
- **copy_constraints**: 摘要保持在 2 行以內

---

## [INTERACTION & STATE FLOW]

### 主要互動流程

1. 頁面載入 → 取得學員資料 + 課程列表 + 指標數據
2. 點擊快捷卡片 → 導航至對應功能頁
3. 點擊「繼續學習」→ 進入課程播放頁
4. 點擊指標卡片 → 展開詳細報表

### RWD 行為差異

| 斷點 | 佈局 | 差異說明 |
|------|------|---------|
| Desktop (>1280px) | 完整 4 欄佈局 + 左側 Sidebar 展開 | 完整體驗 |
| Tablet (768-1280px) | 2 欄佈局 + Sidebar 收合 | 指標卡片 2x2 |
| Mobile (<768px) | 單欄堆疊 + 底部導航 | Sidebar 消失，改底部 Tab |

### 資料更新策略

- 課程進度：每次返回頁面時更新
- 指標數據：每 5 分鐘更新
- 活動紀錄：即時更新（新活動 prepend）

---

## [DATA & API]

- **uses_api**: true
- **endpoints**:
  - GET `/api/dashboard/overview` — 取得儀表板綜合資料
  - GET `/api/courses/active` — 取得進行中課程
  - GET `/api/metrics/learning` — 取得學習統計指標
  - GET `/api/activity/recent` — 取得最近活動
- **error_cases**:
  - 網路錯誤：顯示離線提示，使用快取資料
  - API 錯誤：顯示友善錯誤訊息 + 重試按鈕
  - 權限不足：導向登入頁

---

## [EXCEPTION TO GLOBAL RULES]

無特殊例外，完全遵循 Global System Prompt 規範。

---

## [ACCEPTANCE CRITERIA]

- [ ] 所有 5 個 Section 功能正常
- [ ] 所有快捷操作可正常導航
- [ ] 課程進度條正確顯示百分比
- [ ] 指標數據含趨勢箭頭
- [ ] Loading / Error / Empty 三態完備
- [ ] RWD 三個斷點行為正確
- [ ] 響應時間 < 2 秒
- [ ] 符合 Design System 視覺規範
