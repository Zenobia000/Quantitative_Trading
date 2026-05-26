# backtest_platform — 開發文檔總覽

> 依 `VibeCoding_Workflow_Templates` v3.0 模板產出，對應實際 `backtest_platform/` 程式碼狀態。
> **產出日期**：2026-05-26 | **對應版本**：backtest_platform 0.1.0 (M1)

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
| 04 | [adrs/](./adrs/) | 架構決策記錄（4 份 ADR） |
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
