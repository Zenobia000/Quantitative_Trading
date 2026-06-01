# ADR-005: 主骨架選定 TQuant-Lab（Zipline 台股 fork）

> **狀態：** 已 superseded | **日期：** 2026-05-31 | **決策者：** Self
> **Superseded by：** [ADR-013](./ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md)
> — Sprint 0 S1 spike 揭露 zipline-tej import 階段 hard-code TEJ API call，
> 違反 ADR-005 § 1「免 TEJ key 仍可開發」隱含假設。改採 `zipline-reloaded`
> 主線 fork（0 商業綁定），ADR-005 所有 Zipline 生態技術理由（XTAI calendar、
> event-driven、bundle 機制、Shioaji 介接路徑）於 ADR-013 完全保留。
> **Supersedes：** ADR-001（rqalpha 主引擎角色廢止）

---

## 1. 背景與問題

- **上下文**：M1 已交付 962 LOC（資料 + 策略純函式），`engines/` 與 `validation/` 仍為空骨架；M2 必須鎖定主回測引擎並啟動端到端整合。
- **問題**：原 PRD 表 4.1（`dev_docs/02_project_brief_and_prd.md`）與 ADR-001 規劃 rqalpha 為主引擎，但前次調研（`dev_docs/research_open_source_backtest_platforms.md`）已揭示 rqalpha **無台股 mod、無 Shioaji broker、無 XTAI 交易日曆**，自寫 `mod_taiwan_stock` + broker 整合成本估計超過 1500 LOC，且無法重用業界 7 層 reference 架構。
- **驅動因素 / 約束**：
  - 必須支援台股交易日曆（XTAI）、T+1、漲跌停、整股單位、手續費 / 證交稅
  - 必須能 plug 進付費 FinLab 資料源（見 ADR-006）
  - 必須能 plug 進 Shioaji 實盤 broker（M5 目標）
  - 必須天然支援 7 訊號優先序（event-driven）
  - 單人開發節奏：17 週首版上線，自寫程式碼控制在 ~2500 LOC
  - M1 既有 962 LOC 不能浪費，必須 0 重構搬遷

---

## 2. 考量的選項

### 選項一：維持 ADR-001 原方案（rqalpha 主 + 自寫 mod_taiwan_stock）
- **描述**：依原 PRD 規劃，rqalpha + 自訂 mod 處理台股場景
- **優點**：rqalpha 中文文檔豐富、A 股社群成熟
- **缺點**：
  - 無台股交易日曆，需自寫 ~300 LOC
  - 無 Shioaji broker，需從零實作 ~600 LOC
  - 無業界 7 層 reference 對應（rqalpha 是 A 股導向，不是業界標準）
  - 2024 後維護減緩
- **成本/複雜度**：高（~1500 LOC 自寫 + 學習曲線）

### 選項二：自建 Adapter Framework（Hybrid 路線）
- **描述**：抽象 Engine/Broker/DataFeed 介面，自寫薄殼接 vectorbt + Shioaji
- **優點**：完全可控、無上游依賴
- **缺點**：
  - 7 層 reference 全部要自寫（L1-L7）
  - 自寫 portfolio engine、order management、slippage model = reinvent the wheel
  - 6-8k LOC、22 週工期
- **成本/複雜度**：極高

### 選項三：FinLab-Native（用 finlab.sim 當引擎）
- **描述**：直接用 FinLab SDK 跑回測 + 實盤
- **優點**：14 週可上線、整合最快
- **缺點**：
  - 黑盒、精度爭議（社群多次反映 fill 模型不透明）
  - 7 訊號優先序在 vectorized API 內難以表達
  - 廠商深度鎖定，倒閉 / 漲價時無退路
  - 流量上限制約歷史回測規模
- **成本/複雜度**：低（但鎖定風險極高）

