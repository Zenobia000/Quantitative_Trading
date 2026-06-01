# ADR-013: 主骨架切換 zipline-tej → zipline-reloaded

> **狀態：** 已接受 | **日期：** 2026-06-01 | **決策者：** Self
> **Supersedes：** [ADR-005](./ADR-005-mainframe-tquant-lab-zipline-fork.md)（TQuant-Lab / zipline-tej 主骨架角色廢止）
> **Related：** ADR-001（rqalpha 已 superseded）、ADR-007（雙引擎方案受影響，vectorbt 半邊暫停）、ADR-011（M2 目錄結構）、ADR-012（uv 套件管理）

---

## 1. 背景與問題

- **上下文**：ADR-005 採納 TQuant-Lab（zipline-tej，TEJ 維護的 zipline 台股 fork）為主骨架。Sprint 0 spike S1（TQuant-Lab hello-world）原計畫驗證 import + 簡單 ingest 流程。
- **問題**：S1 spike 揭露 fatal flaw — **`import zipline_tej` 在 import 階段 hard-code TEJ API call**，意即程式根本載入不起來，除非 `TEJAPI_KEY` 環境變數已設且 token 有效。
- **與 ADR-005 假設衝突**：ADR-005 § 1 隱含「免 TEJ key 仍可開發」（原文：「若無 TEJ key 仍可使用 zipline-tej framework，但 ingest 需用自製 bundle」）— 該描述基於「import 不依賴 key」的假設，spike 驗證後不成立。
- **驅動因素 / 約束**：
  - ADR-005 既定的全部技術約束（XTAI 交易日曆、T+1、event-driven 訊號優先序、Shioaji 介接路徑、7 層 reference 重用）**仍有效**
  - **新增約束**：0 商業綁定 — 免費開發者必須能完整跑 backtest，CI 無 TEJ key 也要能跑測試
  - M1 既有 962 LOC + Sprint 0 S2-S6 deliverable 必須 0 重構保留

---

## 2. 考量的選項

### 選項一：維持 zipline-tej + 強制 TEJ key
- **描述**：要求所有 contributor 申請 TEJ 試用 key 才能 import
- **優點**：保留 ADR-005 已寫定的 bundle 設計與套件命名
- **缺點**：
  - 違反 0 商業綁定原則
  - TEJ 試用 key 有效期短（通常 30 天），續期程序耗時
  - CI 無法跑 zipline 相關測試（除非把 key 寫進 secret store，引入額外維運成本）
  - 個人開發者每次重灌環境都要重申請
- **成本/複雜度**：低開發 / 高長期維護成本

### 選項二：zipline-reloaded ★採納
- **描述**：切到社群維護的 zipline 主線 fork（quantopian zipline 退役後的延續），自寫 Taiwan bundle
- **優點**：
  - **0 商業綁定** — clean import，無強制 API key
  - 主流維護（GitHub 持續 release）
  - XTAI calendar 透過 `exchange-calendars 4.13.2` 完整支援（與 zipline-tej 同來源）
  - SQLAlchemy 2.x 支援（zipline-tej 卡在 1.4，本身就是技術債）
  - ADR-005 所有「Zipline 生態」技術理由 — event-driven、bundle 機制、order/slippage/commission 抽象、broker 介接路徑 — **100% 保留**
- **缺點**：
  - pandas / numpy 必須降版（zipline-reloaded 3.0.4 cap `pandas<2`、`numpy<2`）
  - `requires-python <3.12`（與 zipline-tej 相同，無回歸）
  - vectorbt 與 `pandas<2` 不相容 → **ADR-007 雙引擎方案的 vectorbt 半邊暫停**
  - 需自寫 Taiwan data bundle（FinMind / FinLab）— 但這本來就在 ADR-006 規劃中
- **成本/複雜度**：中（bundle 自寫成本 ~360 LOC，但 ADR-006 已預期）

### 選項三：自寫 event-driven engine（v2.0 退場路線）
- **描述**：完全脫離 zipline 生態，自寫 ~2500 LOC event-driven backtester
- **優點**：完全可控、無依賴版本限制、無 pandas 降版問題
- **缺點**：
  - 開發成本巨大（17 週首版上線進度受影響）
  - 生態（quantstats / pyfolio / empyrical-reloaded）失去整合
  - 7 層 reference 架構無從重用，回到 ADR-001 前的窘境
- **保留作退場路線**：選項二後續若再次失敗（如 zipline-reloaded 維護中斷或無法解決 pandas<2 限制），啟動此路線

---

## 3. 決策

**選擇：選項二（zipline-reloaded 3.0.4 + 自寫 FinMind/FinLab bundle）**

### Sprint 1 Day 1 Gate Verification 結果（commit `d31044a`）

