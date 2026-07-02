# 專案簡報與 PRD — backtest_platform

> **版本：** v4.0 | **更新：** 2026-07-02
> **進度狀態：** 詳見 [`16_wbs_development_plan.md`](./16_wbs_development_plan.md)（單一狀態真相源，見 [`15 §10`](./15_documentation_and_maintenance_guide.md) 規則）
>
> **v1.0** (2026-05-26)：M1 完成時的 PRD 基線版本（原 rqalpha + FinMind 路線）
> **v2.0** (2026-05-31)：M2+ 重大路線變更，以 Pivot Banner 標示過時段落
> **v3.0** (2026-06-01)：§1-§7 全面對齊 ADR-013（zipline-reloaded 主骨架），移除過時標示；完整規劃見 [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md)
> **v4.0** (2026-07-02)：**產品正名重寫**。承 [platform_full_audit_2026-07-02](./platform_full_audit_2026-07-02.md) §1/§3 缺陷 #15：v3.0 仍以已判死刑的四層共振為產品主軸（[ADR-023](./adrs/ADR-023-momentum-no-go-hold-gate.md) 判其負 edge 廢止），ADR-023~031 定義現今產品的決策全部缺席於決策沿革——依 v3.0 判準專案已「失敗」，敘事真空是最大產品風險。v4.0 把產品從「四層共振回測平台」正名為「**個人量化 edge 驗證工廠 + 晉升管線**」：策略是消耗品、審判庭是資產、連續 NO-GO 是產品正常運作的證據。Persona 正式化、部署假設明文、平台/策略 KPI 分列、❌ 清單收斂。**§1-§4 描述現況主軸；四層共振相關敘述一律標 legacy**。

---

架構與產品決策記錄於 [adrs/](./adrs/)（ADR-001~032），本 PRD 只描述現行產品。

---

## 1. 專案總覽

| 項目 | 內容 |
| :--- | :--- |
| **專案名稱** | backtest_platform — **個人量化 edge 驗證工廠 + 晉升管線**（single-user、standalone、台股專用）|
| **一句話定位** | 一座能誠實殺掉壞策略、讓極少數真 edge 走不可逆 backtest→paper→live 晉升管線的個人審判系統 |
| **狀態** | 詳見 [`16_wbs_development_plan.md`](./16_wbs_development_plan.md)（單一狀態真相源）|
| **目標里程碑** | M5 小倉位實盤 2027-Q2（暫定）；**下一個價值里程碑 = 修好審判庭（ADR-030）→ 用可信的閘重驗 inst_flow → after-close 排程器收 live OOS**|
| **核心團隊** | 單人開發（Zenobia000），單人雙帽（見 §2 Persona）|
| **策略契約** | 現行真相源 = [ADR-027](./adrs/ADR-027-strategy-contract-and-registry.md)/[ADR-028](./adrs/ADR-028-strategy-dispatch-contract.md) `StrategyRunner` 輸出契約 + registry；`strategy/v2.md`（四層共振 v2.1.0）為 **legacy**（已廢止）|

### 產品哲學（v4.0 正名）

- **策略是消耗品，審判庭是資產。** 四層共振（負 edge 廢止）、動能/多因子/long-short/資金流四結構撞 ~0.9 Sharpe survivorship-clean 牆——這些策略被殺掉不是失敗，是產品在正常工作。平台的核心資產是**審判庭本身**：PBO/DSR/WFA/survivorship-clean 強制 gate + 兩段閘 + OOS sealed vault + 試驗計數 deflate。
- **連續 NO-GO 是產品正常運作的最強證據。** 天真回測器會部署一個「看似 1.28、實際 OOS 0.63」的策略然後在真錢上虧；本平台量出「過擬合/偏誤稅」（WFA OOS 1.28→1.07→0.63，每剝一層 degree of freedom 就掉）並擋下它。
- **唯一護城河是「驗證信心」。** 零售市場沒有任何 SaaS 把 PBO/DSR/WFA/survivorship-clean 做成強制 gate（FinLab 只做 lookahead 偵測、TradingView/Composer 幾乎不做、QuantConnect 止於警告）；學術級防過擬合在開源生態近乎空白（MLFinLab 已閉源）。**前提：審判庭自己必須先可信**（ADR-030 修復三缺陷是 P0 中的 P0）。

