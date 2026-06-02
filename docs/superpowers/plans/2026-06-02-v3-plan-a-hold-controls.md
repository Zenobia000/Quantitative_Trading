# v3 Plan A — Hold-Control Components Implementation Plan

> **For agentic workers:** Use the Execute Plan phase of sunnydata-design. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Implement v2.md §2.1.3 hold controls (min-2-bar hold, 60-bar time-stop) so the strategy stops the 3-day flameout churn, then quick-verify on the existing large-cap cache.

**Architecture:** Add `min_hold_bars` / `max_hold_bars` to `StrategyConfig`; thread a `bars_held` count through the exit decision (`_evaluate_priority`) so soft exits (flameout/exit/takeprofit/reduce) are blocked before `min_hold_bars` while hard `stoploss` is exempt, and a `max_hold_bars` time-stop forces exit. Propagate `bars_held` through both evaluation paths: `compute_signals` walk-loop (maintains its own counter) and the event-driven `EvaluateBar`/`evaluate_bar` (engine supplies it).

**Tech Stack:** Pydantic, pandas, pytest.

---

## Task 1: StrategyConfig — min/max hold params

**Files:**
- Modify: `backtest_platform/src/backtest_platform/config/strategy_config.py`
- Test: `backtest_platform/tests/config/test_strategy_config.py` (append; create if absent)

- [ ] **Step 1: Write failing test**

```python
def test_hold_bar_defaults_and_validation():
    from backtest_platform.config.strategy_config import StrategyConfig
    import pytest
    c = StrategyConfig()
    assert c.min_hold_bars == 2
    assert c.max_hold_bars == 60
    # min must be < max
    with pytest.raises(ValueError):
        StrategyConfig(min_hold_bars=60, max_hold_bars=2)
```

- [ ] **Step 2: Run → FAIL** (`AttributeError: min_hold_bars`)

Run: `cd backtest_platform && uv run --extra sprint1 --extra dev pytest tests/config/test_strategy_config.py -k hold_bar -q --no-cov`

- [ ] **Step 3: Implement** — add fields after `add_score_threshold` (line ~31) and a validator clause:

```python
    # --- Hold controls (v2.md §2.1.3) ---
    min_hold_bars: int = Field(
        2, ge=0, le=20, description="最短持倉 bar 數（避免假突破洗單）；soft exit 受此約束，stoploss 不受"
    )
    max_hold_bars: int = Field(
        60, ge=2, le=250, description="最長持倉 bar 數（time-stop 強制出場）"
    )
```

In `_validate_thresholds` (after existing checks, before `return self`):

```python
        if self.min_hold_bars >= self.max_hold_bars:
            raise ValueError("min_hold_bars must be < max_hold_bars")
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit**

```
git add backtest_platform/src/backtest_platform/config/strategy_config.py backtest_platform/tests/config/test_strategy_config.py
git commit -m "feat(config): add min_hold_bars/max_hold_bars (v2.md §2.1.3)"
```
(commit body: WHY ADR-017 hold-control gap → 3-day churn; WHAT min/max hold params + validator; IMPACT consumed by signals in next task)

---

## Task 2: `_evaluate_priority` — min-hold gate + time-stop

**Files:**
- Modify: `backtest_platform/src/backtest_platform/strategies/four_layer_resonance/signals.py`
- Test: `backtest_platform/tests/strategies/four_layer_resonance/test_signals.py` (append)

- [ ] **Step 1: Write failing tests**

```python
def test_min_hold_blocks_soft_exit_but_not_stoploss():
    from backtest_platform.strategies.four_layer_resonance.signals import _evaluate_priority
    from backtest_platform.config.strategy_config import StrategyConfig
    import pandas as pd
    cfg = StrategyConfig()  # min_hold_bars=2
    # flameout row, in position, held only 1 bar → soft exit blocked
    row = pd.Series({
        "close": 100.0, "high": 101.0, "box_lower": 95.0, "risk_swing_low": 90.0,
        "volume": 1000.0, "avg_volume_5": 1000.0, "upper_shadow": 0.0,
        "candle_body_size": 1.0, "structure_score": 1, "direction_score": 1,
        "chip_score": 1, "momentum_score": -1, "total_score": 2,
        "state_flameout": 1, "state_strong_buy": 0, "edge_ok": 1,
    })
    sig = _evaluate_priority(row, cfg, in_position=1, prev_high=99.0, prev_total=5,
                             prev_total_for_warning=5, prev_momentum=0,
                             net_profit_rate=0.0, bars_held=1)
    assert sig["exit"] is False  # blocked by min-hold
    # held 2 bars → soft exit allowed
    sig2 = _evaluate_priority(row, cfg, in_position=1, prev_high=99.0, prev_total=5,
                              prev_total_for_warning=5, prev_momentum=0,
                              net_profit_rate=0.0, bars_held=2)
    assert sig2["exit"] is True
    # stoploss (close<box_lower) exempt from min-hold even at bars_held=1
    row_sl = row.copy(); row_sl["close"] = 90.0  # below box_lower 95
    sig3 = _evaluate_priority(row_sl, cfg, in_position=1, prev_high=99.0, prev_total=5,
                              prev_total_for_warning=5, prev_momentum=0,
                              net_profit_rate=0.0, bars_held=1)
    assert sig3["stoploss"] is True


