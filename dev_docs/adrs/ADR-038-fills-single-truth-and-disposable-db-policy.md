# ADR-038: fills 為單一成交真相源 + 可拋式 DB schema 政策 — schema 收斂，砍 8 張零 IO / 反轉表

> **狀態：** 已接受 | **日期：** 2026-07-03 | **決策者：** Self
> **相關：** [ADR-002](./ADR-002-timescaledb-for-time-series.md)（TimescaleDB 選型）、[ADR-036](./ADR-036-pod-sleeve-portfolio-gate.md)（pod/sleeve 多策略架構；per-sleeve P&L 開放項）、[ADR-021](./ADR-021-unify-rest-contract-into-single-doc-and-openapi.md)（Monitor 端點 typed-empty 契約）、[ADR-012](./ADR-012-adopt-uv-package-manager.md)（dev 環境）

---

## 1. 背景與問題

一次 schema IO 稽核（先於本 ADR 完成、已驗真實讀寫路徑）揭露 TimescaleDB `init.sql` 的 15 張表中有大量**零 IO 死表**與一組**寫讀反轉**，dev 模式（資料可拋、`docker compose down -v` 重建、無 backfill/向後相容需求）下這是純負債。

### 1.1 orders / fills 真相反轉（核心缺陷）

`fills` 表原本設計為成交回報的專表，但實際：

- **`fills` 表零讀取者**——沒有任何 reader SELECT 它。
- **`orders` 表唯一寫入者是 `upsert_fills` 的雙寫**——`upsert_orders` 除該雙寫外零生產呼叫者（僅整合測試呼叫）。`upsert_fills` 把每筆成交寫成一列 `status='filled'` 的 `orders`（給 `/monitor/fills` 讀）＋一列 `fills`（承載 commission/tax/slippage_bps），兩列以 client 端 uuid4 `order_id` 互聯。

結果：**成交的真相被寫進 `orders`（本該是訂單生命週期表），`fills`（本該是成交專表）反而沒人讀**。這是本末倒置——`fills` 才該是成交的單一真相源。

### 1.2 positions 表讀而不寫 → `/monitor/positions` 永遠空白

`db_reader.open_positions`（餵 `GET /monitor/positions`）SELECT `positions` 表，但**生產流程從不寫 `positions`**（只有測試呼叫 `upsert_positions`）。GUI 部位頁因此**永遠空白**——一個真實但沉默的 bug。真相其實在成交日誌裡（`load_broker_state` 已在用「摺疊 fills」重建部位），`open_positions` 卻走了一張沒人寫的表。

### 1.3 migrations 無 runner + 六張零 IO 表

- `docker/timescaledb/migrations/`（002/003/004）**無任何 runner 執行**：只有 `init.sql` 經 `docker-entrypoint-initdb.d` 跑；三個 migration 的 end-state 早已併入 `init.sql`。它們是 drift 溫床（002 還帶著 ADR-028 前的 `preset` 欄）。
- 六張表生產零 INSERT/SELECT：`trades`（M1 legacy）、`validation_runs`（結果實存 JSONL validation_store）、`risk_metrics`（circuit_breaker 純記憶體）、`data_quality_log`、`alerts`（discord_notifier 直接發送、不入庫）、`universe`（來自 parquet/config）。

### 1.4 per-sleeve P&L 被 orders 缺 strategy_id 卡住（ADR-036 §3.4 開放項）

ADR-036 pod/sleeve 架構明列 per-sleeve P&L 歸因為「第二艙位前置」，卡在成交記錄無 `strategy_id`（原 `orders`/`fills` 皆無策略辨識欄）。`load_broker_state` 的 LIMITATION 註解也記著「orders 無 strategy_id → 只能 portfolio-wide 摺疊」。

---

## 2. 考量的選項

### 選項一：維持現狀（雙寫 orders + 死表全留）
- **缺點**：`fills` 永遠死、`orders` 語意錯置、`/monitor/positions` 永遠空、8 張死表持續累積 drift、per-sleeve P&L 永遠卡住。dev 模式下無任何向後相容價值可換。**拒絕。**

### 選項二：補寫 positions 表 + 保留 orders 雙寫
- **描述**：讓生產流程真的寫 `positions`，`open_positions` 就有資料；orders 雙寫照舊。
- **缺點**：新增一條與「摺疊 fills」重複的部位真相源（雙真相 → 對帳負擔），且沒解決 orders/fills 反轉與死表。**拒絕。**

### 選項三（★採納）：fills 為單一成交真相源 + init.sql 單一真相 dev 政策
- **描述**：`fills` 成為唯一成交儲存（加 `strategy_id`）；`open_positions` / `load_broker_state` / `recent_fills` 全部改讀/摺疊 `fills`；`orders`+`positions`+ 六張零 IO 表一併砍除，待真實 producer 落地再回歸。`init.sql` 為 schema 單一真相源，schema 變更＝改 `init.sql` + `docker compose down -v` 重建。
- **優點**：一次解掉反轉、空白頁 bug、死表 drift、per-sleeve P&L 卡點；dev 模式零遷移成本。**採納。**

---

## 3. 決策

**採納選項三。**

### 3.1 fills = 單一成交真相源