---

## 2. 商業目標與 Persona

### 2.1 商業目標

| 項目 | 內容 |
| :--- | :--- |
| **背景與痛點** | 開發者本人手上有多個直覺策略假設，缺乏可重現、可稽核、防過擬合的量化審判機制。跳過驗證直接實盤 = 拿錢學習；停在直覺階段 = 永遠不知策略是真 edge 還是運氣 |
| **價值主張** | 提供「這策略真的有 Edge、還是過擬合/生存者偏誤/運氣」的科學判決，並把極少數過關者送上不可逆晉升管線 |
| **成功定義** | 不是「找到會賺錢的策略」（那是運氣函數），而是「**每個假設都得到誠實、可重現、成本可控的判決**」。平台成功與否，用平台 KPI 衡量（§3），不綁單一策略成敗 |

### 2.2 Persona：單人雙帽

唯一使用者是開發者本人，依時段戴不同帽子：

| 帽子 | 時段 | 主要工具 | 典型動作 |
| :--- | :--- | :--- | :--- |
| **策略研究者** | 研究時段 | **CLI-first**（GUI 檢視為輔）| 跑 DOE / truth-gate / sweep（`research doe/go-gates/truth-gate/paper-replay`），GUI 檢視 runs / 報告 / 比較 |
| **艦隊運維者** | 營運時段 | **GUI + Discord**（gated 於 ≥1 paper-ready 策略）| 看 Fleet 監控、收 Discord 退化告警、處置晉升/退場 |

### 2.3 部署假設（正式化，據此裁決長期懸置矛盾）

| 假設 | 內容 | 影響的決策 |
| :--- | :--- | :--- |
| **單機自託管** | 全系統跑在開發者個人 PC / 單機，無多實例、無叢集 | 路徑、備份、排程器（cron/systemd timer 級，非企業 scheduler）|
| **內網 localhost** | API 綁 `127.0.0.1`，前端走 vite proxy 同機存取，無公網暴露 | **auth 裁決（[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)：localhost-only 綁定即邊界，移除 Bearer 承諾）**、CORS |
| **無多人協作** | 無多角色 RBAC、無跨人 leaderboard、無簽核流程 | 認證從簡、無 model registry 族譜 |
| **無合規審批** | 個人資金、無外部合規要求 | 免 audit 簽核鏈（僅保留晉升 audit log 供自我追溯）|

> **秘密仍嚴管（不因 standalone 放鬆）**：`FINLAB_API_TOKEN`、`DISCORD_*`、`INFLUX_*` 僅後端持有，絕不出現在任何回應或前端 bundle（`rules/security.md`）。

---

## 3. 成功指標（兩層分列）

> **關鍵區分**：平台 KPI 衡量「審判機器好不好用、可不可信」；策略 KPI 衡量「某個具體策略該不該部署」。兩者解耦——策略連續 NO-GO 時平台 KPI 仍可為優。

### 3.1 平台 KPI（審判機器本身）

| 指標 | 定義 | 現況 / 目標 |
| :--- | :--- | :--- |
| **判決可重現性** | `inst_flow` 的「TRUTH GATE REAL」判決能否在標準化工作流（ADR-029）下重現 | ⚠️ 目前 REAL 判決來自已刪除的 scripts，現行程式路徑待 ADR-030 修好審判庭後重現（P0）|
| **新策略 lead time** | 假設 → 真偽判決所需成本 | ADR-027 已降至「複製 4 檔 + 1 行」；**應量測**實際 wall-clock |
| **每次驗證成本** | 單次 truth-gate 的算力/時間/資料 quota | 單機可負擔為底線 |

### 3.2 策略 KPI（ADR-025 兩段閘）

| 閘 | 判準 | 性質 |
| :--- | :--- | :--- |
| **真偽閘（hard-fail）** | PBO / DSR（deflated，含試驗計數）/ WFA OOS 廣度 / survivorship-clean | 過不了 = REJECTED，不進 paper |
| **配置閘（連續 sizing）** | Sharpe / 對艦隊相關性 / 容量 → 倉位大小 | 過真偽閘後決定 size，非 yes/no |
| **paper 前移** | 過真偽閘 + OOS>0 即可最小倉位 paper 收 live OOS | 不再排在絕對 CAGR 門檻後 |
| **實盤解鎖** | paper 期 live OOS + 配置閘 sign-off（不可逆晉升） | 唯一硬 gated 於此 |