def test_max_hold_forces_exit():
    from backtest_platform.strategies.four_layer_resonance.signals import _evaluate_priority
    from backtest_platform.config.strategy_config import StrategyConfig
    import pandas as pd
    cfg = StrategyConfig()  # max_hold_bars=60
    # benign row (no flameout), in position 60 bars → time-stop exit
    row = pd.Series({
        "close": 100.0, "high": 101.0, "box_lower": 95.0, "risk_swing_low": 90.0,
        "volume": 1000.0, "avg_volume_5": 1000.0, "upper_shadow": 0.0,
        "candle_body_size": 1.0, "structure_score": 2, "direction_score": 2,
        "chip_score": 2, "momentum_score": 2, "total_score": 8,
        "state_flameout": 0, "state_strong_buy": 1, "edge_ok": 1,
    })
    sig = _evaluate_priority(row, cfg, in_position=1, prev_high=99.0, prev_total=5,
                             prev_total_for_warning=5, prev_momentum=2,
                             net_profit_rate=0.05, bars_held=60)
    assert sig["exit"] is True
```

- [ ] **Step 2: Run → FAIL** (`_evaluate_priority() got unexpected keyword 'bars_held'`)

- [ ] **Step 3: Implement** — change signature + gate logic.

Signature (line ~244): add `bars_held: int` param (keyword, default 0 for back-compat at call sites updated in later tasks):

```python
def _evaluate_priority(
    row: pd.Series,
    config: StrategyConfig,
    in_position: int,
    prev_high: float,
    prev_total: float,
    prev_total_for_warning: float,
    prev_momentum: float,
    net_profit_rate: float,
    bars_held: int = 0,
) -> dict[str, bool]:
```

Add after `in_pos = in_position == 1` (line ~259):

```python
    min_hold_met = bars_held >= config.min_hold_bars
    time_stop = in_pos and bars_held >= config.max_hold_bars
```

Change `exit_sig` (line ~271) to gate soft-exit by min-hold and add time-stop:

```python
    exit_sig = in_pos and (
        (min_hold_met and (flameout or two_warnings)) or time_stop
    )
```

Gate `takeprofit` and `reduce_sig` by `min_hold_met` (append `and min_hold_met` to each condition). Leave `stoploss` UNGATED (risk signal, v2.md §2.5.3).

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit**

```
git commit -m "feat(signals): min-hold gate + max-hold time-stop in _evaluate_priority"
```

---

## Task 3: EvaluateBar + evaluate_bar — thread bars_held

**Files:**
- Modify: `backtest_platform/src/backtest_platform/strategies/four_layer_resonance/signals.py`
- Test: same test file (append)

- [ ] **Step 1: Write failing test**

```python
def test_evaluate_bar_respects_min_hold():
    from backtest_platform.strategies.four_layer_resonance.signals import EvaluateBar, evaluate_bar
    from backtest_platform.config.strategy_config import StrategyConfig
    cfg = StrategyConfig()
    base = dict(
        in_position=1, entry_cost_price=100.0, close=100.0, high=101.0, open=99.0,
        box_lower=95.0, risk_swing_low=90.0, volume=1000.0, avg_volume_5=1000.0,
        body_high=100.0, body_low=99.0, upper_shadow=0.0, candle_body_size=1.0,
        structure_score=1, direction_score=1, chip_score=1, momentum_score=-1,
        total_score=2, prev_total_score=5.0, prev_momentum_score=0.0, prev_high=99.0,
        state_flameout=1, state_strong_buy=0, state_hold=0, state_warning=0,
        volatility_rate=0.05,
    )
    assert evaluate_bar(EvaluateBar(bars_held=1, **base), cfg) == "hold"  # flameout blocked < min_hold
    assert evaluate_bar(EvaluateBar(bars_held=2, **base), cfg) == "exit"
