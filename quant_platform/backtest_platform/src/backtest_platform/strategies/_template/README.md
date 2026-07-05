# 策略撰寫模板（Strategy authoring template）

把這個資料夾複製一份，就是一隻新策略。平台用**同一個介面**呼叫每隻策略，玩家只負責填「策略內容」，輸入/輸出格式由契約 (`strategies/protocol.py`) 保證一致。

## 一隻策略 = 一個自包含資料夾

```
strategies/<your_strategy>/
├── __init__.py     # re-export 你的 config / backtest 函式
├── strategy.py     # ★ 你的 alpha 在這裡：Config（frozen）+ 純函式 backtest
├── runner.py       # 4 行 adapter：建 panel → 跑 backtest → 回傳 StrategyRun
└── README.md       # （選填）
```

## 契約（輸入 / 輸出）

| | 形狀 | 由誰提供 |
| :--- | :--- | :--- |
| **輸入** | `symbols, start, end, config, loader` | 回測系統傳入；`loader(sid)` 給你該股的 merged frame |
| **你的純函式** | `backtest(panel, config, start, end) -> Result` | 你寫；無 IO、無副作用（ADR-003）|
| **輸出** | `StrategyRun(metrics, returns, trades)` | runner 包裝；`metrics` 餵 gate、`returns` 畫淨值 |

`run(symbols, start, end, config, loader) -> StrategyRun` 的簽名**必須完全一致**——這份一致性就是平台能用同一套 metrics / gate / ledger 公平評斷任何策略的原因。

## 新增一隻策略的步驟

1. 複製 `strategies/_template/` → `strategies/<your_strategy>/`。
2. 在 `strategy.py` 改名 Config / Result，寫你的訊號邏輯（唯一放 alpha 的地方）。
3. 在 `runner.py` 改類名 + `@register_strategy("<your_strategy>")`，呼叫你的 backtest。
4. 在 `research/runners.py`（aggregator）加一行 import 觸發註冊。
5. 完成——`get_strategy("<your_strategy>").run(...)` 即可被回測系統調用。**動 2-3 個檔，不碰引擎 / CLI / gate。**

## 驗證

```python
from backtest_platform.strategies.protocol import get_strategy, list_strategies
list_strategies()                       # 應包含你的名字
run = get_strategy("<your_strategy>").run(symbols, start, end, cfg, loader)
run.metrics, run.returns, run.trades    # 一致的輸出
```

`template` 本身是個可運作的 trivial 策略（等權買進持有），同時當作契約的活範例與冒煙測試。複製它、換掉 `backtest_*` 的內容、保留形狀即可。
