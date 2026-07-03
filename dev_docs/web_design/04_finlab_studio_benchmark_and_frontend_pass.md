# FinLab Studio 對標 + 前端排版補強 pass

> **產出**：2026-07-02 ｜ **方法**：multi-agent workflow（FinLab teardown + 現況前端 audit + 設計意圖 map → 三維第三方 UX review → adversarial verify → 綜合計畫）+ 主 agent 實作 + 2 個第三方 reviewer sub-agent 覆核
> **對象**：`frontend/`（React 19 + Router 7 + Tailwind，Grok 單色 dark）
> **範圍**：frontend-only 排版 / 位置 / 層級 / 旅程 / 可及性；**後端邏輯 / API / hooks 資料契約完全不動**
> **關聯**：`03_uiux_benchmark_and_reinforcement_plan.md`（10 大廠對標，**無 FinLab**——本文補此缺口）、`global/02_backtest_platform_brand_system.md`（設計系統真相源）

## 1. FinLab Studio 設計語言拆解（可轉移 / 不可轉移）

studio.finlab.finance 需登入；以下由 finlab.finance 公開站 + docs 歸納。

| FinLab 模式 | 對本平台的判定 |
| :--- | :--- |
| **chat-first**：自然語言描述選股 → AI 生成策略 + 回測 → 回報 | **部分轉移**：把「意圖」升為 New Run 的顯眼入口 + Cmd-K 收語意；不整碗端走對話迴圈 |
| **分頁報告**（return / risk / holdings / trades + 年份選擇） | **暫不轉移**：本平台 tear-sheet 端點尚未接線（PendingNote），硬做 tabs 會是空殼；待端點上線再說 |
| **大數字 stat 卡** | **轉移（重框）**：沿用為「以佐證取信」（coverage / reproduce），非炫耀式 CAGR |
| **顯眼 primary CTA（Start free）** | **轉移**：New Run 升為控制塔顯眼 primary；每工作流頁保留 sticky 下一步 |
| **漸進揭露**（自然語言先、Python 後） | **強轉移**：New Run raw-JSON params 收進「進階」`<details>`，guided 欄位先行 |
| **卡片式高可掃描 + 大量留白（淺色）** | **拆分**：卡片式 IA 轉移；**淺色主題不轉移**——維持 Grok 單色 dark |
| 橫向 top nav / 定價分層 / 社群背書 | **不轉移**：本平台為機構級單人研究工具，用 sidebar + Cmd-K；無獲客漏斗 |
| 「validation, not prediction」定調 | **轉移為核心論述**：防過擬合 gate 維持不可逆、不消費化 |

**一句話**：本平台既有 IA（Research→Monitor→System，doc 03 已落地）正確，本次是「FinLab 對標的排版 / 層級 / 旅程打磨」而非改版換膚。

## 2. 第三方 UX review 結果

33 個 workflow sub-agent（32 成功）產出 26 findings；adversarial verify（real + frontend-only）後 **23 confirmed**、3 dropped（not-real）。兩輪獨立 review 收斂到同一批 cluster。另抓到 2 個自身 faithfulness bug：`CommandPalette` `shadow-xl`（違反 flat）、`PromotePage` 未定義 token `bg-surface-raised`（渲染透明）。

## 3. 已實作變更（4 workstream，全 frontend-only）

- **WS-A 旅程完整性 + bug**：Promote orphan → Strategy Library 卡片加 **gated** 「晉升」forward-link（`validation_status==='is_pass'` 才解鎖，維持 gated 語意，不進 sidebar）；`RunsTable` 接住 `?strategy_id=` 客端篩選 + 篩選 chip（原先卡片帶的篩選被丟棄）；Validate 冷啟動加「從 Runs 挑選候選」回 ledger link；補 `--bg-raised` token（修 `surface-raised`）；移除 `shadow-xl`。
- **WS-B 共用原子**：新增 `StatCard`（big-number 層級；loss 用 `--loss-aaa` 達 AAA），合併三處重複 KPI 卡；`SimpleTable` 加 sticky 表頭 / row hover / 右對齊選項；`PendingNote` 改虛線 + 退 `bg-base`。
- **WS-C 控制塔 + wayfinding + onboarding**：Home 前置真實資料（pending 置底）、New Run 升為顯眼 primary、移除死 ⌘K 重複鈕；`PageHeader` 加 `back` 深頁導覽（route 弱化為 `sm:` 才顯）；`FirstRunEmptyState` 三 on-ramp 改真實可點；sidebar RESEARCH 標序號成有序迴圈。
- **WS-D 漸進揭露 + a11y**：New Run raw-JSON params → `<details>` 進階區（payload 不變、錯誤自動展開）；drawer focus-trap + Escape + aria-modal + 關閉還焦點；CommandPalette combobox/listbox/option roles（options `tabIndex=-1`）；`--text-muted` 0.55→0.6（仍 < secondary 0.65）。

## 4. 驗證 + 第三方覆核

- typecheck ✅、`npm test` 46/46 ✅、`npm run build` ✅
- `git diff --name-only`：18 檔全在 `frontend/src` + `tailwind.config.ts` + 新 `StatCard.tsx`；**無** api / hooks / services / types 變更
- **Reviewer 1（correctness）**：SHIP —— KPI 格式化在 KpiCard 路徑證明等價；filter/gate/details/router 全正確；契約保留。
- **Reviewer 2（design/a11y）**：SHIP-WITH-FIXES —— 1 HIGH（loss KPI 應用 `--loss-aaa` 達 AAA，已修）+ 4 LOW（3 已修：CommandPalette option `tabIndex`、drawer 還焦點、範例鈕正名；1 sidebar 序號 acceptable）。token 紀律 / 雙編碼 / gated Promote / 漸進揭露皆判定 faithful。

## 5. 刻意不做（維持設計意圖）

- 不翻淺色主題、不換掉 Grok 單色 dark；不引入品牌色 / 陰影。
- 不消費化防過擬合 gate（Validate / Promote 維持不可逆、gated）。
- tear-sheet 不硬做分頁（端點未接線前是空殼）——待 producer 上線再落地。
- VH-02 通用 `Section` primitive 未全面採用（僅 `StatCard` 落地），留待增量收斂 spacing/heading drift。
