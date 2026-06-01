# ADR-015: 監控儀表板採用 Design System + 策略績效層 Streamlit→React 升級

> **狀態：** 已接受 | **日期：** 2026-06-01 | **決策者：** Self
> **Supersedes（部分）：** [ADR-009](./ADR-009-dual-dashboard-telegram-monitoring.md) § 2 選項一/三將 Streamlit 定為策略績效層（面板 A–E）的實作選擇，及其「純 Python、無前端工程負擔」理由。
> 本 ADR 將**策略績效層**改以 React 實作；ADR-009 的**雙儀表板分層原則**（策略績效 / 系統健康 / 主動告警三層分工）維持有效。
> **不受影響：** Grafana 系統健康層（面板 F–I）、Discord 告警層（ADR-010）、TimescaleDB 單一真相（ADR-002）。
> **Related：** ADR-002（TimescaleDB）、ADR-009（雙儀表板分層）、ADR-010（Discord 告警）、`20_dashboard_specification.md`（面板功能真相源）、`web_design/design-system-specs/cloning/clones/xai/`（設計系統來源）

---

## 1. 背景與問題

- **上下文**：ADR-009 已定 L7 監控三層分工，策略績效層（面板 A–E）原以 Streamlit 實作，主題僅一組臨時 token（`primaryColor #00d4ff` cyan / `backgroundColor #0e1117`），無正式 Design System。
- **問題**：
  - 無 token 化設計系統 → 跨 5 面板視覺易漂移、難維持一致
  - Streamlit 的互動與視覺天花板，對「策略 PM 視角的深度績效歸因 + drill-down」體驗有限；客製化元件需繞 `st.components`
  - 臨時主題未經對比度驗算（cyan/灰）→ 長時間盯盤可讀性與色盲友善不足
  - 已透過 x.ai 設計複製流程（clone workflow）產出一套 dark-first、WCAG 達標、含 gain/loss 金融語義的 token 系統，具備導入條件
- **驅動因素 / 約束**：
  - 盤後長時間檢視 → dark-first、低眩光、數值高對比（AAA）為硬需求
  - 金融數據 → 漲跌「色 + 文字」雙編碼（色盲友善）、數值等寬對齊
  - 策略績效層需高互動（filter / drill-down / 自訂期間）— ADR-009 既有訴求
  - 受眾僅一人（單人開發）→ 前端工程負擔是真實成本，須誠實評估

---

## 2. 考量的選項

### 選項一：維持純 Streamlit，僅換色票（config.toml + Plotly 主題）
- **描述**：把新 token 套到 `.streamlit/config.toml` 與 Plotly template，不引入前端棧。
- **優點**：零前端負擔（延續 ADR-009 初衷）、改動最小、M3 MVP 不中斷。
- **缺點**：仍受 Streamlit 元件/版面天花板限制；無法落實完整 Design System（元件 states、RWD table→card、focus 管理）；token 只能局部套用。
- **成本/複雜度**：低 / 能力受限。

### 選項二：Streamlit + 局部嵌入 React 自訂元件（`st.components.v1`）
- **描述**：保留 Streamlit 殼，重點面板用自訂 React component 嵌入。
- **優點**：漸進、保留 Python 後端直連。
- **缺點**：兩套心智模型混雜、build/打包複雜、跨元件狀態同步麻煩；設計系統仍難全站一致。
- **成本/複雜度**：中 / 維護心智負擔高。

### 選項三：策略績效層全面 React + Tailwind + Recharts/Plotly.js ★採納
- **描述**：面板 A–E 改以 React 重寫，套用 `web_design/global/02_backtest_platform_brand_system.md` 設計系統；Plotly 圖型以 Plotly.js / Recharts 對接；經 Lovable 依 assembly Master Prompt 產出。
- **優點**：完整落實 Design System（token / 元件庫 / 四態 / RWD / a11y / WCAG）；視覺與互動天花板解除；行銷頁與儀表板共用同一設計系統；可版本化、可測試。
- **缺點**：**引入前端工程負擔——正是 ADR-009 當初選 Streamlit 要避免的**；需 build pipeline 與前端棧；**React 無法直連 SQL，需新增 REST API 層**（Streamlit 原本 SQLAlchemy 直連 TimescaleDB）。
- **成本/複雜度**：中高。

### 選項四：策略績效層也走 Grafana
- **描述**：A–E 用 Grafana 面板。
- **狀態**：**已於 ADR-009 § 2 選項二否決**——Grafana 對事件式快照、互動式歸因展示能力弱。本 ADR 維持否決。

---

## 3. 決策

**選擇：選項三（策略績效層 A–E 全面 React + Tailwind + Recharts/Plotly.js，導入 token 化 Design System）**

**理由**：
- 設計系統一致性、互動/視覺天花板、a11y/WCAG 達標，三者只有全 React 能完整落實；選項一/二都只能半套。
- ADR-009 的**分層原則不變**：策略績效仍是獨立一層，只是實作從 Streamlit 換成 React；Grafana（F–I）與 Discord（ADR-010）完全不動。
- 設計系統已備齊（衍生自 x.ai clone，dark-first / teal / flat / Geist Mono 數值 / gain-loss 雙編碼 / 全 token 經對比度驗算）。
- 接受其代價：引入前端工程負擔與 REST API 層，以換取可維護、可規模化的監控前端（M4 paper 3 月、M5 live 長期值守需要更穩健的前端）。

