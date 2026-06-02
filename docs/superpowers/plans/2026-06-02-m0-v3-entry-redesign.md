# M0 v3 進場重設 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or the Execute Plan phase of superpowers:sunnydata-design to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把四層共振「進場過嚴」重設為參數化分級放寬（必含層+可選 + confirm + cooldown + 負向 veto）+ 最小 exit 搭配（flameout 2-bar 確認），v2 預設精確重現 baseline。

**Architecture:** 不動 `scoring.py`（四層分數）。改動集中在 `config/strategy_config.py`（+6 進場參數，v2 預設）與 `strategies/four_layer_resonance/signals.py`（`_evaluate_priority` buy/exit gate + `compute_signals` 迴圈狀態 + `EvaluateBar`）。新增 `DEFAULT_CONFIG_V3` preset。所有放寬可由 config 關閉，v2 regression 釘死。

**Tech Stack:** Python 3.12, Pydantic v2 (frozen), pandas/numpy, pytest（synthetic fixtures，不依賴 parquet cache）。

> **設計來源 spec：** `docs/superpowers/specs/2026-06-02-m0-v3-entry-redesign-design.md`（四交易視角壓測定稿）。
> **誠實邊界（MEMORY [[validation-tests-auto-skip-on-missing-cache]]）：** 單元測試用 synthetic fixture 驗「邏輯正確性」（非 cache-gated）；「真實 2330 重現 14 筆 + 雙窗口 IS edge」是 Sprint 6 手動整合步驟（cache-gated），綠燈≠有 edge。

---

## File Structure Mapping

| 檔案 | 責任 | 動作 |
|:--|:--|:--|
| `backtest_platform/src/backtest_platform/config/strategy_config.py` | 進場參數單一真相源 | Modify：+6 欄位 + `DEFAULT_CONFIG_V3` |
| `backtest_platform/src/backtest_platform/strategies/four_layer_resonance/signals.py` | 進出場 gate | Modify：`_evaluate_priority`（buy/exit）、`compute_signals`（迴圈狀態）、`EvaluateBar`/`evaluate_bar` |
| `backtest_platform/tests/test_strategy_config.py` | config 測試 | Modify：+v3 欄位 / preset / 邊界 |
| `backtest_platform/tests/strategies/four_layer_resonance/test_v3_entry.py` | v3 gate 邏輯測試（新） | Create：synthetic fixture truth-table |
| `strategy/v2.md` `dev_docs/21` `dev_docs/24` `dev_docs/16` ADR-019 | 文件同步 | Phase 3 Task 9（與 code 同 PR） |

**設計原則：** `_evaluate_priority` 維持「純函式：吃 row + 標量狀態 → 回 signal dict」。新放寬所需的跨 bar 狀態（`consec_structure_bars`、`bars_since_exit`、`prev_box_upper`、`prev_momentum`）由呼叫端（`compute_signals` 迴圈 / `evaluate_bar` 的 `EvaluateBar`）算好後傳入，gate 本身不持有狀態。

---

## Task 1: StrategyConfig +6 進場參數（v2 預設重現 baseline）

**Files:**
- Modify: `backtest_platform/src/backtest_platform/config/strategy_config.py`
- Test: `backtest_platform/tests/test_strategy_config.py`

- [ ] **Step 1: 寫失敗測試（v2 預設值 + v3 preset + 邊界）**

加到 `tests/test_strategy_config.py`：

```python
def test_v3_entry_fields_default_to_v2_behavior() -> None:
    c = StrategyConfig()
    assert c.entry_min_layers == 4
    assert c.entry_min_structure == 2
    assert c.entry_first_cross_only is True
    assert c.entry_confirm_days == 1
    assert c.entry_cooldown_bars == 0
    assert c.exit_flameout_confirm_bars == 1


def test_v3_preset_relaxed_values() -> None:
    from backtest_platform.config.strategy_config import DEFAULT_CONFIG_V3
    c = DEFAULT_CONFIG_V3
    assert (c.entry_min_layers, c.entry_min_structure) == (3, 1)
    assert c.entry_first_cross_only is False
    assert c.entry_confirm_days == 2
    assert c.entry_cooldown_bars == 3
    assert c.exit_flameout_confirm_bars == 2


def test_v3_entry_field_bounds() -> None:
    with pytest.raises(ValidationError):
        StrategyConfig(entry_min_layers=5)
    with pytest.raises(ValidationError):
        StrategyConfig(entry_min_structure=3)
    with pytest.raises(ValidationError):
        StrategyConfig(entry_confirm_days=0)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd backtest_platform && uv run pytest tests/test_strategy_config.py -k v3 -q`
