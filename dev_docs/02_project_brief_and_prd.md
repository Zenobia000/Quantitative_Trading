# 專案簡報與 PRD — backtest_platform

> **版本：** v3.0 | **更新：** 2026-06-01
> **進度狀態：** 詳見 [`16_wbs_development_plan.md`](./16_wbs_development_plan.md)（單一狀態真相源，見 [`15 §10`](./15_documentation_and_maintenance_guide.md) 規則）
>
> **v1.0** (2026-05-26)：M1 完成時的 PRD 基線版本（原 rqalpha + FinMind 路線）
> **v2.0** (2026-05-31)：M2+ 重大路線變更，以 Pivot Banner 標示過時段落
> **v3.0** (2026-06-01)：§1-§7 全面對齊 ADR-013（zipline-reloaded 主骨架），移除過時標示；完整規劃見 [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md)

---

## 決策沿革（Decision Lineage）

本文 §1-§7 已對齊以下決策的最新狀態。完整 M2-M5 規劃以 [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md) 為準。

| 主題 | 最終決策（最新） | 沿革 | 正式文檔 |
| :--- | :--- | :--- | :--- |
| **回測引擎主骨架** | **zipline-reloaded**（社群版，免商業綁定） | rqalpha → TQuant-Lab/zipline-tej → zipline-reloaded | [ADR-013](./adrs/ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md)（supersedes [ADR-005](./adrs/ADR-005-mainframe-tquant-lab-zipline-fork.md)、[ADR-001](./adrs/ADR-001-engine-rqalpha-plus-vectorbt.md)）|
| **資料源** | **付費 FinLab** 為主 + FinMind 免費版 fallback | FinMind 免費版 + sponsor → 付費 FinLab | [ADR-006](./adrs/ADR-006-data-source-finlab-paid.md) |
| **引擎策略** | **雙引擎**（Zipline event 主 + vectorbt vector） | 單引擎 → 雙引擎 | [ADR-007](./adrs/ADR-007-dual-engine-zipline-vectorbt.md)（vector 半邊隨 [ADR-014](./adrs/ADR-014-zipline-reloaded-3-1-1-upgrade-reverses-adr-013-constraints.md) 恢復）|
| **系統定位** | **完整交易系統**（backtest / paper / live 三模式共用 strategy code） | 純回測平台 → 三模式 | [ADR-008](./adrs/ADR-008-tri-mode-shared-strategy-code.md) |
| **監控架構** | **Streamlit + Grafana + Discord** 三層 | Grafana 單一 → 三層（Telegram → Discord）| [ADR-009](./adrs/ADR-009-dual-dashboard-telegram-monitoring.md) + [ADR-010](./adrs/ADR-010-discord-alerter-supersedes-telegram.md) |
| **套件管理** | **uv** | poetry → uv | [ADR-012](./adrs/ADR-012-adopt-uv-package-manager.md) |
| **M2 目錄結構** | engines/ + adapters/ + validation/ 模組邊界 | — | [ADR-011](./adrs/ADR-011-m2-directory-structure-and-module-boundaries.md) |

---

## 1. 專案總覽

| 項目 | 內容 |
| :--- | :--- |
| **專案名稱** | backtest_platform — 四層共振戰法回測平台 |
| **狀態** | 詳見 [`16_wbs_development_plan.md`](./16_wbs_development_plan.md)（單一狀態真相源）|
| **目標 M5 上線** | 2027-Q2（暫定，含 M2 重組緩衝）|
| **核心團隊** | 單人開發（Zenobia000） |
| **策略契約** | `strategy/v2.md` v2.1.0 |

---

## 2. 商業目標

| 項目 | 內容 |
| :--- | :--- |
| **背景與痛點** | 四層共振戰法在 ChatGPT 對話中設計（3,427 行），缺乏可重現的量化驗證；XQ XScript 只能繪圖，無法回測 portfolio 級別績效 |
| **策略契合度** | 提供策略本人對「策略真的有 Edge / 還是運氣」的科學判斷依據 |
| **成功指標** | 主要：IS Sharpe > 1.0、OOS Sharpe > 0.6 × IS；次要：PBO < 30%、滑點 0.3% 下 Sharpe > 1.0 |

### 為什麼是現在做

- v1 ChatGPT 對話已完成（M0 規格）
- 不做回測 → 永遠停在「直覺策略」階段，無法判斷是否上實盤
- 跳過回測直接實盤 = 拿錢學習

---

## 3. 使用者故事與允收標準

### Epic 1：策略研究者跑歷史回測

