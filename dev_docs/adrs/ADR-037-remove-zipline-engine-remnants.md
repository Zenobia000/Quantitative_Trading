# ADR-037: 移除 zipline 引擎殘骸 — sim 為唯一引擎，engines/ 樹刪除

> **狀態：** 已接受 | **日期：** 2026-07-03 | **決策者：** Self
> **Supersedes：** [ADR-013](./ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md)（zipline-reloaded 為 M2 主骨架的角色廢止）；連帶 [ADR-014](./ADR-014-zipline-reloaded-3-1-1-upgrade-reverses-adr-013-constraints.md)（3.1.1 升級約束解除）之對象已不存在
> **相關：** [ADR-007](./ADR-007-dual-engine-zipline-vectorbt.md)（雙引擎方案的 vectorbt 半邊）、[ADR-027](./ADR-027-strategy-contract-and-registry.md)（策略契約 + registry — 上層改以 `get_strategy(name).run()` 派發，不再經 engine Protocol）、[ADR-035](./ADR-035-datafeed-seam-realtime-deferred.md)（DataFeed 讀取層 seam）

---

## 1. 背景與問題

ADR-013 於 2026-06-01 選定 `zipline-reloaded` 為 M2 event 回測主骨架，並自寫 FinMind → zipline bundle（`engines/zipline_adapter/`），ADR-014 隨後升 3.1.1 解除 pandas<2 等約束。然而平台此後的實際演進路線**未走 zipline event 引擎**：研究迴圈主力落在離線 close-to-close **sim**（`strategies/four_layer_resonance/sim.py` + `research.is_harness`）與橫斷面 panel runner；策略派發於 ADR-027 改走**策略契約 + registry**（`get_strategy(name).run()`），不再經 engine Protocol。

2026-07-02 全平台審查確認：`engines/` 樹的 zipline 路徑實質為**stub / 不可達**——

- `engines/protocol.py` 的 `get_engine()` **零 production 呼叫**；`zipline` / `vectorbt` 成員是只會 `raise NotImplementedError` 的 `_StubEngine` 佔位。
- `engines/zipline_adapter/`（algorithms / cli / controls / validation）僅由 `engines/__init__` 與 `tests/engines/` 自我引用，無任何上層 production 進入點。
- 整棵 `engines/` 約 **2271 LOC**，加上 `zipline-reloaded==3.1.1` 這個重量級依賴（連帶 statsmodels / tables / networkx 等傳遞依賴），全為死重。

唯二**production 可達**的檔案是資料層、非引擎層：

- `engines/zipline_adapter/bundles/parquet_cache.py` — 被 `adapters/data_feed/eod_parquet.py` 引用（EOD 讀取）。
- `engines/zipline_adapter/bundles/finmind_bundle.py` 的 `ingest_universe` — 被 `orchestration/collaborators.py` ingest 路徑引用。

這兩者放在 `engines/zipline_adapter/bundles/` 是 ADR-013 bundle 設計的歷史殘留；它們本質是**資料層**（parquet 快取讀取 + FinMind 批次 ingest），與 zipline event 引擎無關。

---

## 2. 考量的選項

### 選項一：維持現狀（engines/ 樹保留）
- **描述**：保留 stub 引擎與 zipline bundle 程式碼，等未來或許重啟 event 引擎。
- **缺點**：2000+ LOC 死碼 + 一個重量級依賴長期掛在依賴樹與 CI；`docs/17` 等文件仍寫「zipline 主骨架」誤導新人；stub 的 `NotImplementedError` 路徑是隱形陷阱。**拒絕。**

### 選項二（★採納）：刪除 engines/ 樹 + mainframe extra，兩個資料層檔案下放 data/
- **描述**：整棵 `engines/` 與 `tests/engines/` 刪除、`get_engine`/`SimEngine`/`_StubEngine`（`engines/protocol.py`）刪除；`parquet_cache.py` 與 `finmind_bundle.py` 的**資料層部分**下放 `data/`（它們是資料層而非引擎層）；`finmind_bundle.py` 的 zipline bundle-writer callback（`finmind_to_bundle` / `ensure_registered` / daily-frame 正規化）隨 zipline 一併刪除，只留 `ingest_universe` ingest 路徑；`pyproject.toml` 移除 zipline-reloaded。
- **優點**：2000+ LOC + 一個重量級依賴移除；sim 成為文件與程式碼一致的唯一引擎；資料層檔案回到正確目錄。**採納。**

### 選項三：連 exchange-calendars 一併移除
- **描述**：mainframe extra 打包了 `zipline-reloaded` + `exchange-calendars`，整包移除。
- **缺點**：`exchange-calendars` **不是** zipline 殘骸——它是 `runtime/trading_calendar.py`（after-close 排程的交易日曆閘門）的**live** 依賴，提供精確 XTAI 假日日曆（春節 / 掃墓等浮動日）。移除會使排程永久退化為週一至五近似，平日國定 / 農曆假期誤判為交易日（年約 10–15 天假告警來源）。**拒絕（見 §4 保留決策）。**