Expected: FAIL（`entry_min_layers` 等屬性不存在 / `DEFAULT_CONFIG_V3` ImportError）

- [ ] **Step 3: 加欄位 + preset**

在 `StrategyConfig` 的 cost model 區段後、`@property` 前插入：

```python
    # --- v3 entry gate (M0 v3 redesign; v2 defaults reproduce baseline) ---
    entry_min_layers: int = Field(
        4, ge=1, le=4, description="N-of-4 冗餘計數上限門 (v2=4 全AND, v3=3)"
    )
    entry_min_structure: int = Field(
        2, ge=0, le=2, description="進場最低結構分 (v2=2 箱型突破, v3=1 站上箱中)"
    )
    entry_first_cross_only: bool = Field(
        True, description="僅單日首次站上進場 (v2=True, v3=False 放行持續站上)"
    )
    entry_confirm_days: int = Field(
        1, ge=1, le=10, description="structure 持續站穩確認天數 (v2=1, v3=2)"
    )
    entry_cooldown_bars: int = Field(
        0, ge=0, le=20, description="出場後 re-entry 冷卻 bar (v2=0, v3=3)"
    )
    exit_flameout_confirm_bars: int = Field(
        1, ge=1, le=5, description="flameout momentum 觸發確認 bar (v2=1, v3=2)"
    )
```

在檔尾 `DEFAULT_CONFIG = StrategyConfig()` 後加：

```python
DEFAULT_CONFIG_V3 = StrategyConfig(
    entry_min_layers=3,
    entry_min_structure=1,
    entry_first_cross_only=False,
    entry_confirm_days=2,
    entry_cooldown_bars=3,
    exit_flameout_confirm_bars=2,
)
```

- [ ] **Step 4: 跑測試確認通過 + 既有 config 測試不破**

Run: `cd backtest_platform && uv run pytest tests/test_strategy_config.py -q`
Expected: PASS（含既有 `test_defaults_match_v2_spec` 等全綠 — 新欄位有預設、`extra=forbid` 不受影響）

- [ ] **Step 5: Commit**

```bash
git add backtest_platform/src/backtest_platform/config/strategy_config.py backtest_platform/tests/test_strategy_config.py
git commit -m "feat(config): add 6 v3 entry-gate params + DEFAULT_CONFIG_V3 preset (v2 defaults reproduce baseline)"
```

---

## Task 2: 建立 synthetic fixture（不依賴 parquet cache）

**Files:**
- Create: `backtest_platform/tests/strategies/four_layer_resonance/test_v3_entry.py`

- [ ] **Step 1: 寫 fixture helper（手工構造已知四層分數的 scored DataFrame）**

`_evaluate_priority` 與 `compute_signals` 只吃分數欄位（不需原始 OHLCV 真值），故可直接構造分數列驗 gate 邏輯。建立檔案：

```python
"""v3 entry gate logic — synthetic fixtures (NOT cache-gated).

Tests entry/exit gate behavior on hand-built score rows. The "reproduce 14
entries on real 2330" check is a separate manual IS step (Sprint 6, cache-gated).
"""
from __future__ import annotations

import pandas as pd
import pytest

from backtest_platform.config.strategy_config import StrategyConfig, DEFAULT_CONFIG_V3
from backtest_platform.strategies.four_layer_resonance.signals import (
    compute_signals,
    compute_states,
)

# 欄位：compute_signals 需要的最小集合（分數 + OHLCV + box）。
_COLS = [
    "open", "high", "low", "close", "volume",
    "structure_score", "direction_score", "chip_score", "momentum_score",
    "total_score", "box_upper", "box_lower",
]


def make_row(structure, direction, chip, momentum, *, close=100.0, box_upper=99.0,
             box_lower=80.0, high=None, low=None, volume=1000.0):
    total = structure + direction + chip + momentum
    return {
        "open": close, "high": high if high is not None else close + 1,
        "low": low if low is not None else close - 1, "close": close, "volume": volume,
        "structure_score": structure, "direction_score": direction,
        "chip_score": chip, "momentum_score": momentum, "total_score": total,
        "box_upper": box_upper, "box_lower": box_lower,
    }


def frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    # high volatility so edge_ok=1 by default; tests that need edge_ok=0 override.
    df["high"] = df["close"] * 1.05
    df["low"] = df["close"] * 0.95
    return df[_COLS]
```

