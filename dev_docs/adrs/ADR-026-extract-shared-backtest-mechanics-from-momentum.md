# ADR-026: 共用回測基礎建設抽出 momentum → `strategies/common`，並封存非正式驗證碼

> **狀態：** 已接受 | **日期：** 2026-06-16 | **決策者：** Self
> **相關：** [ADR-023](./ADR-023-momentum-no-go-hold-gate.md)（動能 NO-GO，momentum 為已驗證但 hold 的策略）、[ADR-024](./ADR-024-institutional-flow-candidate-strategy.md)（資金流候選 = inst_flow）、[ADR-025](./ADR-025-two-stage-validation-gate-and-paper-promotion.md)（inst_flow 為 paper-ready 正式候選）

---

## 1. 背景與問題

`backtest_platform` 累積到多套策略（momentum / inst_flow / multi_factor / four_layer_resonance）後，出現一個模組邊界的設計債：

**`momentum` 是第一個被實作的策略，於是通用回測基礎建設（再平衡日曆、波動目標部位、報酬清洗）被順手塞進了 `momentum/strategy.py`，並以 private（底線開頭）函式存在。** 後來的 `inst_flow`、`multi_factor` 要重用這些機制，就反向 import momentum 的私有函式：

```python
# inst_flow/strategy.py（重構前）
from backtest_platform.strategies.momentum.strategy import (
    TRADING_DAYS, _clean_returns, _rebalance_dates, _vol_target,
)
```

`runtime/paper_daemon.py`（正式 runtime）同樣 import `momentum.strategy._rebalance_dates`。

### 為什麼這是問題

- **跨模組 import 私有函式**：一個策略模組去挖另一個策略的 `_private` API，在任何 code review 都是紅燈——破壞封裝、製造隱性耦合。
- **特化模組淪為意外基底**：momentum 是一個特定因子策略（12-1 cross-sectional），卻被當成 inst_flow / multi_factor 的共用底座。經典「第一個實作意外變成基底類別」反模式。
- **阻擋整理**：因為正式候選 inst_flow 反向依賴 momentum，無法把 momentum 當「非正式策略」下架——naive 搬移會直接打斷 inst_flow + paper_daemon（Never Break Userspace）。

被借用的 4 個東西（`TRADING_DAYS` 常數 + `_clean_returns` / `_rebalance_dates` / `_vol_target`）**全是中立的回測機制，不含任何 momentum 訊號邏輯**。

---

## 2. 考量的選項

### 選項一：維持現狀（私有跨 import）
- **優點**：零變更
- **缺點**：封裝破壞持續、momentum 永遠卡成承重底座無法下架、新策略只會繼續挖 momentum 私有 API
- **拒絕**：設計債只會複利

### 選項二：把 4 個函式複製進每個策略
- **優點**：模組各自獨立、無跨 import
- **缺點**：重複程式碼（DRY 違反）、4 份 vol-target 各自演化 → 行為漂移、測試重複
- **拒絕**：用重複換解耦是劣解

### 選項三：抽出中立共用層 `strategies/common` ★採納
- **描述**：把 4 個中立機制抽到 `strategies/common/mechanics.py`，去掉底線升為正式 public API；所有策略改依賴 common，**策略之間互不依賴**
- **優點**：封裝正確、單一真實來源、解除 momentum 的承重卡點、新策略有明確的共用入口
- **缺點**：一次性 import 改寫 + 測試搬遷（機械式、有測試保護）

---

## 3. 決策

**採納選項三**，並順帶完成一次資料夾整理。

### 3.1 抽出共用機制

新增 `src/backtest_platform/strategies/common/`：

| 函式（public） | 原私有名 | 用途 |
| :--- | :--- | :--- |
| `TRADING_DAYS` | 同 | 年化常數 252 |
| `clean_returns` | `_clean_returns` | 日報酬 + inf/資料缺口 winsorize |
| `rebalance_dates` | `_rebalance_dates` | 月/季/半年首個交易日 |
| `vol_target` | `_vol_target` | trailing 波動目標部位縮放（無 look-ahead）|