| ID | 描述 (As a / I want to / So that) | 允收標準 | BDD |
| :--- | :--- | :--- | :--- |
| US-001 | As a 策略研究者, I want to 用單一指令對某檔股票跑 v2.md 全套四層計分+訊號, so that 我可以快速驗證程式邏輯是否與 XQ 一致 | 1. CLI `python -m backtest_platform.pipeline run --stock-id 2330 --start ... --end ...` 跑通<br>2. 輸出 calendar CSV + summary stats<br>3. 訊號與 XQ 標記差異 < 0.5% | `pipeline.feature` |
| US-002 | As a 策略研究者, I want to 拉某段期間的 FinMind 資料並 cache 為 parquet, so that 重跑回測時不需重 call API | 1. CLI 支援 `--output data/parquet`<br>2. 三表（daily / institutional / broker_chips）獨立檔案<br>3. 重跑時優先讀 parquet | `etl.feature` |

### Epic 2：策略研究者驗證策略 Edge

| ID | 描述 | 允收標準 | BDD |
| :--- | :--- | :--- | :--- |
| US-003 | As a 策略研究者, I want to 跑 IS 期間（2015–2020）的 portfolio 回測, so that 我能判斷策略是否達標 v2.md 4.3.1 綠燈 | 1. zipline-reloaded 整合（Backtest 模式，ADR-013）<br>2. 輸出 quantstats 報表<br>3. 對照綠/黃/紅燈表自動標記 | `backtest_is.feature` (M2) |
| US-004 | As a 策略研究者, I want to 跑 OOS（2023–2024）一次性驗證, so that 我能判斷策略是否過擬合 | 1. OOS 結果不可回頭調參<br>2. 自動計算 PBO / DSR<br>3. 失敗即標記策略淘汰 | `backtest_oos.feature` (M3) |

### Epic 3：風控與運維（M4+）

| ID | 描述 | 允收標準 | BDD |
| :--- | :--- | :--- | :--- |
| US-005 | As a 策略研究者, I want to 跑 paper trading 3 個月模擬, so that 驗證實盤滑點與回測假設一致 | 1. 每日訊號生成<br>2. 對比實際開盤價 vs 假設進場價<br>3. 滑點 < 預估 1.5x 才晉升 | `paper_trade.feature` (M4) |
| US-006 | As a 策略研究者, I want to 看 Streamlit + Grafana 雙儀表板即時監控策略健康度, so that 退化時能及早發現 | 1. 30D 滾動 Sharpe、PF<br>2. 退化告警經 Discord 發送（ADR-010）<br>3. 熔斷規則自動執行 | `monitoring.feature` (M4+) |

---

## 4. 範圍與限制

### 功能範圍

| 層 | M1 ✅ | M2 | M3 | M4 | M5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 資料層（Bundle + DB） | ✅ | FinMind/FinLab bundle | — | 即時資料 feed | — |
| 策略層（計分 + 訊號） | ✅ | plug 為 Algorithm | — | — | — |
| 回測引擎 | — | zipline-reloaded (event) | vectorbt + WFA | — | — |
| 統計驗證 | — | — | PBO/DSR/MC | — | — |
| 紙上交易 | — | — | — | PaperBroker | — |
| 實盤下單 | — | — | — | — | ShioajiBroker |
| 監控告警 | — | — | Streamlit | Grafana + Discord | — |
| 前端 UI | — | — | Streamlit 面板 A–C | — | 面板 D–E |

### 非功能需求

| 分類 | 需求 | 目標值 |
| :--- | :--- | :--- |
| 性能 | 單檔 10 年回測 | < 60 秒 |
| 性能 | 100 檔 portfolio 回測 | < 30 分鐘 |
| 可靠性 | ETL idempotent | 重跑結果一致 |
| 可觀測性 | Trade audit trail | 100% trade 記錄含 scores/prices/position |
| 可重現性 | 訊號邏輯 | zipline & vectorbt 結果差異 < 0.1% |

### 不做什麼

- ❌ 即時行情接收（M5 才考慮）
- ❌ 自動實盤下單（M5 才考慮）
- ❌ 多策略管理（單一策略為主）
- ❌ 多市場（台股為主，不做美股 / 港股）
- ❌ 期權 / 期貨（純股票策略）
- ❌ 多帳戶管理

### 假設與依賴

**假設**：
- 付費 FinLab 為主資料源、FinMind 免費版作 fallback（ADR-006）
- 券商分點資料可透過 TWSE 公開資訊補爬
- 個人 PC 算力足夠跑 100 檔 × 10 年回測

