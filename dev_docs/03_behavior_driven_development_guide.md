# BDD 行為驅動情境 — backtest_platform

Feature scenarios 描述**策略無關的平台工作流**（研究迴圈 + 審判庭 + 風控），對應 PRD Epic 3/4/5。策略本身是消耗品，不在此描述具體策略的計分邏輯。

---

## Gherkin 速查

| 關鍵字 | 用途 |
| :--- | :--- |
| `Feature` | 功能（對應 PRD Epic） |
| `Scenario` | 業務場景 |
| `Given` | 初始狀態 |
| `When` | 操作 |
| `Then` | 預期結果 |

---

## Feature 1：survivorship-clean universe 建構

**對應**：US-007 前置；`research build-universe` → `research/workflows/universe.py::run_build_universe`（ADR-032）

```gherkin
Feature: survivorship-clean universe 建構
  # 策略以 research_config.UNIVERSE 宣告 span / top_n / min_turnover

  Background:
    Given FinLab API token 已設定
    And UniverseConfig 宣告 span 2010-01-01..2024-12-31、季度 rebalance

  @happy-path
  Scenario: 建構含下市股的乾淨 universe
    When 執行 build-universe --strategy inst_flow
    Then universe 應同時含存活股與下市股（n_delisted > 0）
    And 應寫出 universe_manifest.json 記錄 bundle 血統
    And ingest 部分失敗不應中止（回報 n_ingested_failed）

  @dry-run
  Scenario: dry-run 只印 config 不抓資料
    When 執行 build-universe --strategy inst_flow --dry-run
    Then 應印出 span / top_n / min_turnover / cache_dir
    And 不應呼叫 FinLab API
```

---

## Feature 2：DOE 參數網格掃描

**對應**：US-007；`research doe` → `research/workflows/doe.py::run_doe`（讀 `research_config.DOE`）

```gherkin
Feature: DOE 參數網格掃描
  # 工作流與策略無關，走 get_strategy(name).run() dispatch

  Background:
    Given 策略以 research_config.DOE 宣告參數網格

  @happy-path
  Scenario: 全網格結果一律輸出（防 cherry-pick）
    Given DOE grid 展開為 N 個 config
    When 執行 doe --strategy <name> --out-csv reports/doe.csv
    Then CSV 應含全部 N 列（不篩選、不只留最佳）
    And 每列應含 cagr / sharpe 指標

  @sad-path
  Scenario: 策略未宣告 DOE 時明確報錯
    Given 策略 research_config 缺 DOE
    When 執行 doe --strategy <name>
    Then 應回傳非零 exit code 並印出「缺 DOE 宣告」
    And 不應靜默略過或回傳空結果
```

---

## Feature 3：兩段式真偽閘（審判庭）

**對應**：US-008；`research truth-gate` → `research/workflows/truth_gate.py::run_truth_gate`（ADR-025 / ADR-030）
真偽閘 hard-fail 判準：PBO / DSR（deflated）/ WFA OOS 廣度 / survivorship-clean。

```gherkin
Feature: 兩段式真偽閘
  # 真偽閘（hard-fail）+ 配置閘（連續 sizing）

  Background:
    Given 策略以 research_config.TRUTH_GATE 宣告 is/oos 窗口與 n_trials（pre-registered）

  @happy-path
  Scenario: 過真偽閘的策略判 REAL 並產出倉位
    Given WFA OOS 廣度 ≥ 門檻
    And DSR（deflated）> 0.95
    And universe 為 survivorship-clean
    When 執行 truth-gate --strategy <name>
    Then verdict 應為 REAL
    And 配置閘應據 Sharpe / 相關性 / 容量產出倉位大小

  @hard-fail
  Scenario: survivorship 未達 clean 時 hard-fail
    Given universe 為 survivor-only（含生存者膨脹假陽性）
    When 執行 truth-gate --strategy <name>
    Then verdict 應為 REJECTED
    And reasons 應含 survivorship hard-fail
    And 不應進入配置閘或 paper

  @deflation
  Scenario: 試驗次數使 DSR 通縮至門檻下
    Given 年化 Sharpe 邊際為正但 n_trials 大
    When 執行 truth-gate --strategy <name>
    Then DSR 應以 per-period SR + cross-trial variance 反映 n_trials 通縮
    And DSR ≤ 0.95 時 verdict 為 REJECTED（單一正 Sharpe 不足以過閘）
```

---

## Feature 4：paper 重放晉升鏈

**對應**：US-010；`research paper-replay` → `research/workflows/paper_replay.py`（讀 `research_config.PAPER_REPLAY`）

```gherkin
Feature: paper 重放晉升鏈
  # 過真偽閘的候選在接真 daemon 前先驗證晉升鏈

  @happy-path
  Scenario: 逐日跑完整 chain 並寫 telemetry
    Given 過真偽閘的候選 + PAPER_REPLAY 宣告 as_of 與 initial_cash
    When 執行 paper-replay --strategy <name>
    Then 應逐日跑 ETL→signals→risk→orders→log
    And 跨日 resilient（單日缺料不整段崩）
    And 應回報 run_id 與 gate_status
```