> **絕對門檻（legacy 參考）**：ADR-016 的 CAGR>18% / Sharpe>1.0 曾為 binary 部署門檻，已由 [ADR-025](./adrs/ADR-025-two-stage-validation-gate-and-paper-promotion.md) 降為配置閘的 sizing 參考。

### 3.3 價值關鍵路徑（下一個里程碑）

修好審判庭（ADR-030）→ 用可信的閘重驗 inst_flow → after-close 排程器開始收 live OOS → 3 個月 paper → M5 小倉位實盤（2027-05）。

---

## 4. 使用者故事與允收標準

> **v4.0 說明**：Epic 1/2 原以「v2.md 四層計分 + XQ 對照」為核心，四層共振已 ADR-023 廢止，故標 **legacy**（保留為歷史脈絡，不再是活躍需求）。現今活躍主線是 Epic 3（研究工作流）與 Epic 4/5（審判與晉升）。

### Epic 1（legacy）：四層策略歷史回測

> ⚠️ **legacy**：四層共振負 edge 廢止（ADR-023），以下 US 保留為 M1 歷史紀錄。US-001 的 v2.md/XQ 對照已成歷史。

| ID | 描述 | 允收標準（歷史）| BDD |
| :--- | :--- | :--- | :--- |
| US-001 (legacy) | As a 策略研究者, I want to 用單一指令對某檔股票跑 v2.md 全套四層計分+訊號, so that 驗證程式邏輯與 XQ 一致 | CLI 跑通 + calendar CSV + 訊號與 XQ 差異 < 0.5% | `pipeline.feature` |
| US-002 | As a 策略研究者, I want to 拉某段期間資料並 cache 為 parquet, so that 重跑回測不需重 call API | `--output data/parquet`、三表獨立檔案、重跑優先讀 parquet（**仍活躍**：資料層通用能力）| `etl.feature` |

### Epic 2（legacy）：四層策略 Edge 驗證

> ⚠️ **legacy**：以下 US 的「v2.md 綠燈」判準已被 ADR-025 兩段閘取代；四層本身已廢止。統計驗證能力（PBO/DSR/WFA）本身仍活躍，見 Epic 4。

| ID | 描述 | 允收標準（歷史）| BDD |
| :--- | :--- | :--- | :--- |
| US-003 (legacy) | As a 策略研究者, I want to 跑 IS 期間 portfolio 回測, so that 判斷是否達標 v2.md 4.3.1 綠燈 | zipline-reloaded 整合 + quantstats 報表 + 綠/黃/紅燈 | `backtest_is.feature` |
| US-004 (legacy) | As a 策略研究者, I want to 跑 OOS 一次性驗證, so that 判斷是否過擬合 | OOS 不可回頭調參 + PBO/DSR + 失敗即淘汰 | `backtest_oos.feature` |

### Epic 3：策略研究者跑標準化研究工作流（ADR-029，現今主線）