```

- [ ] **Step 2: Run → FAIL** (`EvaluateBar got unexpected keyword 'bars_held'`)

- [ ] **Step 3: Implement** — add field to `EvaluateBar` dataclass (after `entry_cost_price`):

```python
    bars_held: int = 0
```

(Place after the last field with a default-safe position; dataclass without defaults elsewhere → add `bars_held: int` as a regular field near top after `entry_cost_price`. If dataclass has no defaults, keep it non-default and update all constructors.)

In `evaluate_bar`, pass it through to `_evaluate_priority`:

```python
    signals = _evaluate_priority(
        row=row,
        config=config,
        in_position=bar.in_position,
        prev_high=bar.prev_high,
        prev_total=bar.prev_total_score,
        prev_total_for_warning=bar.prev_total_score,
        prev_momentum=bar.prev_momentum_score,
        net_profit_rate=net_profit_rate,
        bars_held=bar.bars_held,
    )
```

Note: if `EvaluateBar` has no field defaults, add `bars_held` as the LAST field with `= 0` default (dataclass requires defaults last) — verify field order at execution time.

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit**

```
git commit -m "feat(signals): thread bars_held through EvaluateBar/evaluate_bar"
```

---

## Task 4: compute_signals walk-loop — maintain bars_held

**Files:**
- Modify: `backtest_platform/src/backtest_platform/strategies/four_layer_resonance/signals.py`
- Test: `backtest_platform/tests/strategies/four_layer_resonance/test_signals.py`

- [ ] **Step 1: Write failing test** — a synthetic frame that triggers a flameout right after entry; assert no exit before min_hold_bars.

```python
def test_compute_signals_min_hold_extends_position(synthetic_scored_df):
    # synthetic_scored_df: a small DataFrame with score/state columns engineered
    # so buy fires on bar k and flameout on bar k+1. With min_hold_bars=2 the
    # position must persist through k+1 (action != exit at k+1).
    from backtest_platform.strategies.four_layer_resonance.signals import compute_signals
    from backtest_platform.config.strategy_config import StrategyConfig
    out = compute_signals(synthetic_scored_df, StrategyConfig())
    entries = out.index[out["action"] == "buy"].tolist()
    assert entries, "fixture must produce a buy"
    k = entries[0]
    # the bar immediately after entry must NOT be a soft exit (min-hold=2)
    assert out.loc[k + 1, "action"] != "exit"
```

(Build `synthetic_scored_df` fixture from existing test helpers in the file; reuse the score-column construction pattern already used by other compute_signals tests.)

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement** — in the walk loop (lines ~94-149), add a `bars_held` counter:

Before the loop (near `pos = 0`):
```python
    bars_held = 0
```

Pass to `_evaluate_priority` inside the loop:
```python
        signals = _evaluate_priority(
            row=row, config=config, in_position=pos, prev_high=prev_high,
            prev_total=prev_total_score, prev_total_for_warning=prev_total_warning,
            prev_momentum=prev_momentum if pd.notna(prev_momentum) else 0,
            net_profit_rate=net_profit_rate, bars_held=bars_held,
        )
```

After the existing pos-update block (the `if pos==0 and action=="buy" / elif pos==1 and action in (...)` section), maintain the counter:
```python
        if pos == 1 and action == "buy":
            bars_held = 0          # just entered
        elif pos == 1:
            bars_held += 1         # still held
        else:
            bars_held = 0          # flat
```

(Place this AFTER `pos` is updated so it reflects the post-action state.)

- [ ] **Step 4: Run → PASS** + full signals test module green

Run: `uv run --extra sprint1 --extra dev pytest tests/strategies/four_layer_resonance/test_signals.py -q --no-cov`

- [ ] **Step 5: Commit**

```
git commit -m "feat(signals): track bars_held in compute_signals walk-loop"
```

---

## Task 5: Algorithm — track entry bar, supply bars_held

**Files:**
- Modify: `backtest_platform/src/backtest_platform/engines/zipline_adapter/algorithms/four_layer_resonance.py`
- Test: `backtest_platform/tests/engines/zipline_adapter/algorithms/` (add or extend)

- [ ] **Step 1: Write failing test** — unit-test the bars_held bookkeeping helper in isolation (avoid full zipline run).

Extract a pure helper and test it:
```python
def test_update_bars_held_counter():
    from backtest_platform.engines.zipline_adapter.algorithms.four_layer_resonance import _update_bars_held
    held = {}
    # asset A enters (in_position True, was absent) → 0
    assert _update_bars_held(held, "A", in_position=True) == 0
    # next bar still held → 1, 2, ...
    assert _update_bars_held(held, "A", in_position=True) == 1
    assert _update_bars_held(held, "A", in_position=True) == 2
    # exits → reset, absent
    assert _update_bars_held(held, "A", in_position=False) == 0
    assert "A" not in held
