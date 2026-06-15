# backtest_platform — 開發文檔總覽

> 依 `VibeCoding_Workflow_Templates` v3.0 模板產出，對應實際 `backtest_platform/` 程式碼狀態。
> **產出日期**：2026-05-26 | **對應版本**：backtest_platform 0.1.0 (M1)
> **2026-06-01 更新**：階段 7 完整定版（11 份 ADR + 7 份規格文檔 17/18/20-24，原 19 已併入 01 §5.A）；16 WBS 升 v2.0 為單一狀態真相源（見 15 §10 規則）
>
> **2026-06-02 更新**：universe ingest（`ingest` CLI）完成、R14 關閉；**M2 IS gate FAIL → 回 M0 重設進場（ADR-017）**；ADR 數量 16→17；16 WBS 升 v2.5
>
> **2026-06-02 更新（二）**：大廠 UI/UX deep-research 對標完成 → **監控優先 → 研究迴圈優先 pivot（ADR-018）**：Run 物件化 + 研究工作區 IA + IS→WFA→OOS gate 工作流；新增 `web_design/03_uiux_benchmark_and_reinforcement_plan.md`（10 平台對標 + 10 維度差距 + 7 流程圖 + roadmap）；ADR 數量 17→18；16 WBS 升 v2.6（§8.G 研究迴圈 UX）
> **2026-06-03 更新**：研究迴圈 CLI 補 `validate`+`promote-check`（8.G.5 封頂）；large-cap v3 IS FAIL → **escalate 候選 D（ADR-020 提案中）**：換 point-in-time 中小型動能 universe（rank 51-300、反 survivorship），機制凍結、資料 spike（FinLab 進階券商分點）為 go/no-go gating；新增設計 spec `specs/2026-06-03-candidate-d-smallcap-universe-design.md`；ADR 數量 19→20
> **2026-06-04 更新**：前後端契約優先盤點（FE 14 頁需求 ↔ FastAPI 11 條供給 ↔ 既有契約）→ **REST 契約合一（ADR-021）**：三處分裂（06 §9 / 21 §8 / per-page）併入新建 **25_fe_be_rest_contract.md**（71→83 端點 registry + 單一 envelope/錯誤碼/分頁/裸 root/Bearer/realtime + OpenAPI→TS）；06 §9 / 21 §8 / 20 / 12 §7 加降級 banner；ADR 數量 20→21
> **2026-06-04 更新（二）**：Trade Review 去 four_layer_resonance 策略耦合（泛化為 reason_json 動態 N 因子歸因）；**多策略艦隊營運 lite（ADR-022）**：營運層擴張為同時操作數隻已晉升策略 + 退化換掉（研究層仍單策略），改寫 PRD「❌ 多策略管理」+ D-018；ADR 數量 21→22
> **2026-06-09 更新**：R9 edge 掃描收斂 — 動能 NO-GO（ADR-023，守 ADR-016 + 四層廢止）、資金流 survivorship-clean NO-GO（ADR-024）；4 結構同 ~0.9 Sharpe 牆；ADR 數量 22→24
> **2026-06-14 更新**：驗證機制設計修正 — **驗證閘從 binary 絕對通關改兩段式（ADR-025）**：真偽閘（PBO/DSR/WFA/survivorship-clean hard-fail）+ 配置閘（Sharpe/相關性/容量→倉位，連續，絕對 CAGR 降參考）+ paper 前移；修正部署閘≠研究迭代閘混用、絕對 CAGR 對市場中性錯配、gate 排序死鎖；不翻案 ADR-023/024（死於真偽閘）；16 WBS 升 v3.4；ADR 數量 24→25

---

## 文檔清單

### 階段 0：總覽

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 01 | [workflow_manual.md](./01_workflow_manual.md) | 開發流程選擇（MVP 模式） |

### 階段 1：規劃

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 02 | [project_brief_and_prd.md](./02_project_brief_and_prd.md) | 專案簡報與 PRD |
| 03 | [behavior_driven_development_guide.md](./03_behavior_driven_development_guide.md) | BDD scenarios |

### 階段 2：架構與設計

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 04 | [adrs/](./adrs/) | 架構決策記錄（**22 份 ADR**：…017/018/019 + 2026-06-03 新增 020（候選 D）+ 2026-06-04 新增 021（REST 契約合一）/022（多策略艦隊 lite）） |
| 05 | [architecture_and_design_document.md](./05_architecture_and_design_document.md) | 架構設計（C4 嚴格版 / DDD） |
| 06 | [api_design_specification.md](./06_api_design_specification.md) | CLI + Python API 規範 |

