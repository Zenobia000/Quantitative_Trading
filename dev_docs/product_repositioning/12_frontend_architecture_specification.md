# 前端架構規範 - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 架構目標

前端是操作台，不是行銷網站。目標是讓單一操作者快速回答：

- 今日資料是否正常？
- 哪些策略在 paper / live / halted？
- 是否有 risk block / reconciliation mismatch？
- PnL、drawdown、decay 是否異常？
- 哪個 package / order / fill 導致問題？

> UI 是**治理 + 證據審閱台**，不是策略 IDE、也不是研究驅動台。策略撰寫與 research 閉環在 Claude Code dev-time harness 完成（ADR-009 / SPEC-03）；UI 只消費後端 read model、呈現 evidence ledger 與 gate verdict、承載 governance 核准動作。

## 2. 技術選型

| 項目 | 選型 |
| :--- | :--- |
| Framework | React + TypeScript |
| Data Fetching | TanStack Query |
| State | URL state + local UI state；避免全域濫用 |
| Charts | lightweight charts / ECharts |
| Styling | CSS variables + component library |
| Testing | Vitest + Testing Library + Playwright |

## 3. 資訊分層

| Layer | 職責 |
| :--- | :--- |
| Pages | routing、layout、data composition |
| Features | research、governance、risk、execution、monitoring |
| Components | table、chart、badge、timeline、form |
| Design Tokens | color、spacing、typography、status |
| API Client | typed OpenAPI client |

## 4. 設計系統

| Token | 原則 |
| :--- | :--- |
| Color | 狀態色清楚：pass/warn/error/crit/halted |
| Typography | dashboard 密度優先，不做 hero |
| Layout | 左側導航 + 主內容 + detail drawer |
| Tables | 可排序、可篩選、可 drill-down |
| Forms | release/risk 操作需 confirm + audit reason |

## 5. 前端安全

- 不儲存 broker credential。
- 高風險操作需 confirmation dialog。
- 所有 mutation 顯示 request_id / audit_id。
- UI 不可只靠前端隱藏權限；API 仍需檢查。

## 6. 效能目標

| 指標 | 目標 |
| :--- | :--- |
| Initial dashboard load | < 2s on local/VPS |
| Table 10k rows interaction | virtualized |
| Critical status refresh | <= 30s polling or push |

## 7. 測試

- Component tests：risk badge、package status、order timeline。
- E2E：approve package、risk block、kill switch、reconciliation alert。
- Visual regression：dashboard dense layouts。