> **edge_ok 注意：** `compute_signals` 內部用 `volatility_rate = (high-low).rolling(14).mean()/close` 算 `edge_ok`，需 ≥14 bar 暖機。fixture 一律給寬 high/low（±5%）使 `edge_ok=1`；測 edge_ok 擋單時把該股 high/low 設極窄。

- [ ] **Step 2: 跑（僅確認 import 與 fixture 不爆）**

Run: `cd backtest_platform && uv run pytest tests/strategies/four_layer_resonance/test_v3_entry.py -q`
Expected: PASS（無測試函式，收集 0 項；或加一個 `test_imports` 斷言 `DEFAULT_CONFIG_V3.entry_min_layers == 3`）

- [ ] **Step 3: Commit**

```bash
git add backtest_platform/tests/strategies/four_layer_resonance/test_v3_entry.py
git commit -m "test(v3-entry): add synthetic score-row fixtures (not cache-gated)"
```

---

## Task 3: buy gate 參數化核心（必含層 + 負向 veto + min_structure + N-of-4 + total + first_cross flag）

**Files:**
- Modify: `backtest_platform/src/backtest_platform/strategies/four_layer_resonance/signals.py:306-313` (`buy_sig` in `_evaluate_priority`)
- Test: `backtest_platform/tests/strategies/four_layer_resonance/test_v3_entry.py`

> 本任務先不做 confirm_days / cooldown（預設值 confirm=1/cooldown=0 為 no-op）。先把 buy 核心參數化並證明 v2 預設不變、v3 放寬生效。`_evaluate_priority` 需新增參數 `prev_structure_ok_count`（confirm 用，Task 4 才接，本任務先加簽名並預設使 confirm 無效）。為降低耦合，本任務只加 `config` 既有欄位驅動的條件。

- [ ] **Step 1: 寫失敗測試（v2 reproduce + v3 各放寬 + 負向 veto）**

```python
def _buy_actions(rows, config):
    df = compute_signals(frame(rows), config)
    return df["action"].tolist()


def test_v2_default_requires_breakout_and_all_layers():
    # structure==1 (非突破) 在 v2 下不得進場
    rows = [make_row(1, 1, 1, 1, close=90)] * 3
    actions = _buy_actions(rows, StrategyConfig())
    assert "buy" not in actions  # v2: min_structure=2 擋下


def test_v3_accepts_structure_1_with_mandatory_layers():
    # structure==1 + momentum>=1 + (dir or chip)>=1 + total>=5 → v3 放行
    rows = [make_row(1, 2, 2, 1, close=90, box_lower=70)] * 3   # total=6
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert "buy" in actions


def test_v3_rejects_when_momentum_below_1():
    # 強制守門：momentum<1 即使 total>=5 也不進
    rows = [make_row(2, 2, 2, 0, close=90, box_lower=70)] * 3   # total=6 但 mom=0
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert "buy" not in actions


def test_v3_rejects_when_no_institutional_consensus():
    # 必含層：dir 與 chip 都 <1 → 不進（structure+momentum 再好也不行）
    rows = [make_row(2, 0, 0, 2, close=90, box_lower=70)] * 3   # total=4 < 5 也會擋，改 total>=5：
    rows = [make_row(2, 0, 0, 2, close=90, box_lower=70, )]
    # 用 total>=5 但 dir=chip=0：structure=2,mom=2,需再湊1 → 用 direction? 設 dir=0 chip=0 → total=4
    # 構造 total>=5 且 dir=chip=0 不可能(只剩 structure<=2+mom<=2=4)，故此情境天然被 total 地板擋。
    # 改測 negative veto：
    rows = [make_row(2, -1, 2, 2, close=90, box_lower=70)] * 3  # total=5, chip=2 但 dir=-1
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert "buy" not in actions  # 負向 veto：dir==-1 擋下


def test_v3_n_of_4_redundant_gate():
    # min_layers=3：四層達標數須>=3。structure=1,dir=1,chip=0,mom=2 → 3 層>=1 → 過
    rows = [make_row(1, 1, 0, 2, close=90, box_lower=70)] * 3   # total=4 <5 → total 地板擋
    # 需 total>=5：structure=1,dir=1,chip=1,mom=2 → layers=4,total=5 → 過
    rows = [make_row(1, 1, 1, 2, close=90, box_lower=70)] * 3
    assert "buy" in _buy_actions(rows, DEFAULT_CONFIG_V3)
```