### 階段 3：詳細設計

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 07 | [module_specification_and_tests.md](./07_module_specification_and_tests.md) | 模組規格（DbC） |
| 08 | [project_structure_guide.md](./08_project_structure_guide.md) | 專案結構 |
| 09 | [file_dependencies_template.md](./09_file_dependencies_template.md) | 依賴關係 |
| 10 | [class_relationships_template.md](./10_class_relationships_template.md) | 類別關係 |

### 階段 4：開發與品質

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 11 | [code_review_and_refactoring_guide.md](./11_code_review_and_refactoring_guide.md) | 程式碼審查指南 |
| 12 | [frontend_architecture_specification.md](./12_frontend_architecture_specification.md) | 前端架構（React/TS stack、分層、效能/a11y 量化）；IA 真相源在 `web_design/`，契約在 25（2026-06-04 對齊現實啟用）|

### 階段 5：安全與部署

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 13 | [security_and_readiness_checklists.md](./13_security_and_readiness_checklists.md) | 安全與生產準備 |
| 14 | [deployment_and_operations_guide.md](./14_deployment_and_operations_guide.md) | 部署與運維 |

### 階段 6：維護與管理

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 15 | [documentation_and_maintenance_guide.md](./15_documentation_and_maintenance_guide.md) | 文檔維護 |
| 16 | [wbs_development_plan.md](./16_wbs_development_plan.md) | WBS 開發計劃 |

### 階段 7：M2+ 策略選型與規劃（2026-05-31 新增）

> 配合 M1 完成、進入 M2 之際的重大架構決策變更（rqalpha → TQuant-Lab → zipline-reloaded（ADR-013）、FinMind → FinLab、新增三模式+雙儀表板）
> **2026-05-31 整併**：原 19 號 sprint_0_design 已合併入 01 §5.A 並撤回；21/22/23/24 為既有 05/03/14/13 的**擴充版** source of truth

| # | 檔名 | 用途 | 與既有檔關係 |
| :---: | :--- | :--- | :--- |
| 17 | [m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) | **M2-M5 總體規劃**（路線、17 週時程、Verification） | 獨立（02/16 已加 v2.0 banner 指向）|
| 18 | [reference_architecture_and_metrics.md](./18_reference_architecture_and_metrics.md) | 業界 7 層 reference + 30+ 指標 taxonomy | 獨立（M3 指標實作時 single source of truth）|
| ~~19~~ | ~~sprint_0_design.md~~ | ~~Sprint 0 spike 細部規格~~ | **已合併入 [01 §5.A](./01_workflow_manual.md)，本檔撤回** |
| 20 | [dashboard_specification.md](./20_dashboard_specification.md) | 雙儀表板 + Discord 告警 spec（原 Telegram 已 superseded by ADR-010） | 獨立（UI 詳設）|
| 21 | [data_contract.md](./21_data_contract.md) | FinLab/FinMind/Shioaji schema + TimescaleDB 13 表 DDL | **擴充** [05 §4](./05_architecture_and_design_document.md)（05 為 M1 baseline，21 為 M2+ 完整版）|
| 22 | [test_strategy.md](./22_test_strategy.md) | 測試金字塔 + 對拍矩陣 + CI/CD YAML 草案 | **擴充** [03](./03_behavior_driven_development_guide.md)（03 §6 加金字塔摘要 + 指向 22）|
| 23 | [deployment_topology.md](./23_deployment_topology.md) | Dev/Staging/Production 三環境拓撲 + docker-compose | **擴充** [14 §1](./14_deployment_and_operations_guide.md)（14 為 SOP，23 為拓撲設計）|
| 24 | [risk_management_spec.md](./24_risk_management_spec.md) | 12 條 ex-ante 規則 + 3 級熔斷狀態機 + SOP | **擴充** [13 §J](./13_security_and_readiness_checklists.md)（13 §J 為摘要 + 指向 24）|
| 25 | [fe_be_rest_contract.md](./25_fe_be_rest_contract.md) | **前後端 REST 契約唯一真相源**（71 端點 registry + 單一 envelope/錯誤碼/分頁/auth/realtime + OpenAPI→TS bridge，ADR-021）| **合一** 06 §9 + 21 §8 + per-page `[DATA & API]`（三者降為 feeder by reference）|
| — | [research_open_source_backtest_platforms.md](./research_open_source_backtest_platforms.md) | 開源回測平台選型調研報告（決策依據，已 freeze） | 獨立 |

#### 階段 7 新增 ADR

