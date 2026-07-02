# 測試策略 — backtest_platform

> **版本：** v2.0 | **更新：** 2026-07-02 | **狀態:** 對齊實際測試體系
> **進度**：見 [`16_wbs_development_plan.md`](./16_wbs_development_plan.md)（單一狀態真相源）
> **關聯：** `03_behavior_driven_development_guide.md`、`.claude/rules/testing.md`、[platform_full_audit_2026-07-02](./platform_full_audit_2026-07-02.md) §缺陷 #6（行覆蓋≠判決覆蓋）。

本產品唯一護城河是「驗證信心」，而審判庭自己必須先可信。因此測試策略的核心不是覆蓋率數字，而是**判決級測試**（oracle）——行覆蓋放過的 DSR 單位錯誤，是判決 oracle 才擋得住的（審查缺陷 #6 教訓）。

---

## 1. 現況總覽

| 指標 | 值 |
| :--- | :--- |
| 後端測試 | ~1116 passed（100 個 `test_*.py`）|
| 後端覆蓋率 | ~92.6%（gate `--cov-fail-under=80`，branch coverage）|
| 前端測試 | 22 個 vitest 檔（Testing Library）|
| E2E | Playwright `frontend/e2e/audit`（endpoint 稽核）|
| CI | GitHub Actions 三 job（§7）|

測試以 pytest 為主，`pyproject.toml` `[tool.pytest.ini_options]`：`--strict-markers`、`--cov=backtest_platform`、`--cov-fail-under=80`。markers：`integration`（需 DB / 外部服務，預設自跳過）、`slow`。

### 1.1 金字塔現況

多數測試是**純函式單元 + 契約 / 判決 oracle**；integration（真 DB round-trip）以 marker 隔離，CI 不設 service container 讓其 self-skip；雙引擎對拍為 harness（需本地 parquet cache，fresh checkout self-skip）。E2E 為前端 Playwright，尚未進 CI（§9 roadmap）。

---

## 2. 測試分佈（`backtest_platform/tests/`）

| 目錄 | `test_*.py` | 重點 |
| :--- | :---: | :--- |
| `research/`（含 `workflows/`）| 23 | 研究迴圈：run harness、compare、sweep、promotion、**工作流 doe/go_gates/truth_gate/paper_replay/universe** |
| `api/` | 17 | FastAPI routers + envelope 契約 + 錯誤碼映射 |
| `strategies/` | 12 | 策略契約 + **conformance gate（全 registry parametrized）** |
| `engines/` | 12 | zipline adapter：algorithms / bundle / parquet cache / 台股規則 / **雙引擎對拍 harness** |
| `validation/` | 12 | 審判庭：dsr / pbo / wfa / two_stage_gate / gate_machine / metrics / full_report |
| `data/` | 8 | schema / finmind_etl / finlab_source / db_writer / **init.sql 防漂移** |
| `monitoring/` | 4 | alert_rules（規則 + 去重 + 靜默）/ discord_notifier / influx_writer / grafana JSON |
| `orchestration/` | 4 | collaborators / daily_flow（paper 鏈）|
| `risk/` | 2 | ex-ante gate / circuit breaker |
| `runtime/` | 2 | 執行期組裝 |
| `adapters/` / `jobs/` | 各 1 | broker / 非同步 job runner |

---

## 3. 判決級測試（核心，審查缺陷 #6）

行覆蓋 92.6% 不等於判決覆蓋——shape-only 測試（只驗型別與 0–1 範圍）曾放過 DSR 單位錯誤級 CRITICAL。以下三類測試守的是**判決正確性**，不是行是否被跑到。

### 3.1 Conformance gate（全 registry parametrized）

`tests/strategies/test_conformance.py`：

```python
@pytest.mark.parametrize("name", list_strategies())
def test_strategy_conforms(name: str):
    report = check_strategy(name)
    assert report.ok, ...
```