> **測試精簡備註：** 構造資料時 total 地板(>=5)與 N-of-4 會交互，撰寫時逐一驗算 total。實作者落地時請刪除上面探索性的中間註解列，只留最終斷言列。

- [ ] **Step 2: 跑確認失敗**

Run: `cd backtest_platform && uv run pytest tests/strategies/four_layer_resonance/test_v3_entry.py -q`
Expected: FAIL（v3 放寬未實作，`buy` 不出現）

- [ ] **Step 3: 改 `_evaluate_priority` 的 `buy_sig`**

把 `signals.py` L306-313 的 `buy_sig` 取代為：

```python
    # --- v3 parameterized entry gate (v2 defaults reproduce baseline) ---
    layers_hit = sum(
        s >= 1
        for s in (
            row["structure_score"], row["direction_score"],
            row["chip_score"], row["momentum_score"],
        )
    )
    mandatory = (
        row["momentum_score"] >= 1
        and row["structure_score"] >= 1
        and (row["direction_score"] >= 1 or row["chip_score"] >= 1)
    )
    negative_veto = row["direction_score"] == -1 or row["chip_score"] == -1
    first_cross_ok = (
        not config.entry_first_cross_only
        or (pd.notna(prev_total) and prev_total < config.strong_buy_threshold)
    )
    buy_sig = (
        not in_pos
        and mandatory
        and not negative_veto
        and layers_hit >= config.entry_min_layers
        and row["structure_score"] >= config.entry_min_structure
        and row["total_score"] >= config.strong_buy_threshold
        and first_cross_ok
        and bool(row.get("edge_ok", 0))
    )
```

> **v2 等價性檢核：** v2 預設 `min_layers=4`→`layers_hit>=4`=四層全≥1（含 mandatory 與 dir/chip≥1，故 negative_veto 必 False）；`min_structure=2`→`structure>=2`即`==2`；`first_cross_only=True`→保留 `prev_total<5`；total≥5、edge_ok 不變 ⇒ 與舊 `state_strong_buy & structure==2 & prev_total<5 & edge_ok` 等價。

- [ ] **Step 4: 跑確認通過 + 既有 signals 測試不破**

Run: `cd backtest_platform && uv run pytest tests/strategies/four_layer_resonance/ -q`
Expected: PASS（v3 新測試綠；既有 `test_signals*` 全綠 — v2 預設等價）

- [ ] **Step 5: Commit**

```bash
git add backtest_platform/src/.../signals.py backtest_platform/tests/.../test_v3_entry.py
git commit -m "feat(signals): parameterize buy gate — mandatory layers + negative veto + N-of-4 + min_structure (v2 reproduces)"
```

---

## Task 4: confirm_days（structure 持續站穩 K bar）

