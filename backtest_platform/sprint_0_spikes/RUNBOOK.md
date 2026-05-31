# Sprint 0 Spike RUNBOOK

> **目的**：Sprint 0 是 plan v1.0 (`dev_docs/17_m2_to_m5_master_plan.md` §7) 的 strict gate
> **總時程**：1 週（6 spikes，可平行）
> **退場準則**：任一 spike FAIL → 退回 Hybrid 路線（plan §8、ADR-005 §4）
> **全部 PASS** → 進入 M2 第一個 Sprint（plan §6 詳細任務）

---

## 0. 前置條件清單

執行 spike 前必須完成以下：

### 環境（必）

| 項目 | 檢查指令 | 期望 |
|:--|:--|:--|
| Python 版本 | `python --version` | >= 3.10 |
| uv | `uv --version` | 已安裝（取代 poetry，見 ADR-012）|
| Docker Desktop | `docker ps` | daemon 運行中 |
| Git 分支 | `git branch --show-current` | `feat/m2-tquant-lab-integration` |

### API token（按 spike 需求）

| Token | 取得方式 | 用於 spike |
|:--|:--|:--|
| `FINLAB_API_TOKEN` | https://ai.finlab.tw 個人資料 | S3, S5 |
| `TEJAPI_KEY`（選用） | https://tquant.tejwin.com | S1（如要跑 TEJ bundle）|
| `SHIOAJI_*` | 永豐金證券 API 中心申請（1-3 工作天） | S4 |
| `FINMIND_TOKEN` | https://finmindtrade.com | M1 既有，可選 |

### 一次性安裝（必）

```bash
# 1. 複製 .env.example 為 .env，填入上述 token
cd backtest_platform
cp .env.example .env  # Windows: copy .env.example .env
# 編輯 .env 填入 token

# 2. 安裝 sprint 0 所有依賴
uv sync --extra sprint0
# 或分項：uv sync --extra mainframe --extra data_paid --extra engines --extra ui --extra broker --extra monitoring --extra dev
# 或全部：uv sync --all-extras

# 3. 啟動本機服務
docker compose up -d  # 啟 TimescaleDB
docker ps             # 確認運行
```

---

## 1. Spike 執行順序建議

平行可行性：
- **可平行**：S1, S3, S4, S5, S6（無互相依賴）
- **必須串行**：S2（依賴 S1）

建議節奏：
- Day 1：S1（半天）+ S6（半天）
- Day 2：S2（一天）
- Day 3：S3（一天）— 需 FINLAB token
- Day 4：S4（半天）+ S5（半天）— 需 Shioaji + FinLab token
- Day 5：Gate Review 撰寫決策報告

---

## 2. 各 Spike 詳細指令

### S1 — TQuant-Lab + XTAI 安裝跑通

```bash
uv run python sprint_0_spikes/s1_tquant_hello_world.py
```

**Pass 標準**（檔案內列出，輸出含 `[S1] PASS`）：
- ✅ `import zipline` 成功
- ✅ `exchange_calendars.get_calendar('XTAI')` 取得台股交易日曆
- ✅ XTAI 2024 全年 sessions 數 ≈ 245（誤差 ±5）
- ✅ Zipline minimal backtest 跑通（用內建 quandl-csv bundle 或 synthetic）

### S2 — M1 純函式 plug 進 Zipline Algorithm

```bash
# 預設用 synthetic 資料（不需要 FinMind token）
uv run python sprint_0_spikes/s2_m1_plug_zipline.py

# 或對拍 M1 既有 pipeline (需要 FinMind token)
uv run python sprint_0_spikes/s2_m1_plug_zipline.py --compare-m1 --stock 2330 --start 2024-01-01 --end 2024-06-30
```

**Pass 標準**：
- ✅ Zipline Algorithm 初始化成功，能 load StrategyConfig
- ✅ `compute_scores` + `compute_signals` 在 `handle_data` 內可呼叫
- ✅ 對 2330 一年資料，產出的 action 序列與 M1 `pipeline.py` 一致（差異 0）

### S3 — FinLab bundle ingester POC

```bash
# 需 FINLAB_API_TOKEN
uv run python sprint_0_spikes/s3_finlab_bundle_poc.py
uv run zipline ingest -b finlab_poc
uv run python sprint_0_spikes/s3_verify_bundle.py
```

