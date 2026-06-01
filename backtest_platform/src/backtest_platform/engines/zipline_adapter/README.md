# zipline-reloaded Adapter (M2 主回測引擎)

> **狀態**：Sprint 1 Day 1-7 完成（zipline 整合 + FinMind bundle + 四層共振 Algorithm + 台股規則 + CLI）
> **架構**：ADR-013 採 zipline-reloaded（取代 ADR-005 TQuant-Lab）
> **資料源**：ADR-014 FinMind 免費版（取代 ADR-006 FinLab 付費版）

## 為什麼是 zipline-reloaded

| 比較 | TQuant-Lab (zipline-tej) | **zipline-reloaded** (本方案) |
|:--|:--|:--|
| 維護 | TEJ 商業公司 | 社群（Stefan Jansen et al.） |
| TEJ key 依賴 | **import 階段 hard-coded** | **零** |
| Algorithm API / Pipeline / Blotter | ✅ 但 import 卡死 | ✅ 完全可用 |
| XTAI 台股日曆 | 強綁 TEJ | `exchange_calendars` 套件已有 |

詳見 [ADR-013](../../../../../dev_docs/adrs/ADR-013-zipline-reloaded-pivot.md)。

## 模組結構

```
engines/zipline_adapter/
├── __init__.py           import-time 自動 register() finmind bundle
├── bundles/              ★ 商業綁定可抽換點
│   ├── parquet_cache.py  M1 write_parquet 反向（讀 cache）
│   └── finmind_bundle.py FinMind → zipline bundle（主，免費）
│                         未來抽換成 finlab_bundle.py / tej_bundle.py 同 pattern
├── algorithms/
│   ├── base.py           preload_merged_frames + get_history_window
│   └── four_layer_resonance.py
│                         M1 純函式 → zipline TradingAlgorithm
├── controls/
│   └── taiwan_stock_rules.py
│                         TaiwanCommission 買賣不同稅率 + FixedBasisPointsSlippage
├── cli.py                click entry: backtest-run, list-bundles
└── (M3+) multi_strategy/ portfolio aggregator
    (M3+) validation/     對拍 M1 + vectorbt
    (M4-M5) adapters/brokers/  paper / shioaji
```

## 快速開始

### 1. 一次性 backfill（首次跑）

```bash
# 確認環境
uv run python -c "import zipline; print('zipline', zipline.__version__)"

# Ingest FinMind 資料到 zipline bundle（首次拉約 5-10 分鐘 / 股）
UNIVERSE_FINMIND=2330 uv run python -c "
import os; os.environ['ZIPLINE_ROOT'] = os.path.abspath('data/zipline')
from backtest_platform.engines.zipline_adapter.bundles import finmind_bundle  # noqa
from zipline.data.bundles import ingest
ingest('finmind', show_progress=True)
"
```

### 2. 跑回測

```bash
uv run python -m backtest_platform.engines.zipline_adapter.cli backtest-run \
  --stocks 2330 \
  --start 2024-01-15 --end 2024-02-29 \
  --capital-base 1000000 \
  --tearsheet
```

輸出：
- `reports/perf__<run_id>.pkl` — zipline 完整 daily perf frame
- `reports/summary__<run_id>.json` — 摘要指標
- `reports/tearsheet__<run_id>.html`（含 `--tearsheet` 時）

### 3. 抽換資料源（未來）

要從 FinMind 換到 FinLab VIP：

```bash
# 1. 新建 bundles/finlab_bundle.py（仿 finmind_bundle.py 結構）
# 2. import 它觸發 register("finlab", ...)
# 3. 跑 ingest -b finlab，跑 backtest --bundle finlab
```

`algorithms/` 與 `strategies/` **0 改動** — 這是 plan v3.0 §1.0 商業綁定可抽換性的核心。

## 關鍵設計決策

### 為什麼 commission 與 slippage 分開

`StrategyConfig.cost_buy_rate` (M1) 內含 `slip_rate` — 適合 vectorbt 等 single-rate 引擎。
zipline 分 `set_commission` + `set_slippage` 兩機制，若直接用 `cost_buy_rate` 會雙重計算。

解法：`controls/taiwan_stock_rules._broker_only_rates()` 從 StrategyConfig 抽 broker-only
（去除 slip），slip 交給 `FixedBasisPointsSlippage`。

### 為什麼用 parquet preload 而非 zipline `data.history()`

M1 純函式 `compute_scores` 需要 14 個 REQUIRED_COLUMNS（OHLCV + 三大法人 + 籌碼），
但 zipline bundle 只儲存 OHLCV。Per-bar 從 parquet 讀盤太慢。

解法：`algorithms/base.preload_merged_frames()` 一次性載入 M1 `ETLBundle.merged()`
進 in-memory dict，per-bar 用 `get_history_window(as_of, bar_count)` O(1) 切片。

### 為什麼 FinMind 缺失 sessions 要 ffill

zipline `BcolzDailyBarWriter._write_internal` 嚴格 assert
`len(df) == len(sessions_in_range)`。FinMind 偶有缺失 sessions（整股暫停交易），
若不補會 assertion fail。

解法：`bundles/finmind_bundle._to_zipline_daily_frame()` reindex 到完整 XTAI sessions，
缺失日 ffill OHLC + volume=0。

## Tests

```bash
# 全套 zipline_adapter tests（35 tests）
uv run pytest tests/engines/zipline_adapter/ -v

# 只跑單元（< 5s）
uv run pytest tests/engines/zipline_adapter/ -m "not integration"
```

## 已驗證 / 待補

| 項目 | 狀態 |
|:--|:--:|
| zipline-reloaded 乾淨 import | ✅ Day 1 |
| XTAI calendar 2024 243 sessions | ✅ Day 1 |
| FinMind bundle ingest (2330 全歷史 4898 bars) | ✅ Day 2-3 |
| Algorithm + Taiwan rules + smoke run | ✅ Day 4-5 |
| CLI `backtest-run` + tearsheet hook | ✅ Day 6-7 |
| **對拍 M1 pipeline.py** | ⏳ Sprint 2 |
| 多策略 portfolio aggregator | ⏳ Sprint 3 |
| 漲跌停 TradingControl | ⏳ Sprint 2-3 |
| LimitUpDownControl 自寫 | ⏳ Sprint 2 |