**Files:**
- Modify: `signals.py` — `_evaluate_priority`（+`consec_structure_bars` 參數）、`compute_signals`（迴圈追蹤連續站穩）
- Test: `test_v3_entry.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_v3_confirm_days_requires_2_consecutive_structure():
    # confirm=2：第一根 structure>=1 不進，連續第二根才進
    rows = [
        make_row(0, 2, 2, 2, close=85, box_lower=70),   # structure=0 → 不站上
        make_row(1, 2, 2, 1, close=90, box_lower=70),   # structure>=1 第1根 → confirm 未滿
        make_row(1, 2, 2, 1, close=91, box_lower=70),   # 連續第2根 → 進
    ]
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert actions[1] != "buy"
    assert actions[2] == "buy"


def test_v2_confirm_days_1_is_noop():
    rows = [make_row(2, 2, 2, 1, close=90, box_lower=70, ),  # 突破首根
            make_row(2, 2, 2, 1, close=91, box_lower=70)]
    # prev_total 需 <5：第一根 prev_total NaN → first_cross_ok True；structure==2,total>=5 → v2 進場
    assert _buy_actions(rows, StrategyConfig())[0] == "buy"
```

- [ ] **Step 2: 跑確認失敗**

Run: `cd backtest_platform && uv run pytest tests/strategies/four_layer_resonance/test_v3_entry.py -k confirm -q`
Expected: FAIL

- [ ] **Step 3: 加 `consec_structure_bars` 參數 + 迴圈追蹤**

在 `_evaluate_priority` 簽名加 `consec_structure_bars: int = 1`，並在 buy_sig 加一條：

```python
    confirm_ok = consec_structure_bars >= config.entry_confirm_days
```
把 `and first_cross_ok` 後追加 `and confirm_ok`。

在 `compute_signals` 迴圈（`for i in range(n)`）內、呼叫 `_evaluate_priority` 前追蹤連續站穩：

```python
        structure_now = int(row["structure_score"]) >= 1
        consec_structure = (consec_structure + 1) if structure_now else 0
```
（在迴圈外初始化 `consec_structure = 0`）。把 `consec_structure` 傳入 `_evaluate_priority(..., consec_structure_bars=consec_structure)`。

> **暖機/邊界（spec open risk #7）：** `structure_score` 在前 `box_period=60` bar 為 NaN；`int(NaN)` 會爆。改用 `structure_now = bool(row["structure_score"] >= 1)`（NaN>=1 為 False，安全），確保 warmup bars 連續計數歸 0。加邊界測試：前 60 bar 不得進場。

- [ ] **Step 4: 跑確認通過**

Run: `cd backtest_platform && uv run pytest tests/strategies/four_layer_resonance/test_v3_entry.py -k confirm -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(signals): confirm_days K-bar sustained-structure entry gate (v2 K=1 no-op)"
```

---

## Task 5: re-entry cooldown（出場後冷卻 + 突破新箱頂豁免）

**Files:**
- Modify: `signals.py` — `_evaluate_priority`（+`bars_since_exit`, `prev_box_upper` 參數）、`compute_signals`（追蹤 bars_since_exit）
- Test: `test_v3_entry.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_v3_cooldown_blocks_reentry_within_3_bars():
    rows = [
        make_row(1, 2, 2, 1, close=90, box_lower=88),   # 進場
        make_row(1, 2, 2, 1, close=87, box_lower=88),   # close<box_lower → stoploss 出場
        make_row(1, 2, 2, 1, close=90, box_lower=70),   # 出場後第1 bar → cooldown 擋
        make_row(1, 2, 2, 1, close=91, box_lower=70),   # 第2 bar → cooldown 擋
    ]
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert actions[0] == "buy"
    assert actions[2] != "buy" and actions[3] != "buy"


def test_v3_cooldown_exempt_on_new_breakout():
    rows = [
        make_row(1, 2, 2, 1, close=90, box_lower=88, box_upper=92),
        make_row(1, 2, 2, 1, close=87, box_lower=88, box_upper=92),   # 出場
        make_row(2, 2, 2, 1, close=95, box_lower=70, box_upper=92),   # 突破新箱頂(close>prev box_upper) → 豁免
    ]
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert actions[2] == "buy"
```

- [ ] **Step 2: 跑確認失敗** — `pytest ... -k cooldown` → FAIL

- [ ] **Step 3: 加 `bars_since_exit` / `prev_box_upper` 參數 + 迴圈追蹤 + cooldown 條件**

`_evaluate_priority` 簽名加 `bars_since_exit: int = 10**9`, `prev_box_upper: float = float("nan")`。在 buy_sig **最前**加 cooldown gate：

