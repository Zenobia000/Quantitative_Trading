# ADR-004: StrategyConfig 採用 Pydantic v2 frozen model

> **狀態：** 已接受 | **日期：** 2026-05-26 | **決策者：** Self

---

## 1. 背景與問題

- **上下文**：策略參數（box_period、chip_strong_threshold 等 13 個）需要在多處共用，不能被意外修改
- **問題**：用 dict / dataclass / pydantic / namedtuple 哪個最好
- **驅動因素 / 約束**：
  - **不可變**：回測過程中改參數 = bug
  - **型別驗證**：`box_period` 必須是整數且 >= 10
  - **業務規則**：`warning_threshold < strong_buy_threshold`
  - **可重現**：同 config 跑出同結果（hash 化）

---

## 2. 考量的選項

### 選項一：plain dict
- **描述**：`config = {"box_period": 60, ...}`
- **優點**：簡單
- **缺點**：無驗證、可被修改、IDE 無 autocomplete
- **成本/複雜度**：低

### 選項二：dataclass(frozen=True)
- **描述**：標準庫 dataclass
- **優點**：標準庫、輕量、frozen 防修改
- **缺點**：型別驗證需自己寫 `__post_init__`
- **成本/複雜度**：低

### 選項三：Pydantic v2 BaseModel(frozen=True)
- **描述**：Pydantic 提供 validation + frozen
- **優點**：宣告式驗證、原生 JSON 序列化、`model_validator` 處理交叉驗證
- **缺點**：多一個依賴
- **成本/複雜度**：低

### 選項四：namedtuple
- **描述**：`Config = namedtuple("Config", [...])`
- **優點**：天然不可變
- **缺點**：無 default values、無驗證、欄位多時冗長
- **成本/複雜度**：低

---

## 3. 決策

**選擇：選項三（Pydantic v2 frozen model）**

**理由**：
- 已用 Pydantic 做 ETL schema 驗證（`schemas.py`），不增加依賴
- `Field(60, ge=10, le=250)` 一行搞定範圍驗證
- `@model_validator(mode="after")` 處理「warning < strong_buy」這類交叉規則
- `frozen=True, extra="forbid"` 雙保險：不可改 + 不可加未知欄位
- 衍生屬性（`cost_buy_rate`、`cost_round_rate`）用 `@property`

---

## 4. 後果

- **正面**：
  - 任何錯誤參數在建構時即拋例外（fail fast）
  - 函式簽名清晰：`compute_scores(df, config: StrategyConfig)`
  - 易於 JSON 序列化（trade audit trail 存 strategy_version + config snapshot）
- **負面**：
  - 改參數需建新 instance（不能 `config.box_period = 90`）
  - 但這正是想要的行為！
- **影響範圍**：`config/strategy_config.py`、所有 strategy / signal 函式
- **重新評估觸發**：需要 hot-reload 參數 → 重新評估（但這應該透過建新 instance 處理）

---

## 5. 執行計畫

1. ✅ M1：定義 `StrategyConfig` 13 個欄位、3 個交叉驗證
2. ✅ M1：所有 strategy 函式接受 `StrategyConfig` 參數
3. M2：trade audit trail 序列化 config snapshot
4. M3：DOE 參數網格用 `StrategyConfig.model_copy(update={...})` 生成變體
5. M5：實盤 config 變更需 log 留下 diff

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-26 | Self | 初版 |