### 選項四：TQuant-Lab 主骨架 + vectorbt 副引擎 ★採納
- **描述**：以 TEJ 維護的 TQuant-Lab（Zipline 台股 fork, MIT, 84 stars）為 L1-L6 主骨架，M1 純函式 plug 為 Zipline Algorithm；vectorbt 作副引擎跑 grid/WFA（細節見 ADR-007）
- **優點**：
  - Zipline 是業界 7 層 reference 最經典實作（Quantopian 遺產，LEAN/Nautilus 設計師都讀過）
  - **內建 `exchange_calendar_xtai`**（其他框架沒有）
  - TEJ 官方 repo `tejtw/TEJAPI_Python_Medium_Application` 有 **Shioaji 整合範例**，M4-M5 實盤幾乎 0 自寫
  - MIT 授權、純 Python、可任意 fork
  - L1-L7 模組（Data Bundle / Pipeline / Algorithm / Portfolio / Risk / Broker / Reporting）全部就位
  - Event-driven 天然支援 7 訊號優先序
  - 自寫程式碼 ~2500 LOC，工期 17 週
- **缺點**：
  - TQuant-Lab 上游社群小（84 stars）→ 緩解：Zipline 本體 17k stars，TQuant-Lab 只是台股 patch，可 fork 到自己 repo 不依賴 upstream
  - Zipline API 學習曲線 1-2 週
- **成本/複雜度**：中

---

## 3. 決策

**選擇：選項四（TQuant-Lab 主骨架 + vectorbt 副引擎）**

**理由**：
- 唯一能同時滿足「業界 reference 對齊」「台股場景天然支援」「Shioaji 實盤路徑現成」「M1 程式碼 0 重構」四項硬約束的方案
- Zipline 是 event-driven 標竿實作，7 訊號優先序在 `handle_data` 內天然成立
- TEJ 已驗證 Shioaji 整合可行，M5 實盤從「自寫 600 LOC」降至「抄範例改 150 LOC」
- 與付費 FinLab 資料源（ADR-006）配對後，L1 資料層僅需寫 ~150 LOC bundle ingester
- 詳見 plan `C:\Users\xdxd2\.claude\plans\maintain-calm-blossom.md` § 2

---

## 4. 後果

- **正面**：
  - 業界 7 層架構一次到位（不是「想到才加」）
  - M1 既有 962 LOC 100% 保留、0 重構
  - 三模式（backtest/paper/live）共用同一份 strategy code（見 ADR-008）
  - 自寫程式碼從 6-8k 降至 2500 LOC
- **負面**：
  - 必須學 Zipline API（Algorithm / Pipeline / Blotter / Broker / Bundle）
  - TQuant-Lab upstream 若停更需自行 fork 維護
  - rqalpha 學習投資 → 沉沒成本（ADR-001 已廢止）
- **影響範圍**：
  - `engines/`（rqalpha_runner.py 廢止，改 zipline algorithm wrapper）
  - `strategies/four_layer_resonance/__init__.py`（新增 ~100 LOC Zipline algorithm）
  - 所有 M2-M5 排程（見 plan § 7）
- **重新評估觸發**：
  - Sprint 0 Spike S1/S2 fail（TQuant-Lab 安裝失敗 / M1 plug 失敗）→ 退回選項二 Hybrid
  - TQuant-Lab upstream MIT 撤回（法律不可能，但仍列為 trigger）→ fork 自維護
  - Zipline event-driven 在 portfolio 級回測 100 檔 × 10 年 > 30 分鐘 → 評估 backtrader 替代

---

## 5. 執行計畫

1. **Sprint 0（W1）**：S1（TQuant-Lab 安裝）+ S2（M1 純函式 plug）spike 必須全綠才晉升 M2
2. **M2 W1**：fork `tejtw/TQuant-Lab` 到自有 GitHub，pin commit hash 鎖版本
3. **M2 W2**：撰寫 `strategies/four_layer_resonance/__init__.py` Zipline Algorithm wrapper（~100 LOC）
4. **M2 W3**：對 2330 跑 1 年回測，與 M1 `pipeline.py` 訊號 diff < 0.1%
5. **M2 W4**：端到端 backtest mode（FinLab bundle → algorithm → output）跑通
6. **ADR-001 廢止公告**：在 ADR-001 header 補註 "Superseded by ADR-005"；rqalpha 不再採購學習資源
7. **回填 PRD**：`dev_docs/02_project_brief_and_prd.md` 表 4.1 主引擎欄位由 rqalpha 改為 Zipline (TQuant-Lab)

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-31 | Self | 初版；Supersedes ADR-001 |