| ID | 描述 (As a / I want to / So that) | 允收標準 | 對應端點 / CLI |
| :--- | :--- | :--- | :--- |
| US-007 | As a 策略研究者, I want to 對任一已註冊策略跑 DOE（design of experiments）, so that 我能系統化掃描參數空間而非手敲 | 1. `research doe --strategy <name>`（`--dry-run` / `--is-start/--is-end/--out-csv`）跑通<br>2. 各策略以 `strategies/<name>/research_config.py` 宣告 `DOE`，作者只填參數不寫工作流邏輯<br>3. name→package 由 registry 解析（不假設 name==目錄名）| `research.cli doe` |
| US-008 | As a 策略研究者, I want to 對策略跑真偽閘（truth-gate）, so that 我能得到 REAL/REJECTED 的可重現判決 | 1. `research truth-gate --strategy <name>` 走 `get_strategy(name).run(...)`，**絕不直接 import 策略的 backtest 函式**（AST 測試守門）<br>2. 輸出兩段閘結果（真偽閘 hard-fail + 配置閘 sizing）<br>3. 判決可在標準化工作流下重現（平台 KPI）| `research truth-gate` |
| US-009 | As a 策略研究者, I want to 透過 GUI/HTTP 觸發研究工作流並非同步取結果, so that 研究迴圈永不阻塞 | 1. `POST /research/workflows/{workflow}`（`{strategy, overrides}`）→ 202 `{job_id, status}`<br>2. `GET /research/workflows/{strategy}` 列該策略宣告的工作流<br>3. 未知 workflow → 404、未知 strategy → 400 | `/research/workflows/*` |
| US-010 | As a 策略研究者, I want to 對過真偽閘的候選跑 paper-replay, so that 我能在接真實 daemon 前先驗證晉升鏈 | 1. `research paper-replay --strategy <name>` 逐日跑 chain（ETL→signals→risk→orders→log）<br>2. 跨日 resilient、寫真實 telemetry | `research paper-replay` |

### Epic 4：策略審判與晉升（ADR-025，現今主線）

| ID | 描述 | 允收標準 | 對應端點 |
| :--- | :--- | :--- | :--- |
| US-011 | As a 策略研究者, I want to 對 run 跑 IS→WFA→OOS 不可逆 gate, so that OOS 不會被 post-hoc 污染 | 1. IS PASS 才解鎖 WFA、WFA PASS 才解鎖 OOS<br>2. OOS sealed vault：前置 gate 未過前對 CLI 不可讀、存取計次留痕<br>3. 狀態不可回退 | `/research/validate/*` |
| US-012 | As a 策略研究者, I want to 把過關策略經晉升狀態機 advance, so that 每階段強制 gate 且留 audit | 1. `advance` 未滿足 gate → 409（前後端雙防線）<br>2. immutable 晉升 audit log<br>3. paper 觀察期強制 | `/research/promote/*` |

### Epic 5：艦隊運維（ADR-022，gated 於 ≥1 paper-ready 策略）

| ID | 描述 | 允收標準 | 對應端點 |
| :--- | :--- | :--- | :--- |
| US-005 | As a 艦隊運維者, I want to 跑 paper trading 收 live OOS, so that 驗證實盤摩擦與回測假設一致 | 1. after-close 排程器（systemd timer/cron + Discord 成敗通知）<br>2. 每日訊號生成 + 對比實際成交<br>3. 觀察期倒數 + 退化偵測 | `/monitor/*` |
| US-006 | As a 艦隊運維者, I want to 看 Fleet 監控 + 收 Discord 告警, so that 退化時能及早處置 | 1. Fleet 板（live 淨值 / 健康 / 退化 / 相關性）<br>2. 退化告警經 Discord（ADR-010）<br>3. 熔斷規則自動執行（ADR-024 風控）| `/monitor/fleet` |

---

## 5. 範圍與限制

### 功能範圍

| 層 | M1 ✅ | M2 | M3 | M4 | M5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 資料層（FinLab 主 + FinMind fallback + Bundle） | ✅ | FinLab/FinMind bundle | survivorship-clean universe | 即時 feed | — |
| 策略層（契約 + registry） | ✅ | plug 為 Runner | 多策略 registry | — | — |
| 回測引擎 | — | zipline-reloaded (event) | vectorbt + WFA | — | — |
| 統計驗證（審判庭） | — | — | PBO/DSR/WFA/兩段閘 | — | — |
| 研究工作流（ADR-029） | — | — | doe/truth-gate/paper-replay | — | — |
| 紙上交易 | — | — | — | PaperBroker + 排程器 | — |
| 實盤下單 | — | — | — | — | ShioajiBroker |
| 監控告警 | — | — | React Monitor zone | Discord + Grafana | — |
| 前端 UI | — | — | **React 研究前端**（ADR-021/015）| Monitor 接真 | Panel D/E + 晉升 stepper |

### 非功能需求

