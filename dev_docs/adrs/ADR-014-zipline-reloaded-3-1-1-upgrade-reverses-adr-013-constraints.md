# ADR-014: zipline-reloaded 3.0.4 → 3.1.1 升級，解鎖 pandas 2 / numpy 2 / vectorbt

> **狀態：** 已接受 | **日期：** 2026-06-01 | **決策者：** Self
> **Amends：** [ADR-013](./ADR-013-mainframe-zipline-reloaded-supersedes-tquant-lab.md) § 4 後果（負面）— 解除 pandas<2 / numpy<2 / Python<3.12 / vectorbt 暫停四項約束
> **Resumes：** [ADR-007](./ADR-007-dual-engine-zipline-vectorbt.md) vector 半邊（vectorbt）恢復可用，雙引擎方案完整回復
> **Implementation：** commit `b8dc5a9`（pyproject + uv.lock）+ commit `b5c97de`（validation 層加入 vectorbt cross-check）

---

## 1. 背景與問題

- **上下文**：ADR-013 鎖定 `zipline-reloaded==3.0.4` 作為 M2 主骨架。3.0.4 強制 `pandas<2` 與 `numpy<2`，導致：
  - **vectorbt 與本棧不相容**（vectorbt 依賴 pandas 2.x）— ADR-013 § 4 列為負面後果，ADR-007 雙引擎的 vector 半邊被迫暫停
  - `requires-python <3.12`（zipline-tej 同款限制延續）
  - 部分新版 numpy/pandas API 不可用
- **觸發事件**：`zipline-reloaded 3.1.1` 於 2026-06-01 釋出，原生支援 pandas 2 / numpy 2 / Python 3.12
- **問題**：是否升級？升級後能否真正同棧裝 vectorbt？M1 56 tests 在 pandas 2 下是否仍綠？
- **驅動因素 / 約束**：
  - ADR-013 § 4 三項負面後果若能解除，等於免費獲得 ADR-007 雙引擎方案完整能力
  - 不引入新引擎、不重寫 M1，純依賴版本升級
  - Sprint 2 acceptance 需 vectorbt vs self-written cross-check（ADR-013 §J recovery plan 之外的更強驗證）

---

## 2. 考量的選項

### 選項一：維持 zipline-reloaded 3.0.4
- **描述**：不動，vectorbt 半邊持續暫停，pandas / numpy 維持 1.x / 1.26
- **優點**：零變更風險
- **缺點**：
  - vectorbt cross-check 不可用，Sprint 2 cross-check 只剩 self-written vectorized PnL
  - 累積 pandas 1 → pandas 2 升級的技術債（社群多數套件 2026 年都已要求 pandas 2）
- **拒絕**：機會成本明顯大於變更風險

### 選項二：升級 zipline-reloaded 3.1.1 ★採納
- **描述**：pyproject 升 3.0.4 → 3.1.1；pandas / numpy 上限 ×2；engines extra 啟用 vectorbt>=1.0
- **優點**：
  - 解除 ADR-013 § 4 三項負面後果
  - vectorbt 同棧可用 → Sprint 2 cross-check 雙路驗證（self-written + vectorbt）
  - ADR-007 雙引擎方案完整回復，M3 grid/WFA 不需評估替代方案
  - 升級成本低：pyproject 替換 + uv lock 全量重解
- **缺點**：
  - 3.1.1 是新版本，可能存在未發現的 regression
  - pandas 1 → 2 對 M1 ETL 程式碼的相容性需驗證（雖然純 numpy/pandas 操作預期向後相容）
- **緩解**：M1 56 tests 全量跑驗證；保留回退路徑（git revert b8dc5a9 即恢復 3.0.4）

### 選項三：升級 + 改換次要引擎（如 polars-based grid）
- **描述**：除升級 zipline 外，把副引擎換成 polars
- **優點**：避開 vectorbt 任何潛在問題
- **缺點**：
  - 引入新生態系（polars 與 pandas 並存）
  - 偏離 ADR-007 既定方向
  - 為「臆想威脅」做過度工程（vectorbt 升級後並無問題）
- **拒絕**：違反實用主義原則

---

## 3. 決策

**選擇：選項二（升級至 zipline-reloaded 3.1.1）**

### 具體 pyproject 變更（已於 `b8dc5a9` 落地）

