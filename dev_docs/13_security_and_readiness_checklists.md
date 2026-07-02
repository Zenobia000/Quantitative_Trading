# 安全與生產準備檢查清單 — backtest_platform

> **版本：** v2.0 | **更新：** 2026-07-02 | **審查：** Self
> **威脅模型基準：** [ADR-031](./adrs/ADR-031-standalone-auth-decision.md)（standalone = localhost-only）、[02 PRD v4.0 §2.3](./02_project_brief_and_prd.md)（部署假設）、`rules/security.md`。
> **關聯：** [24_risk_management_spec.md](./24_risk_management_spec.md)（風控規格，paper/live gate 真相源）。

---

## A. Standalone 威脅模型（ADR-031）

本平台是**單機自託管、內網 localhost、單人、無多人協作、無合規審批**的個人系統（PRD v4.0 §2.3）。安全設計據此假設一次裁定，不做企業級 gold-plating。

### A.1 安全邊界 = loopback bind（唯一防線）

- [ ] **後端 API MUST 綁 `127.0.0.1`**（loopback）：`uvicorn --host 127.0.0.1`，前端走 vite proxy 同機存取，無公網暴露。**綁定本身即安全邊界。**
- [ ] **無 app 層 auth**（ADR-031 裁決）：能存取 `127.0.0.1` 者已擁有這台機器，20 行 static Bearer 不增實質防線、卻增每個 client（curl / CLI / 排程器）摩擦。前端 `http.ts` 的 `dev-token` 為無害殘留（後端不檢查）。
- [ ] **DB / 監控埠建議綁 loopback**：docker-compose 的 `5432 / 8086 / 3000` port mapping 預設對 host 全介面開放；單機部署應改綁 `127.0.0.1:<port>:<port>`，避免同網段其他機器直連。
- [ ] `401 UNAUTHORIZED` 保留於錯誤碼 enum（25 §2），供 **M5 遠端存取**啟用 auth 時使用（reverse-proxy guard 或 static Bearer），standalone 期不觸發。

### A.2 威脅模型明確排除（standalone 不做）

- 多角色 RBAC、跨人 leaderboard、簽核鏈 → 單人單角色，不適用。
- 公網 DoS / rate-limit → 無公網暴露，不適用（唯一「DoS 自己」風險由 EX-009 訂單頻率上限處理，見 24 §2）。
- WAF / IDS / 容器逃逸強化 → 個人機不投資；M5 遠端存取時重議。

---

## B. 秘密管理（不因 standalone 放鬆）

第三方 token **僅後端持有、絕不出現在任何 API 回應或前端 bundle**（ADR-031 明文）。

| Secret | 用途 | 載體 | 輪換 |
| :--- | :--- | :--- | :--- |
| `FINLAB_API_TOKEN` | 主資料源（付費，ADR-006）| `.env`（gitignored）| 年度（伴隨續費）|
| `FINMIND_TOKEN` | fallback 資料源 | `.env` | 免費版，變更時 |
| `DISCORD_BOT_TOKEN` / `DISCORD_*_ID` | 告警通道（ADR-010）| `.env` | Bot token 變更時 |
| `INFLUXDB_TOKEN` | 系統 metrics（M4 選配）| `.env` | 季度 |
| `POSTGRES_PASSWORD` | TimescaleDB | `.env` | 季度 |
| `SHIOAJI_*` | 實盤下單（M5）| `.env` | 半年 |

檢查項：

- [x] secrets 一律從 env 載入（`config/settings.py` + `pydantic-settings`），不寫入原始碼、不入 git（`.env` gitignored）
- [x] log 不印 token（`grep -rE "TOKEN|SECRET"` 確認無明文輸出）
- [x] `/system/alerts/channels` 回應遮罩（`bot_token → "***"`，25 §4）
- [x] **`POSTGRES_PASSWORD` 預設 `change_me_in_production` 有連線期防呆**（`config/settings.py` `require_postgres()`，於 `data/db_writer._connection` 單一連線 choke point 呼叫）——密碼仍為預設時開連線前即 `RuntimeError`；只在真正連 DB 時驗，import / 無 DB 的 CI 不受影響（審查缺陷 #19，已修）
- [ ] 疑似外洩（貼到 chat / log / PR）即到對應後台輪換

---

## C. 應用程式安全

### 輸入驗證（系統邊界）

- [x] CLI 參數經 Click 型別驗證（date / choice / required）
- [x] 資料源回應經 Pydantic schema 驗證（`data/schemas.py` `ETLBundle` 等）
- [x] 策略 config 為 Pydantic **frozen** model（ADR-004），Field 驗證參數範圍
- [x] API body `extra='forbid'`，未知欄位 → 422 逐欄（25 §2 `VALIDATION_ERROR`）
- [x] **HTTP / CLI overrides 路徑於系統邊界重驗**（`research/workflows/config.revalidate_with_overrides`：`model_validate({**dict(cfg), **overrides})`）——錯型別 / 未知欄位（`extra=forbid`）/ 非法窗序（`_window_ordered`）全在邊界擋下（HTTP → 422、CLI → 明確 ClickException），不再用 `model_copy(update=)` 繞過 validator（審查缺陷 #11，已修）

### 注入與輸出