```python
    breakout_exempt = (
        row["structure_score"] == 2
        and pd.notna(prev_box_upper)
        and row["close"] > prev_box_upper
    )
    cooldown_ok = bars_since_exit >= config.entry_cooldown_bars or breakout_exempt
```
把 `cooldown_ok and` 加進 `buy_sig` 開頭（`not in_pos and cooldown_ok and mandatory ...`）。

`compute_signals` 迴圈：外部初始化 `bars_since_exit = 10**9`；每 bar 末尾，若該 bar action 為 `stoploss`/`exit` 則 `bars_since_exit = 0`，否則 `bars_since_exit += 1`。傳 `prev_box_upper = rows["box_upper"].iloc[i-1] if i>0 else nan`。

> v2 預設 `cooldown_bars=0`→`bars_since_exit>=0` 恆真 → no-op，baseline 不變。

- [ ] **Step 4: 跑確認通過** — `pytest ... -k cooldown` → PASS；全 four_layer 測試綠

- [ ] **Step 5: Commit** — `git commit -am "feat(signals): re-entry cooldown with new-breakout exemption (v2 cooldown=0 no-op)"`

---

## Task 6: flameout 2-bar 確認（exit 最小搭配，不改 state_flameout 語意）

**Files:**
- Modify: `signals.py` — `_evaluate_priority` 的 `exit_sig`（用 momentum+prev_momentum+box_lower 自算，不讀 `state_flameout`）
- Test: `test_v3_entry.py`

- [ ] **Step 1: 寫失敗測試**

```python
def test_v3_flameout_needs_2_bar_momentum_confirm():
    rows = [
        make_row(1, 2, 2, 2, close=90, box_lower=70),   # 進場(v3)
        make_row(1, 2, 2, -1, close=89, box_lower=70),  # momentum==-1 單根 → v3 不出
        make_row(1, 2, 2, -1, close=88, box_lower=70),  # 連續2根 → 出
    ]
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert actions[1] != "exit"
    assert actions[2] == "exit"


def test_v3_box_break_exits_immediately_even_with_confirm():
    rows = [
        make_row(1, 2, 2, 2, close=90, box_lower=85),
        make_row(1, 2, 2, 1, close=84, box_lower=85),   # close<box_lower → stoploss(優先), 即時出
    ]
    actions = _buy_actions(rows, DEFAULT_CONFIG_V3)
    assert actions[1] == "stoploss"


def test_v2_flameout_single_bar_exit_preserved():
    rows = [
        make_row(2, 2, 2, 1, close=90, box_lower=70),   # v2 進場
        make_row(2, 2, 2, -1, close=89, box_lower=70),  # 單根 momentum==-1 → v2 即出
    ]
    actions = _buy_actions(rows, StrategyConfig())
    assert actions[1] == "exit"
```

- [ ] **Step 2: 跑確認失敗** — `pytest ... -k flameout` → FAIL

- [ ] **Step 3: 改 `exit_sig`（在 `_evaluate_priority` 內）**

把現有：

```python
    flameout = bool(row["state_flameout"])
    ...
    exit_sig = in_pos and (flameout or two_warnings)
```
取代為（自算 confirmed flameout，**不依賴 state_flameout**）：

```python
    mom_flameout = row["momentum_score"] == -1
    if config.exit_flameout_confirm_bars >= 2:
        mom_flameout = mom_flameout and (prev_momentum == -1)
    box_break = row["close"] < row["box_lower"]
    flameout_confirmed = mom_flameout or box_break
    exit_sig = in_pos and (flameout_confirmed or two_warnings)
```

> v2 預設 `exit_flameout_confirm_bars=1`→`mom_flameout = momentum==-1`（單根），`flameout_confirmed = (momentum==-1) or (close<box_lower)` = 原 `state_flameout` 語意 ⇒ 等價。`compute_states` 的 `state_flameout` 欄位**不動**（warning 仍依賴它）。`prev_momentum` 已是 `_evaluate_priority` 既有參數。

- [ ] **Step 4: 跑確認通過** — `pytest tests/strategies/four_layer_resonance/ -q` → PASS（含既有 signals 測試）

- [ ] **Step 5: Commit** — `git commit -am "feat(signals): flameout 2-bar momentum confirm in signal layer (v2=1 preserves; state_flameout untouched)"`