| 分類 | 需求 | 目標值 |
| :--- | :--- | :--- |
| 性能 | 單檔 10 年回測 | < 60 秒 |
| 性能 | 100 檔 portfolio 回測 | < 30 分鐘 |
| 可靠性 | ETL idempotent | 重跑結果一致 |
| 可觀測性 | Trade audit trail | 100% trade 記錄含 scores/prices/position |
| 可重現性 | 訊號邏輯 | zipline & vectorbt 結果差異 < 0.1% |
| **可稽核性** | run 血統 | 每個 run 記 bundle hash / git_sha（審判可稽核）|
| **判決可信度** | 審判庭自身 | truth gate 三缺陷修復（ADR-030）為所有策略 KPI 前提 |

### 不做什麼（Won't — 與「做」同等正式）

> **standalone lite 原則**：明確不做的清單和要做的清單同等重要——它是「保持個人剛需、不過度工程」的護欄（呼應 ADR-018「補齊研究迴圈前不擴張監控」自訂鐵律）。

**即時/實盤（依 edge 進程往後疊）**
- ❌ 即時行情接收（M5 才考慮）
- ❌ 自動實盤下單（M5 才考慮）

**多策略：研究單策略、營運多策略（ADR-022 已界定邊界）**
- 🟡 研究層維持**單策略深究**；營運層擴張為**多策略艦隊 lite**（同時監控/操作數隻已晉升策略 + 退化換掉，gated 於 ≥1 完成 3 個月 paper 的策略，現 0）
- ❌ 仍不做：跨人 leaderboard / staking / 完整 champion-challenger model registry 族譜 / 多人簽核

**市場與商品**
- ❌ 多市場（台股為主，不做美股 / 港股）
- ❌ 期權 / 期貨（純股票策略）
- ❌ 多帳戶管理

**基礎建設（standalone 剛需之外）**
- ❌ 分散式掃描叢集、自建計算圖引擎、hosted notebook、K8s、企業級 scheduler
- ❌ 多人協作 / RBAC / 合規審批鏈（見 §2.3 部署假設）

### standalone 安全假設（明文）

- **邊界 = loopback bind**：API 綁 `127.0.0.1`，同機存取，無公網暴露（[ADR-031](./adrs/ADR-031-standalone-auth-decision.md)）。
- **不承諾未實作的 auth**：doc 25 原「M3.0 起全端點 static Bearer」承諾（後端零實作、前端硬編碼 dev-token）已由 ADR-031 裁決**移除**——localhost-only 綁定即邊界，Bearer 降為 M5 遠端存取時重議。「承諾了沒做」比「決定不做」更傷文件可信度。
- **秘密後端獨佔**：見 §2.3。
- **未來遠端存取（M5+）**：若需跨機存取，於 M5 重開 auth 決策（reverse-proxy guard 或 static Bearer dependency）。

### 假設與依賴

**假設**：
- 付費 FinLab 為主資料源（全史 2007→今、原生 survivorship-clean 2753 檔含 369 下市股）、FinMind 免費版 fallback（ADR-006 realized）
- 個人 PC 算力足夠跑 100 檔 × 10 年回測
- 單機自託管、內網 localhost、無多人協作（§2.3）

**依賴**：
- FinLab API（主資料源，付費）+ FinMind API（fallback）— ADR-006
- TimescaleDB（telemetry / bundle cache）
- zipline-reloaded（回測引擎主骨架）— ADR-013 / ADR-014
- vectorbt 1.0+（回測引擎副，參數網格）— ADR-007 / ADR-014
- FastAPI + React（後端 API + 前端）— ADR-021 / ADR-015
- Discord（告警主通道）+ Grafana（系統面板輔）— ADR-009 / ADR-010
- uv（套件管理）— ADR-012
- Shioaji（永豐金證券下單 API，M5）

---

## 6. 待辦問題與決策

