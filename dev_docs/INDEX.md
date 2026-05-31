# backtest_platform — 開發文檔總覽

> 依 `VibeCoding_Workflow_Templates` v3.0 模板產出，對應實際 `backtest_platform/` 程式碼狀態。
> **產出日期**：2026-05-26 | **對應版本**：backtest_platform 0.1.0 (M1)
> **2026-05-31 更新**：新增階段 7（M2+ 規劃文檔），含 5 份新 ADR + 8 份新規格文檔（17-24）

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
| 04 | [adrs/](./adrs/) | 架構決策記錄（**9 份 ADR**：原 4 份 + 2026-05-31 新增 005~009） |
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

（12 / 17 前端模板 — 不適用，本專案後端為主，前端 Phase 2 才啟動）

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

> 配合 M1 完成、進入 M2 之際的重大架構決策變更（rqalpha → TQuant-Lab、FinMind → FinLab、新增三模式+雙儀表板）
> **2026-05-31 整併**：原 19 號 sprint_0_design 已合併入 01 §5.A 並撤回；21/22/23/24 為既有 05/03/14/13 的**擴充版** source of truth

| # | 檔名 | 用途 | 與既有檔關係 |
| :---: | :--- | :--- | :--- |
| 17 | [m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) | **M2-M5 總體規劃**（路線、17 週時程、Verification） | 獨立（02/16 已加 v2.0 banner 指向）|
| 18 | [reference_architecture_and_metrics.md](./18_reference_architecture_and_metrics.md) | 業界 7 層 reference + 30+ 指標 taxonomy | 獨立（M3 指標實作時 single source of truth）|
| ~~19~~ | ~~sprint_0_design.md~~ | ~~Sprint 0 spike 細部規格~~ | **已合併入 [01 §5.A](./01_workflow_manual.md)，本檔撤回** |
| 20 | [dashboard_specification.md](./20_dashboard_specification.md) | 雙儀表板 + Telegram/Discord 告警 spec | 獨立（UI 詳設）|
| 21 | [data_contract.md](./21_data_contract.md) | FinLab/FinMind/Shioaji schema + TimescaleDB 13 表 DDL | **擴充** [05 §4](./05_architecture_and_design_document.md)（05 為 M1 baseline，21 為 M2+ 完整版）|
| 22 | [test_strategy.md](./22_test_strategy.md) | 測試金字塔 + 對拍矩陣 + CI/CD YAML 草案 | **擴充** [03](./03_behavior_driven_development_guide.md)（03 §6 加金字塔摘要 + 指向 22）|
| 23 | [deployment_topology.md](./23_deployment_topology.md) | Dev/Staging/Production 三環境拓撲 + docker-compose | **擴充** [14 §1](./14_deployment_and_operations_guide.md)（14 為 SOP，23 為拓撲設計）|
| 24 | [risk_management_spec.md](./24_risk_management_spec.md) | 12 條 ex-ante 規則 + 3 級熔斷狀態機 + SOP | **擴充** [13 §J](./13_security_and_readiness_checklists.md)（13 §J 為摘要 + 指向 24）|
| — | [research_open_source_backtest_platforms.md](./research_open_source_backtest_platforms.md) | 開源回測平台選型調研報告（決策依據，已 freeze） | 獨立 |

#### 階段 7 新增 ADR

| ADR | 主題 | Supersedes |
| :---: | :--- | :--- |
| [ADR-005](./adrs/ADR-005-mainframe-tquant-lab-zipline-fork.md) | 主骨架選定 TQuant-Lab（Zipline 台股 fork） | **ADR-001** |
| [ADR-006](./adrs/ADR-006-data-source-finlab-paid.md) | 資料源改 FinLab 付費版 + FinMind fallback | — |
| [ADR-007](./adrs/ADR-007-dual-engine-zipline-vectorbt.md) | 雙引擎：Zipline event-driven + vectorbt vectorized | — |
| [ADR-008](./adrs/ADR-008-tri-mode-shared-strategy-code.md) | 三模式共用 strategy code (backtest/paper/live) | — |
| [ADR-009](./adrs/ADR-009-dual-dashboard-telegram-monitoring.md) | 雙儀表板（Streamlit+Grafana）+ Telegram 告警 | — |

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
