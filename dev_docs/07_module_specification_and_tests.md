# 模組規格與測試 — backtest_platform

> 對應架構文件 [05](./05_architecture_and_design_document.md)、類別關係 [10](./10_class_relationships_template.md)、BDD [03](./03_behavior_driven_development_guide.md)。本檔以契約式設計（DbC）規格核心模組，每模組列職責 / 公開介面 / 前置後置條件 / 對應測試檔（`backtest_platform/tests/` 現行檔案）。

## 產品定位

backtest_platform 是 **個人量化 edge 驗證工廠 + 晉升管線**。核心資產是審判庭。以下規格的重心依價值鏈排列：**策略契約 → 研究工作流 → 審判庭 → 風控 → 每日鏈 → 資料層**。策略是消耗品，這些模組是資產——所以它們的前置後置條件寫得比策略本身嚴。

---

## 一、策略契約層 `strategies/`

### 1.1 `strategies.protocol` — StrategyRunner 契約 + registry（ADR-027/028）

**職責**：定義平台↔策略的唯一接縫（畫在**輸出** `StrategyRun`），並提供 name→runner registry 供上層 dispatch。

**公開介面**：
- `StrategyRunner`（Protocol）：`config_model` / `title` / `gate` ClassVar + `run(symbols, start, end, config, loader) -> StrategyRun`
- `register_strategy(name)` 裝飾器、`get_strategy(name)`、`get_strategy_gate(name)`、`list_strategies()`、`describe_strategies()`
- `StrategyRun`（frozen）：`metrics` / `returns` / `trades`；`GateSpec = tuple[Criterion, ...]`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | 1. `name` 已註冊（否則 `get_strategy` raise ValueError 附可選清單）<br>2. `config` 是 `config_model(**params)` 的已驗證輸出（runner 不得再包 isinstance 守衛）|
| **後置** | 1. `run(...)` 回 `StrategyRun`，`metrics ⊇ {cagr, sharpe, slippage_sharpe, maxdd, trades, bars}`（空結果亦全填 0）<br>2. `get_strategy_gate(name)` 回策略宣告的 `gate`；未宣告 = hard error（拒用別人的尺）|
| **不變性** | 1. 重複註冊同名 raise ValueError（抓 duplicate import）<br>2. registry 為 name→instance dict |

**對應測試**：`tests/strategies/test_protocol.py`、`test_dependency_untangle.py`

### 1.2 `strategies.conformance` — 契約合規閘

**職責**：對任一已註冊 runner 證明其滿足契約，供 CI parametrized 與 CLI `validate-strategy`。

**公開介面**：`synthetic_loader(n_bars, seed) -> Loader`、`check_conformance(name) -> ConformanceReport`；`REQUIRED_METRIC_KEYS = {cagr, sharpe, slippage_sharpe, maxdd, trades, bars}`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | runner 已註冊；synthetic loader 產出正規化 merged panel（doc 21 欄位）|
| **後置** | `ConformanceReport.ok` ⟺ `config_model()` 無參可建 ∧ `run` 不 raise ∧ metrics ⊇ 必需 keys ∧ gate 已宣告且 criterion key ⊆ 產出 metrics |
| **不變性** | 對合成資料同 seed 同結果 |

**對應測試**：`tests/strategies/test_conformance.py`（parametrized over `list_strategies()`，4/4 PASS）

---

## 二、研究工作流 `research/workflows/`（ADR-029/032）

五個泛用工作流，全走 `get_strategy(name).run(...)` dispatch，**絕不直接 import 策略 backtest 函式**（AST 測試守 invariant）。各策略以 `research_config.py` 宣告 config。

### 2.1 `run_doe(cfg: DOEConfig, loader) -> DOEResult`

**職責**：對參數網格系統化掃描（first-read）。

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `cfg.grid` 非空、`cfg.symbols` 非空、`is_start < is_end`（frozen validator）|
| **後置** | 回 `n_configs = Π(grid 軸長)` 筆結果；`DOEResult.best(key)` / `.to_dataframe()` 可用 |
| **不變性** | 每筆經 registry dispatch，不假設 `name==目錄名` |

**對應測試**：`tests/research/workflows/test_doe.py`

### 2.2 `run_go_gates(cfg: GOGatesConfig, loader) -> GOGatesResult`

**職責**：對 fixed_config 跑 WFA + 對 landscape 跑 PBO（config_grid=None → 只跑 WFA）。

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `fixed_config` 為策略的 config model；`n_wfa_folds ∈ [2,20]`、`pbo_n_splits ≥ 2`（偶數）|
| **後置** | 回 WFA OOS 廣度 + PBO（若有 grid）；PBO 走 `validation.pbo.probability_of_backtest_overfitting` |