- `fills` 新增 `strategy_id TEXT NOT NULL` + index `(strategy_id, fill_time DESC)`，解鎖 per-sleeve P&L（ADR-036 §3.4）。
- `db_writer.upsert_fills` 由「雙寫 orders + fills」改為**單一 append-only INSERT into `fills`**。`order_id` 保留為 client 端 uuid4 產生的**邏輯事件 id**（連結成交到產生它的訂單意圖；欄位仍 NOT NULL），不再代表一張 `orders` 表的列。刪除 `upsert_orders` + `_ORDERS_COLS`。
- `signal_id` 維持 plain 欄（非 FK）：TimescaleDB 2.x 拒絕指向 hypertable 的 FK，`fills`/`signals` 皆 hypertable，連結在應用層維護、可攜至 managed Postgres。

### 3.2 讀取全部改讀 fills

- `recent_fills`（`/monitor/fills`）：SELECT `fills`（fill_time/stock_id/side/fill_quantity/fill_price）；`fills` 無 `status` 欄 → reader 恆發常數 `'filled'` 保 FE `FillRow` shape 不變（無 openapi churn）。
- `open_positions`（`/monitor/positions`，**修真實 bug**）：改為對 `fills` 依 (strategy_id, stock_id) 時序摺疊（重用 `reconstruct_positions` 的加權平均邏輯），回傳 FE `PositionRow` shape（stock_id/quantity/entry_price/stop_loss=None/opened_at/strategy_id）。空白頁自此顯示真實部位。
- `load_broker_state`（#155 跨日部位還原）：摺疊來源由 `orders` 改 `fills`，且新增 `strategy_id` 過濾（欄位存在後 scope 到策略，解除舊「portfolio-wide only」限制）。

### 3.3 砍 8 張表（init.sql）

| 砍除 | 理由 | 回歸時機 |
| :--- | :--- | :--- |
| `orders` | 唯一寫入者是 fills 雙寫；語意錯置 | **M5**：真實 broker 訂單生命週期 |
| `positions` | 讀而不寫；真相在成交日誌 | 有真實 producer 時（或維持 fills 摺疊） |
| `trades` | M1 legacy，零 IO | 有需求時 |
| `validation_runs` | 結果實存 JSONL validation_store | 有需求時 |
| `risk_metrics` | circuit_breaker 純記憶體 | 有需求時 |
| `data_quality_log` | 零 IO | 有需求時 |
| `alerts` | discord_notifier 直接發送 | 有需求時 |
| `universe` | 來自 parquet/config | 有需求時 |

存活 7 張：`daily_bars` / `institutional_flows` / `broker_chips` / `runs` / `equity_snapshots` / `signals` / `fills`。

### 3.4 init.sql 單一真相 dev 政策 + 刪 migrations/

- 刪除 `docker/timescaledb/migrations/`（002/003/004）：無 runner、end-state 已在 init.sql。
- **dev-mode schema 政策**：`init.sql` 是 schema 的唯一真相源；schema 變更＝改 `init.sql` + `docker compose down -v` 重建。migrations 只在有**需保留的生產資料**時回歸。

### 3.5 runs FK backfill 明確不做

telemetry hypertables → `runs(run_id)` 的 FK 技術上可行（`runs` 是 plain 表），但 paper-chain 的 run_id 無 `runs` 父列（`make_db_sink` 從不寫 `runs`），app 層連結維持不變，待 paper chain 會 upsert 一筆 `runs` stub 時再議（見 21 §4.2b）。

---

## 4. 影響與後果

### 4.1 正面

- **per-sleeve P&L 解鎖**：`fills.strategy_id` 落地，ADR-036 §3.4 開放項消除。
- **`/monitor/positions` 顯示真實資料**：修掉「永遠空白」的沉默 bug。
- **少 8 張死表 + 刪無 runner 的 migrations**：drift 面積大減、schema 一眼可讀。
- **成交真相歸位**：`fills` 成為唯一成交儲存，語意正確。

### 4.2 破壞性變更

- **任何持有既有 docker volume 者必須 `docker compose down -v` 重建 DB**（dev 模式資料可拋，無 backfill）。舊 volume 內含被砍表不會自動移除，但 app 已不觸碰它們。
- `db_writer.upsert_orders` / `upsert_positions` 移除：任何呼叫者需改走 `upsert_fills`（生產零呼叫者，僅測試受影響、已同 PR 更新）。
- `fills.order_id` 語意由「指向 orders 列」改為「邏輯事件 id」；`fills.strategy_id` NOT NULL — 寫入者必須供給（`make_db_sink._fill_row` 已接線）。

### 4.3 受影響模組

`docker/timescaledb/init.sql`（7 表）、`data/db_writer.py`（upsert_fills 單寫 + strategy_id、刪 upsert_orders/upsert_positions）、`data/db_reader.py`（recent_fills/open_positions/load_broker_state 改讀 fills + `_fold_open_positions`）、`orchestration/collaborators.py`（`_fill_row` 串 strategy_id）、對應測試、`dev_docs/21`。回應 shape（`/monitor/positions`、`/fills`）不變 → 無 openapi churn。未觸 `runs` DDL（drift Check B 依賴）。

### 4.4 後續動作

- [ ] **M5**：真實 broker 訂單生命週期落地時，`orders` 表回歸（含 PENDING/SUBMITTED/FILLED 狀態機、broker_order_id 回填）。
- [ ] paper chain 若開始 upsert `runs` stub → 重議 telemetry → runs FK（§3.5 / 21 §4.2b）。
- [ ] 第二 paper 策略上線時，驗證 `open_positions(strategy_id=...)` per-sleeve 摺疊。
