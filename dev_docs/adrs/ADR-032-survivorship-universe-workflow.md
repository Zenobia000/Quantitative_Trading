# ADR-032: Survivorship-Clean Universe Build as a Platform Workflow

**Date:** 2026-07-02
**Status:** Accepted
**Extends:** [ADR-029](./ADR-029-research-workflow-standardization.md)（research workflow standardization）
**Related:** [ADR-030](./ADR-030-truth-gate-judgement-fix.md)（truth gate judgement fix / anti-self-deception）、[ADR-024](./ADR-024-institutional-flow-candidate-strategy.md)（inst_flow survivorship false-positive）、[ADR-025](./ADR-025-two-stage-validation-gate-and-paper-promotion.md)（two-stage gate）、[ADR-006](./ADR-006-data-source-finlab-paid.md)（FinLab primary source）

---

## Context

ADR-029 標準化研究工作流時，**刻意延後**了 `scripts/inst_flow_revalidate_finlab.py`
（FinLab survivorship-clean universe 建構）的遷移，理由是它屬 sub-project ②。該 driver
很薄，核心 API 一直存活（`data/finlab_source.py` 的 `login`/`_default_getter`/
`ingest_universe_finlab`、`research/finlab_universe.py` 的 `select_survivorship_universe`），
只是缺一個「策略宣告 → 平台執行」的入口。

2026-07-02 修正後審判庭（ADR-030）上線後，用**現行程式路徑**重跑
`truth-gate --strategy inst_flow` → **REJECTED**（DSR 0.789 < 0.95、WFA OOS+ 33% < 60%、
survivorship hard-fail）。原因是現行 `TRUTH_GATE` 只綁著 ADR-024 判定為**假陽性**的
survivor-only 40 檔（`_WIDE`）。既往「TRUTH GATE REAL」（2026-06-15，FinLab
survivorship-clean 全史 universe，423 檔含下市股）**在現行路徑無法重現**——因為那份
survivorship-clean universe 的建構器已隨 ADR-029 的 scripts 清除，只存在 git 歷史。

要誠實重驗，必須先把 universe 建構器**平台化**（可重跑、有 provenance），再讓 inst_flow
的真偽閘宣告**跟著資料走**，而不是硬編一個 survivorship_clean 常數。

## Decisions

| # | 決策 |
| :--- | :--- |
| D1 | universe 建構成為平台工作流 `research/workflows/universe.py::run_build_universe(cfg, getter=None)`：fetch FinLab 寬表（market cap / adj-close / turnover）→ `select_survivorship_universe`（季度 rebalance、point-in-time、含下市）→ `ingest_universe_finlab` 寫專屬 parquet cache → 寫 `universe_manifest.json`（params / symbols / n_alive / n_delisted / ingest ok·failed / generated_at）。回傳 frozen `UniverseBuildResult`。|
| D2 | 策略以 `research_config.UNIVERSE`（frozen `UniverseConfig`：strategy / span / top_n / min_turnover / cache_dir，rebalance 固定季度）宣告建構參數，與 ADR-029 的 DOE/GO_GATES/... 同一「declare-then-execute」契約。|
| D3 | finlab **只在 `getter=None` 時** lazy import（`finlab_source.login()` + `_default_getter()`）；模組頂層絕不 import finlab（CI 無此依賴，測試用 fake getter + 合成寬表）。ingest 失敗數 surface 到 result 與 manifest，絕不靜默吞錯。|
| D4 | `TruthGateConfig` 新增 `parquet_dir: str \| None = None`（資料快取覆蓋）。`run_truth_gate` 的 loader 參數改 `loader=None`：顯式傳 loader 仍勝出（tests 不受影響）；否則 `cfg.parquet_dir` 有值 → `partial(load_merged_parquet, parquet_dir=…)`，None → 預設 `data/parquet`。CLI/HTTP 派發不再顯式傳 loader，讓 config 生效。|
| D5 | **真偽閘宣告跟著 cache 走**（反自欺，ADR-030 原則的資料層落地）：inst_flow `TRUTH_GATE` 條件建構——`cached_universe_symbols(cache_dir)` 掃到料時宣告 `survivorship_clean=True`、`symbols=乾淨 universe`、`parquet_dir=cache`、窗口 2010/2021/2024；缺席時維持 survivor-only `_WIDE` fallback（`survivorship_clean` 預設 False、2015/2021/2024）。cache 即證據，宣告不是硬編常數。|
| D6 | 入口比照 ADR-029：CLI `build-universe --strategy --dry-run`、HTTP `_WORKFLOWS` map 加 `build_universe`（沿用既有 tuple 形狀，經 `jobs/` 非同步）。`get_universe_config` 刻意**不進** `_WORKFLOW_ATTRS`/`list_workflow_configs`——`build_universe` 是資料備料工作流，非驅動 `get_strategy().run()` 的策略研究工作流。|

## Consequences

**正面：**
- inst_flow 的 survivorship-clean 重驗從一次性 script 變成可重跑、有 manifest provenance 的
  平台工作流；任何策略只要宣告 `UNIVERSE` 即可建自己的乾淨 universe，零新腳本（延續 ADR-029）。
- 「survivorship_clean」不再可能被硬編成免死金牌：cache 存在才宣告 clean，且 `parquet_dir`
  讓真偽閘實際讀那份乾淨資料。**宣告、資料、判決三者對齊**（ADR-030 反自欺）。
- `parquet_dir` 是通用資料覆蓋，未來任何策略要對非預設 cache 跑真偽閘都能用。

**接受的代價 / 待辦：**
- 本 PR 只落地**工作流與宣告接線**，未執行真實重驗（worktree 無 FinLab 資料、CI 無 finlab
  依賴）。真實 2010→2024 全史 ingest + 重驗須在有 `FINLAB_API_TOKEN` 的環境跑
  `build-universe` 後再跑 `truth-gate`；在此之前 inst_flow 維持 REJECTED（fallback 態），
  paper-ready 地位續 gated。
- `run_build_universe` 直接執行（非經 job ledger）；HTTP 路徑經 `jobs/` 非同步回傳
  `{job_id,status}`，結果在 manifest + job result。

## 受影響模組

新增 `research/workflows/universe.py`、`research/finlab_universe.cached_universe_symbols`。
修改 `research/workflows/config.py`（`UniverseConfig` + `TruthGateConfig.parquet_dir`）、
`research/workflows/loader.py`（`get_universe_config`）、`research/workflows/truth_gate.py`
（`loader=None` + `_resolve_loader`）、`research/cli.py`（`build-universe` + truth-gate 不傳
loader）、`api/routers/research_workflows.py`（`_WORKFLOWS` 加 `build_universe`）、
`strategies/inst_flow/research_config.py`（`UNIVERSE` + 條件式 `TRUTH_GATE`）。
OpenAPI 無變（`POST /research/workflows/{workflow}` 為字串 path param，非 enum）。
