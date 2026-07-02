# ADR-035: DataFeed 讀取層 seam — 現行 EOD parquet，realtime（XQ/Q）延後至滿足接入準則

> **狀態：** 已接受 | **日期：** 2026-07-02 | **決策者：** Self
> **相關：** [ADR-006](./ADR-006-data-source-finlab-paid.md)（FinLab 主資料源，EOD wide frames）、[ADR-008](./ADR-008-tri-mode-shared-strategy-code.md)（tri-mode 共用策略碼，含 Shioaji 實盤 M4-M5）、[ADR-032](./ADR-032-survivorship-universe-workflow.md)（survivorship universe 工作流）、[ADR-033](./ADR-033-paper-watch-tier.md)（零資本觀察艙收 live OOS）

---

## 1. 背景與問題

### 1.1 資料讀取路徑目前散落、且與 EOD 假設硬綁

平台目前所有價格資料的讀取都直接打 `engines/zipline_adapter/bundles/parquet_cache.py::ParquetCache`（load 三表 → `ETLBundle`）或更上層的 `research.is_harness.load_merged_parquet`。這些呼叫點**內建「資料是收盤後 parquet 批次」的假設**：沒有「最新報價」概念、沒有「這個來源支不支援即時」的能力旗標。

`src/backtest_platform/adapters/data_feed/__init__.py` 早在 M2 結構重組時就保留為套件位（0 bytes 空殼，見 [08 §空殼表](../08_project_structure_guide.md)），本意即為「未來 live feed 的落點」，但一直未定義介面 —— 於是「未來要接 realtime」這件事沒有一個穩定的縫。

### 1.2 realtime 是否現在做？—— CP 值不足

觀察艙（ADR-033）收 live OOS、after-close 排程器（`orchestration/after_close.py`）已落地，**當前運作模式明確是「盤後 EOD 批次」**：收盤後跑 forward paper session、算訊號、記帳，不需要盤中即時報價。真正需要 realtime feed 的情境是**實盤盤中下單**（ADR-008 Shioaji，M4-M5 才排），而：

- 現階段**無任何可部署 edge**（四結構同 ~0.9 Sharpe 牆，見 16 WBS），沒有策略需要盤中執行；
- realtime 接入（XQ 訊號流 / Q 券商報價）牽涉行情授權、連線維運、盤中錯誤處理，工程成本高；
- 在「沒有 edge、沒有實盤」的當下投入 realtime，是典型的 premature infrastructure。

但**若不現在定義 seam**，未來接 realtime 時每個讀取點都要改，且無處掛「能力旗標」讓呼叫端分流 batch/streaming —— 會重演 §1.1 的散落問題。

---

## 2. 考量的選項

### 選項一：現在就實作 realtime feed（XQ/Q 接入）
- **缺點**：§1.2 —— 無 edge、無實盤需求，行情授權/連線維運成本高，premature。**拒絕。**

### 選項二：什麼都不做，維持直接呼叫 parquet_cache
- **缺點**：未來接 realtime 時無穩定介面，每個讀取點都要改；「支不支援即時」無處表達。把已知的未來成本推給未來、且更貴。**拒絕。**

### 選項三（★採納）：現在只定義 seam（Protocol + 一個 EOD 具體實作），realtime 延後
- **描述**：定義小而穩定的 `DataFeed` Protocol（`get_daily_bars` / `get_latest_prices` / `supports_realtime` 能力旗標），並提供唯一具體實作 `EODParquetFeed`（薄封裝既有 `ParquetCache`，`supports_realtime=False`）。**不改接任何既有呼叫點** —— seam 存在的目的是「未來 realtime 落在穩定介面後」，不是現在就切換。
- **優點**：以極小成本（<100 行 + 一個 Protocol）鎖定未來 realtime 的落點；能力旗標讓呼叫端可分流 batch/streaming；不 premature 實作 realtime；不動既有路徑（零回歸風險）。**採納。**

---

## 3. 決策

**採納選項三。** 在 `adapters/data_feed/` 定義讀取層 seam，realtime 延後。

### 3.1 `DataFeed` Protocol（`adapters/data_feed/base.py`）

結構型 `typing.Protocol`（`@runtime_checkable`），只宣告消費端真正需要的最小面：

| 成員 | 意義 |
| :--- | :--- |
| `supports_realtime: bool` | 能力旗標 —— 是否能供盤中/串流報價（EOD feed 為 `False`）|
| `get_daily_bars(symbols, start, end) -> DataFrame` | 區間日線 OHLCV（long-format，無資料的 symbol 自然缺席，全無 → 空 frame）|
| `get_latest_prices(symbols) -> dict[str, float]` | 每檔最新收盤（缺料 symbol 略過）|

刻意保持**小**：這是縫，不是框架。未來 realtime 若需要 order-book / tick 級介面，另立擴充 Protocol，不把 `DataFeed` 撐大。

### 3.2 唯一具體實作 `EODParquetFeed`（`adapters/data_feed/eod_parquet.py`）

薄 adapter（<100 行）：所有 IO 委派給既有 `ParquetCache`，只把 per-symbol `ETLBundle` 重塑成區間/最新兩個視圖。`supports_realtime = False`（盤後 EOD 批次為運作模式）。**不 rewire 任何既有呼叫點** —— 既有 caller 仍直接用 `ParquetCache` / `load_merged_parquet`，`EODParquetFeed` 純為未來 realtime 預留的介面示範與落點。

### 3.3 realtime（XQ / Q）接入準則 —— 滿足才做

以下條件**全部**成立時，才實作第二個 `DataFeed`（如 `XQRealtimeFeed` / `QBrokerQuoteFeed`，`supports_realtime=True`）：

1. **存在可部署 edge**（過真偽閘 DSR ≥ 0.95 或觀察艙重評後晉升），且該 edge 的執行**需要盤中報價**（非盤後批次可滿足）；
2. **進入實盤階段**（ADR-008 Shioaji M4-M5 下單鏈路就緒）；
3. 行情來源（XQ 訊號 / Q 券商報價）**授權與連線維運成本已評估可承擔**。

未滿足前，realtime 維持延後；`EODParquetFeed` 是唯一實作。

---

## 4. 影響與後果

### 4.1 受影響模組

- **新增**：`adapters/data_feed/{__init__,base,eod_parquet}.py`（seam + EOD 實作）。08 §空殼表 `data_feed` 由「空殼」改為「seam 已定義（design-only）」。
- **未觸**：`engines/zipline_adapter/bundles/parquet_cache.py`、`research/is_harness.py`、`orchestration/`、`runtime/` 等既有讀取點 —— 零 rewire、零回歸。

### 4.2 破壞性變更

**無。** 純新增套件內容，不改任何既有介面或呼叫點。既有測試、既有資料流不變。

### 4.3 後續動作

- [ ] realtime feed 實作 gated-on §3.3 三準則同時成立（可部署 edge + 實盤 + 行情授權）。
- [ ] 若未來將既有讀取點遷移到 `DataFeed` 介面，屬獨立重構（新 PR），本 ADR 不含該遷移。
