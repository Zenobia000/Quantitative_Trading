# Quantitative_Trading — 個人量化 edge 驗證工廠

**台股、單人、standalone 的量化策略 edge 驗證工廠 + 晉升管線。**

這不是一支策略，而是一台**判斷策略有沒有真 edge 的機器**。你把候選策略丟進來，平台用一致的審判庭（真偽閘 + 配置閘）誠實判它真偽、給它倉位、或砍掉它。核心信念：

- **策略是消耗品，審判庭是資產** — 連續 NO-GO 是平台正常運作的證據，不是失敗。
- **平台先行、策略後驗** — 先把驗證/研究/監控 pipeline 建到可信，再讓策略一個個過閘。
- **反自欺** — survivorship-clean、pre-registered hypothesis、OOS sealed vault、DSR deflate 全部 hard-fail。
- **single-user standalone** — localhost-only 綁定（[ADR-031](dev_docs/adrs/ADR-031-standalone-auth-decision.md)），無多租戶、無認證層。

> ⚠️ 策略研究紀錄，非投資建議。四層共振經驗證已判**負 edge 廢止**（[ADR-023](dev_docs/adrs/ADR-023-momentum-no-go-hold-gate.md)）；資金流 inst_flow 正在 survivorship-clean 平台化重驗中。

---

## 快速開始

### 後端（Python，uv）

```bash
cd quant_platform/backtest_platform
cp .env.example .env                       # 填 FINLAB/FINMIND/SHIOAJI/DISCORD token（可選）
uv sync --extra sprint1 --extra api --extra dev   # 主要棧：FinLab/FinMind、sim/vectorbt、FastAPI、測試
uv run pytest -q                            # 全套單元 + 整合測試（1116 passed）
```

### 資料庫（TimescaleDB，Docker）

```bash
cd quant_platform/backtest_platform
docker compose up -d timescaledb
POSTGRES_PASSWORD=quant_local_dev_password uv run python ../scripts/seed_demo_data.py
```

### HTTP API（FastAPI）

```bash
cd quant_platform/backtest_platform
POSTGRES_PASSWORD=quant_local_dev_password uv run uvicorn backtest_platform.api.app:app --reload --port 8083
# OpenAPI 文件：http://localhost:8083/docs（統一信封 {success,data,error,meta}，見 dev_docs/25）
```

### 前端（React 19 + Vite）

```bash
cd quant_platform/apps/web_console
npm install
npm run dev                                # http://localhost:5173（研究/監控/系統三 zone + Cmd-K）
# 後端不在預設 :8000 時（如共用機 port 被占）：cp .env.example .env 並設 DEV_API_PROXY_TARGET=http://localhost:<port>
```

---

## 研究迴圈：五個通用工作流

每隻策略只寫一份 `strategies/<name>/research_config.py`（宣告 `UniverseConfig` / `DOE` / `GO_GATES` / `TRUTH_GATE` / `PAPER_REPLAY`）即可參與全部工作流，**零新腳本**（[ADR-029](dev_docs/adrs/ADR-029-research-workflow-standardization.md)）。晉升管線：

```
build-universe → doe → go-gates → truth-gate → paper-replay
   (資料)        (掃描)   (WFA/PBO)   (審判庭)      (paper 重放)
```

| 工作流 | 用途 | ADR |
| :--- | :--- | :--- |
| `build-universe` | FinLab 寬表 → 季度 rebalance → survivorship-clean universe + `universe_manifest.json` | ADR-032 |
| `doe` | DOE 參數網格掃描，輸出**全網格**（防 cherry-pick） | ADR-029 |
| `go-gates` | WFA + PBO GO 閘 | ADR-029 |
| `truth-gate` | 兩段式真偽閘（survivorship/PBO/DSR/WFA hard-fail → 配置閘產倉位） | ADR-025 / ADR-030 |
| `paper-replay` | paper 重放 sim（收 forward OOS 前的最後一關） | ADR-029 |

```bash
cd quant_platform/backtest_platform
# --dry-run 只印 config 不跑；真實資料工作流加 --extra data_paid（FinLab token）
uv run python -m backtest_platform.research.cli build-universe --strategy inst_flow --dry-run
uv run python -m backtest_platform.research.cli doe          --strategy inst_flow --dry-run
uv run python -m backtest_platform.research.cli truth-gate   --strategy inst_flow
```

> 另有唯讀審判庭 `run-is`（逐條綠紅落 runs ledger）、`runs`/`compare`/`validate`/`promote-check` 研究 CLI，見 [dev_docs/06](dev_docs/06_api_design_specification.md) §3.5。

---

## 目錄地圖

```
.
├── quant_platform/          # Golden monorepo（W7.1 收斂）
│   ├── backtest_platform/   # Python 研究/驗證平台（維持 backtest_platform import path）
│   │   ├── src/backtest_platform/   # domain/application/adapters（research 三層）+ services/ 5 個 + api
│   │   ├── tests/           # pytest（1453 passed）
│   │   ├── docker/          # TimescaleDB init schema
│   │   └── deploy/          # systemd/cron 運維單元
│   ├── apps/web_console/    # React 19 + TS + Vite 前端（研究/監控/系統三 zone + Cmd-K）
│   ├── packages/contracts/  # 跨層 published language（schemas + examples）
│   ├── services/            # golden service 骨架（M1-M6 逐服務碎解目標）
│   └── docs/research_notes/ # 策略點子筆記 + 歷史規格 archive
├── dev_docs/                # 工程文檔（INDEX + PRD + REST 契約 + ADR + 審查報告）
├── scripts/                 # check_openapi_drift 等 repo-root 工具
└── .github/workflows/       # CI（backend / frontend / architecture / contract-drift）
```

---

## 文件入口

| 想知道 | 讀這份 |
| :--- | :--- |
| 全部文檔導覽 | [dev_docs/INDEX.md](dev_docs/INDEX.md) |
| 產品定位與 PRD | [dev_docs/02_project_brief_and_prd.md](dev_docs/02_project_brief_and_prd.md)（v4.0）|
| 前後端 REST 契約 | [dev_docs/25_fe_be_rest_contract.md](dev_docs/25_fe_be_rest_contract.md)（唯一真相源）|
| 架構決策 | [dev_docs/adrs/](dev_docs/adrs/)（ADR-001~032）|
| **當前狀態真相源** | [dev_docs/16_wbs_development_plan.md](dev_docs/16_wbs_development_plan.md) §1 banner + §2（整體 ~86%）|

> 狀態集中在 16 WBS，README 與其他文檔不重複寫 milestone 進度，避免不一致。

---

個人研究專案（single-user，localhost-only）。策略假設未經實證前不代表可獲利，任何使用造成的損失自負。
