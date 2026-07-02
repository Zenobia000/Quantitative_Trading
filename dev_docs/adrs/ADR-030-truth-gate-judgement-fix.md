# ADR-030: 修正真偽閘（審判庭）四個判決缺陷 — DSR 單位、OOS holdout、生存者宣告、配置閘接線

> **狀態：** 已接受 | **日期：** 2026-07-02 | **決策者：** Self
> **修正（amends）：** [ADR-025](./ADR-025-two-stage-validation-gate-and-paper-promotion.md)（驗證閘兩段化）— 本 ADR 修正 ADR-025 §3.1 真偽閘在 `research/workflows/truth_gate.py` 的實作缺陷，不改變其判準與哲學
> **相關：** [ADR-016](./ADR-016-m2-acceptance-kpi-freeze.md)（DSR>0.95 部署門檻）、[ADR-024](./ADR-024-institutional-flow-candidate-strategy.md)（inst_flow 候選）、[ADR-029](./ADR-029-research-workflow-standardization.md)（研究工作流標準化）

---

## 1. 背景與問題

ADR-025 把驗證閘拆成「真偽閘（防自欺、binary hard-fail）+ 配置閘（決定 size、連續）」，並在 ADR-029 落地為 `research/workflows/truth_gate.py` 的 `run_truth_gate` 泛用工作流。實地審查（2026-07-02）發現該實作有**四個已證實缺陷**，使真偽閘無法真正防自欺——最嚴重者讓一個年化 Sharpe 僅 0.333 的策略被判為 DSR=1.000000（確定有 edge），並據此產出過去的「inst_flow TRUTH GATE REAL」判決。

### 缺陷 1 — DSR 計算單位錯誤（CRITICAL）

`truth_gate.py` 把 `run.metrics["sharpe"]`（**年化** Sharpe，已 ×√252）當作 `sr`，並把 `rets.var()`（**日報酬變異數**）當作 `sharpe_variance`（跨試驗 Sharpe 變異 `V[SR_n]`）餵進 `deflated_sharpe_ratio`。但 Bailey & López de Prado 的 DSR 公式要求 **per-period Sharpe** 搭配 **同單位的跨試驗 Sharpe 變異**——兩者單位皆錯。

實測（年化 0.333、n_obs=1260、n_trials=16、高斯矩）：

| 路徑 | `sr` | `sharpe_variance` | DSR | 判決 |
| :--- | :--- | :--- | :--- | :--- |
| **舊（bug）** | 0.333（年化）| ~1e-4（日報酬變異數）| **1.000000** | 🟢 誤判 REAL |
| **修正後** | 0.02098（per-period = 0.333/√252）| 7.94e-4（V[SR_n]）| **0.145310** | 🔴 REJECTED |

n_trials 通縮完全失效：年化 SR 遠大於錯配的 SR*（≈0.018），PSR 飽和到 1.0。同 codebase `validation/full_report.py:37-40` 早有正確的 per-period 實作可對照。

### 缺陷 2 — OOS holdout 從未被評估（CRITICAL）

`TruthGateConfig` 宣稱 `OOS = [oos_start, is_end]`，但 full-span run 只跑 `is_start → oos_start`（IS 區間），holdout 資料**零讀取**（`grep is_end truth_gate.py` 零命中）。鎖定不可觸碰的 OOS holdout 是 pre-registered 策略最終的誠實檢驗，卻整段缺席。

### 缺陷 3 — `survivorship_clean` 寫死 True

`evaluate_truth_gate` 的 hard precondition `survivorship_clean` 在 workflow 端被寫死 `True`，讓 ADR-025 最硬的生存者前提永遠亮綠——任何 universe 都自動通過。

### 缺陷 4 — `validation/dsr.py` 無輸入衛兵

對「年化 SR + 日變異數」這種明顯單位錯配的輸入不報錯，靜默回傳 1.0，讓缺陷 1 無聲通過。

### 缺陷 5 — 配置閘（SizingGate）零 production 呼叫者

ADR-025 第二段的 `compute_position_size` / `evaluate_two_stage` 在 `src/` 無任何 production 呼叫點，「過真偽閘 → 配置 size」的兩段設計在工作流層斷線。

---

## 2. 考量的選項

### 選項一：維持現狀，僅記錄缺陷
- **拒絕**：DSR=1.0 的誤判會被下游 gate machine / 晉升狀態機採信，等於平台在自欺。

### 選項二：DSR 改用 WFA 折的 Sharpe 離散度當 `V[SR_n]`
- **描述**：以 3-5 個 WFA fold OOS Sharpe 的變異數（轉 per-period）作為跨試驗變異。
- **缺點**：折數過少、量的是**體制離散**而非**配置選擇離散**、估計極不穩。**拒絕**。

### 選項三（★採納）：per-period + 虛無假設估計量變異 + holdout 入判 + config 化生存者 + 接線配置閘
- **描述**：見 §3。DSR 用 per-period Sharpe，`V[SR_n]` 取**虛無假設下單試驗 Sharpe 估計量的抽樣變異**（Lo 2002）；OOS holdout 實跑並入判；`survivorship_clean` 由 config 宣告、預設 False；真偽閘 REAL 後接 `evaluate_two_stage` 產出倉位；`dsr.py` 加單位衛兵。
- **優點**：修全部五缺陷、與 `full_report.py` 既有正確實作對齊、對 ADR-025 判準零改動（只修實作）。