**依賴**：
- FinLab API（主資料源，付費）+ FinMind API（fallback）— ADR-006
- TimescaleDB（儲存 / bundle cache）
- zipline-reloaded（回測引擎主骨架）— ADR-013
- vectorbt 1.0+（回測引擎副，參數網格；ADR-014 升級後恢復可用）— ADR-007
- Streamlit + Grafana + Discord（監控告警三層）— ADR-009 / ADR-010
- uv（套件管理）— ADR-012
- Shioaji（永豐金證券下單 API，M5）

---

## 5. 待辦問題與決策

| ID | 描述 | 狀態 | 備註 |
| :--- | :--- | :--- | :--- |
| Q-001 | 下市股資料源如何取得 | 待決定 | 詳見 `strategy/research/v2.2_ic_test_plan.md` 評估表 |
| Q-002 | 券商分點補爬策略 | 待決定 | M2 開始時決定 |
| Q-003 | 是否升級 FinMind sponsor | 已關閉 | 改採付費 FinLab 為主源（ADR-006），FinMind 降為 fallback |
| Q-004 | rqalpha 自訂 mod 是否值得寫 | 已關閉 | 廢止 rqalpha，主骨架改 zipline-reloaded（ADR-013，原 ADR-005 TQuant-Lab 已 superseded）|
| D-001 | 採用 v2.md 為單一策略契約 | 已決定 | 偏離須在 6.3 留記錄 |
| D-002 | 採用 MVP 工作流模式 | 已決定 | 見 01_workflow_manual.md |
| D-003 | 使用 Public GitHub repo（Zenobia000） | 已決定 | 2026-05-26 上線 |
| D-004 | risk_pct 從 1% → 0.5% 對齊 Heat 6% | 已決定（v2.1） | v2.md changelog |
| D-005 | 主骨架採 zipline-reloaded | 已決定 | ADR-013（supersedes ADR-005 / ADR-001）— Sprint 0 S1 揭露 zipline-tej import 強綁 TEJ key |
| D-006 | 主資料源採付費 FinLab + FinMind fallback | 已決定 | ADR-006 |
| D-007 | 雙引擎（Zipline event + vectorbt vector） | 已決定 | ADR-007（vector 半邊隨 ADR-014 升級恢復）|
| D-008 | 系統定位升級為三模式（backtest/paper/live） | 已決定 | ADR-008 |
| D-009 | 監控三層 Streamlit + Grafana + Discord | 已決定 | ADR-009 / ADR-010（Discord 取代 Telegram）|
| D-010 | 套件管理採 uv | 已決定 | ADR-012 |
| D-014 | zipline-reloaded 3.0.4 → 3.1.1 升級，解除 pandas<2 / numpy<2 / vectorbt 暫停 | 已決定（2026-06-01） | ADR-014（amends ADR-013 § 4）— upstream 3.1.1 release 解鎖三項約束 |
| D-015 | M2 IS gate FAIL（雙窗口無 edge、進場過嚴）→ 觸發退場條件，回 M0 重設**進場**假設 | 已決定（2026-06-02） | ADR-017 — 記錄 ADR-016 gate 執行結果；參數探針定位約束在進場非出場 |
| D-016 | **監控優先 → 研究迴圈優先**：Run 物件化（runs 主表）+ 研究工作區 IA（A–E 降 live 子視圖）+ IS→WFA→OOS gate 工作流 + OOS sealed vault + 試驗次數 deflate + 晉升狀態機；後端契約先行 | 已決定（2026-06-02） | ADR-018 — 大廠 UI/UX deep-research 對標（10 平台）；重定位 ADR-009/015 產物、UX 化 ADR-017；證據包 `web_design/03_uiux_benchmark_and_reinforcement_plan.md` |

---

## 6. 成功與失敗的判斷

### 成功
- 策略通過 M3 統計驗證 → 進入 paper trading
- Paper trading 滑點與回測一致 → 進入小倉位實盤
- 小倉位 3 個月不退化 → 進入全倉

### 失敗（接受）
- M2 IS 回測達不到綠燈 → 砍策略或重新設計
- M3 PBO > 50% → 策略過擬合，淘汰
- M4 paper trading 滑點 > 預估 2x → 重新校準成本模型

### 失敗（必須處理）
- 訊號邏輯與 XQ 差異 > 1% → bug 修復
- ETL 資料遺失 → 重灌資料源
- 任何階段違反預註冊紀律 → 強制重跑該階段