**對應測試**：`tests/research/workflows/test_go_gates.py`

### 2.3 `run_truth_gate(cfg: TruthGateConfig, loader=None) -> TruthGateResult`（審判庭主線）

**職責**：ADR-025 兩段閘的可重現判決入口。真偽閘 hard-fail + 配置閘 sizing。

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `is_start < oos_start < is_end`（frozen validator）；`survivorship_clean` 由策略 `research_config` 或 universe builder 宣告 True 才可能 REAL（預設 False）|
| **後置** | 1. 真正讀 OOS holdout `[oos_start, is_end]`（非全在 IS 內）<br>2. DSR 走 `validation.dsr` 正確路徑（per-period SR + cross-trial variance），缺誠實來源即 raise<br>3. 回 `TruthVerdict.{REAL, REJECTED, INCOMPLETE}`（ADR-030）|
| **不變性** | `parquet_dir` 設定時經 `_resolve_loader` 路由至該快取（[ADR-032](./adrs/ADR-032-survivorship-universe-workflow.md)），caller 免傳 loader；滑價壓力測試走契約 `slippage_sharpe`，不另造第三套 |

**對應測試**：`tests/research/workflows/test_truth_gate.py`、`test_truth_gate_judgement.py`（含已知 REJECTED oracle）、`test_truth_gate_parquet_dir.py`

### 2.4 `run_paper_replay_workflow(cfg: PaperReplayConfig, loader) -> PaperReplayResult`

**職責**：對過真偽閘候選逐日跑 chain（接真 daemon 前先驗晉升鏈）。

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `as_of` 提供、`lookback_buffer_days ≥ 30` 讓 runner 有足夠歷史 |
| **後置** | 跑 `runner.run(symbols, as_of - lookback, as_of, fixed_config, loader)` → 經 `get_strategy_gate` 判決 |

**對應測試**：`tests/research/workflows/test_paper_replay.py`

### 2.5 `run_build_universe(cfg: UniverseConfig, getter=None) -> UniverseBuildResult`（ADR-032）

**職責**：從 FinLab 寬表建 survivorship-clean universe → ingest → 寫 provenance。

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `span_start < span_end`、`top_n ≥ 1`、`min_turnover ≥ 0`；`finlab` 僅 `getter=None` 時 lazy import（頂層零依賴）|
| **後置** | 季度 rebalance → `select_survivorship_universe` → `ingest_universe_finlab` → 寫 `universe_manifest.json`（bundle provenance）|

**對應測試**：`tests/research/workflows/test_universe.py`；config/loader → `test_workflow_config.py`、`test_workflow_loader.py`

---

## 三、審判庭 `validation/`（核心資產）

> gate-as-code：門檻是資料（`Criterion` / 模組常數），調門檻 = 可見可記錄決策。純函式，零 IO。

### 3.1 `two_stage_gate` — 真偽閘 + 配置閘（ADR-025）

**公開介面**：`evaluate_truth_gate(TruthGateInput) -> TruthGateResult`、`compute_position_size(SizingInput, SizingConfig) -> float`、`evaluate_two_stage(...) -> GateDecision`、`fleet_correlation(candidate, fleet) -> float`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `TruthGateInput.survivorship_clean` / `pre_registered` 決定分支；門檻常數 `PBO_MAX=0.30`、`WFA_OOS_POSITIVE_MIN=0.60`、`DSR_MIN=0.95` |
| **後置** | 1. `pre_registered=True` 用 WFA OOS 廣度 + DSR（不用 landscape PBO）；`False` 用 PBO<br>2. survivorship 不 clean / 滑價 ≤0 / OOS holdout ≤0 → REJECTED（REJECTED 蓋過 INCOMPLETE）<br>3. `compute_position_size`：Sharpe≤0 → 0；否則 `max_weight × conviction × diversification × capacity`；絕對 CAGR 永不 size |
| **不變性** | truth 非 REAL → `GateDecision.size == 0.0` |

**對應測試**：`tests/validation/test_two_stage_gate.py`

### 3.2 `dsr` — Deflated Sharpe Ratio（Bailey & López de Prado 2014）