---

## Feature 5：晉升狀態機（IS→WFA→OOS 不可逆）

**對應**：US-011 / US-012；`research validate` / `promote-check` → `validation.gate_machine`

```gherkin
Feature: 晉升狀態機
  # OOS sealed vault：前置 gate 未過前不可讀，狀態不可回退

  Background:
    Given ledger 內某 run 已判 gate

  @happy-path
  Scenario: IS 通過才解鎖 WFA
    Given run 的 IS 指標達門檻
    When 執行 validate --run-id <id>
    Then gate state 應為 IS_PASS
    And OOS vault 應維持 SEALED（WFA 通過前不可讀）

  @sad-path
  Scenario: 未達 APPROVED 不得晉升
    Given run 尚未走完 IS→WFA→OOS→approve
    When 執行 promote-check --run-id <id>
    Then 應回報 NOT ELIGIBLE
    And 應列出待完成階段
```

---

## Feature 6：pre-trade 風控攔單

**對應**：US-006 風控；`orchestration/daily_flow` → risk gate（EX-002 單股上限）

```gherkin
Feature: pre-trade 風控攔單
  # AccountState 由 broker.positions + 總權益建立（非空倉快照）

  Background:
    Given AccountState 反映既有部位與總權益

  @happy-path
  Scenario: 同批多筆 buy 合計超單股上限被 EX-002 攔下
    Given 現金快照在同批下單間遞減
    And 兩筆 buy 對同一標的合計超過單股上限
    When 風控閘評估這批訂單
    Then 第二筆應被 EX-002 拒絕
    And 已核准訂單不因此整日 halt

  @vocab
  Scenario: side 詞彙轉換
    Given 風控核准一筆 reduce 訂單
    When 送至 PaperBroker
    Then reduce 應轉為 sell（不拋 ValueError）
```

---

## 最佳實踐

1. **每個 Scenario 只測一件事**
2. **使用陳述式** — `Then verdict 應為 REJECTED`，非「系統應判斷為拒絕」
3. **避免實作細節** — `When 執行 truth-gate`，非「When 呼叫 run_truth_gate(cfg)」
4. **從使用者角度寫** — 策略研究者 / 艦隊運維者能讀懂
5. **策略無關** — scenario 描述工作流行為，具體策略以 `--strategy <name>` 佔位

---

## BDD 與單元測試的對應

| BDD Scenario | Pytest 對應 |
| :--- | :--- |
| F1 含下市股 universe | `tests/research/workflows/test_universe.py` |
| F2 全網格輸出 | `tests/research/workflows/test_doe.py` |
| F3 survivorship hard-fail | `tests/research/workflows/test_truth_gate.py`（oracle：已知 REJECTED） |
| F3 DSR 通縮 | `tests/validation/test_dsr.py`（per-period SR + n_trials 單調） |
| F4 逐日 chain | `tests/research/workflows/test_paper_replay.py` |
| F5 OOS sealed vault | `tests/validation/test_gate_machine.py` |
| F6 EX-002 批次超限 | `tests/orchestration/test_daily_flow.py` |

當前 BDD scenarios 為**文檔**形式（給人讀），未自動化執行。若要用 `behave` / `pytest-bdd` 把 `.feature` 自動跑起來，列入後續待補事項。

---

## 測試金字塔（總覽，詳見 [22_test_strategy.md](./22_test_strategy.md)）

本節為 22 號文件的高層摘要，完整測試規範（比例、工具、CI/CD 整合）以 22 為準。

```
           ┌──────────────────┐
           │   E2E  (10%)     │  pytest + zipline run + docker
           ├──────────────────┤
           │ Integration (20%)│  pytest + docker-compose；DB / API / 對拍
           ├──────────────────┤
           │   Unit  (70%)    │  pytest + hypothesis；pure functions / adapters
           └──────────────────┘
```

| 層 | 比例 | 跑時 | 失敗影響 |
| :--- | :---: | :--- | :--- |
| Unit | 70% | < 30s | block PR |
| Integration | 20% | < 5min | block PR |
| E2E | 10% | < 30min | block release |
| 對拍 (Recon) | 跨層 | < 10min | block milestone |
| Performance | 跨層 | < 2h | warn only |

### 對拍測試矩陣（跨引擎一致性）

| ID | 對拍對 | 容忍 | 失敗動作 |
| :--- | :--- | :--- | :--- |
| R-001 | Zipline vs vectorbt | 相對 1% / 絕對 10bps | 找撮合假設差異 |
| R-002 | 向量化 sim vs 逐單 paper | 相對 1% / 絕對 10bps | 模擬精度問題 |
| R-003 | FinLab vs FinMind OHLCV | < 1% | log + 採 FinLab |
| R-004 | 自寫 PBO vs pypbo | < 1e-4 | 數學 bug |

BDD scenarios（F1–F6）對應 unit + integration + E2E 三層的**行為敘述**；22 號補完比例、工具、執行策略與 CI/CD 整合。寫 BDD scenario → 產出 pytest test 案例。
