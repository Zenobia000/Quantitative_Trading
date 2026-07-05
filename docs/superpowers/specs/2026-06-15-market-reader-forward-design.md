# market_reader + Forward-Paper Wiring — Spec (③)

> **Date:** 2026-06-15 · **Status:** Built (sequence pre-approved ①→②→③) · **Sub-project:** ③
> **Relates:** 7.A.4 (paper forward), 8.H.8 (live daemon), [ADR-025](../../../dev_docs/adrs/) (paper-forward). Builds on ① `finlab_source` + `runtime/paper_daemon` replay core.

## Goal

Complete the **forward live-paper** data path: the daemon's replay core is clock-agnostic, so forward = swap the cached-parquet loader for a **live FinLab EOD panel through "today"**. Provide the wiring so the *same* inst_flow `signal_fn` runs forward, plus a **generic adapter** so any strategy (incl. the FinLab `stock_strategy/` references) can drive the platform chain.

## Components — `runtime/market_reader.py`

| Unit | Responsibility | Tested |
|:--|:--|:--|
| `read_live_panel(universe, as_of, *, lookback_days, getter)` | FinLab EOD `(close, flow=foreign net-buy, volume)` wide panel sliced to `[as_of−lookback, as_of]` (same shape as the replay loader; no look-ahead) | ✓ slice/window/flow-sum |
| `live_config_for_date(universe, cfg, broker, *, run_id, strategy_id, getter, equity, sink)` | Per-session `config_for_date` for `run_paper_replay`: read live panel → `make_inst_flow_signal_fn` → `build_paper_collaborators` (no-op live ETL; `sink` injectable for tests) | ✓ end-to-end chain GREEN (stub getter + PaperBroker + memory sink) |
| `make_position_signal_fn(holdings, prices, avg_volume, *, equity, …)` | **Generic** strategy→`signal_fn` adapter: a buy-list → gate-safe BUY signal dicts. Lets any strategy's holdings run the real RiskGate+broker+sink chain | ✓ schema/qty/stop + empty |
| `run_forward_session(as_of, config_for_date)` | Thin one-session entry over the proven replay core | (stub) |

## What's intentionally a stub

The **after-close recurring scheduler** (fire `run_forward_session(today)` once per session close, over real calendar time): needs real time, can't be unit-tested, and is a systemd-timer / CLI deployment choice. The per-date execution + persistence is identical to replay (②-proven). This is the *only* remaining gate for live OOS — and it's a time gate, not a code gate.

## Using the `stock_strategy/` references (the user's ask)

The 4 FinLab-DSL strategies produce a `position` (wide boolean/weight). Its True columns on a date = a buy-list → `make_position_signal_fn(holdings, prices, avg_volume, equity=…)` → drives the platform chain. This is how "import the references to test the system end-to-end" is realized — the platform runs *their signals* through *its* gate/broker (the platform's value-add over FinLab's `backtest.sim`).

## Test Plan
- [x] `read_live_panel` slices to universe + window, no look-ahead, flow = summed foreign net-buy.
- [x] `live_config_for_date` → `run_paper_replay([as_of])` → chain GREEN (ETL→signals→risk→orders→log), sink ran, fills placed — with stub FinLab + in-memory sink (no DB).
- [x] `make_position_signal_fn` emits gate-safe signals (stop < entry, qty>0) + empty-holdings.
- [x] Full suite 971 pass / 3 skip, ruff clean.

## Non-goals
- The recurring scheduler / real-time loop (deployment + needs real calendar time).
- Executing the FinLab-DSL `stock_strategy/` `.md` files (they call FinLab's own `backtest.sim`); the integration point is the position→signal adapter.