**公開介面**：`deflated_sharpe_ratio(sr, n_trials, n_obs, skew, kurtosis, sharpe_variance) -> float`、`psr(...)`、`expected_max_sharpe(n_trials, variance_of_sharpes)`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `n_obs > 1`、`n_trials ≥ 1`、`sharpe_variance ≥ 0`（輸入衛兵 raise on 違反）|
| **後置** | 回 `PSR(SR*)`，`SR* = E[max_n SR_n]`；ADR-016 M3 門檻 `DSR > 0.95` |
| **不變性** | DSR 對 `n_trials` 單調不增（試驗越多、通縮越狠）|

**對應測試**：`tests/validation/test_dsr.py`（對 Bailey 論文範例數值匹配）

### 3.3 `pbo` — Probability of Backtest Overfitting（CSCV，自寫避 pypbo AGPL）

**公開介面**：`probability_of_backtest_overfitting(returns_matrix, n_splits=16, metric=sharpe_metric) -> float`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `returns_matrix` shape `(T, N_configs)`；`n_splits` 為偶數 |
| **後置** | 回 `[0,1]`；列舉 `C(S, S/2)` 對稱 IS/OOS 切分（S=16 → 12870 組合）|

**對應測試**：`tests/validation/test_pbo.py`

### 3.4 `wfa` — Walk-Forward 切分器

**公開介面**：`walk_forward_splits(start, end, is_days, oos_days, step_days=None, purge_days=0, embargo_days=0, *, anchored=False) -> list[WFAFold]`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `[start, end)`（end 排他）；`is_days`/`oos_days > 0` |
| **後置** | 回 `WFAFold` 列表；`step_days=None` → OOS 相鄰不重疊；purge/embargo 依 AFML §7.4.1 |
| **不變性** | fold 之間 OOS 不重疊（property 測試守）|

**對應測試**：`tests/validation/test_wfa.py`

### 3.5 `gate_state` + `gate_machine` — 逐 criterion 判決 + 晉升狀態機

**公開介面**：`evaluate_gate(metrics, gate) -> GateResult`；`ValidationGate`（`submit_is` → `submit_wfa` → `submit_oos` → `approve`）、`OOSSealedError`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | metrics 為 mapping；gate 為 `Criterion` 元組 |
| **後置** | 缺 metric → `INCOMPLETE`（絕不假 PASS）；OOS sealed vault：前置 gate 未過前 `read_oos` raise `OOSSealedError`、存取計次留痕 |
| **不變性** | 狀態不可回退（IS→WFA→OOS→APPROVED 單向）|

**對應測試**：`tests/validation/test_gate_state.py`、`test_gate_machine.py`

---

## 四、風控 `risk/`（spec 24）

### 4.1 `risk_gate.RiskGate` — 12 個 pre-trade 檢查（EX-001..EX-012）

**職責**：strategy-agnostic ex-ante 風控閘，注入 `AccountState` 快照 + `RiskGateConfig` 門檻，回可否下單。

**公開介面**：`RiskGate.check(order, account_state, *, collect_all=False) -> RiskGateResult`；12 個 `check_exNNN` 純函式；`risk_spec(config)` 唯讀投影

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `order.side ∈ {buy,add,sell,reduce,exit,stoploss}`、`qty ≥ 0`、`equity ≥ 0`（否則 raise ValueError）|
| **後置** | `allowed ⟺ rejections 空`；`rejections` 為有序 `(rule_id, reason)`（審計軌）；預設 fail-fast，`collect_all=True` 全掃 |
| **不變性** | 依 spec §2.2 優先序（EX-012 熔斷最先、heat 較後）；EX-012 對 `L3`/`HALTED` 皆 reject；never mutate 輸入（frozen 值物件）|

**對應測試**：`tests/risk/test_risk_gate.py`

### 4.2 `circuit_breaker.CircuitBreaker` — 三級熔斷狀態機

**公開介面**：`evaluate(RiskMetrics) -> BreakerState`、`reset(reason)`、`should_halt()` / `should_reduce()` / `should_block_new_entries()`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `CircuitBreakerConfig` 門檻（DD / 連虧等）；`RiskMetrics` 快照 |
| **後置** | 產生瞬態 `L3` 後 latch 進終端 `HALTED`（只有 `reset` 清）；`transitions` 留完整軌跡 |
| **不變性** | `BreakerState.severity` 單調；與 `risk_gate` 共用單一 `risk/types.BreakerState`（避免 enum 分岔）|

**對應測試**：`tests/risk/test_circuit_breaker.py`

---

## 五、編排 `orchestration/`

### 5.1 `daily_flow` — staged 每日鏈引擎

