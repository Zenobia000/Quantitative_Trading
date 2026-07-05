# Golden 文件集索引 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline
>
> 來源模板: `VibeCoding_Workflow_Templates` v3.2
>
> 上游架構依據: `dev_docs/機構級量化交易平台系統架構設計文件_SAD.docx`

## 1. 核心定位

本產品是**個人級 EOD 量化交易平台**，採用 golden SAD 七層權威架構，但 right-size 到單一操作者、日線資料、隔日/低頻執行。

七層皆屬產品內子系統：

1. Data Platform
2. Research & Validation Platform
3. Strategy Governance & Release
4. Strategy Runtime / Execution Platform
5. Risk / Portfolio / Compliance
6. Monitoring & Operations
7. Platform Foundation

FinLab / backtest_platform 僅屬第 2 層 Research & Validation：負責 Alpha research、因子選股、回測、WFA、Target Portfolio，不直接下單。

## 2. 文件地圖

| # | 文件 | 目的 |
| :--- | :--- | :--- |
| 01 | `01_workflow_manual.md` | 開發流程、Gate、RACI、文件即契約。 |
| 02 | `02_project_brief_and_prd.md` | 產品目標、使用者故事、範圍、KPI。 |
| 03 | `03_behavior_driven_development_guide.md` | BDD 情境與可執行規格。 |
| 04 | `04_architecture_decision_records.md` | 主要 ADR 與反覆爭議的結論。 |
| 05 | `05_architecture_and_design_document.md` | C4、DDD、QAS、資料、部署、風險、Fitness Functions。 |
| 06 | `06_api_design_specification.md` | REST / Event / Batch 契約。 |
| 07 | `07_module_specification_and_tests.md` | 七層模組規格、DbC、測試策略。 |
| 08 | `08_project_structure_guide.md` | 乾淨新專案目錄結構。 |
| 09 | `09_file_dependencies.md` | 分層依賴規則與禁止依賴。 |
| 10 | `10_class_relationships.md` | 核心介面、類別關係、設計模式。 |
| 11 | `11_code_review_and_refactoring_guide.md` | Review gate、重構準則、PR checklist。 |
| 12 | `12_frontend_architecture_specification.md` | 前端架構、設計系統、效能、測試。 |
| 13 | `13_security_and_readiness_checklists.md` | 安全與生產準備檢查。 |
| 14 | `14_deployment_and_operations_guide.md` | 部署、監控、Runbook、Rollback。 |
| 15 | `15_documentation_and_maintenance_guide.md` | 文件維護、變更流程、文檔即程式碼。 |
| 16 | `16_wbs_development_plan.md` | 分階段 WBS 與里程碑。 |
| 17 | `17_frontend_information_architecture.md` | 前端資訊架構、頁面、路由、旅程。 |
| 18 | `18_refactor_wbs.md` | 現況碼 → golden 七層的重構 WBS、kill-list、波次。 |
| — | `adrs/` | Repositioning refactor ADRs（R01–R06），見 `adrs/INDEX.md`。 |
| — | `specs/` | Product slices：SPEC-01 named universe、SPEC-02 strategy package / dynamic params / optimization UI。 |

## 3. 決策摘要

| 決策 | 結論 |
| :--- | :--- |
| 產品層級 | 整體產品採七層，不是單一 Research 工具。 |
| Research 邊界 | Research 產 Signal / Target，不直接下單。 |
| 執行層級 | 個人級隔日開盤 / 簡單分批；不做 HFT / EMS。 |
| 基礎設施 | 單機或小型 VPS，Docker Compose + systemd；不做 K8s。 |
| 資料頻率 | EOD / 財報 / 籌碼 / 月營收；不做 Tick / Order Book。 |
| 交付方式 | API-first、contract-first、ADR-first。 |
| 策略撰寫 | 策略是 repo 內 Strategy Package；AI coding/IDE 寫策略，Console 透過 descriptor/schema/workflow 互動。 |

## 4. 非目標

- 不以當前程式碼為約束。
- 不遷就既有模組命名或技術債。
- 不做機構級 Tick/HFT/EMS/K8s/RBAC。
- 不讓研究程式直接碰 Broker API。