---

## 3. 決策

**採納選項二。**

1. **刪除** `engines/`（含 `protocol.py` 的 Engine Protocol / SimEngine / get_engine / _StubEngine、`zipline_adapter/` 全部）與 `tests/engines/` 全部。
2. **下放** 兩個資料層檔案（保留 git 歷史）：
   - `engines/zipline_adapter/bundles/parquet_cache.py` → `data/parquet_cache.py`（原樣）。
   - `engines/zipline_adapter/bundles/finmind_bundle.py` → `data/finmind_bundle.py`（**僅**保留 `ingest_universe` + universe/cache 解析 + `UniverseIngestResult` + `DEFAULT_UNIVERSE` re-export；刪除 zipline bundle-writer callback），並修正兩個 importer（`adapters/data_feed/eod_parquet.py`、`orchestration/collaborators.py`）與測試。
3. **`pyproject.toml`**：移除 `zipline-reloaded==3.1.1`（`mainframe` extra + `sprint1` extra）。`mainframe` extra 更名為 `calendar`（其唯一剩餘用途是 `exchange-calendars` XTAI 日曆）。`uv lock` 同步（連帶移除 statsmodels / tables / networkx 等 zipline 傳遞依賴）。
4. **metadata 保留**：`RunConfig.engine` 欄位與 runs DDL `engine` 欄保留（歷史 run 的 `engine='zipline'` 值仍可讀）；相關註解更新為「sim（zipline/vectorbt removed 2026-07-03, ADR-037）」。
5. **loader seam 保留**：未來要重加 event 引擎，是在 `research.is_harness` 的 `loader` seam 後新增一個 adapter，而非復活本次刪除的模組。

---

## 4. 影響與後果

### 4.1 正面
- **~2271 LOC（engines/）+ 對應 tests 移除**；一個重量級依賴（zipline-reloaded 及其傳遞依賴）從依賴樹與 CI 移除。
- sim 成為文件與程式碼一致的唯一引擎；`engines.protocol` 的 `NotImplementedError` stub 陷阱消失。
- `parquet_cache` / `finmind_bundle` 回到 `data/`（正確的資料層歸屬）。

### 4.2 exchange-calendars 保留（審查前提修正）
2026-07-02 審查前提假設「engines/ 移除後無物使用 zipline/exchange_calendars（僅 validation 測試會）」——此假設對 **exchange-calendars 錯誤**。`runtime/trading_calendar.py`（production；`orchestration/after_close.py` / `api/deps.py` / `research/watch_registry.py` 引用）以 lazy try/except 使用 `exchange_calendars.get_calendar("XTAI")` 提供精確日曆，無則降級週一至五近似。故 **exchange-calendars 保留**，僅移除 zipline-reloaded；`mainframe` extra 更名 `calendar` 誠實反映其唯一剩餘用途。安裝指令由 `uv sync --extra mainframe` 改為 `uv sync --extra calendar`。

### 4.3 破壞性變更
- extra 更名 `mainframe` → `calendar`：既有以 `--extra mainframe` 安裝的腳本 / 文件需改 `--extra calendar`（本 PR 已更新 `runtime/trading_calendar.py` docstring、`deploy/README.md`、`dev_docs/14`）。`legacy/spikes/*` 的 POC RUNBOOK 為歷史封存，不更新。
- 上層若有殘留 `import backtest_platform.engines...`：本 repo 已審計為零（唯二 importer 已改指 `data/`）。

### 4.4 受影響模組
`engines/`（刪）、`tests/engines/`（刪）、`data/parquet_cache.py`（新）、`data/finmind_bundle.py`（新）、`adapters/data_feed/eod_parquet.py`、`orchestration/collaborators.py`、`config/universe.py`、`data/bundle_registry.py`、`config/settings.py`、`research/is_harness.py` / `strategies/four_layer_resonance/sim.py`（back-compat 註解）、`pyproject.toml`、`uv.lock`、`docker/timescaledb/init.sql`（engine 欄註解）、`runtime/trading_calendar.py` + `deploy/README.md`（extra 更名）。文件：INDEX、08、09、02、16、05/17 banner。

### 4.5 重新評估觸發
- 若重啟 event 引擎需求：在 `research.is_harness` 的 loader seam 後新增 adapter（不復活本模組）。
- `vectorbt`（`engines` optional extra）於 engines/ 移除後亦不再被引用；本 ADR 未動該 extra（範疇聚焦 zipline），列為後續可清理項。

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-07-03 | Self | 初版 — 刪 engines/ 樹 + zipline-reloaded；sim 為唯一引擎；exchange-calendars 保留（審查前提修正）|