| ADR | 主題 | Supersedes |
| :---: | :--- | :--- |
| [ADR-005](./adrs/ADR-005-mainframe-tquant-lab-zipline-fork.md) | ~~主骨架選定 TQuant-Lab（Zipline 台股 fork）~~ — 已 superseded by ADR-013 | **ADR-001** |
| [ADR-006](./adrs/ADR-006-data-source-finlab-paid.md) | 資料源改 FinLab 付費版 + FinMind fallback | — |
| [ADR-007](./adrs/ADR-007-dual-engine-zipline-vectorbt.md) | 雙引擎：Zipline event-driven + vectorbt vectorized（vectorbt 半邊已由 ADR-014 恢復） | — |
| [ADR-008](./adrs/ADR-008-tri-mode-shared-strategy-code.md) | 三模式共用 strategy code (backtest/paper/live) | — |
| [ADR-009](./adrs/ADR-009-dual-dashboard-telegram-monitoring.md) | 雙儀表板（Streamlit+Grafana）+ 告警（Telegram 路線，已部分 superseded） | 被 ADR-010 部分取代 |
| [ADR-010](./adrs/ADR-010-discord-alerter-supersedes-telegram.md) | Discord 取代 Telegram 為告警通道 | 部分 supersede **ADR-009** |
| [ADR-011](./adrs/ADR-011-m2-directory-structure-and-module-boundaries.md) | M2 目錄結構與模組邊界（追溯 commit `ae869f5`） | — |
| [ADR-012](./adrs/ADR-012-adopt-uv-package-manager.md) | 採用 uv 為 Python 套件管理器（取代 poetry） | poetry 用法 |
| [ADR-013](./adrs/ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md) | 主骨架切換 zipline-tej → zipline-reloaded（0 商業綁定） | **ADR-005**（§ 4 後果部分由 ADR-014 修正）|
| [ADR-014](./adrs/ADR-014-zipline-reloaded-3-1-1-upgrade-reverses-adr-013-constraints.md) | zipline-reloaded 3.0.4 → 3.1.1 升級，解鎖 pandas 2 / numpy 2 / vectorbt | amends **ADR-013** § 4 |
| [ADR-015](./adrs/ADR-015-dashboard-design-system-and-react-upgrade.md) | 儀表板設計系統 + React 升級（5 面板規格 + Assembly + REST API 契約） | — |
| [ADR-016](./adrs/ADR-016-m2-acceptance-kpi-freeze.md) | M2 acceptance KPI 凍結（CAGR>18% / Sharpe>1.0 / 滑點 0.3% 穩健性）— 彙整 01/02/v2.md 既有數字 | — |
| [ADR-017](./adrs/ADR-017-m2-is-gate-failed-return-to-m0-entry-redesign.md) | M2 IS gate FAIL（雙窗口無 edge、進場過嚴）→ 觸發退場條件，回 M0 重設進場假設；附帶修 `_format_perf_summary` ffill metric bug | 記錄 ADR-016 gate 的執行結果 |
| [ADR-018](./adrs/ADR-018-monitoring-to-research-loop-pivot.md) | 監控優先 → 研究迴圈優先：Run 物件化（runs 主表）+ 研究工作區 IA（A–E 降 live 子視圖）+ IS→WFA→OOS gate 工作流 + OOS sealed vault + 試驗次數 deflate + 晉升狀態機；後端契約先行 | **重定位** ADR-009/ADR-015 產物（不取代分層/設計系統）；UX 化 ADR-017 |
| [ADR-019](./adrs/ADR-019-v3-entry-redesign-relaxation-and-minimal-exit-pairing.md) | v3 進場重設：參數化分級放寬（必含層+可選，非純 N-of-4 — L2⊂L3）+ flameout 最小 exit 搭配；6 參數 v2 預設重現 baseline；反過擬合硬約束（v0.1 不 sweep、進場數非 edge） | ADR-017 的 M0 進場 hypothesis 定稿；v0.1 策略側 |
| [ADR-020](./adrs/ADR-020-candidate-d-smallcap-universe-escalation.md) | **候選 D（提案中）**：large-cap v3 IS FAIL → escalate 換 point-in-time 中小型動能 universe（rank 51-300、季 rebalance、反 survivorship）；機制凍結、成本上調；資料 spike（FinLab 進階券商分點 ~250 檔）為 go/no-go gating | ADR-017 §5 退場路徑落地；ADR-019 機制不動 |
| [ADR-021](./adrs/ADR-021-unify-rest-contract-into-single-doc-and-openapi.md) | **前後端 REST 契約合一**：三處分裂（06 §9 / 21 §8 / per-page）→ 單一契約 doc 25 + OpenAPI 機器真相；envelope error 字串→物件、offset 分頁、裸 root、single-user Bearer、polling+單一 WS、Monitor stub | **supersede** ADR-015 §4/§5 + ADR-018 契約落點指派 |
| [ADR-022](./adrs/ADR-022-multi-strategy-fleet-operations.md) | **多策略艦隊營運（lite）**：營運層擴張為同時監控/操作數隻已晉升策略 + 退化換掉（研究層仍單策略）；處置複用 ADR-018 晉升 audit；仍排除跨人 leaderboard/staking/完整 registry/多人簽核；gated 於 M4 + ≥1 可部署策略 | **部分放寬** 03 §5.3「刻意不做 champion/challenger」+ PRD「❌ 多策略管理」（D-018）|
| [ADR-023](./adrs/ADR-023-momentum-no-go-hold-gate.md) | **動能 NO-GO**：大 universe + survivorship-clean WFA OOS 0.63-0.86、final CAGR 7.1% 仍未過 ADR-016；守門檻不放寬 → 動能廢止、四層廢止、艦隊轉掃描下一候選 | 記錄 ADR-016 gate 對動能的執行結果 |
| [ADR-024](./adrs/ADR-024-institutional-flow-candidate-strategy.md) | **三大法人資金流候選 → 🔴 survivorship-clean FAIL**：survivor-only 40 檔條件式 GO 係生存者膨脹假陽性；含下市股 116 檔複驗 CAGR 13.1%/Sharpe 0.90/PBO 42.9% → NO-GO，條件式 GO 撤回 | 記錄 ADR-016 gate 對資金流的執行結果 |
| [ADR-025](./adrs/ADR-025-two-stage-validation-gate-and-paper-promotion.md) | **驗證閘兩段化 + paper 前移**：修正 ADR-016 binary 絕對通關三缺陷（部署閘≠研究迭代閘混用、絕對 CAGR 對市場中性錯配、gate 排序死鎖）→ 真偽閘（PBO/DSR/WFA/survivorship-clean hard-fail）+ 配置閘（Sharpe/相關性/容量→倉位，連續，絕對 CAGR 降參考）+ paper 前移；不翻案 ADR-023/024（死於真偽閘）| **amends** ADR-016（binary→兩段閘）|