---

## Task 7: event-driven engine 對齊（EvaluateBar + evaluate_bar）

**Files:**
- Modify: `signals.py` — `EvaluateBar` dataclass、`evaluate_bar` 把新狀態接進 `_evaluate_priority`
- Test: `test_v3_entry.py`（evaluate_bar 與 compute_signals 同 row 同 config 給同 signal）

- [ ] **Step 1: 寫失敗測試（parity）**

```python
def test_evaluate_bar_matches_compute_signals_v3():
    from backtest_platform.strategies.four_layer_resonance.signals import (
        EvaluateBar, evaluate_bar,
    )
    # 建一個 v3 會進場的 bar，evaluate_bar 與 compute_signals 結論一致
    bar = EvaluateBar(
        in_position=0, entry_cost_price=0.0, close=90, high=94.5, open=90,
        box_lower=70, risk_swing_low=65, volume=1000, avg_volume_5=900,
        body_high=90, body_low=89, upper_shadow=4.5, candle_body_size=1,
        structure_score=1, direction_score=2, chip_score=2, momentum_score=1,
        total_score=6, prev_total_score=3, prev_momentum_score=1, prev_high=89,
        state_flameout=0, state_strong_buy=1, state_hold=0, state_warning=0,
        volatility_rate=0.05,
        consec_structure_bars=2, bars_since_exit=10**9, prev_box_upper=88,
    )
    assert evaluate_bar(bar, DEFAULT_CONFIG_V3) == "buy"
```

- [ ] **Step 2: 跑確認失敗** — FAIL（`EvaluateBar` 無新欄位 → TypeError）

- [ ] **Step 3: 加欄位 + 接線**

`EvaluateBar` dataclass 末尾加三欄：

```python
    consec_structure_bars: int = 1
    bars_since_exit: int = 10**9
    prev_box_upper: float = float("nan")
```

`evaluate_bar` 內呼叫 `_evaluate_priority(...)` 時補傳：

```python
        consec_structure_bars=bar.consec_structure_bars,
        bars_since_exit=bar.bars_since_exit,
        prev_box_upper=bar.prev_box_upper,
```

> 預設值使既有 evaluate_bar 呼叫端（zipline adapter）在未提供時退化為「confirm/cooldown 無效」= v2 行為，不破壞既有引擎；zipline adapter 接 v3 時再補傳（v0.1 IS 用 compute_signals 路徑為主，adapter 接線可列 Sprint 6 整合步）。

- [ ] **Step 4: 跑確認通過** — `pytest tests/strategies/four_layer_resonance/ -q` → PASS

- [ ] **Step 5: Commit** — `git commit -am "feat(signals): wire v3 entry state into EvaluateBar/evaluate_bar (defaults = v2 behavior)"`

---

## Task 8: v2 全路徑 regression（synthetic）+ coverage gate

**Files:**
- Test: `test_v3_entry.py`

- [ ] **Step 1: 寫 regression 測試（v2 預設在多情境下與「放寬前語意」一致）**

```python
@pytest.mark.parametrize("rows", [
    [make_row(2, 2, 2, 1, close=90 + i, box_lower=70) for i in range(5)],   # 突破續強
    [make_row(1, 1, 1, 1, close=90, box_lower=70)] * 5,                     # 非突破
    [make_row(2, -1, -1, 2, close=90, box_lower=70)] * 5,                   # 法人賣
])
def test_v2_default_entry_unchanged_by_v3_params(rows):
    # v2 預設下，新參數不應改變進出場序列（與放寬前邏輯等價的回歸護欄）
    df = compute_signals(frame(rows), StrategyConfig())
    # v2: 僅 structure==2 + total>=5 + first-cross + edge_ok 才進
    for _, r in df.iterrows():
        if r["action"] == "buy":
            assert r["structure_score"] == 2 and r["total_score"] >= 5
```

- [ ] **Step 2: 跑確認通過** — PASS

- [ ] **Step 3: 全測試 + coverage gate（≥80）**

Run: `cd backtest_platform && uv run pytest -q`
Expected: PASS，`--cov-fail-under=80` 不退（新增 gate 邏輯需被測試覆蓋）

