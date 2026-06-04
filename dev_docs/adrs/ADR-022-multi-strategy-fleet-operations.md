# ADR-022: 多策略艦隊營運（champion/challenger lite）— 營運層範圍擴張

> **狀態：** 已接受 | **日期：** 2026-06-04 | **決策者：** Self
> **相關：**
> - [ADR-018](./ADR-018-monitoring-to-research-loop-pivot.md)（監控→研究迴圈優先）— 本 ADR **延伸**其監控層：A–E 單策略子視圖之上補一個多策略艦隊總控。
> - [ADR-008](./ADR-008-tri-mode-shared-strategy-code.md)（三模式 backtest/paper/live）+ ADR-018 晉升狀態機 — 艦隊是「已晉升至 paper/live 的策略」的營運面，研究面（晉升前）不變。
> - 證據/落地：`web_design/pages/monitor_fleet.md`（艦隊板頁規格，route `/monitor`）、`web_design/03_uiux_benchmark_and_reinforcement_plan.md` §5.3（原刻意延後）、`25_fe_be_rest_contract.md` §6.2（`/monitor/fleet*` 端點已登錄）、`02_project_brief_and_prd.md` §不做什麼 + 決策沿革 D-018。

---

## 1. 背景與問題

- **既有範圍宣告（單策略）**：`02 PRD` §不做什麼明列 **「❌ 多策略管理（單一策略為主）」**；D-001「採用 v2.md 為單一策略契約」。`03 §5.3` 也把 **champion/challenger registry、跨人 leaderboard、staking** 列為「刻意不做」，把研究流程縮小成單人務實版「一次研究一隻 → 晉升 → 監控那一隻」。
- **觸發事件**：使用者明確要求「**管理多隻策略像員工、退化就換掉**」（退化偵測 + 降級/退役/換掉 challenger）。為此補回 `web_design/pages/monitor_fleet.md`（艦隊板，Monitor zone home `/monitor`），但該頁自陳「**屬產品範圍擴張，建議補一則 ADR**」——即與 PRD「❌ 多策略管理」+ 03 §5.3「刻意不做」直接抵觸，需一則 ADR 正式裁定範圍，否則 monitor_fleet 成為孤兒 scope-creep。
- **問題本質**：要不要把「同時營運多隻策略」納入範圍？若要，邊界畫在哪，才不滑坡成大廠級 model registry / 多人簽核（單人專案養不起）？

## 2. 關鍵區分（裁定的核心）

**「研究」與「營運」分屬兩層，範圍各自獨立**：

| 層 | 範圍 | 本 ADR 立場 |
| :--- | :--- | :--- |
| **研究迴圈**（Draft→Backtested→Validated）| 一次深究一隻策略的進場/驗證迭代 | **維持單策略**（ADR-018 不變；研究工作區仍 strategy_id 單選深究）|
| **營運/監控**（Paper→Live→Retired）| 同時監控/操作多隻**已晉升**策略，退化偵測 + 處置 | **擴張為多策略艦隊（lite）** |

即：**多策略不是「同時研究很多隻」，而是「同時營運已驗證晉升的數隻」**。艦隊板服務的是 ADR-018 晉升狀態機「Paper/Live」端的數隻策略，不是研究端。

## 3. 考量的選項

### 選項一：維持單策略，不做艦隊（撤回 monitor_fleet）
- **描述**：堅守 PRD「❌ 多策略管理」，monitor_fleet 撤回，營運永遠只看一隻。
- **缺點**：使用者實需「退化換掉」是真實營運痛點（champion 退化時要有 challenger 接手、要看相關性避免重押同因子）；單策略監控無法回答「我這幾隻整體曝險/相關性如何」。**拒絕**。

### 選項二：做完整 champion/challenger Model Registry（大廠級）
- **描述**：照 BRAIN/機構平台做完整模型註冊、跨人 leaderboard、staking、多人簽核。
- **缺點**：單人專案、0 可部署策略的當下，ROI 倒掛；03 §5.3 已正確排除。**拒絕**。