| 項目 | 升級前 | 升級後 |
| :--- | :--- | :--- |
| `requires-python` | `>=3.10,<3.12` | `>=3.10,<3.13`（支援 3.12） |
| `pandas` | `>=1.5,<2` | `>=2.0,<3` |
| `numpy` | `>=1.26,<2` | `>=2.0,<3` |
| `mainframe` extra | `zipline-reloaded==3.0.4` | `zipline-reloaded==3.1.1` |
| `sprint1` extra | `zipline-reloaded==3.0.4` | `zipline-reloaded==3.1.1` + `quantstats` + `empyrical-reloaded` + `vectorbt` |
| `engines` extra | `# "vectorbt>=0.26"  # disabled` | `vectorbt>=1.0`（啟用） |

### 驗證閘門

- ✅ **M1 regression**：M1 56 tests 在 pandas 2 下全綠（前置驗證）
- ✅ **vectorbt 同棧裝得起來**：`uv sync --extra sprint1` 一次解出包含 vectorbt 1.x 的鎖檔
- ✅ **vectorbt API 對齊**：`engines/zipline_adapter/validation/cross_check_vectorbt.py` 已能呼叫 `vectorbt.Portfolio.from_signals` 通過 smoke test（見 commit `b5c97de`）

---

## 4. 後果

### 正面
- ADR-013 § 4 標示為「負面」的三項約束全數解除（pandas<2 / numpy<2 / requires-python<3.12 / vectorbt 暫停）
- ADR-007 雙引擎方案完整回復，M3 grid/WFA 規劃毋需修訂
- Sprint 2 acceptance 可用 vectorbt + self-written 雙路 cross-check（互為驗證，PnL 兩份實作差異 < 1% 即 pass）
- 跟上 Python / pandas 主流版本，降低未來升級債

### 負面
- zipline-reloaded 3.1.1 為新版，可能存在未發現的 regression（暫未顯現；保留 git revert b8dc5a9 為回退路徑）
- pandas 1 → 2 API 變動：M1 純函式部分 deprecated warning 增加（不影響功能；建議 Sprint 2 後清理）

### 影響範圍
- `backtest_platform/pyproject.toml` + `uv.lock`（已落地於 `b8dc5a9`）
- `backtest_platform/src/backtest_platform/engines/zipline_adapter/validation/cross_check_vectorbt.py`（已落地於 `b5c97de`）— vectorbt-based cross-check 模組
- ADR-013：本 ADR 為其 amendment；負面後果章節需 cross-ref 本 ADR
- ADR-007：vector 半邊「pending」狀態取消
- 17 master plan v1.1 banner「vectorbt 半邊 pending」描述失效
- 18 reference architecture 框架比較表 vectorbt 列「pandas<2 暫停」失效
- 16 WBS 5.B.1 / 5.B.3 vectorbt 路線「🚫 暫停」恢復為 M3 排程任務
- 02 PRD v3.0 §依賴清單「vector 半邊暫停」描述失效
- 後續單獨 commit 處理上述受影響 docs（與本 ADR 同 PR 範圍）

### 重新評估觸發
- zipline-reloaded 3.1.x 出現 regression（特別是 XTAI calendar / fee / slippage）→ 回 3.0.4 + 維持 vectorbt 暫停
- vectorbt 1.x 升級破壞 cross-check API → 鎖版或回 0.26（須評估 pandas 相容）
- pandas 3.x 釋出且 zipline-reloaded 不跟進 → 重評本決策

---

## 5. 執行計畫

1. ✅ `b8dc5a9`：pyproject 升級 + uv.lock 全量重解（已 commit）
2. ✅ `b5c97de`：validation 層加入 vectorbt cross-check + event-driven evaluate_bar（已 commit）
3. ✅ **本 ADR**：retroactive 記錄升級決策
4. **本 commit 一同 sweep**：17 / 18 / 16 / 02 / ADR-007 / ADR-013 中標示「vectorbt 暫停」「pandas<2」「Python<3.12」的描述
5. **Sprint 2**：執行 vectorbt vs self-written PnL cross-check 全 universe（acceptance 條件：return 差 < 1%、Sharpe 差 < 1%）

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-01 | Self | 初版 — Amends ADR-013 § 4 / Resumes ADR-007 vector 半邊 |
