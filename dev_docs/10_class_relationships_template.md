# 類別 / 元件關係 — backtest_platform

> 對應架構文件 [05](./05_architecture_and_design_document.md)、模組規格 [07](./07_module_specification_and_tests.md)。本檔聚焦定義平台骨幹的核心類別與其關係，全部對應 `backtest_platform/src/backtest_platform/` 現行程式碼。

## 產品定位

backtest_platform 是 **個人量化 edge 驗證工廠 + 晉升管線**。核心資產是審判庭。以下類別圖的重心正是這個資產：**策略契約**（讓平台判任意策略）、**審判庭資料模型**（兩段閘）、**風控值物件**。策略是消耗品，這些骨幹類別是資產。

---

## 1. 策略契約 + registry（平台↔策略接縫，ADR-027/028）

接縫畫在**輸出**：策略輸入天生不同（four_layer 逐股事件驅動、momentum/inst_flow 橫斷面 panel），但都產出同一個 `StrategyRun`。上層只依賴此契約。

```mermaid
classDiagram
    direction LR

    class StrategyRunner {
        <<Protocol / runtime_checkable>>
        +ClassVar~type~ config_model
        +ClassVar~str~ title
        +ClassVar~GateSpec~ gate
        +run(symbols, start, end, config, loader) StrategyRun
    }

    class StrategyRun {
        <<frozen dataclass>>
        +dict metrics
        +Series returns
        +list trades
    }

    class StrategyInfo {
        <<frozen dataclass>>
        +str name
        +str title
        +str description
        +dict config_schema
    }

    class Registry {
        <<module: strategies.protocol>>
        +register_strategy(name) decorator
        +get_strategy(name) StrategyRunner
        +get_strategy_gate(name) GateSpec
        +list_strategies() list
        +describe_strategies() list~StrategyInfo~
    }

    class FourLayerRunner
    class MomentumRunner
    class InstFlowRunner
    class TemplateRunner

    FourLayerRunner ..|> StrategyRunner
    MomentumRunner ..|> StrategyRunner
    InstFlowRunner ..|> StrategyRunner
    TemplateRunner ..|> StrategyRunner
    StrategyRunner ..> StrategyRun : run() 產出
    Registry ..> StrategyRunner : name→instance
    Registry ..> StrategyInfo : describe
```

**契約不變式**（conformance gate 強制，`strategies/conformance.py`）：

| 不變式 | 說明 |
| :--- | :--- |
| `config_model()` 無參可建 | 所有欄位有預設或無欄位 |
| `run(...)` 不 raise on synthetic data | 合成資料下不炸 |
| `metrics ⊇ {cagr, sharpe, slippage_sharpe, maxdd, trades, bars}` | 空結果亦須全填 0，讓 gate 不 INCOMPLETE |
| `gate` 必宣告且其 criterion key ⊆ 產出 metrics | 平台拒絕用別人的尺判這隻策略 |

> `GateSpec = tuple[Criterion, ...]`：策略宣告自己的審判閘（見 §2）。dispatch 用 `get_strategy_gate(name)` 解析——four_layer 的 entry-quality 檢查對 panel 策略無意義，故每隻策略自帶尺，缺席即 hard error（審查缺陷 #8 修正）。

---

## 2. 審判庭資料模型（validation，ADR-025/030）

審判庭是核心資產。gate-as-code：門檻是**資料**（`Criterion` / 模組常數），調門檻是可見、可記錄的決策，不是靜默 edit。

### 2.1 gate_state — 泛用逐 criterion 判決

```mermaid
classDiagram
    direction LR

    class GateStatus {
        <<Enum>>
        PASS
        FAIL
        INCOMPLETE
    }

    class Criterion {
        <<frozen dataclass>>
        +str key
        +str op
        +float threshold
        +str kind
        +str label
        +check(value) bool
        +gap(value) float
    }

    class CriterionResult {
        <<frozen dataclass>>
        +Criterion criterion
        +float value
        +bool passed
        +float gap
    }

    class GateResult {
        <<frozen dataclass>>
        +tuple~CriterionResult~ results
        +status() GateStatus
        +passed() bool
        +failing() list
        +missing() list
    }

    GateResult "1" *-- "*" CriterionResult
    CriterionResult ..> Criterion
    GateResult ..> GateStatus
```

`evaluate_gate(metrics, gate)`：缺 metric → `INCOMPLETE`（絕不假 PASS）。內建閘：`DEFAULT_GATE`（four_layer entry-quality）、`PANEL_GATE`（橫斷面分散度）、`MOMENTUM_GATE`（PANEL 別名）。

### 2.2 two_stage_gate — 真偽閘 + 配置閘（ADR-025）