### 選項三：多策略艦隊 lite（營運層擴張，研究層不動）★採納
- **描述**：營運/監控層支援同時看 N 隻 paper/live 策略——艦隊健康評分、live 績效、退化偵測一覽 + 對退化者的降級/退役/換掉（晉升 challenger）處置；補組合層相關性矩陣（避免重押同因子）。研究迴圈、晉升狀態機、不可逆 gate 全部沿用 ADR-018 不動。
- **刻意仍不做**（保留 03 §5.3 排除項）：跨人競賽 leaderboard、群眾外包/staking 經濟後果、Alpha marketplace、完整 champion/challenger Model Registry（版本族譜/血統的重型註冊）、多人簽核審批。**lite = 單人營運數隻策略，非組織級模型治理。**
- **優點**：服務真實營運痛點；複用 ADR-018 晉升 audit（換掉=demote/retire 寫 promotion_audit）；端點已在 doc 25 §6.2 登錄、屬 Monitor 區 M4 deferred-stub，不增前置。

## 4. 決策

**選擇：選項三。** 確立四點：

1. **營運層範圍擴張為多策略艦隊 lite**：Monitor zone 補 zone home `/monitor`（monitor_fleet）——N 隻 paper/live 策略的 stage/健康評分/live KPI/退化旗標一覽，下鑽單策略 Panel A–D。
2. **處置 = 沿用 ADR-018 晉升狀態機**：降級/退役/換掉（晉升 challenger）皆為晉升狀態機轉換，寫 `promotion_audit`（不另立治理）。`POST /monitor/fleet/{strategy_id}/action`（doc 25 §6.2）即此。
3. **補組合層視角**：組合 equity/曝險/Heat/計數（`/monitor/portfolio-summary`）+ 策略間報酬相關性矩陣（`/monitor/correlation`，避免重押同因子，呼應 03 §5.3 correlation gate）。
4. **研究層與排除項不動**：研究迴圈維持單策略深究；跨人 leaderboard / staking / 完整 registry / 多人簽核 **仍刻意不做**。

**Gating（誠實標註）**：艦隊屬 **M4–M5**（需 M4 live-telemetry daemon 才有 live 資料），且**唯有 ≥1 隻可部署策略才有意義、≥2 隻艦隊才划算**。當下**0 隻可部署策略**（四層共振負 edge 已砍、動能未達門檻）——故本 ADR 為**前瞻範圍裁定**：記錄「為何 monitor_fleet 存在 + 何時啟用」，**不在 edge 未證前實作**（與 8.G/8.H 前端 gating 同律）。

## 5. 後果

### 正面
- monitor_fleet 從孤兒 scope-creep 轉為有 ADR 背書的營運層範圍；端點契約（doc 25 §6.2）有依據。
- 服務真實營運痛點（退化換掉 + 相關性避險），且複用既有晉升 audit，不增治理重量。
- 研究層/排除項邊界清楚，防滑坡成大廠級 registry。

### 負面 / 成本
- PRD「❌ 多策略管理」宣告需修訂為「研究單策略 / 營運多策略艦隊 lite」，並補 D-018。
- 相關性矩陣需多隻策略 returns（M4 後 + 有候選池才有資料）。

### 影響範圍
- `02 PRD` §不做什麼（「❌ 多策略管理」改寫）+ 決策沿革 **D-018**。
- `web_design/pages/monitor_fleet.md`（移除「建議補 ADR」自註，改指 ADR-022）、`03 §5.3` 相關行（→ 指 ADR-022）。
- `25_fe_be_rest_contract.md` §6.2（`/monitor/fleet*` 已登錄，無需改）。
- `16_wbs_development_plan.md`（ADR 21→22；8.0/8.H 艦隊歸 M4）、`INDEX.md`（ADR 表 + 計數）。

### 重新評估觸發
- 若始終只有 ≤1 隻可部署策略 → 艦隊退化為單策略監控，相關性/換掉功能凍結（不浪費工時）。
- 若營運需求升級到跨人/多帳戶/真錢 staking → 需另立 ADR（本 lite 不涵蓋）。

## 6. 執行計畫

1. ✅ 本 ADR 記錄營運層多策略艦隊 lite 範圍裁定
2. ✅ PRD「❌ 多策略管理」改寫 + D-018；monitor_fleet / 03 §5.3 自註改指 ADR-022；INDEX/WBS 計數
3. ⏳ M4（live daemon 後）：實作 `/monitor/fleet*`、`/monitor/portfolio-summary`、`/monitor/correlation`、`POST /monitor/fleet/{id}/action`（doc 25 §6.2，gated 於 ≥1 可部署策略）

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-04 | Self | 初版 — 營運層擴張為多策略艦隊 lite（研究層維持單策略）；處置複用 ADR-018 晉升 audit；仍排除跨人 leaderboard/staking/完整 registry/多人簽核；gated 於 M4 + ≥1 可部署策略 |