消費者改依賴 common：`momentum`、`inst_flow`、`multi_factor`、`runtime.paper_daemon`。`vol_target` / `rebalance_dates` / `clean_returns` 的 primitive 測試從 `tests/strategies/momentum/` 抽到 `tests/strategies/common/test_mechanics.py`（它們現在是 production 共用，值得一級測試）。

### 3.2 正式版策略邊界釐清

| 策略 | 狀態 | 理由 |
| :--- | :--- | :--- |
| `inst_flow` | 正式 | paper-ready 候選（ADR-024/025）|
| `momentum` | **保留**（解耦後變乾淨對等策略）| research IS harness 承重 + 平台 strategy-agnostic 證明（ADR-023 hold，非死）|
| `four_layer_resonance` | 保留 | `pipeline.py` + zipline 引擎承重 |
| `multi_factor` | **封存 → `legacy/`** | 零 production 引用的葉子策略實驗 |

### 3.3 非正式驗證碼封存到 `legacy/`

`legacy/`（src 外，不被打包、不進 CI）收容：
- `strategies/multi_factor/` + 其測試
- `spikes/`（原 `sprint_0_spikes/` Sprint 0 POC）
- `scripts/`（非 inst_flow_* 的一次性 momentum / DOE / candidate-D / factor-baseline 驗證腳本）

並刪除死空目錄 `engines/zipline_adapter/adapters/`。契約見 `legacy/README.md`。

---

## 4. 後果

### 正面
- **封裝修復**：策略之間零互相依賴；通用機制單一真實來源
- **解除卡點**：momentum 不再是「想下架卻動不了」的承重底座（雖最終決定保留它為乾淨對等策略）
- **整理完成**：active tree 只剩正式策略 + 共用層；驗證雜物進 legacy 但保留溯源
- **測試升級**：共用 primitive 有獨立 `test_mechanics.py`（rebalance/vol-target/clean-returns 一級覆蓋）

### 負面 / 風險
- `legacy/` 內的封存測試與 `*_gates.py` 對 `multi_factor` 的引用為封存當下快照，非 CI 保證可跑（已於 `legacy/README.md` 載明契約）
- 歷史 result 文件（`dev_docs/*_result_*.md`）仍以 `scripts/<name>.py` 記錄當時路徑——屬 point-in-time 記錄，不回溯改寫

### 影響範圍
- `src/.../strategies/common/`（新模組）、`momentum` / `inst_flow` / `multi_factor` / `runtime.paper_daemon`（import 改寫）
- `tests/strategies/common/`（新）、`tests/strategies/momentum/`（移除 primitive 測試）
- `legacy/`（新封存樹）、`.gitignore`（spike 輸出路徑）
- 文件：08 結構、09 依賴、16 WBS、17 master plan banner、INDEX ADR 表

### 重新評估觸發
- 出現第 5 套策略需要 common 之外的共用機制 → 評估 common 是否該再細分（calendar / sizing / returns 分檔）
- multi_factor 需復活 → 從 legacy 搬回 src 並補回 CI

---

## 5. 執行計畫

1. ✅ **抽 common**：`mechanics.py` + 4 個 public 函式；改寫 4 個消費者；primitive 測試搬 `tests/strategies/common/`
2. ✅ **封存**：multi_factor / spikes / 舊 scripts → `legacy/`；刪空目錄；`legacy/README.md` 契約
3. ✅ **綠燈驗證**：989 passed / coverage 94%（≥80 閘門）
4. **文件同步**（本 PR）：本 ADR + INDEX + 08 + 09 + 16 + 17 banner

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-06-16 | Self | 初版 — 抽 momentum 私有機制成 `strategies/common`，解策略間 leaky abstraction；封存 multi_factor/spikes/舊 scripts 到 legacy；保留 momentum 為乾淨對等策略 |