- ✓ **Gate 1：clean import** — zipline / TradingAlgorithm / zipline.api / zipline.data.bundles / zipline.finance.{slippage, commission} 全乾淨 import，零 TEJ 依賴
- ✓ **Gate 2：XTAI calendar** — `exchange-calendars 4.13.2`，2024 共 243 sessions，春節 2024-02-08 正確標記為非交易日
- ✓ **M1 regression**：56 tests passed, 1 skipped — pandas 降版對 M1 ETL / 策略純函式無破壞
- ✓ **開發鏈**：ta-lib 0.6.8 Windows wheel 可用（vs ta-lib-bin 0.4.26 無 Windows wheel）

### Sprint 1 Day 2-3 Bundle 實作（commit `ed3a987`）

- `engines/zipline_adapter/bundles/finmind_bundle.py`（~270 LOC）— Zipline bundle protocol 完整實作，`register('finmind', ..., calendar_name='XTAI')`，`zipline ingest -b finmind` 可跑通
- `engines/zipline_adapter/bundles/parquet_cache.py`（~90 LOC）— `cached_or_fetch()` 短路 FinMind API，100 stocks × 7 年從 2100 req 降到 < 7/day（緩解 plan R2 風險）
- 11 個單元測試覆蓋兩模組（涵蓋 missing-session ffill、cache hit/miss、universe resolution 三條鏈）

---

## 4. 後果

- **正面**：
  - 0 商業綁定 — CI 可完整跑 zipline 測試、新 contributor 0 摩擦
  - SQLAlchemy 2.x 升級獲免費（zipline-tej 想升要等 upstream fork 同步）
  - ADR-005 所有 Zipline 生態決策理由 100% 保留
  - M1 + Sprint 0 deliverable 0 重構
  - 移除 TEJ 商業關係依賴後，TEJ 仍可作為 ADR-006 的次要資料源（不阻塞主路徑）
- **負面**：
  - pandas / numpy 降版限制部分新版 API（實測 M1 既有程式碼 56 tests 全通過，無實質影響）
  - vectorbt 暫不可用 → ADR-007 雙引擎方案需重評向量化替代（候選：polars / numba 自寫 grid runner）
  - `requires-python <3.12` 限制延續
  - M2-M5 整套 plan 中所有「zipline-tej」「TQuant-Lab」字樣需訂正（本 PR 後續 commits 處理）
- **影響範圍**：
  - `backtest_platform/pyproject.toml`：dependencies + extras 改寫，mainframe extra 從 `zipline-tej>=2.0` 改 `zipline-reloaded==3.0.4`，sprint0→sprint1，engines 中 vectorbt 暫停
  - `backtest_platform/src/backtest_platform/engines/zipline_adapter/`：新模組目錄（bundle 實作 ~360 LOC）
  - `backtest_platform/tests/engines/zipline_adapter/`：11 個單元測試
  - ADR-005：標 superseded 指向本 ADR
  - ADR-007：dual-engine vectorbt 半邊 pending（M3 grid/WFA 評估替代方案，可能另開 ADR-014）
  - 後續 doc sweep：17（M2 master plan）/ 18（reference architecture）/ 21（data contract）/ 08（project structure）/ 22（test strategy）/ 02（PRD）/ 05（architecture）/ 16（WBS）/ INDEX
- **重新評估觸發**：
  - zipline-reloaded 後續版本破壞性變更（如 pandas 2.x 解鎖）→ 升版重評約束放鬆
  - vectorbt 替代方案 M3 評估失敗 → ADR-007 修訂或退回單引擎
  - zipline-reloaded 維護中斷 / 1 年以上無 release → 啟動 v2.0 退場路線（自寫 event-driven）

---

## 5. 執行計畫

1. ✓ **Sprint 1 Day 1**（commit `d31044a`）— pyproject swap + Gate verification（2 gates + regression）
2. ✓ **Sprint 1 Day 2-3**（commit `ed3a987`）— FinMind bundle + parquet cache 模組 + 11 單元測試
3. ✓ **本 ADR**（本 commit）— 正式記錄 pivot 決策、ADR-005 加 superseded banner
4. **同分支後續 commits** — doc sweep 兩輪（Telegram→Discord、zipline 訂正）+ data contract 對齊 bundle 實作 + WBS 進度更新
5. **Sprint 1 Day 4+** — 第一個 zipline algorithm hello-world（把 M1 strategy 純函式串到 `zipline.api.order_target`）
6. **M3** — vectorbt 替代方案評估（polars-backed grid runner / numba JIT），視結果可能補 ADR-014

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-01 | Self | 初版 — 取代 ADR-005 主骨架選擇；Sprint 1 Day 1-3 Gate 全綠後落定 |