| ID | 描述 | 狀態 | 備註 |
| :--- | :--- | :--- | :--- |
| Q-001 | 下市股資料源如何取得 | 已關閉 | FinLab 全史原生含 369 下市股（ADR-006 realized），survivorship-clean 已解 |
| Q-002 | 券商分點補爬策略 | 已關閉 | FinMind 三大法人量化 chip 層 + FinLab 進階分點（已於 R9 掃描使用）|
| Q-003 | 是否升級 FinMind sponsor | 已關閉 | 改採付費 FinLab 為主源（ADR-006），FinMind 降 fallback |
| Q-004 | rqalpha 自訂 mod 是否值得寫 | 已關閉 | 廢止 rqalpha，主骨架改 zipline-reloaded（ADR-013）|
| Q-005 | 審判庭三缺陷（DSR 單位 / OOS holdout / survivorship 寫死）修復 | **進行中** | ADR-030（truth gate 修正，PR #137，另分支）— 平台 KPI「判決可重現性」前提 |
| Q-006 | standalone auth 三方矛盾裁決 | **已決定** | ADR-031：localhost-only 綁定 + 移除 Bearer 承諾 |
| D-001 | ~~採用 v2.md 為單一策略契約~~ | **已取代** | 四層 v2.md 廢止（ADR-023）；策略契約改 `StrategyRunner`（ADR-027/028）|
| D-002 | 採用 MVP 工作流模式 | 已決定 | 見 01_workflow_manual.md |
| D-003 | 使用 Public GitHub repo（Zenobia000） | 已決定 | 2026-05-26 上線 |
| D-005 | 主骨架採 zipline-reloaded | 已決定 | ADR-013（supersedes ADR-005 / ADR-001）|
| D-006 | 主資料源採付費 FinLab + FinMind fallback | 已決定 | ADR-006 realized |
| D-007 | 雙引擎（Zipline event + vectorbt vector） | 已決定 | ADR-007（vector 半邊隨 ADR-014 恢復）|
| D-008 | 系統定位升級為三模式（backtest/paper/live） | 已決定 | ADR-008 |
| D-009 | 監控/告警 React + Discord 主線 | 已決定 | ADR-009 / ADR-010 / ADR-015 / ADR-021（Streamlit → React）|
| D-010 | 套件管理採 uv | 已決定 | ADR-012 |
| D-011 | 前後端 REST 契約合一（doc 25 + OpenAPI） | 已決定 | ADR-021 |
| D-016 | 監控優先 → 研究迴圈優先 | 已決定 | ADR-018 |
| D-018 | 多策略艦隊營運（lite） | 已決定 | ADR-022（gated 於 ≥1 paper-ready 策略）|
| D-019 | 四層共振廢止 + 動能 NO-GO（守 ADR-016 不放寬） | 已決定 | ADR-023 |
| D-020 | 驗證閘兩段化 + paper 前移 | 已決定 | ADR-025（amends ADR-016 binary）|
| D-021 | 策略契約 + registry + dispatch + preset 移除 | 已決定 | ADR-027 / ADR-028 |
| D-022 | 研究工作流標準化 | 已決定 | ADR-029 |
| D-023 | standalone auth = localhost-only 綁定 | 已決定 | ADR-031 |

---

## 7. 成功與失敗的判斷

### 平台層（審判機器）

- **成功**：每個策略假設都得到誠實、可重現、成本可控的判決（見 §3.1 平台 KPI）。
- **成功**：審判庭量出並擋下「看似高、實際過擬合」的策略（連續 NO-GO = 平台正常運作證據）。
- **失敗（必須處理）**：審判庭自身不可信（DSR 單位錯誤 / OOS holdout 未評估 / survivorship 寫死）→ ADR-030 P0 修復。
- **失敗（必須處理）**：判決無法重現（來自已刪除 scripts）→ 標準化工作流（ADR-029）重跑。

### 策略層（單一策略）

- **成功**：策略過兩段閘真偽閘 + OOS>0 → 進入 paper 收 live OOS。
- **成功**：paper 期 live OOS + 配置閘 sign-off → 進入小倉位實盤。
- **失敗（接受，且是常態）**：策略死於真偽閘（PBO 過高 / OOS 崩 / survivorship FAIL）→ 砍策略、換 edge family。四層/動能/多因子/long-short/資金流 binary 皆已如此死過——**這是產品在工作，不是專案失敗**。

### 紀律（任何階段）

- 任何階段違反預註冊（hypothesis 預登記）紀律 → 強制重跑該階段。
- ETL 資料遺失 → 重灌資料源。
- 守 gate 門檻不因單一策略瓶頸放寬（ADR-023 裁定：紀律 > 救策略）。