- [ ] **Step 4: Commit** — `git commit -am "test(v3-entry): v2 full-path regression guard + coverage"`

---

## Task 9: 文件同步（code-doc-sync，與 code 同 PR）

**Files:**
- Modify: `strategy/v2.md`（§2.4 開 v3 並存對照、§2.5.1 成本基準校正）、`dev_docs/21_data_contract.md`（StrategyConfig 6 欄位）、`dev_docs/24_risk_management_spec.md`（flameout 確認窗 / 負向 veto / cooldown）、`dev_docs/16_wbs_development_plan.md`（§5 R9 進度 + §8.G / 模組 4.0 v3）、`dev_docs/INDEX.md` + `dev_docs/02_project_brief_and_prd.md`（D-017）
- Create: `dev_docs/adrs/ADR-019-v3-entry-redesign-relaxation-and-minimal-exit-pairing.md`

- [ ] **Step 1: 成本基準校正（先做，spec §8）**

實測值寫定：以 `strategy_config.py` 為真相源 `cost_round_rate ≈ 0.671%` / `edge_ok 門檻 ≈ 1.27%`。修 `strategy/v2.md` §2.5.1（原 1.07%）與 line 777（原 1.3%）對齊 code，並註明「0.2%×2 保守 buffer 不在 v0.1 code；中小型 universe slip buffer 上調留 v0.2」。

- [ ] **Step 2: ADR-019**

新增 `ADR-019`：記錄 v3 進場放寬（必含層+可選、6 參數、layer_policy L2⊂L3 依據）+ exit 最小搭配 + 不違反 ADR-017 論證 + 反過擬合硬約束。cross-ref ADR-017/016。

- [ ] **Step 3: v2.md §2.4 v3 並存段落 + 21/24 + INDEX/02/16 WBS**

§2.4 加「v3 進場（M0 重設）」小節對照 v2，引用本 spec；21 補 6 欄位；24 補 flameout 確認窗/負向 veto/cooldown；INDEX ADR 18→19；02 §決策沿革 D-017；16 WBS §5 R9 進度欄 + 模組 4.0/8.G.3 標記。

- [ ] **Step 4: Commit** — `git commit -am "docs(v3-entry): sync v2.md/21/24/ADR-019/INDEX/02/16 for v3 entry redesign + cost-basis fix"`

---

## Phase 3 後（Sprint 6）手動整合步驟（非單元測試 — cache-gated，誠實標註）

1. 用 `DEFAULT_CONFIG_V3` 對 **2330 + 2-3 檔中小型成分股**（1101/1303/2308/2317/2891/3008/2412）跑雙窗口（2015-2020 / 2020-2024）IS。
2. 同批跑 `exit_flameout_confirm_bars=1` 對照組。
3. 人工讀片 spec §11 成功判準：跨窗符號一致 + 邊際單品質 + 操盤手體檢（平均持有≥6、中段進場<30%、churn<20%）。**進場數只當樣本下限，非 edge。**
4. 結論寫 `sprint_*_gate_review.md` + 更新 16 WBS R9。綠燈→v0.2；紅燈→ADR-017 退場（回 M0 換 edge 來源）。

> **MEMORY 警示：** 若 parquet cache 缺，IS 步驟會 skip — 必須看 skip 數、用 ground-truth 核對，綠燈 CI≠驗證過。

---

## Plan Self-Review

- **Spec coverage：** layer_policy（Task 3）、6 參數（Task 1）、confirm（4）、cooldown（5）、exit 搭配（6）、event-driven（7）、v2 regression（1/3/8）、成本校正 + ADR + doc-sync（9）、誠實 IS gate（Phase 3 後手動）— 全覆蓋。
- **No placeholders：** 各 step 含實際 code/指令/預期。Task 3 Step 1 的探索性中間註解列已標註「落地時刪除」。
- **Type consistency：** `_evaluate_priority` 新參數 `consec_structure_bars`/`bars_since_exit`/`prev_box_upper` 在 Task 4/5 引入且 Task 7 `EvaluateBar` 同名同型對齊；`config` 6 欄位名跨 Task 1/3/4/5/6/7 一致。
