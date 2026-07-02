# backtest_platform — 開發文檔總覽

本目錄是 backtest_platform（**個人量化 edge 驗證工廠 + 晉升管線**）的工程文檔。狀態真相源為 [16 WBS](./16_wbs_development_plan.md)、架構決策見 [adrs/](./adrs/)、REST 契約見 [25](./25_fe_be_rest_contract.md)。更新歷史見 git log。

---

## 文檔清單

### 階段 0–1：總覽與規劃

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 00 | [system_architecture_overview.md](./00_system_architecture_overview.md) | 系統架構總覽 |
| 01 | [workflow_manual.md](./01_workflow_manual.md) | 開發流程手冊（研究迴圈 + 工程流程） |
| 02 | [project_brief_and_prd.md](./02_project_brief_and_prd.md) | 專案簡報與 PRD v4.0 |
| 03 | [behavior_driven_development_guide.md](./03_behavior_driven_development_guide.md) | BDD scenarios（策略無關工作流） |

### 階段 2–3：架構與詳細設計

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 04 | [adrs/](./adrs/) | 架構決策記錄（ADR-001~035） |
| 05 | [architecture_and_design_document.md](./05_architecture_and_design_document.md) | 架構設計（C4 嚴格版 / DDD） |
| 06 | [api_design_specification.md](./06_api_design_specification.md) | CLI + Python API 規範 |
| 07 | [module_specification_and_tests.md](./07_module_specification_and_tests.md) | 模組規格（DbC） |
| 08 | [project_structure_guide.md](./08_project_structure_guide.md) | 專案結構 |
| 09 | [file_dependencies_template.md](./09_file_dependencies_template.md) | 依賴關係 |
| 10 | [class_relationships_template.md](./10_class_relationships_template.md) | 類別關係 |

### 階段 4–5：開發、品質、安全、部署

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 11 | [code_review_and_refactoring_guide.md](./11_code_review_and_refactoring_guide.md) | 程式碼審查與重構 |
| 12 | [frontend_architecture_specification.md](./12_frontend_architecture_specification.md) | 前端架構（React/TS） |
| 13 | [security_and_readiness_checklists.md](./13_security_and_readiness_checklists.md) | 安全與生產準備 |
| 14 | [deployment_and_operations_guide.md](./14_deployment_and_operations_guide.md) | 部署與運維（另見 [runbooks/](./runbooks/)） |

### 階段 6：維護與計畫

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 15 | [documentation_and_maintenance_guide.md](./15_documentation_and_maintenance_guide.md) | 文檔維護（含狀態真相源規則） |
| 16 | [wbs_development_plan.md](./16_wbs_development_plan.md) | **WBS 開發計劃（狀態真相源）** |

### 階段 7：規格擴充

| # | 檔名 | 用途 |
| :---: | :--- | :--- |
| 17 | [m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) | M2–M5 總體規劃 |
| 18 | [reference_architecture_and_metrics.md](./18_reference_architecture_and_metrics.md) | reference 架構 + 指標 taxonomy |
| 20 | [dashboard_specification.md](./20_dashboard_specification.md) | 儀表板 + Discord 告警 spec |
| 21 | [data_contract.md](./21_data_contract.md) | 資料契約 + TimescaleDB DDL |
| 22 | [test_strategy.md](./22_test_strategy.md) | 測試金字塔 + 對拍矩陣 |
| 23 | [deployment_topology.md](./23_deployment_topology.md) | 部署拓撲 |
| 24 | [risk_management_spec.md](./24_risk_management_spec.md) | 風控規則 + 熔斷狀態機 |
| 25 | [fe_be_rest_contract.md](./25_fe_be_rest_contract.md) | **前後端 REST 契約唯一真相源** |

> 19（sprint_0_design）已撤回，內容併入 01。

---

## 架構決策（ADR）

[adrs/](./adrs/) — ADR-001~035。近期主軸：023 動能 NO-GO / 024 資金流 FAIL / 025 驗證閘兩段化 / 027 策略契約 + registry / 028 dispatch + preset 移除 / 029 研究工作流標準化 / 030 truth gate 判決修正 / 031 standalone auth / 032 survivorship universe 工作流 / 033 Paper-Watch 零資本觀察艙 / 034 逐筆覆盤 K 線改 lightweight-charts / 035 DataFeed 讀取層 seam（EOD 現行、realtime XQ/Q 延後）。

---

## 審查報告

- [platform_full_audit_2026-07-02.md](./platform_full_audit_2026-07-02.md) — 全平台多視角審查（缺陷 Top 25 + 三階段路線圖 + 平行工作包）
- [competitive_analysis_2026-07-02.md](./competitive_analysis_2026-07-02.md) — 競品分析 + 五視角附錄

---

## 研究證據檔（一次性判決紀錄，已 freeze）

- [inst_flow_truth_gate_verdicts.md](./inst_flow_truth_gate_verdicts.md) — inst_flow 三輪 truth-gate 判決總表
- [momentum_go_nogo_result_2026-06-05.md](./momentum_go_nogo_result_2026-06-05.md)（ADR-023 依據）
- [factor_baseline_diagnostic_result_2026-06-04.md](./factor_baseline_diagnostic_result_2026-06-04.md)

---

## UI / 設計系統

[web_design/](./web_design/) — 設計系統參考 + 大廠量化平台 UI/UX 對標（[03_uiux_benchmark_and_reinforcement_plan.md](./web_design/03_uiux_benchmark_and_reinforcement_plan.md)，ADR-018 證據包）。

---

## 角色查找

| 角色 | 常用文檔 |
| :--- | :--- |
| 策略研究者 | 01 → 02 → 06（CLI）→ 03 |
| 後端 DEV | 05、07、08、09、10、11 |
| 前端 DEV | 12、25 |
| ARCH | 04、05、09、10 |
| OPS | 13、14、23、24 |
| 新人 | 01 → 02 → 08 → 05 |