```mermaid
classDiagram
    direction LR

    class TruthVerdict {
        <<Enum>>
        REAL
        REJECTED
        INCOMPLETE
    }

    class TruthGateInput {
        <<frozen dataclass>>
        +bool survivorship_clean
        +bool pre_registered
        +float pbo
        +float wfa_oos_positive_frac
        +float dsr
        +float slippage_sharpe
        +float oos_holdout_sharpe
    }

    class TruthGateResult {
        <<frozen dataclass>>
        +TruthVerdict verdict
        +tuple~str~ reasons
        +is_real() bool
    }

    class SizingInput {
        <<frozen dataclass>>
        +float oos_sharpe
        +float correlation_to_fleet
        +float capacity_fraction
        +float cagr : reference-only
    }

    class SizingConfig {
        <<frozen dataclass>>
        +float max_weight
        +float reference_sharpe
    }

    class GateDecision {
        <<frozen dataclass>>
        +TruthGateResult truth
        +float size
    }

    TruthGateResult ..> TruthVerdict
    GateDecision *-- TruthGateResult
    GateDecision ..> SizingInput : size only if REAL
```

- **真偽閘** `evaluate_truth_gate(TruthGateInput)`：binary hard-fail。`pre_registered=True` 用 WFA OOS 廣度 + trials-deflated DSR（不用 landscape PBO）；`False` 用 PBO。survivorship 不 clean / 滑價崩 / OOS holdout 負 = REJECTED。
- **配置閘** `compute_position_size(SizingInput)`：連續映射 `size = max_weight × conviction × diversification × capacity`。絕對 CAGR 降為 reference，永不 size。
- **兩段編排** `evaluate_two_stage(...)`：truth 非 REAL → `size == 0.0`。

---

## 3. Run 物件化 + 研究工作流 config（research，ADR-029/032）

`RunConfig` 是一個 IS run 的一級物件；工作流 config 是各策略以 `research_config.py` 宣告「怎麼被研究」的契約。

```mermaid
classDiagram
    direction LR

    class RunConfig {
        <<Pydantic frozen>>
        +str hypothesis : 預先註冊，必填
        +str strategy : registered name
        +dict params : dispatch 時驗證
        +tuple~str~ stocks
        +date is_start
        +date is_end
        +str engine : sim | zipline
        +run_id() str : deterministic hash
    }

    class DOEConfig {
        <<Pydantic frozen>>
        +str strategy
        +dict grid
        +list~str~ symbols
        +date is_start
        +date is_end
        +n_configs() int
    }

    class GOGatesConfig {
        <<Pydantic frozen>>
        +BaseModel fixed_config
        +dict config_grid
        +int n_wfa_folds
        +int pbo_n_splits
    }

    class TruthGateConfig {
        <<Pydantic frozen>>
        +BaseModel fixed_config
        +date is_start
        +date oos_start
        +date is_end
        +int n_trials
        +bool pre_registered
        +bool survivorship_clean : 預設 False
        +str parquet_dir : 快取覆蓋
        +float slippage_stress
    }

    class PaperReplayConfig {
        <<Pydantic frozen>>
        +BaseModel fixed_config
        +date as_of
        +float initial_cash
        +int lookback_buffer_days
    }

    class UniverseConfig {
        <<Pydantic frozen>>
        +date span_start
        +date span_end
        +int top_n
        +float min_turnover
        +str cache_dir
    }
```

> 工作流 config 全 `frozen + extra=forbid`；window validator 守 `is_start < oos_start < is_end`。`TruthGateConfig.survivorship_clean` 預設 `False`——ADR-025 的 hard precondition 是待證明的主張，不是硬編碼綠燈（ADR-030 反自欺原則）。

---

## 4. 風控值物件（risk，spec 24）

pre-trade 風控純函式化：12 個 `check_exNNN(order, account, cfg) -> reason | None`，`RiskGate` 依 spec §2.2 優先序 wire。所有狀態注入，零 IO。

```mermaid
classDiagram
    direction LR

    class Order {
        <<frozen dataclass>>
        +str stock_id
        +str side : buy/add/sell/reduce/exit/stoploss
        +float qty
        +float price
        +str industry
        +float stop_loss
        +notional() float
        +is_buy() bool
    }

    class Position {
        <<frozen dataclass>>
        +str stock_id
        +float qty
        +float entry
        +float stop_loss
        +float market_value
        +risk_amount() float
    }

    class AccountState {
        <<frozen dataclass>>
        +float equity
        +float cash
        +tuple~Position~ positions
        +BreakerState breaker_state
        +int orders_last_minute
        +frozenset blacklist
        +position(stock_id) Position
    }

    class RiskGateConfig {
        <<frozen dataclass>>
        +float single_name_max_pct
        +float industry_max_pct
        +float portfolio_heat_max
        +int max_positions
        +... 12 rule 門檻
    }

    class RiskGateResult {
        <<frozen dataclass>>
        +bool allowed
        +list rejections
    }

    class RiskGate {
        +check(order, account, collect_all) RiskGateResult
    }

    class BreakerState {
        <<Enum>>
        NORMAL / L1 / L2 / L3 / HALTED
        +severity() int
    }

    AccountState "1" *-- "*" Position
    AccountState ..> BreakerState
    RiskGate ..> Order
    RiskGate ..> AccountState
    RiskGate ..> RiskGateConfig
    RiskGate ..> RiskGateResult
```