```

- [ ] **Step 2: Run → FAIL**

- [ ] **Step 3: Implement** — add helper + wire into `evaluate_and_trade`:

```python
def _update_bars_held(held: dict, sym: str, in_position: bool) -> int:
    """Maintain per-symbol bars-held count. Returns bars_held BEFORE this bar.

    Called once per symbol per bar. On the first bar a position is seen the
    count is 0; each subsequent held bar increments. Cleared when flat.
    """
    if not in_position:
        held.pop(sym, None)
        return 0
    prior = held.get(sym, 0)
    held[sym] = prior + 1
    return prior
```

In `initialize`, add `context.bars_held = {}`.

In `evaluate_and_trade`, inside the per-symbol loop, replace `in_position, entry_cost = _portfolio_state(...)` usage so it also computes `bars_held`:
```python
        in_position, entry_cost = _portfolio_state(context, asset)
        bars_held = _update_bars_held(context.bars_held, sym_str, bool(in_position))
        ...
        action = evaluate_window_with_state(
            window, context.config, in_position, entry_cost, bars_held
        )
```

- [ ] **Step 4: Update `evaluate_window_with_state` + `_build_evaluate_bar`** to accept/pass `bars_held`:

`evaluate_window_with_state(window, config, in_position, entry_cost_price, bars_held=0)` → pass to `_build_evaluate_bar(last, prev, in_position, entry_cost_price, bars_held)` → set `EvaluateBar(..., bars_held=bars_held)`.

- [ ] **Step 5: Run helper test → PASS**, then full algorithm + signals tests green.

- [ ] **Step 6: Commit**

```
git commit -m "feat(algorithm): per-symbol bars_held tracking → hold controls active"
```

---

## Task 6: Quick verification probe on existing large-cap cache (checkpoint)

**Files:** none committed (analysis only; uses existing `data/parquet` cache + ZIPLINE_ROOT bundle)

- [ ] **Step 1: Full suite green + coverage gate**

Run: `cd backtest_platform && uv run --extra sprint1 --extra dev pytest -q`
Expected: all pass, coverage ≥ 80.

- [ ] **Step 2: Re-run the 2330 + portfolio backtest (2020-2024 & 2015-2020)** with hold controls active, compare to the v2 baseline (−0.39% / −1.75% / −4.94%):

```bash
export ZIPLINE_ROOT="$PWD/data/zipline"
uv run --extra sprint1 --extra dev python -m backtest_platform.engines.zipline_adapter.cli \
  backtest-run --stocks 2330 --start 2020-01-02 --end 2024-12-31 --capital-base 10000000
```
Record: total_return, n_round_trips, and — via a short perf-inspection — avg holding-days (expect > 3.4, closer to the §2.1.3 intent).

- [ ] **Step 3: Decision checkpoint (report to user, do NOT auto-proceed)**

Interpret per the spec §7 checkpoint:
- Holding period lengthened (3.4 → larger) and churn dropped → hold controls work as designed; proceed to Plan B (mid-cap universe).
- Returns still flat on large-caps → expected (wrong universe); the real test is Plan B+C. Note this explicitly.
- Behaviour unchanged → bug in bars_held wiring; return to debugging before Plan B.

---

## Plan Self-Review

- **Spec coverage:** WS1 components (min/max hold) = Tasks 1-5; checkpoint (spec §7) = Task 6. Regime filter + universe are Plan B/C (out of scope here). ✓
- **Placeholder scan:** Task 4 references a `synthetic_scored_df` fixture "built from existing helpers" — this is the one soft spot; at execution, build it explicitly from the score-column pattern already in `test_signals.py` (do not leave abstract). All other steps have concrete code. ⚠ flagged.
- **Type consistency:** `bars_held: int` added to `EvaluateBar`, `_evaluate_priority(..., bars_held=0)`, `evaluate_window_with_state(..., bars_held=0)`, `_build_evaluate_bar(..., bars_held)`, `_update_bars_held(held, sym, in_position) -> int`. Signatures consistent across tasks. ✓
- **Back-compat:** `bars_held` defaults to 0 everywhere so the `cross_check_vectorbt`/`regression_vs_m1` paths that call `compute_signals` keep working (compute_signals now sets it internally). Verify regression tests still pass in Task 6 Step 1. ✓