---

### 階段 8：UI / 設計系統參考（2026-06-01 新增）

> 與核心 dev_docs 並行的設計系統工作區。M3 Streamlit 面板 + M5 React 前端的視覺基礎；目前內容以「AI 網頁開發流水線」為框架，含 design-system specs + 既有 UI clone 分析（x.ai、Grok）。

| 路徑 | 用途 | 對應 |
| :--- | :--- | :--- |
| [web_design/README.md](./web_design/README.md) | 模組化 AI 網頁開發流水線總覽 | 獨立 |
| [web_design/design-system-specs/cloning/clones/xai/](./web_design/design-system-specs/cloning/clones/xai/) | x.ai UI 5 層設計分析（L0-L4；原始擷取產物 raw/extracted 已剪除） | 設計參考 |
| [web_design/design-system-specs/cloning/clones/grok/](./web_design/design-system-specs/cloning/clones/grok/) | Grok 完整 UI 5 層分析 | 設計參考 |
| web_design/{global,modules,pages,assembly,guides,references}/ | base design system 框架（**WIP，多數尚未 commit**） | M3 dashboard 啟用時對齊 |
| [web_design/03_uiux_benchmark_and_reinforcement_plan.md](./web_design/03_uiux_benchmark_and_reinforcement_plan.md) | **大廠量化/回測平台 UI/UX deep-research 對標**（10 平台）+ 10 維度差距分析 + 7 張 Mermaid 使用者旅程/流程圖 + 補強 roadmap（ADR-018 證據包） | ADR-018 / ADR-015 / 20 |

---

## 與上游文件的關係

```
strategy/v2.md (策略規格 v2.1.0)
    ↓ 實作對應
backtest_platform/ (程式碼 M1)
    ↓ 文檔對應
dev_docs/ (本目錄)
    ↓ 後續驗證
strategy/research/ (DOE 模板與 IC 測試計畫)
```

`v2.md` 是策略契約，`backtest_platform/` 是其 Python 實作，`dev_docs/` 是工程文檔，`strategy/research/` 是驗證計畫。

---

## 角色查找

| 角色 | 常用文檔 |
| :--- | :--- |
| 策略設計者 | 02、05、07 |
| 後端 DEV | 05、07、08、09、10、11 |
| ARCH | 04、05、09、10 |
| OPS | 13、14 |
| 新人 | 01 → 02 → 08 → 05 |