`CircuitBreaker.evaluate` 產生瞬態 `L3`，機器立即 latch 進終端 `HALTED`；`risk_gate.check_ex012` 對 `L3`/`HALTED` 皆 reject（單一 `BreakerState` 於 `risk/types.py`，避免 per-module enum 分岔讓 halted 單漏過）。

---

## 5. Paper 撮合器（adapters.brokers）

`PaperBroker` 是 M4 paper daemon 的 in-process 撮合引擎，strategy-agnostic 純簿記（無 order book / partial fill / 網路），成本模型單一來源 `StrategyConfig`。

```mermaid
classDiagram
    direction LR

    class PaperBroker {
        <<dataclass>>
        +float initial_cash
        +StrategyConfig config
        +float cash
        +submit_order(stock_id, side, qty, price) Fill
        +equity(marks) float
        +portfolio_snapshot(marks, stop_prices) dict
    }

    class Fill {
        <<frozen dataclass>>
        +str stock_id
        +OrderSide side
        +int qty
        +float price
        +float fee
        +float tax
        +notional() float
        +cash_flow() float
    }

    class Position {
        <<dataclass>>
        +int qty
        +float cost_basis
    }

    class OrderSide {
        <<Enum: str>>
        BUY / SELL
        +coerce(value) OrderSide
    }

    PaperBroker "1" *-- "*" Position : 持倉
    PaperBroker ..> Fill : 產出成交記錄
    Fill ..> OrderSide
```

`portfolio_snapshot` 回 `{positions, cash, equity, heat}`（EX-004 heat 公式，stop 注入式）——正是 `orchestration.collaborators` 建 `AccountState` 餵風控閘的來源。無賣空（賣超持有量 raise `InsufficientPositionError`）。

---

## 6. 每日鏈 staged engine（orchestration.daily_flow）

```mermaid
classDiagram
    direction LR

    class FlowContext {
        <<dataclass>>
        +dict config : 注入的 collaborators
        +dict outputs : 逐 stage output
    }

    class StageResult {
        <<frozen dataclass>>
        +str name
        +bool ok
        +str detail
        +Any output
    }

    class FlowRun {
        <<frozen dataclass>>
        +tuple~StageResult~ stages
        +ok() bool
        +failed_stage() str
        +summary() str
    }

    FlowRun "1" *-- "*" StageResult
```

`run_flow(stages, ctx)`：依序跑 `etl → signals → risk_gate → orders → log`，**fail-fast**（首個 `ok=False` 或 raise 即停，raise 被捕捉成失敗 stage，永不 crash 排程器）。collaborators 從 `ctx.config` 注入，stage body 只編排。

---

## 設計模式與 SOLID

| 模式 | 應用 | 目的 |
| :--- | :--- | :--- |
| **Protocol（結構型）** | `StrategyRunner`、`engines.Engine`（DEPRECATED） | 平台依賴契約非具體策略 |
| **Registry** | `strategies.protocol` name→runner dict | 輕量 dispatch（[ADR-022](./adrs/ADR-022-multi-strategy-fleet-operations.md) 拒重量級 registry）|
| **Gate-as-code / 資料驅動** | `Criterion` 元組、two_stage 門檻常數 | 調門檻 = 可見可記錄決策 |
| **Frozen Value Object** | `RunConfig`、workflow configs、`Order`/`Position`/`AccountState` | 不可變，避免狀態洩漏 |
| **Pure Function 核心** | 策略計分、validation、risk 12 檢查 | 零 IO、易測、可跨 backtest/paper/live 重用 |
| **Staged Pipeline** | `daily_flow.run_flow` | fail-fast + 完整審計軌 |

- **S 單一職責**：`validation/` 每檔一種統計檢驗、`risk_gate` 只做 pre-trade、`paper_broker` 只做簿記。
- **O 開放封閉**：新增策略 = 複製 `_template/` 填 alpha + registry 註冊一行，不改上層。
- **L 里氏替換**：任何 `StrategyRunner` 實作可經 registry 互換。
- **I 介面隔離**：`Loader = Callable[[str], DataFrame]` 是唯一資料存取接縫。
- **D 依賴反轉**：上層依賴 `strategies.protocol` 抽象；`validation` 不依賴 `strategies`（無循環）。
