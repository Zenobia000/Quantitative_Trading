# ADR-018: 監控優先 → 研究迴圈優先（Run 物件化 + 研究工作區 IA + 驗證/晉升 gate 工作流）

> **狀態：** 已接受 | **日期：** 2026-06-02 | **決策者：** Self
> **相關：**
> - [ADR-009](./ADR-009-dual-dashboard-telegram-monitoring.md)（雙儀表板分層）、[ADR-015](./ADR-015-dashboard-design-system-and-react-upgrade.md)（儀表板 Design System + React）— 本 ADR **不取代**其分層原則與設計系統，但**重定位**其產物：A–E 從「sidebar 主層級」降為 live 監控子視圖，Panel E 從唯讀展示改隸屬 Validate gate。
> - [ADR-017](./ADR-017-m2-is-gate-failed-return-to-m0-entry-redesign.md)（M2 IS gate FAIL → 回 M0 重設進場）— 本 ADR 是其 UX/工具層投射：把「IS gate FAIL → 回 M0」從散落 ADR 的人工事件，升為系統內可重複、可審計的 gate 工作流。
> - [ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（K1/K2/K3 凍結）— IS gate 硬門檻來源。
> - 證據包：[`web_design/03_uiux_benchmark_and_reinforcement_plan.md`](../web_design/03_uiux_benchmark_and_reinforcement_plan.md)（10 平台大廠對標 + 10 維度差距 + 7 流程圖 + roadmap）。
> - 後續落地真相源：`21_data_contract.md`（runs 主表 / RunConfig / validation_status DDL）、`06_api_design_specification.md`（CLI/API）、`16_wbs_development_plan.md` §8.G。

---

## 1. 背景與問題

- **上下文**：現行 L7 監控規劃（ADR-009 / ADR-015 / `20_dashboard_specification.md`）共 5 面板（A 績效 / B 部位 / C 訊號 / D 風控 / E 驗證）+ Grafana（F–I）+ Discord 告警，**100% 服務「監控一支已部署/live 策略」**。sidebar 主層級被 A–E 佔滿。
- **問題**：回測平台真正的核心工作迴圈 — **構想 → authoring → 設定回測 → 跑 → 分析 → 比較/掃描 → 驗證(IS→WFA→OOS) → 晉升(paper→live)** — 在 UX 層幾乎完全缺席，且後端缺對應契約：
  - **「一次回測」未物件化**：`run_id` 已散落在 4 張時序表（equity/positions/signals/risk）卻無主表承載、無 lineage、無 code/engine/bundle 版本綁定 — 等於「插了鋼筋沒蓋樓」。雙引擎（zipline+vectorbt）下尤其無法回答「這條 equity 是哪版策略、哪個引擎、哪段資料跑的」。
  - **防過擬合只停在「算數字 + 唯讀展示」**：Panel E 把 PBO/DSR/WFA 畫成 KPI 卡，但不擋任何晉升動作。M2 IS gate FAIL（ADR-017）已親身證明「唯讀指標 + 人工紀律」這次靠人撐住、下次未必。
  - **晉升靠改一個 flag**：backtest→paper→live 三模式切換（ADR-008）無狀態機、無強制 checklist、無 audit，任何時候可跳過驗證直接 live。
- **觸發事件**：ADR-017 回 M0 重設進場（v2→v3）本質是一連串「改 13 參數 → 跑 run → 比較 → 守門」的密集迭代，目前只能在 CLI + ADR 純文字裡硬撐。2026-06-02 對 10 個大廠量化/回測/實驗追蹤平台（QuantConnect / WorldQuant BRAIN / Numerai / Bloomberg-BQuant / W&B / MLflow / zipline·vectorbt·QuantStats 報表慣例 / 機構研究平台 / 開發者工具設計語言 / 防過擬合研究紀律）做 deep-research 對標，**一致驗證**價值重心在迴圈前半段，監控只是最後一站。

## 2. 大廠對標核心結論（證據摘要）

完整見 `web_design/03_uiux_benchmark_and_reinforcement_plan.md`。三條決定性發現：

1. **所有大廠的 UX 都圍繞一等公民 `Run` 物件**（config + 資料快照 + code/engine 版本 + metrics + status + lineage）的「生成 → 比較 → 守門 → 晉升」狀態機。runs table 是研究者每日真正的工作台，價值高於 tear sheet。
2. **唯讀展示 ≠ 工作流強制**。有效的防過擬合是「流程鎖定 + 資料封存 + 試驗次數校正」：QuantConnect 的 overfitting power gauge（每跑一次就更靠近過擬合）、WorldQuant BRAIN 的提交後才 OOS 計分、Numerai 的 staking 後果。
3. **沒有任何一家**同時做到「強制鎖 OOS + 限提交次數 + 試驗次數 deflate DSR + PBO/DSR 自動擋晉升」。這是本專案可超越大廠的**差異化機會**，且全部可純後端 Python/CLI 實作。

## 3. 考量的選項

### 選項一：維持監控優先，僅補完 A–E 細節
- **描述**：續推 5 面板監控，補 tear sheet 缺件，研究迴圈繼續走 CLI。
- **缺點**：在策略尚無 edge、無前端、正密集重設進場（ADR-017）的當下，把投資押在大廠**最不投資**的監控階段；研究迭代的痛點（無 run 追蹤、無比較、無 gate）完全不解。**拒絕**。

### 選項二：先做最重前端（hosted notebook / 完整 model registry / 競賽 leaderboard）
- **描述**：照機構平台規格做重前端。
- **缺點**：單人開發、無前端基礎、ROI 倒掛；多為過度設計。**拒絕**。

### 選項三：監控優先 → 研究迴圈優先，後端契約先行 ★採納
- **描述**：把 sidebar 主層級從 A–E 監控擴成「研究工作區（Runs / New Run / Compare / Sweep / Validate / Promote）」，A–E 降為 live 監控子視圖；把「一次回測」升格為一等公民 `Run` 物件；把防過擬合從唯讀展示升為 IS→WFA→OOS 不可逆 gate 工作流 + OOS sealed vault + 試驗次數→DSR deflate；把晉升升為 backtest→paper→live 狀態機。**後端契約（純 Python/CLI、可 TDD）先行，最薄前端隨 ADR-015 React 化批次補。**
- **優點**：直接服務正在進行的 M0 進場重設；複用既有設計系統與 A–D 高品質元件；可純後端起步、符合「無前端」現況；防過擬合差異化。
- **成本**：新增 runs 持久層與狀態機後端、IA 重構、前端逐步補。可控且分階段。

## 4. 決策

**選擇：選項三。** 確立四項決策：

1. **Run 物件化為一等公民**：新增 `runs` 主表為 single source of truth（run_id PK + strategy_version + engine + bundle_ref + git_commit + params_json + cost_assumptions_json + IS/OOS 區間 + metrics + status + trials_count + lineage）。equity/positions/signals/risk_metrics 的 `run_id` 補 FK。DDL 落 `21_data_contract.md` §4。
2. **資訊架構：研究工作區為 sidebar 主層級，監控降子視圖**。route 由 `/dashboard/*` 重整為 `/research/*`（Runs / New Run / Compare / Sweep / Validate / Promote）+ `/monitor/*`（A–E live 子視圖）。新增 Cmd-K command palette + Saved Views + CLI-first `FirstRunEmptyState`。**這是本 ADR 唯一的 IA 級變動。**
3. **驗證 = gate 工作流而非展示**：`validation/gate_state.py` 實作 IS→WFA→OOS 不可逆狀態機（IS PASS 才解鎖 WFA，WFA PASS 才解鎖 OOS）；**OOS sealed vault**（前置 gate 未過前 OOS 區段對 CLI/UI 皆不可讀/不可執行、每次存取計次留痕）；**試驗次數 → DSR 自動 deflate**；IS gate 硬門檻清單逐條綠/紅（ADR-016 K1/K2/K3 + sub-period/HHI/min-trades）；PBO>0.5 或 DSR<1.0 自動擋晉升。Panel E 從監控區唯讀展示**重定位**至 `/research/validate` gate 視圖。
4. **晉升 = backtest→paper→live 不可逆狀態機**：`Draft → Backtested → Validated → Paper → Live → Retired`，各轉換有硬門檻 checklist + audit log + 回退邊（gate FAIL 回 Draft = ADR-017「IS gate FAIL → 回 M0」的系統化實現）；強制 paper 觀察期取代真錢後果。**刻意不做**：跨人競賽 leaderboard、群眾外包/staking、Alpha marketplace、分散式掃描叢集、完整 champion/challenger Model Registry、多人簽核。

**落地節奏（鐵律：補齊研究迴圈前不再擴張監控 panel）**：
- **M0/M2 後端契約先行**：runs 主表 + RunConfig schema（IS/OOS+成本攤平+engine+range/step+hypothesis）+ gate_state.py + OOS sealed vault + trials 計數 + sweep/compare CLI。純 Python 可 TDD。
- **M3 最薄前端**（與 Panel A/B/C React 化同期）：Runs Table / New Run / Run Report（複用 Panel A）/ Compare·Sweep / Validate gate / Cmd-K。
- **M5**：Promotion stepper；A–E 改名 `/monitor/*`；Panel D / Panel B live WebSocket 維持凍結不提前。

## 5. 後果

### 正面
- 研究迭代迴圈被頁面化，直接服務 ADR-017 的 M0 進場重設（高頻「改參數→跑 run→比較→守門」）。
- 補齊整個 OSS 生態都缺的 Run 物件 + lineage，雙引擎可重現性底線達標。
- 防過擬合從「畫了儀表盤沒接煞車」升為系統強制，是 M2 IS gate FAIL 的結構性解法，且為對大廠的差異化。
- 既有設計系統（Grok 單色 dark / token / WCAG / 漲跌雙編碼 / Geist Mono）與 A–D 高品質元件全可複用，不推翻。

### 負面 / 成本
- 新增後端：runs 持久層、狀態機、sealed vault、trials 計數、sweep/compare CLI（可 TDD，但是真實工時）。
- 設計系統需受控擴充：data-viz 內容區開「離散類別色盤 + 發散色階」例外通道（compare/heatmap 需要 8–12 類別，單色明度階物理上不足；Panel C 已用 5 鮮豔色破例為證），並補 CodeEditor / ResearchTable / CompareChart 元件。**唯一設計語言變動**：把「不引入鮮豔彩色」改為「chrome 單色、資料區受控彩色」雙層規則。
- 前端工時整體上移（與 ADR-015 已接受的前端負擔同方向）。

### 影響範圍
- `21_data_contract.md`：新增 runs 主表 + RunConfig + validation_status / trials_count / is_oos_sealed + promotion_audit DDL；4 張時序表 run_id 補 FK。
- `06_api_design_specification.md` + `README.md`：新增 `run-new`/`run-list`/`sweep`/`compare`/`validate is|wfa|oos`/`promote check` CLI 子命令與對應 endpoints。
- `backtest_platform/src/.../validation/`：新增 `gate_state.py`（狀態機 + sealed vault）；`engines/zipline_adapter/cli.py` 擴 RunConfig。
- `20_dashboard_specification.md`：L7 監控重定位為迴圈最後一站；Panel E 真相源由唯讀展示改 gate。
- `web_design/`：sidebar IA 兩段式、route 表新增 `/research/*`、Panel E 重定位、新增研究級元件規格、設計系統 token 擴充；新增 `pages/03_*`（runs table / run report / compare·sweep / strategy author / promotion）。
- `02_project_brief_and_prd.md` §決策沿革（D-016）、`INDEX.md`（ADR 17→18）、`16_wbs_development_plan.md` §8.G。

### 重新評估觸發
- 若 runs 持久層 + gate 後端工時超出單人負擔 → 縮小至「runs 主表 + IS gate 狀態機」最小集，sweep/promote 延後。
- 若 M0 進場重設快速找到 v3 edge 並計畫近期上 paper → A–D 監控優先序上調。
- 若受控彩色資料區與 Grok 單色基調產生視覺衝突困擾 → 收斂 categorical 色盤飽和度或回退純明度階。

## 6. 執行計畫

1. ✅ 本 ADR 記錄決策 + 大廠對標證據（`web_design/03_uiux_benchmark_and_reinforcement_plan.md`）
2. ⏳ 後端契約（M0/M2，TDD 先行）：runs 主表 DDL（21）+ RunConfig Pydantic schema + `validation/gate_state.py`（IS→WFA→OOS + OOS sealed vault）+ trials 計數
3. ⏳ CLI 擴充（06 + README）：run-new/run-list/sweep/compare/validate/promote
4. ⏳ 設計系統 token 擴充 + 研究級元件規格（web_design global + pages/03_*）
5. ⏳ M3 最薄前端（隨 ADR-015 React 化）：Runs Table / New Run / Run Report / Compare·Sweep / Validate gate / Cmd-K
6. ⏳ M5：Promotion stepper + A–E 改 `/monitor/*` 子視圖

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-02 | Self | 初版 — 監控優先→研究迴圈優先；Run 物件化 + 研究工作區 IA + IS→WFA→OOS gate + OOS sealed vault + 晉升狀態機；後端契約先行 |