- [x] SQL 全參數化（`psycopg` `execute_values` / bind params，無字串拼接）
- [x] 錯誤回應不洩露 stack / 秘密（全域 `Exception` handler → `INTERNAL`，25 §2）
- [x] React 自動 HTML 跳脫；秘密不入 bundle（§B）

### 依賴安全

- [x] 提交 lock file（`uv.lock` / `package-lock.json`）
- [x] 不裝來源不明套件
- [x] `pip-audit` / `npm audit` 排程掃描 — `.github/workflows/dependency-audit.yml`（每週一 + 手動觸發；pip-audit 掃 uv lockfile、npm audit high+；非阻塞、發現即標紅）

---

## D. 資料安全與備份

### D.1 資料分類

| 類別 | 範例 | 處理 |
| :--- | :--- | :--- |
| 公開（市場資料）| 股價、法人籌碼 | 不需加密、可寫 disk（parquet cache）|
| 秘密（API token）| §B 清單 | env 變數，不入 git、不入 log |
| Audit（研究血統）| `reports/runs.jsonl`、`positions` / `fills` 表、晉升 audit log | 不可改寫，長期保留 |

### D.2 備份（單人不可再生資產裸奔的緩解，審查缺陷 #10）

不可再生資產有三類：FinLab 付費 ingest 的 parquet cache、研究血統 `reports/*.jsonl`、TimescaleDB telemetry。最小備份策略：

- [ ] **每日 `pg_dump`** TimescaleDB → 本機備份目錄（保留 N 份輪替）
- [ ] **`rsync` `data/parquet*` + `reports/`** → 備份目錄 / 外接碟（付費資料 + 研究血統）
- [ ] parquet cache 已具**原子寫回 + 缺口 merge**（`parquet_cache.py`），舊歷史不被新 ingest 覆蓋
- [ ] 恢復演練：刪 1 日資料 → restore → smoke test 通過（詳見 [14 §災難恢復](./14_deployment_and_operations_guide.md)）

---

## E. CI 品質守門（已上線）

三起 doc-drift 事故（runs DDL、openapi.json stale、契約 registry 漂移）的共同根因是無機器守門——現已由 GitHub Actions（`.github/workflows/ci.yml`）三 job 補上：

| Job | 守門內容 |
| :--- | :--- |
| **backend** | `uv run pytest`（coverage gate 80% 由 `pyproject.toml --cov-fail-under=80` 強制）|
| **frontend** | `tsc --noEmit` + `vitest run --coverage`（`@vitest/coverage-v8`）|
| **contract-drift** | live OpenAPI ↔ `frontend/openapi.json` + runs DDL ↔ `db_writer._RUNS_COLS`（`scripts/check_openapi_drift.py`，hard gate）|

> 測試體系與缺口見 [22_test_strategy.md](./22_test_strategy.md)。

---

## F. Paper / Live 上線就緒（引用 24 號風控規格）

進 paper（收 live OOS）與 M5 實盤前的 gate 判準以 **[24_risk_management_spec.md](./24_risk_management_spec.md) 為單一真相源**（本節只列 checklist，不複製門檻）。

### F.1 進 paper 前

- [ ] 策略過真偽閘（PBO / DSR / WFA / survivorship-clean）+ OOS>0（ADR-025 兩段閘，24 §8）
- [ ] after-close 排程器就緒（cron / systemd timer + Discord 成敗通知；為收 live OOS 的下一步 blocker，審查缺陷 #17）
- [ ] paper 風控接真實部位快照（EX-002/003/004/007 組合層規則不再對空倉評估，審查缺陷 #3）
- [ ] Discord 告警測試通過（`POST /system/alerts/test` 送達）

### F.2 M5 實盤前（一次性）

- [ ] §D.2 備份 + 恢復演練已跑過
- [ ] Shioaji TLS + 帳號驗證通過（`SHIOAJI_SIMULATION=false` 前）
- [ ] 三級熔斷自動執行驗證（L1/L2/L3，24 §4）
- [ ] `kill_switch.sh` 緊急停機腳本就緒（24 §9.5）
- [ ] 遠端存取 auth 決策重開（若需跨機，ADR-031 §4）
- [ ] 設定資金上限與 DD 熔斷（24 §4）

---

## G. 合規性（個人資金，最小適用）

| 項目 | 適用 | 處理 |
| :--- | :---: | :--- |
| 個資法 / GDPR / SOC2 | ❌ | 無第三方使用者資料、個人專案 |
| 證券交易紀律 | ✅ | 不做拉抬、不做高頻 quote stuffing |
| 個人所得稅（證券交易）| ✅ | 自行申報 |
| 健保補充保費 | ✅ | 單筆 > 2 萬時自動扣繳 |

---

## H. 風險管理總覽（詳見 24 號文件）

風控是產品護城河「驗證信心」的執行層，完整規範（兩階段框架、12 條 ex-ante 規則、3 級熔斷狀態機、SOP、`kill_switch.sh`、配置閘目標倉位）以 **[24_risk_management_spec.md](./24_risk_management_spec.md)** 為準。設計鐵律：

1. **風控不可繞過**：所有 signal 必經 `risk_gate.evaluate()`
2. **熔斷自動執行**：L2/L3 觸發自動下單，不等人工確認
3. **保守優先**：拿不準時拒單
4. **可追溯**：每次拒單寫 audit trail（`rule_id` + `context_json`）