- **每一個註冊策略**都被 parametrize 掃過：`config_model` 可實例化、`run()` 回 `StrategyRun`、metrics 含 `REQUIRED_METRIC_KEYS`（cagr / sharpe / …）。
- 反向測試（`__broken__` runner 缺 metric key）確認 gate 真的會 FAIL，而非空過。
- 新增策略只寫 `research_config.py` 即自動納入 conformance（ADR-027/029），零改測試。

### 3.2 審判庭 oracle（truth-gate judgement，ADR-030）

`tests/research/workflows/test_truth_gate_judgement.py` + `test_truth_gate_parquet_dir.py`：釘住**判決本身**而非型別——已知 REJECTED 案例必須 REJECTED、DSR 走 per-period SR + cross-trial variance 正確路徑、缺誠實來源即 raise、`survivorship_clean` 跟著 cache 走（`parquet_dir` 覆蓋，ADR-032）。這是把「shape-only 放過單位錯誤」的教訓轉成 RED-first oracle。

### 3.3 Gate 依策略 dispatch

run 以其自身策略宣告的 gate 判決（非四層預設）；conformance 補「gate health 指標 ⊆ 策略 metrics keys」斷言，防止「非四層策略永遠 INCOMPLETE」（審查缺陷 #8）。

---

## 4. 對拍矩陣（Reconciliation）

跨引擎 / 跨層一致性是 ADR-008「三模式共用策略碼」的機器證據。

| 對拍 | A | B | 位置 | 現況 |
| :--- | :--- | :--- | :--- | :--- |
| Zipline ↔ vectorbt | event-driven | 向量化 | `engines/zipline_adapter/validation/test_cross_check_vectorbt.py` | harness（需本地 parquet cache）|
| Zipline ↔ M1 pipeline | 新引擎 | M1 baseline | `…/validation/test_regression_vs_m1.py` | harness |
| 向量化 PnL 交叉驗 | — | — | `…/validation/test_vectorized_pnl_check.py` | harness |

- 對拍 harness 從 coverage `omit`（非產品碼），且**依賴本地 parquet cache** → fresh checkout self-skip（審查缺陷 #6 已知缺口）。
- **容差收斂待辦**：雙引擎容差歷史上三份文件三個數字；roadmap 統一為相對 1% / 絕對 10bps 並回寫（audit Phase 2）。
- **backtest ↔ paper 對拍缺席**：研究側 panel rebalance 向量化 vs paper 側 daily_flow 逐單撮合，尚無 reconciliation 測試（roadmap）。

---

## 5. Schema / 契約防漂移

三起 doc-drift 事故（runs DDL、openapi stale、契約 registry 漂移）的根因是無機器守門，現已雙層鎖住：

| 守門 | 位置 | 內容 |
| :--- | :--- | :--- |
| runs DDL ↔ db_writer | `tests/data/test_init_sql_schema.py` | regex 解析 `init.sql`，斷言 13 表 + runs 欄位與 `db_writer._RUNS_COLS` 逐欄對齊 |
| OpenAPI ↔ 前端 snapshot | `scripts/check_openapi_drift.py`（CI）| live `app.openapi()` ↔ `frontend/openapi.json` + runs DDL ↔ `_RUNS_COLS`（AST）|
| 每個 registered 策略契約 | `test_conformance.py` | 全 registry parametrized（§3.1）|

---

## 6. 覆蓋率門檻與 config

`pyproject.toml` 實際設定（branch coverage）：

```toml
[tool.pytest.ini_options]
addopts = "-ra --strict-markers --cov=backtest_platform --cov-report=term-missing --cov-fail-under=80"

[tool.coverage.run]
source = ["src/backtest_platform"]
branch = true
omit = [
    "src/backtest_platform/adapters/__init__.py",
    "src/backtest_platform/adapters/*/__init__.py",
    "src/backtest_platform/dashboard/__init__.py",
    "src/backtest_platform/orchestration/__init__.py",
    "src/backtest_platform/strategies/__init__.py",
    "src/backtest_platform/engines/zipline_adapter/validation/*",  # 對拍 harness
]
```