### 設計系統與規格產物（已落地於 `dev_docs/web_design/`）

| 層 | 檔案 |
|:--|:--|
| 設計來源 | `design-system-specs/cloning/clones/xai/`（inspired by x.ai，含 L0–L4 + spec + validation） |
| Global（設計系統） | `global/02_backtest_platform_brand_system.md` |
| Page（5 面板規格） | `pages/02_panel_{a-e}.md` |
| Assembly（Lovable Master Prompt） | `assembly/02_panel_{a-e}_integrated.md` |
| 總綱索引 | `02_backtest_dashboard_design_update.md` |

### 三層職責對照（修訂 ADR-009 表，僅第 1 層實作變更）

| 層 | 工具（修訂後） | 變更 |
|:--|:--|:--|
| 1 策略績效 A–E | **React + Tailwind + Recharts/Plotly.js** | ⬅ 由 Streamlit 升級（本 ADR） |
| 2 系統健康 F–I | Grafana + Prometheus | 不變 |
| 3 主動告警 | Discord bot（ADR-010） | 不變 |

### 驗證閘門
- 設計系統全 token 經 WCAG 驗算（文字 AA、KPI 數值 AAA）— 見 clone `validation.md`。
- 每面板交付對照 `web_design/02_backtest_dashboard_design_update.md` § 5 QA Gate（四態 / RWD / 無硬編碼舊色 / 雙編碼 / flat）。

---

## 4. 後果

### 正面
- 一致 token 化 Design System 貫穿 5 面板 + 行銷頁，杜絕視覺漂移。
- dark-first + WCAG（數值 AAA）+ 色盲友善雙編碼，盤後檢視體驗顯著提升。
- 可複用元件庫（Button/KPICard/DataTable/StatusBadge/ProgressBar/ChartFrame）、可測試、可版本化。
- 設計即文件：Lovable Master Prompt 可重複產生/迭代。

### 負面
- **引入前端工程負擔**（React + Tailwind + build pipeline）——明確反轉 ADR-009「純 Python、無前端工程負擔」理由；單人維護成本上升。
- **需新增 REST API 層**：React 無法如 Streamlit 直連 TimescaleDB（SQLAlchemy），須為面板 A–E 提供 GET endpoints（對齊各 page 規格 [DATA & API]）。`21_data_contract.md` 需補 API 契約。
- 過渡期 Streamlit MVP 與 React 版並存，短期雙軌。
- `20_dashboard_specification.md` § 2.8 Streamlit config 與 § 2.1 技術選型（針對 A–E）被本 ADR 取代，需加註。

### 影響範圍
- `dashboard/`：策略績效層由 `streamlit_app.py` 轉為 React app（新增前端專案結構）。
- 新增 **REST API 層**（FastAPI/Flask 或既有後端擴充）暴露 A–E 所需 endpoints，讀 TimescaleDB（ADR-002）。
- `dev_docs/web_design/`：新增整套 Design System + 5 面板規格 + assembly（已落地）。
- `21_data_contract.md`：補 dashboard REST API 契約。
- `docker-compose.yml`：可能新增前端服務 / API 服務容器。
- ADR-009 § 4 影響範圍中 `dashboard/streamlit_app.py`（策略績效部分）改為 React。

### 重新評估觸發
- React + Lovable 維護成本超出單人負擔 → 回退選項一（Streamlit 換皮）。
- Lovable 產出品質不足以達 QA Gate → 改手寫 React 或回退。
- REST API 層複雜度過高（即時性需求） → 評估 WebSocket / SSE 或局部回 Streamlit。
- 設計系統與 Grafana（F–I）視覺落差造成困擾 → 評估 Grafana 主題對齊 token。

---

## 5. 執行計畫

1. **設計（已完成，2026-06-01）**：x.ai clone → Global Design System → 5 面板 Page 規格 + Assembly Master Prompt + 總綱索引落地於 `dev_docs/web_design/`。
2. **元件庫（一次性）**：以 Global 壓縮 token 經 Lovable 產 `tailwind.config.js`（dark/light CSS vars）+ 共用元件（Button/KPICard/DataTable/StatusBadge/ProgressBar/ChartFrame）。
3. **API 層**：為面板 A–E 補 REST endpoints（讀 TimescaleDB），更新 `21_data_contract.md` API 契約。
4. **M3 React 化**：面板 A 績效總覽 → B 部位狀態 → C 訊號日誌（貼對應 assembly prompt，逐面板過 QA Gate）。
5. **M5 React 化**：面板 D 風控 → E 統計驗證。
6. **過渡**：Streamlit MVP 於 React 版上線前維持可用，逐面板切換後下線。
7. **文件同步**：`20_dashboard_specification.md` § 2.1 / § 2.8 加註「A–E 前端實作見 ADR-015」；更新 `16_wbs_development_plan.md` § 8。

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-01 | Self | 初版 — 採納設計系統 + 策略績效層 React 升級 |
