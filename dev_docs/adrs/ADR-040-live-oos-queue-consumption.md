# ADR-040: Live-OOS 佇列消費 — after-close 排程器改由「人為選取佇列」驅動 berth enrollment

> **狀態：** 已接受 | **日期：** 2026-07-03 | **決策者：** Self
> **建立於（builds on）：** [ADR-033](./ADR-033-paper-watch-tier.md)（Paper-Watch 零資本觀察艙 — ≤2 席 / 90 天 / one-shot / DSR band，本 ADR **不放寬**任一條款）、[ADR-039](./ADR-039-evaluation-profile-orchestration-layer.md)（候選池 + `live_oos_queue` 人為選取層 — 本 ADR 接上其消費端）
> **相關：** after-close 排程器（`orchestration/after_close.py`，enrollment 守門不改）
> **產品依據：** `rebuild_goal_spec_ai_requirements_2026-07-03.md` Goal 10（昂貴 paper/live OOS 只在人為選取後才跑）；`dev_docs/contracts/README.md` §7（佇列 ↔ watch_registry 關係）

---

## 1. 背景與問題

ADR-039 落地了 `live_oos_queue`（人為選取層）：候選池 `select-live-oos` 把一個候選寫進 append-only 佇列，帶勾選 audit（`selected_by` / `selection_reason` / `override`）。但當時佇列**只入列、不消費**——沒有任何機件把「queued 項」變成實際的 paper/live OOS 工作。

同時 ADR-033 的 after-close 排程器用 `watch_registry` 的 **enrollment 守門**決定「誰可以跑 paper」：一支策略沒有 active berth 就拒跑。但 berth 從哪來？當時唯一入口是**手動 CLI `watch enroll`**——與 Goal 10 要求的「候選池勾選 → 才跑昂貴驗證」這條產品旅程脫節。

Goal 10 的驗收要求：(1) 未被勾選的候選**不自動跑** paper replay；(2) 勾選帶 audit reason；(3) 佇列項連回 report / candidate / strategy；(4) expired/paused/completed 狀態可見。缺的是把佇列接到 `watch_registry` enroll 與 `paper_replay` 的**消費層**，以及佇列狀態機的推進。

---

## 2. 決策

### 2.1 新增 `research/live_oos_consumer.py` — 佇列是 berth enrollment 的唯一自動入口

新增一個消費層（`consume_queue(as_of)`），每個 after-close tick 執行：

| queue `observation.kind` | 消費動作 | 佇列狀態轉移 |
| :--- | :--- | :--- |
| `paper_watch_berth` / `after_close` | 呼叫 `watch_registry.enroll`（band / ≤2 席 / one-shot 由 registry **原封執行**）| `queued → running`（滿艙 → 留 `queued` 等下一 tick）|
| `paper_replay` | 呼叫 `workflows.paper_replay` 一次 | `queued → completed`（失敗留 `queued` 可重試）|

**狀態同步**（每 tick，對 running/paused 的 berth 項）：從 registry 重新摺疊 `WatchStatus.state` → 佇列態（`active→running` / `paused→paused` / `expired→expired` / `exited→completed`），使成熟 / 暫停 / 退出的 berth 在 `GET /research/live-oos/queue` **可見**（無需第二個 store）。

所有副作用 seam（enroll / status 讀 / replay 跑）皆注入，決策路徑全單元可測（無 JSONL / 日曆 / 網路）。

### 2.2 相容性：berth enrollment 改為佇列驅動，`run_after_close` 守門不動

- **`run_after_close` 的 berth 守門邏輯零改動**（~20 既有測試全綠）：它仍只放行持有 active berth 的策略。本 ADR **只改「berth 從哪來」**（佇列消費 enroll），不改「session 如何被守」。
- 手動 `watch enroll` CLI **保留**（ops / 測試 override）；但**主要路徑**是 `select-live-oos → consume`。
- 二者合起來給 Goal 10 保證：**沒有 queued 選取就沒有 berth；有選取也不會自動跑 session**（session 仍走 after-close 守門）。

消費由新 CLI `orchestration.cli live-oos consume` 觸發，接到 after-close **同一 tick**（`deploy/after-close.service` 的 `ExecStartPre`，per-strategy session 之前），空佇列為 clean no-op（exit 0）。

### 2.3 佇列狀態機（contract §7 真相源）

`queued | running | paused | completed | expired | cancelled`——兩個佇列專屬前/終態（`queued` / `cancelled`）夾住從 registry 摺疊的四態。`live_oos_queue.advance()` 以「複製最新快照 + 重蓋 state/observation」append 折疊事件（append-only 審計不 in-place 改）。佇列項新增 `observation.verdict_dsr`（數值 DSR，消費時 enroll 需要——`dsr_band` 標籤丟失了數字）。

---

## 3. 為何不這樣做（被否決的替代）

- **直接在 `run_after_close` 內 enroll**：會把 per-strategy 守門與佇列消費耦合，且污染 ~20 個純函式測試。改以獨立消費層 + 同 tick 觸發，關注點乾淨分離。
- **在 API 讀時即時從 registry 摺疊 berth 欄**：把 `watch_registry` 依賴（含日曆 / as_of）拉進 router。改由消費層在 tick 時把 berth 快照 append 進佇列 JSONL，`GET` 保持純摺疊；細粒度即時進度由 OOS 覆核頁交叉引用 `GET /monitor/watch`（IA §1.2）。
- **放寬 ADR-033**（讓佇列自帶 berth 語意繞過 registry）：明確否決——band / ≤2 席 / one-shot 仍由 `watch_registry` 執行，佇列只是**選取 + 授權**層。

---

## 4. 影響

- **行為**：after-close 現只跑「候選池勾選 → 消費入 berth」的策略；未勾選者永不自動跑（驗收 #1）。
- **模組**：新增 `research/live_oos_consumer.py`；`live_oos_queue.py` 加 `advance` / `QUEUE_STATES` / `verdict_dsr` 欄；`orchestration/cli.py` 加 `live-oos consume/list`。`watch_registry` / `after_close` **行為不變**。
- **API**：`GET /research/live-oos/queue` 回摺疊態（含 running/paused/completed/expired）——**schema 不變**（Envelope `data` 為無型別 dict list，加欄不動 OpenAPI，無 drift）。
- **部署**：`deploy/after-close.service` 加 `ExecStartPre`（consume）；`deploy/README` 註記 enrollment 改佇列驅動。
- **相容**：手動 `watch enroll` 仍可用；`run_after_close` 守門與既有測試全綠。