**公開介面**：`run_flow(stages, ctx) -> FlowRun`、`build_daily_stages()`（etl→signals→risk_gate→orders→log）、`demo_stages()`、`as_prefect_flow(...)`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | collaborators（`ingest`/`signal_fn`/`risk_check`/`place`/`sink`）經 `FlowContext.config` 注入；缺席 → stage `ok=False`（非 raise）|
| **後置** | 依序跑，**fail-fast**（首個 `ok=False` 或 raise 即停）；raise 被捕捉成失敗 stage，**永不 crash 排程器**；`FlowRun` 列所有實際執行 stage |
| **不變性** | stage body 只編排；risk_gate reject → 不下單（halt）|

**對應測試**：`tests/orchestration/test_daily_flow.py`

### 5.2 `collaborators` — production paper 鏈接線工廠

**職責**：把 `PaperBroker` / `RiskGate` / DB sink wire 成 daily_flow collaborators。

**公開介面**：`build_paper_collaborators(...)`、`make_risk_check(broker, gate)`、`make_place(broker)`、`make_ingest(source=)`、`make_db_sink(...)`

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `broker` 為 `PaperBroker`；side 詞彙需轉換（`add→buy`、`reduce/exit/stoploss→sell`，`_broker_side`）|
| **後置** | `make_risk_check` 從 `broker.portfolio_snapshot` 建 `AccountState`（真實部位、非空倉）、批次內遞減現金；`make_place` 撮合並回 `Fill`；`make_db_sink` upsert signals/fills/equity（fills 串 strategy_id，ADR-038）|

**對應測試**：`tests/orchestration/test_collaborators.py`、`test_chain_integration.py`

---

## 六、資料層 `data/`

### 6.1 `finlab_source` — FinLab 付費主源（ADR-006/032）

**職責**：FinLab 全史寬表 → per-stock `ETLBundle`、survivorship universe 建構、ingest。

**公開介面**：`ingest_universe_finlab(...)`、`build_survivorship_universe(...)`、`login()`；`Getter` 抽象（測試注入）

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `finlab` 僅 `getter=None` 時 lazy import；日期窗序正確 |
| **後置** | 回 `FinlabIngestResult`；FinLab 已預調整（無需前復權）|

**對應測試**：`tests/data/test_finlab_source.py`

### 6.2 `finmind_etl.fetch_bundle` — FinMind 免費 fallback

| 類型 | 條件 |
| :--- | :--- |
| **前置** | `stock_id` 非空、`start ≤ end`；`FinMind` lazy import |
| **後置** | 回 `ETLBundle` 三表（即使空亦有 columns）；`_normalize_*` 隔離 FinMind raw schema；rate-limit 不被忽略 |
| **不變性** | FinMind exception 往上拋，不靜默吞 |

**對應測試**：`tests/data/test_finmind_etl.py`、`test_adjustment.py`

### 6.3 `db_writer` / `db_reader` — TimescaleDB IO

| 類型 | 條件 |
| :--- | :--- |
| **前置** | DDL 已建（`docker/timescaledb/init.sql`）；欄位符合 doc 21 契約（`test_init_sql_schema.py` 守 drift）|
| **後置** | `upsert_*` idempotent（`ON CONFLICT DO UPDATE`）；`db_reader.fleet_summary` DISTINCT-ON 每策略最新淨值 |

**對應測試**：`tests/data/test_db_writer.py`（含 `@integration`）、`test_init_sql_schema.py`、`test_universe_builder.py`

---

## 測試體系總覽

| 層 | 目錄 | 重點 |
| :--- | :--- | :--- |
| 策略契約 | `tests/strategies/` | 契約 + conformance（parametrized）+ dependency-untangle |
| 研究工作流 | `tests/research/workflows/` | dispatch invariant（AST）+ truth-gate 判決 oracle |
| 審判庭 | `tests/validation/` | DSR/PBO/WFA 對論文範例；two-stage 判決 |
| 風控 | `tests/risk/` | 12 檢查 + 熔斷 latch |
| 編排 / 運維 | `tests/orchestration/`、`tests/runtime/` | staged flow + paper 鏈整合 |
| 資料 / API | `tests/data/`、`tests/api/` | schema drift + envelope 契約 + zones smoke |

執行：`uv run pytest`（現況 1116 passed / coverage ~92.6%）；CI 三 job hard gate（pytest+coverage / tsc+vitest / contract-drift）。標記：`@integration`（DB/FinMind/FinLab）、`@slow`、`@recon`（跨引擎對拍）、`@e2e`、`@live`（Shioaji，M5）。
