# 文檔與維護指南 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 文檔類型

| 類型 | 文件 |
| :--- | :--- |
| Product | `02`, `03`, `17` |
| Architecture | `04`, `05`, `09`, `10` |
| Engineering | `06`, `07`, `08`, `11`, `12` |
| Operations | `13`, `14` |
| Maintenance | `15`, `16` |

## 2. 文檔即程式碼

- 文件放 repo，走 PR review。
- Mermaid 圖與 API schema 必須可被 CI 檢查。
- ADR 不修改歷史決策；新決策新增 ADR 或 supersede。
- 文件改動與程式改動同 PR 或前置 PR。

## 3. 維護排程

| 頻率 | 任務 |
| :--- | :--- |
| 每週 | WBS、風險、open decisions |
| 每月 | ADR log、runbook、security checklist |
| 每季 | architecture fitness functions、capacity、cost |
| 每次 release | API contract、deployment guide、changelog |

## 4. 變更規則

| 變更 | 必改文件 |
| :--- | :--- |
| 新增 container | `05`, `08`, `09`, `14` |
| 新增 API/event | `06`, `07`, `13` |
| 新增 risk rule | `02`, `03`, `07`, `13` |
| 新增 broker | `04`, `05`, `06`, `10`, `14` |
| 新增頁面 | `12`, `17` |

## 5. CHANGELOG 模板

```markdown
## [Unreleased]
### Added
### Changed
### Fixed
### Security
### Operations
```

