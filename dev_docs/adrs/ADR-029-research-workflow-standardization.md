# ADR-029: Research Workflow Standardization

**Date:** 2026-06-16
**Status:** Accepted
**Extends:** [ADR-028](./ADR-028-strategy-dispatch-contract.md)（strategy dispatch contract）、[ADR-027](./ADR-027-strategy-contract-and-registry.md)（strategy contract + registry）
**Related:** ADR-025（two-stage validation gate）、ADR-023/024（momentum / inst_flow verdicts the migrated configs reproduce）

---

## Context

`backtest_platform/scripts/` 有 7 支 `inst_flow_*.py` 一次性研究腳本（DOE / GO gates /
survivorship / truth gate / FinLab 重驗 / paper replay / daemon replay）。每一支**既是
workflow 定義、又是 strategy-specific runner**：universe、grid、fixed config、視窗全部
硬編碼在腳本裡。要為 `multi_factor` 做同樣研究就得複製 7 支再各自改。它們也繞過 ADR-028
dispatch（直接呼叫 `backtest_inst_flow`），是「特化模組淪為意外 runner」的反模式。

## Decisions

| # | 決策 |
| :--- | :--- |
| D1 | 通用工作流住 `research/workflows/`（`doe` / `go_gates` / `truth_gate` / `paper_replay`），全部呼叫 `get_strategy(name).run(...)`，**絕不直接 import 任何策略的 backtest 函式**（AST 測試守門）。|
| D2 | 每隻策略以 `strategies/<pkg>/research_config.py` 宣告 `DOE` / `GO_GATES` / `TRUTH_GATE` / `PAPER_REPLAY`（`config.py` 的 frozen Pydantic 模型）。策略作者填參數，不寫工作流邏輯。|
| D3 | name→package 由 dispatch registry 解析（`runner.__module__`），**不假設 name == 目錄名**（`four_layer`→`four_layer_resonance`、`template`→`_template`）。|
| D4 | CLI：`research.cli` 加 `doe` / `go-gates` / `truth-gate` / `paper-replay`（`--dry-run`、doe 支援 `--is-start/--is-end/--out-csv`）。|
| D5 | HTTP：`POST /research/workflows/{workflow}`（經 `jobs/` 非同步，202 `{job_id,status}`）+ `GET /research/workflows/{strategy}`（列宣告的工作流）。|
| D6 | `backtest_platform/scripts/` 7 支全數刪除。|

## Consequences

**正面：**
- 新增一隻策略要參與**所有**研究工作流 = 只寫一個 `research_config.py`，零新腳本。
- 所有研究工作流走 ADR-028 dispatch（params 經 `config_model` 驗證），口徑統一。
- `inst_flow` 的 universe / grid / fixed config 從腳本遷入 `research_config.py`，是該策略
  ADR-024/025 判決的可重現宣告。

**接受的代價 / 刻意延後：**
- `inst_flow_revalidate_finlab.py`（FinLab survivorship-clean universe 建構）與
  `inst_flow_daemon_replay.py`（forward-live 排程）的**特有編排邏輯未遷入** `workflows/`——
  前者屬 sub-project ②（dynamic registry + sandbox）、後者屬 8.H.8（真實日曆時間 daemon）。
  其程式碼保存在 git 歷史，需要時於對應 sub-project 以符合 dispatch 契約的方式重實作。
- DOE 結果不寫入 runs ledger（DOE ≠ 單一 RunConfig IS run）；CLI 印出 + 可選 `--out-csv`，
  HTTP 經 job 結果回傳。

## 受影響模組

新增 `research/workflows/`（config/loader/doe/go_gates/truth_gate/paper_replay）、4 個
`strategies/<name>/research_config.py`、`api/routers/research_workflows.py`。修改
`research/cli.py`、`api/app.py`。刪除 `backtest_platform/scripts/`。
