# frontend/GOAL.md — Codex-Style Operations Console

> 版本: v2.0 | 日期: 2026-07-05
>
> 目標：把舊研究後台改成個人級 EOD 量化交易平台的 Codex-style operations console。前端不再依賴已刪除的 `dev_docs/web_design/*`，真相源改為 `dev_docs/product_repositioning/00_INDEX.md` 到 `17_frontend_information_architecture.md`，重構節奏見 `18_refactor_wbs.md`。

## 1. 產品定位

整體產品採 golden SAD 七層權威架構：

```text
Data → Research → Governance → Strategy/Portfolio → Risk → Execution → Monitoring → Foundation
```

前端是一個密集、可維運、可追溯的操作台。它不是 landing page，不是 notebook UI，也不是只給研究用的 dashboard。

## 2. 視覺方向

| 原則 | 規範 |
| :--- | :--- |
| Dense first | 表格、ledger、status strip、risk blotter 優先。 |
| Codex UI color | 中性黑白灰、細格線、緊湊面板、monospace 數字、少量語意狀態色。 |
| Evidence first | 每個 KPI 要能 drill-down 到 bundle/run/package/order/fill/audit。 |
| Risk visible | CRIT、HALT、reconciliation lock 全站可見。 |
| No fake data | pending 端點只顯示 pending/empty，不假造交易數字。 |

## 3. IA

主導航採七層操作台：

| Zone | 用途 |
| :--- | :--- |
| Command | 全局 readiness、風控、資料、PnL、事故 |
| Data | bundle、DQ、資料源、calendar |
| Research | strategies、runs、reports、compare、sweep |
| Governance | candidates、Live OOS、release gate、paper/watch |
| Trading | target portfolio、positions、signals、execution trail |
| Risk | limits、risk decisions、blocks、halts |
| Operations | fleet、performance、alerts、incidents、jobs |
| System | settings、audit、backup、health |

## 4. 硬約束

- Research 頁不可呈現「可直接送單」的操作。
- 高風險 action 必須有二次確認與 audit reason。
- 漲跌必須色彩 + 符號雙編碼。
- 密集表格在窄螢幕橫向捲動，不改成卡片。
- 所有數字使用 tabular-nums。
- 舊 Grok 單色 token 不再是設計真相；改用 `tokens.css` 的 Codex-style neutral token。

## 5. 每頁 Definition of Done

- [ ] 對應七層 zone。
- [ ] loading / empty / error / default 四態。
- [ ] pending 不假造數字。
- [ ] 有 source / as-of / trace id 或明確標 pending。
- [ ] `npm run typecheck` 通過。
- [ ] 主要頁面需 Playwright screenshot 驗證。
