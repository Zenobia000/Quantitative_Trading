# legacy/ — 封存的驗證碼（不屬於正式產品）

這裡保存「以前驗證過、但不再是正式平台一部分」的程式碼。封存而非刪除，保留溯源與未來可能的再驗證。

## 契約（重要）

- **不被安裝**：`pyproject.toml` 的 `packages.find where = ["src"]`，`legacy/` 在 src 外，不會被打包成 `backtest_platform.*`。
- **不進 CI**：`testpaths = ["tests"]`，`legacy/tests/` 不會被 pytest 收集。
- **import 可能已過期**：封存碼對 live 套件的 `from backtest_platform...` 引用反映的是封存當下狀態。要重新跑，需自行把模組搬回 `src/` 或補 path。
- **這不是死碼傾倒場**：只放「曾通過某種驗證、有保存價值」的東西，不放隨手垃圾。

## 內容

| 路徑 | 來源 | 為何封存 |
| :--- | :--- | :--- |
| `strategies/multi_factor/` | `src/.../strategies/multi_factor/` | momentum+inst_flow+low_vol 複合因子實驗；零 production 引用的葉子策略 |
| `spikes/` | `sprint_0_spikes/` | Sprint 0 技術驗證 POC（zipline/finlab/shioaji 接通） |
| `scripts/` | `scripts/`（非 inst_flow_*） | 一次性 momentum / DOE / candidate-D / factor-baseline 驗證跑分腳本 |
| `tests/` | 對應上述模組的測試 | 隨封存碼一起保存，不在 active 測試套件 |

## 正式版保留在 `src/` 的策略

- `inst_flow/` — paper-ready 正式候選
- `momentum/` — 已解耦為依賴 `strategies/common` 的乾淨對等策略；research IS harness 承重 + 平台 strategy-agnostic 證明
- `four_layer_resonance/` — pipeline + zipline 引擎承重

共用回測基礎建設見 `src/.../strategies/common/`（ADR-026）。