---

## 3. 決策

**採納選項三。** 保持 ADR-025 的判準（DSR>0.95、WFA OOS>0 breadth≥0.6、滑點 Sharpe>0、survivorship-clean）不變，只修實作。

### 3.1 DSR 單位修正（缺陷 1）
新增 `truth_gate._deflated_sharpe(returns, n_trials)`：
1. 從**日報酬**重算 per-period Sharpe = `mean / std(ddof=0)`（**絕不**用年化 metrics["sharpe"]）。
2. `V[SR_n]` 取**單試驗估計量抽樣變異** `(1 − γ3·SR + (γ4−1)/4·SR²)/(n_obs−1)`（PSR 分母 / (n−1)，Lo 2002）。虛無假設下 N 個試驗 Sharpe 是繞 0 的雜訊抽樣、變異恰為此值——這是**最寬鬆的誠實通縮**：若策略在此仍不過，即為確定不過。
3. pandas excess kurtosis + 3.0 → raw kurtosis。

### 3.2 OOS holdout 入判（缺陷 2）
`run_truth_gate` 實跑 `runner.run(symbols, oos_start, is_end, …)`，取年化 holdout Sharpe，經 `TruthGateInput.oos_holdout_sharpe`（新增、選填）進入 `evaluate_truth_gate`；holdout Sharpe ≤ 0（`OOS_HOLDOUT_SHARPE_MIN`）即 REJECTED。選填設計對既有呼叫者零破壞（None → 不檢查）。

### 3.3 `survivorship_clean` config 化（缺陷 3）
`TruthGateConfig` 新增 `survivorship_clean: bool = False`。工作流讀 `cfg.survivorship_clean`。預設 False → 未宣告即維持 hard-fail 武裝；各策略須由 `research_config.py` 的 `TRUTH_GATE`（或 universe 建構器）明文宣告 True 才可能過閘。

### 3.4 `dsr.py` 輸入衛兵（缺陷 4）
`deflated_sharpe_ratio` 前置 `_validate_dsr_inputs`：非有限值（NaN/inf）快速失敗；`n_trials>1` 且 `sharpe_variance>0` 時，若其低於單試驗估計量變異的 `0.5×` 下限即報錯——真實 `V[SR_n]` 不可能低於單一試驗自身的估計雜訊，低於此下限即單位錯配（如把日報酬變異數當 Sharpe 變異）。`sharpe_variance==0`（明示無離散）與 `n_trials==1`（無通縮）維持合法。

### 3.5 接線配置閘（缺陷 5）
`run_truth_gate` 以 `evaluate_two_stage(TruthGateInput, SizingInput(oos_sharpe=holdout_sharpe))` 一次產出判決 + 倉位；`TruthGateResult` 新增 `position_size`、`oos_holdout_sharpe` 欄位（REAL → >0，非 REAL → 0.0）。

---

## 4. 影響與後果

### 4.1 對既往 inst_flow「TRUTH GATE REAL」判決的影響（必須重驗）
過去的 inst_flow REAL 判決是在**缺陷 1+3 同時存在**下產生的：DSR 被錯算成 1.0、survivorship 被寫死 True。**該判決作廢，須用修正後的閘重跑重驗**：
- DSR 將改以 per-period + 通縮門檻重算；年化 Sharpe 偏低者（如 0.333 級）會落到遠低於 0.95（示例 ≈0.15），判 REJECTED。
- `strategies/inst_flow/research_config.py` 的 `TRUTH_GATE` 目前未宣告 `survivorship_clean`，套用新預設 False 後真偽閘會因 survivorship 直接 REJECTED。**若 inst_flow 的 `_WIDE` universe 確為 survivorship-clean，需由該策略工作包在其 `research_config.py` 明文補上 `survivorship_clean=True` 後再重驗**（本 ADR 範圍不改 `strategies/`）。

### 4.2 破壞性變更
- `TruthGateConfig` 新增欄位 `survivorship_clean`（預設 False）：既有 `TRUTH_GATE` 宣告不需改即可載入，但**真偽閘結果會從隱性 True 變為顯性 False**，行為改變屬預期修正。
- `TruthGateResult` 新增 `position_size` / `oos_holdout_sharpe` 欄位：僅新增、對讀取舊欄位的 CLI / API 消費者向後相容。
- `deflated_sharpe_ratio` 對單位錯配輸入由「靜默回傳 1.0」改為「拋 ValueError」：任何依賴舊靜默行為者會快速失敗（即本修正目的）。

### 4.3 受影響模組
`research/workflows/truth_gate.py`、`research/workflows/config.py`、`validation/dsr.py`、`validation/two_stage_gate.py` 及對應測試。未觸 `strategies/`、`orchestration/`、`engines/`、`gate_state.py`（其他工作包擁有）。

### 4.4 後續動作
- [ ] inst_flow 工作包：於 `research_config.py` 宣告 `survivorship_clean`（若成立），並用修正後閘重跑真偽閘、更新 ADR-024 判決記錄。
- [ ] gate machine / 晉升狀態機：確認消費 `TruthGateResult` 時採信新的 DSR 與 `position_size`。
