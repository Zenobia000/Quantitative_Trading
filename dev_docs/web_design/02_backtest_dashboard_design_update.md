# 設計更新文件 — backtest_platform 監控儀表板（React 版）

> **版本**：v1.0 ｜ **日期**：2026-06-01
> **用途**：本文件是把 `dev_docs/20_dashboard_specification.md`（Streamlit 面板 A–E）導入新設計系統、交付給 Lovable 產出 React 版的**設計更新總綱與索引**。
> **依據 SOP**：[`lovable_組裝.md`](./lovable_組裝.md)（Global 壓縮 → 組裝 Master Prompt → 餵 Lovable → 驗收）。
> **設計來源**：Grok 單色 dark 設計語言（`global/02_backtest_platform_brand_system.md` v2.0；v1 曾誤用 x.ai teal 差異化，已修正為 Grok 單色）。
> **IA 對齊**：頁面命名已依 `03_uiux_benchmark_and_reinforcement_plan.md` 的三區 IA 重整為 `pages/monitor_{a-d}_*.md`（監控區）與 `pages/research_0N_*.md`（研究區）；route 由 `/dashboard/*` 改為 `/monitor/*`。

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
| **Page（骨架）** | 每面板頁面規格 | `pages/monitor_{a-d}_*.md`（見下表；E 已重定位至研究區 Validate gate） |
| **Assembly（心臟）** | 可貼 Lovable 的 Master Prompt | `assembly/monitor_{a-d}_*_integrated.md`（見下表） |

## 3. 面板索引（監控區 4 面板 A–D；E 重定位至研究區）

> 監控區 route 由 `/dashboard/*` 改名 `/monitor/*`（IA 三區重整，詳見 `03` §4.7 / §5.2）。Panel E 統計驗證從「監控區唯讀展示」**重定位**至研究區 Validate gate（[`pages/research_07_validate_gate.md`](./pages/research_07_validate_gate.md)），語意由唯讀升級為不可逆 gate 工作流，原 `pages/02_panel_e_validation.md` 已移除。

| ID | 面板 | M | Route | Page 規格 | Assembly Prompt | Sections | 主資料表 |
| :-: | :--- | :-: | :--- | :--- | :--- | :-: | :--- |
| A | 績效總覽 | M3 | `/monitor/performance` | [`pages/monitor_a_performance.md`](./pages/monitor_a_performance.md) | [`assembly/monitor_a_performance_integrated.md`](./assembly/monitor_a_performance_integrated.md) | 6 | `equity_snapshots` |
| B | 部位狀態 | M3 | `/monitor/positions` | [`pages/monitor_b_positions.md`](./pages/monitor_b_positions.md) | [`assembly/monitor_b_positions_integrated.md`](./assembly/monitor_b_positions_integrated.md) | 5 | `positions` |
| C | 訊號日誌 | M3 | `/monitor/signals` | [`pages/monitor_c_signals.md`](./pages/monitor_c_signals.md) | [`assembly/monitor_c_signals_integrated.md`](./assembly/monitor_c_signals_integrated.md) | 4 | `signals`+`fills` |
| D | 風控指標 | M5 | `/monitor/risk` | [`pages/monitor_d_risk.md`](./pages/monitor_d_risk.md) | [`assembly/monitor_d_risk_integrated.md`](./assembly/monitor_d_risk_integrated.md) | 4 | `risk_metrics` |
| ~~E~~ | 統計驗證（重定位） | M3 | `/research/validate` | [`pages/research_07_validate_gate.md`](./pages/research_07_validate_gate.md) | （隨 React 化產出） | 6 | `validation_runs`+`runs` |

> Grafana 系統健康（F–I）與 Discord 告警沿用既有，本次僅色彩 token 對齊 Global，不重做。

## 4. 建置順序（給 Lovable）

```
1. 先建 Design System 基底（一次性）
   貼 global/02_backtest_platform_brand_system.md §壓縮 Global Tokens
   → 產 tailwind.config.js（dark/light CSS vars）+ 共用元件
      Button / KPICard / DataTable(含 table→card) / StatusBadge / ProgressBar / ChartFrame
2. 依 M 階段逐面板：貼對應 assembly/monitor_X_integrated.md
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
- [ ] focus-visible ring（**單色白環 rgba(245,245,245,.7)**，非 teal）、表格列可鍵盤 drill-down
- [ ] drill-down / filter / refresh TTL 行為符合 page 規格

## 6. 與既有文件的關係

- 資料 schema 與欄位：以 [`21_data_contract.md`](../21_data_contract.md) 為準（本設計引用其表名/欄位）。
- 面板功能真相源：[`20_dashboard_specification.md`](../20_dashboard_specification.md)（本設計為其前端/視覺升級，不改功能範圍）。
- 進度：對齊 [`16_wbs_development_plan.md`](../16_wbs_development_plan.md) §8（M3 A/B/C、M5 D/E）。

---

## 變更紀錄
- v1.1 (2026-06-03)：依 `03` 三區 IA 重整頁面命名——監控面板 `02_panel_{a-e}` → `pages/monitor_{a-d}_*` + route `/dashboard/*` → `/monitor/*`；風格全面收斂 v1 teal（#22D3EE/#243044）為 Global v2.0 Grok 單色（含 assembly 內嵌 token）；多類別 data-viz（B 產業圓餅、C 5 軌散點）改用 §6.1 受控 Categorical 8-色盤；Panel E 重定位至研究區 Validate gate（`research_07_validate_gate.md`），原監控頁移除。
- v1.0 (2026-06-01)：初版。建立 Global 設計系統 + 5 面板 Page 規格 + Assembly Master Prompt，導入 dark-first token 系統取代 Streamlit cyan 臨時主題。