- 全 repo gate 鎖 **80%**（實際 ~92.6%，留重構餘裕）。
- omit：無產品碼的骨架 `__init__` + 對拍 harness（後者由 integration 覆蓋，非 unit）。
- **per-path gate（如 validation ≥90%）為 roadmap**（§9）——目前單一全域門檻。

---

## 7. CI 三 job（`.github/workflows/ci.yml`，已上線）

每次 push main / PR 觸發；`concurrency` 取消同 ref 前一次 run。

| Job | 步驟 | 守門 |
| :--- | :--- | :--- |
| **backend** | `uv sync --all-extras` → `uv run pytest` | coverage gate 80%（由 pyproject `--cov-fail-under` 強制）；`--all-extras` 提供 pytest/fastapi/zipline/vectorbt 全測試矩陣；`POSTGRES_INTEGRATION` 未設 → DB 測試 self-skip |
| **frontend** | `npm ci` → `tsc --noEmit` → `vitest run --coverage` | 型別 strict + 單元 + coverage（`@vitest/coverage-v8`）|
| **contract-drift** | `uv sync --extra api` → `python3 scripts/check_openapi_drift.py` | OpenAPI live↔snapshot + runs DDL↔`_RUNS_COLS`（**hard gate**：任何 schema 變更必與重生 `openapi.json` + `api.gen.ts` 同 PR）|

> 後端全量測試在 CI runner 數十秒內跑完（無 service container），可負擔每 PR 全跑。

---

## 8. 前端測試

- **Vitest + Testing Library**（22 檔）：工具函式、Hooks、Store、核心元件**四態**（default / loading / empty / error）。
- **型別回歸**：`tsc --noEmit`（CI frontend job）。
- **mock 真實形狀**：測試 mock 必用真實契約欄名（審查缺陷 #6 教訓——drift 後的錯誤欄名 mock 曾綠燈掩蓋 422 與滿版「—」）；`api.gen.ts` 由 OpenAPI 生成，mock 對齊生成型別。
- **E2E**：Playwright `e2e/audit/endpoint-audit.spec.ts`（端點稽核）；`npm run test:e2e` 手動跑，webServer 進 CI 為 roadmap。

---

## 9. 已知缺口（誠實列出，roadmap 非現況）

對應 audit #6，以下標為 **roadmap**，不假裝已有：

- [ ] **checked-in golden master**：目前無凍結的合成 golden bundle；雙引擎對拍依賴本地 parquet cache，fresh checkout self-skip → 補 checked-in 合成 golden 讓對拍脫離本地 cache。
- [ ] **hypothesis property-based 測試**：目前零使用；roadmap 導入 validation / risk（DSR 對 n_trials 單調、WFA fold 不重疊、RiskGate 排列不變等 15–20 條）。
- [ ] **E2E 進 CI**：Playwright specs 已存在，webServer 尚未接入 CI；roadmap 1–2 條使用者旅程 E2E。
- [ ] **per-path coverage gate**：validation ≥90% 等分路徑門檻為 roadmap；目前單一全域 80%。
- [ ] **backtest ↔ paper 對拍**：sim vs paper reconciliation 測試缺席（§4）；roadmap 固定 config 一個月窗口對拍。
- [ ] **台股微結構**：±10% 漲跌停 / 停牌測試缺席（audit #21）；roadmap xfail 釘住期望 + lookahead detector 工具化。

---

## 10. 測試失敗排除流程

對應 `.claude/rules/testing.md`：

1. 載入 sunnydata-testing skill
2. 檢查測試隔離（shared state 殘留 / fixture 汙染）
3. 驗證 mock 正確性（mock 形狀是否 = 真實契約形狀）
4. **修實作而非測試**（除非測試本身有誤——判決 oracle 尤其不可為了綠燈而放寬）
5. 多次 flaky → 標記並開 issue 追蹤
