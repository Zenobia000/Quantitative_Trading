# 設計更新文件 — backtest_platform 監控儀表板（React 版）

> **版本**：v1.0 ｜ **日期**：2026-06-01
> **用途**：本文件是把 `dev_docs/20_dashboard_specification.md`（Streamlit 面板 A–E）導入新設計系統、交付給 Lovable 產出 React 版的**設計更新總綱與索引**。
> **依據 SOP**：[`lovable_組裝.md`](./lovable_組裝.md)（Global 壓縮 → 組裝 Master Prompt → 餵 Lovable → 驗收）。
> **設計來源**：[`design-system-specs/cloning/clones/xai/`](./design-system-specs/cloning/clones/xai/)（inspired by x.ai）。

---

## 1. 為什麼要這次設計更新

| 現況（20_dashboard_specification.md） | 更新後 |
| :--- | :--- |
| Streamlit 臨時主題：`primaryColor #00d4ff` cyan、`backgroundColor #0e1117` | Token 化、dark-first、WCAG 達標的一致設計系統 |
| 無正式 Design System，跨面板易風格漂移 | 單一 Global System（玩具城規則書）貫穿 5 面板 |
| 純 Streamlit | 升級路徑：React + Tailwind + Recharts/Plotly（保留 Plotly 圖型與互動） |
| 對比/色盲未系統化 | 文字 AA、KPI 數值 AAA、漲跌「色+文字」雙編碼 |

> 設計更新不丟棄 Streamlit MVP（M3 仍可用）；本文件定義其**視覺/前端升級版**的規格，供平行開發與後續 React 化。

## 2. 三層交付物對應（玩具城理論）

| 層 | 角色 | 檔案 |
| :--- | :--- | :--- |
| **Global（靈魂）** | 設計系統規則書 | [`global/02_backtest_platform_brand_system.md`](./global/02_backtest_platform_brand_system.md) |
| **Page（骨架）** | 每面板頁面規格 | `pages/02_panel_{a-e}.md`（見下表） |
| **Assembly（心臟）** | 可貼 Lovable 的 Master Prompt | `assembly/02_panel_{a-e}_integrated.md`（見下表） |

## 3. 面板索引（5 面板，平行開發產出）

| ID | 面板 | M | Route | Page 規格 | Assembly Prompt | Sections | 主資料表 |
| :-: | :--- | :-: | :--- | :--- | :--- | :-: | :--- |
| A | 績效總覽 | M3 | `/dashboard/performance` | [`pages/02_panel_a_performance.md`](./pages/02_panel_a_performance.md) | [`assembly/02_panel_a_performance_integrated.md`](./assembly/02_panel_a_performance_integrated.md) | 6 | `equity_snapshots` |
| B | 部位狀態 | M3 | `/dashboard/positions` | [`pages/02_panel_b_positions.md`](./pages/02_panel_b_positions.md) | [`assembly/02_panel_b_positions_integrated.md`](./assembly/02_panel_b_positions_integrated.md) | 5 | `positions` |
| C | 訊號日誌 | M3 | `/dashboard/signals` | [`pages/02_panel_c_signals.md`](./pages/02_panel_c_signals.md) | [`assembly/02_panel_c_signals_integrated.md`](./assembly/02_panel_c_signals_integrated.md) | 4 | `signals`+`fills` |
| D | 風控指標 | M5 | `/dashboard/risk` | [`pages/02_panel_d_risk.md`](./pages/02_panel_d_risk.md) | [`assembly/02_panel_d_risk_integrated.md`](./assembly/02_panel_d_risk_integrated.md) | 4 | `risk_metrics` |
| E | 統計驗證 | M5 | `/dashboard/validation` | [`pages/02_panel_e_validation.md`](./pages/02_panel_e_validation.md) | [`assembly/02_panel_e_validation_integrated.md`](./assembly/02_panel_e_validation_integrated.md) | 4 | `validation_runs` |

> Grafana 系統健康（F–I）與 Discord 告警沿用既有，本次僅色彩 token 對齊 Global，不重做。

## 4. 建置順序（給 Lovable）

```
1. 先建 Design System 基底（一次性）
   貼 global/02_backtest_platform_brand_system.md §壓縮 Global Tokens
   → 產 tailwind.config.js（dark/light CSS vars）+ 共用元件
      Button / KPICard / DataTable(含 table→card) / StatusBadge / ProgressBar / ChartFrame
2. 依 M 階段逐面板：貼對應 assembly/02_panel_X_integrated.md
   M3 先做 A → B → C；M5 再做 D → E
3. 每面板產出後用 §5 QA Gate 驗收，追加 prompt 微調
```

> 平行開發：A–E 五面板規格彼此獨立，可分配多人/多 session 同時用各自 assembly prompt 開發；共用元件先由步驟 1 統一產出避免重複。

## 5. QA Gate（對照 `guides/quality_checklist.md` + lovable_組裝 §四）

每面板交付後逐項檢查：

- [ ] 配色完全來自 Global Tokens（無硬編碼；**舊 `#00d4ff` 不得出現**）
- [ ] Loading / Empty / Error / Populated 四態完備
- [ ] RWD 三斷點正確（table→card、sidebar→drawer @<1024px）
- [ ] KPI 數值用 Geist Mono tabular-nums，達 AAA 對比
- [ ] 漲跌/狀態「顏色 + 文字」雙編碼（色盲友善）
- [ ] flat：1px border 分層、無 drop shadow
- [ ] 即時數據更新無進場動畫；`prefers-reduced-motion` 支援
- [ ] focus-visible ring（accent #22D3EE）、表格列可鍵盤 drill-down
- [ ] drill-down / filter / refresh TTL 行為符合 page 規格

## 6. 與既有文件的關係

- 資料 schema 與欄位：以 [`21_data_contract.md`](../21_data_contract.md) 為準（本設計引用其表名/欄位）。
- 面板功能真相源：[`20_dashboard_specification.md`](../20_dashboard_specification.md)（本設計為其前端/視覺升級，不改功能範圍）。
- 進度：對齊 [`16_wbs_development_plan.md`](../16_wbs_development_plan.md) §8（M3 A/B/C、M5 D/E）。

---

## 變更紀錄
- v1.0 (2026-06-01)：初版。建立 Global 設計系統 + 5 面板 Page 規格 + Assembly Master Prompt，導入 x.ai-inspired dark-first token 系統取代 Streamlit cyan 臨時主題。
