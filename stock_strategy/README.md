# stock_strategy — FinLab reference strategies

Working long-only Taiwan-equity strategies written in **FinLab's own DSL**
(`finlab.data` / `data.indicator` / `hold_until` / `backtest.sim`). Kept as
**reference fixtures** for end-to-end testing of the platform — they are *not*
part of the backtest_platform package.

| File | Idea |
|:--|:--|
| `三頻率RSI策略.md` | Multi-timeframe RSI (20/60/120) + ROE filter |
| `二次創高股票.md` | Second 60-day breakout + revenue/volume confirmation |
| `台股總體經濟ETF.md` | Macro/ETF rotation |
| `監獄兔.md` | (compact momentum/mean-reversion rule) |

## How they integrate with the platform

These run in FinLab's `backtest.sim`. The platform's value-add is running their
**signals** through *its* RiskGate + PaperBroker + persistence + validation
(truth gate / WFA / PBO / DSR) — FinLab's backtest does not apply the platform's
deployment thresholds.

The integration point is **`runtime.market_reader.make_position_signal_fn`**: a
strategy's buy-list on an as-of date → gate-safe signal dicts → the daily-flow
chain (`ETL→signals→risk→orders→log`). Pair with `live_config_for_date` /
`run_paper_replay` to drive any of these through the real chain.

> ⚠️ These use FinLab data keys/DSL; they require a FinLab token to *evaluate*.
> The platform integration consumes only the resulting positions, not the DSL.
