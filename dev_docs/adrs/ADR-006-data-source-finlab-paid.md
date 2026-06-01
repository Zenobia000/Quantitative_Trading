# ADR-006: 資料源切換為付費 FinLab（FinMind 為 fallback）

> **狀態：** 已接受 | **日期：** 2026-05-31 | **決策者：** Self

---

## 1. 背景與問題

- **上下文**：M1 ETL 已交付（`data/finmind_etl.py`, 308 LOC）使用 FinMind 免費版；策略需要券商分點細項、三大法人、籌碼、財報等深度資料才能驗證 4-layer 共振假設。
- **問題**：
  - FinMind 免費版缺券商分點細項，M1 訊號層相關欄位以零值佔位
  - 缺欄位導致 4-layer 訊號中「籌碼面」幾乎廢半邊
  - 自寫 ETL 整合多個免費源（FinMind + TWSE + 公開資訊觀測站）= 持續維護負擔
  - 使用者已明確表達：願意花錢買資料，不想自己 maintain ETL
- **驅動因素 / 約束**：
  - 必須能補齊 4-layer 訊號所需全部欄位（籌碼、財報、技術、價格）
  - 必須與 Zipline bundle 介面相容（見 ADR-005）
  - 必須有 fallback 路徑（廠商倒閉 / 漲價時不能停擺）
  - 預算上限 ~10k TWD / 年
  - 三模式（backtest/paper/live）資料源切換成本要低

---

## 2. 考量的選項

### 選項一：維持 FinMind 免費版
- **描述**：保留 M1 既有 ETL，缺欄位以零值或代理變數補
- **優點**：零成本、M1 既有 308 LOC 直接用
- **缺點**：
  - 籌碼面訊號半廢，4-layer 共振假設無法完整驗證
  - 即時資料需另接（FinMind 即時 API 受限）
  - 無 Shioaji 原生整合
- **成本/複雜度**：低（但效益受限）

### 選項二：FinMind sponsor 方案
- **描述**：贊助 FinMind 升級到 sponsor 帳號取得進階資料
- **優點**：與既有 M1 ETL 相容、成本低
- **缺點**：
  - sponsor 等級資料仍不如 FinLab 完整（無券商分點）
  - 無 Shioaji 原生整合
  - 無即時 quote 串流
- **成本/複雜度**：低

### 選項三：TEJ API
- **描述**：採購 TEJ 官方 API（學術 / 商用版）
- **優點**：資料品質最高、與 TQuant-Lab 同源
- **缺點**：
  - 個人版年費 > 30k TWD，超出預算
  - SDK 相對封閉，社群範例少
  - 與 Shioaji 整合須另寫
- **成本/複雜度**：高（成本超標）

### 選項四：FinLab VIP（年費 ~9-10k TWD）+ FinMind 為 fallback ★採納
- **描述**：主資料源 FinLab VIP 付費版（5GB/月流量，含三大法人、券商分點、籌碼、財報），缺欄位由 FinMind 補；歷史回填一次性寫入 Zipline bundle，日增量打 API
- **優點**：
  - 5GB/月流量足夠日增量 + 一次性歷史回填
  - **原生整合 Shioaji**（FinLab SDK 已有 broker 接口範例）
  - 資料涵蓋：三大法人、券商分點、籌碼分布、財報、技術指標、即時 quote
  - 與 TQuant-Lab Zipline bundle 機制相容
  - 預算 ~9-10k TWD 內
  - 缺欄位可用 FinMind 補齊（雙源互補）
- **缺點**：
  - 5GB/月流量上限 → 緩解：一次性歷史回填寫 Zipline bundle 永久本地，Grafana 監控流量
  - 廠商鎖定風險 → 緩解：FinMind bundle 為 fallback，已驗證可工作
  - 黑盒 schema → 緩解：用 Pydantic `data/schemas.py` 在 adapter 邊界驗證
- **成本/複雜度**：低

---

## 3. 決策

**選擇：選項四（FinLab VIP 為主 + FinMind 為 fallback）**

**理由**：
- 唯一同時滿足「籌碼面完整」「Shioaji 原生整合」「預算內」「有 fallback」四項硬約束
- FinLab 5GB/月流量配合「歷史回填寫 bundle 永久本地」策略後，實際長期消耗只有日增量（< 100MB/月）
- 雙源策略（FinLab + FinMind）讓單一廠商風險降至可接受
- **不採用 `finlab.sim()` 當引擎**（黑盒 + 精度爭議 + 7 訊號優先序表達困難），只用其資料
- 詳見 plan `C:\Users\xdxd2\.claude\plans\maintain-calm-blossom.md` § 2 與風險表

---

## 4. 後果

- **正面**：
  - 4-layer 共振策略訊號層 100% 補齊（籌碼面活化）
  - M4-M5 實盤接 Shioaji 從「自寫」降至「抄 FinLab + TEJ 範例」
  - 即時 quote 與歷史資料同源，paper / live 模式切換成本低
- **負面**：
  - 年度固定支出 ~10k TWD
  - 5GB/月流量需主動監控（Grafana 面板 G，見 ADR-009）
  - 資料 schema 隨 FinLab 改版可能需修改 adapter
- **影響範圍**：
  - `adapters/data_bundle/finlab_bundle.py`（新增 ~150 LOC，主路徑）
  - `adapters/data_bundle/finmind_bundle.py`（新增 ~80 LOC，包裝 M1 ETL 為 fallback）
  - `adapters/data_feed/finlab_live.py`（新增 ~100 LOC，即時資料 polling）
  - `data/finmind_etl.py`（M1 既有，保留作 fallback 路徑，0 改動）
  - `monitoring/`（新增 FinLab 流量 metric emitter）
- **重新評估觸發**：
  - FinLab 漲價 > 20% / 年 → 評估降級 sponsor 或自寫多源 ETL
  - FinLab 5GB/月流量穩定超限 3 個月 → 評估升級或重新設計 bundle 策略
  - FinLab 停止服務 → 切 FinMind fallback bundle，缺欄位重新評估訊號權重
  - FinMind 與 FinLab 同欄位資料差異 > 1% 持續 → 啟動資料品質審查

---

## 5. 執行計畫

1. **Sprint 0（W1）**：S3（FinLab bundle POC 拉 10 檔 1 年）+ S5（即時資料 polling 1 檔 60 秒）spike 必須全綠
2. **M2 W1**：採購 FinLab VIP 年訂閱、設定 API key 至 `.env`（不入 git）
3. **M2 W2**：撰寫 `adapters/data_bundle/finlab_bundle.py`（FinLab → Zipline bundle ingester）
4. **M2 W3**：一次性歷史回填 2015-2024 全市場日線資料寫入 Zipline bundle
5. **M2 W4**：撰寫 `adapters/data_bundle/finmind_bundle.py` 包裝 M1 ETL 為 fallback bundle
6. **M3 W1**：`adapters/data_feed/finlab_live.py` 即時資料 polling 接入 paper broker
7. **M4 W1**：Grafana 面板 G（API quota 監控）上線，FinLab 流量低於 500MB/月剩餘時 Discord High 告警（見 ADR-010）
8. **PRD 同步**：`dev_docs/02_project_brief_and_prd.md` 資料源章節由 FinMind 改為 FinLab（FinMind 標 fallback）

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-31 | Self | 初版 |