**Pass 標準**：
- ✅ FinLab login 成功，流量剩餘 > 100MB
- ✅ 拉 10 檔 1 年 OHLCV 成功
- ✅ 寫入 Zipline bundle 格式
- ✅ `zipline ingest` 跑通，bundle 大小 > 0
- ✅ Zipline 能讀回該 bundle 跑簡單 backtest

### S4 — Shioaji 沙箱範例

```bash
# 需 SHIOAJI_* + SHIOAJI_SIMULATION=true
uv run python sprint_0_spikes/s4_shioaji_sandbox.py
```

**Pass 標準**：
- ✅ shioaji.Shioaji(simulation=True) 初始化成功
- ✅ login 成功，列出帳戶
- ✅ 取得 2330 即時報價（或最後收盤）
- ✅ 下一筆模擬買單（低於市價，不會成交）
- ✅ 取消該訂單成功

### S5 — FinLab 即時資料 polling

```bash
# 需 FINLAB_API_TOKEN，盤中或盤後都可（盤後拿最後一筆 snapshot）
uv run python sprint_0_spikes/s5_finlab_live_polling.py --stock 2330 --duration 60
```

**Pass 標準**：
- ✅ 連續 polling 60 秒不中斷
- ✅ 至少 5 個 snapshot 寫到 `results/s5_polling_2330_*.csv`
- ✅ 每筆含 timestamp + price + volume

### S6 — Streamlit + TimescaleDB equity curve

```bash
# 需 Docker TimescaleDB 運行
uv run python sprint_0_spikes/s6_seed_equity_data.py  # 灌測試資料
uv run streamlit run sprint_0_spikes/s6_streamlit_dashboard.py
# 瀏覽器開 http://localhost:8501
```

**Pass 標準**：
- ✅ Streamlit 頁面開得起來
- ✅ Equity curve 互動正常（zoom / pan / hover）
- ✅ 頁面初次載入 < 2 秒
- ✅ 從 TimescaleDB 讀取 1 年 daily snapshot < 100ms

---

## 3. Gate Review 流程

6 個 spike 完成後，產出決策報告：

```bash
# 自動匯總所有 spike 結果到一份報告
uv run python sprint_0_spikes/gate_review.py > sprint_0_spikes/results/gate_review.md
```

決策樹（見 plan §8、ADR-005 §4）：

| 結果 | 行動 |
|:--|:--|
| 6/6 PASS | 進入 M2 Sprint 1（plan §6），開始建 `core/` Protocol + `adapters/data_bundle/finlab_bundle.py` |
| S1 FAIL | TQuant-Lab 不可用 → 退回原計畫 vectorbt-only 自建 adapter |
| S2 FAIL | M1 plug 失敗 → 修 plug code（不是路線問題） |
| S3 FAIL | FinLab bundle 不成功 → 暫時用 FinMind bundle，M2 並行解決 |
| S4 FAIL | Shioaji 沙箱不通 → M5 才需，暫不影響 M2-M4 |
| S5 FAIL | 即時資料不通 → M4 才需，暫不影響 |
| S6 FAIL | Streamlit 不通 → M3 才需，暫不影響 |

**ADR**：所有 spike 結果（含失敗）寫入 `results/`，留作 ADR-005~009 的 verification evidence。

---

## 4. 故障排除

| 問題 | 解法 |
|:--|:--|
| `ModuleNotFoundError: zipline` | `uv sync --extra mainframe` |
| `XTAI calendar not found` | 升級 `exchange-calendars>=4.5` |
| Docker daemon 未啟動 | 啟 Docker Desktop |
| `FINLAB_API_TOKEN` 未設 | 編輯 `.env` 加入 token；uv 不需 shell，直接 `uv run` 即重讀 env |
| `psycopg2 connection refused` | 確認 `docker compose up -d` 已跑、port 5432 不衝突 |
| `Shioaji simulation` 找不到 | 確認 `.env` 的 `SHIOAJI_SIMULATION=true` |

---

## 5. 完成 checklist

- [ ] 環境 4 項全綠
- [ ] 6 spike 至少跑過一次
- [ ] `results/` 含所有 spike 輸出
- [ ] gate_review.md 已產出
- [ ] 決策（晉升 M2 / 退回 Hybrid）已記錄

完成後通知 Claude 繼續 M2 Sprint 1（plan §6）。
