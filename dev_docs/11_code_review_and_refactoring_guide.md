# 程式碼審查與重構指南 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26

---

## 審查前自我檢查

- [ ] `PYTHONPATH=src python3 -m pytest -p no:asyncio` 全綠
- [ ] `ruff check .` 無 error
- [ ] `mypy --strict src/` 無 error（M2 才嚴格執行）
- [ ] 對應的 dev_docs 已更新（v2.md 改了 → 05/07 跟著改）
- [ ] 完成自我 review：`git diff main...HEAD`
- [ ] 無殘留 `print` debug / `TODO` 沒寫清楚
- [ ] 新增程式碼有對應單元測試

---

## 審查重點

### 1. 程式碼品質

| 項目 | 檢查 |
| :--- | :--- |
| 可讀性 | 命名清楚，函式 < 50 行，巢狀 < 4 層 |
| 一致性 | 遵循 `08_project_structure_guide.md` 命名慣例 |
| 複雜度 | 複雜邏輯有 docstring 說明 WHY |
| pure function | `strategy/` 內函式無副作用 |
| 不可變 | `StrategyConfig` 等 frozen，不寫 `.update()` 之類 |

### 2. 架構與設計

| 項目 | 檢查 |
| :--- | :--- |
| 依賴方向 | Domain 不依賴 Infrastructure（見 09 file_dependencies） |
| SOLID | 新類別檢核 SOLID 5 條 |
| 邊界驗證 | 外部資料進 Pydantic schema 才能往下流 |
| 訊號邏輯單一來源 | 不能在 engine wrapper 重寫 scoring 邏輯 |
| 配置外部化 | 無 hardcode 的 path / token / DB credential |

### 3. 策略邏輯（特殊性）

| 項目 | 檢查 |
| :--- | :--- |
| 對齊 v2.md | scoring / signals 改動須有 v2.md 對應條款 |
| Pydantic Field 範圍 | 新增參數有合理 ge/le 限制 |
| 衍生 cost 計算 | 不繞過 cost_round_rate property |
| 風控優先序 | 不破壞 stoploss > exit > ... > buy > hold |
| Cost filter 不擋風控 | `_evaluate_priority` 中 stoploss/exit 不檢查 net_profit_rate |

### 4. 效能與安全

| 項目 | 檢查 |
| :--- | :--- |
| pandas 操作 vectorize | 避免 `df.iterrows()` 除非必要（signals 例外） |
| Secrets | 從 env 讀，不入 git |
| SQL injection | 用 parameterized query（psycopg2 + execute_values） |
| ETL idempotent | 重跑結果一致 |
| 大資料 | 大檔（parquet > 100MB）gitignore |

### 5. 測試覆蓋

| 項目 | 檢查 |
| :--- | :--- |
| 新函式有測試 | happy / boundary / failure 三類各一 |
| 對應 BDD scenario | 03_bdd 文檔有對應 Gherkin |
| 不用 sleep / random（除非 seeded） | 測試需可重現 |
| integration 標記 | 需 DB / API 的測試標 `@pytest.mark.integration` |

---

## 程式碼風味（code smells）

| Smell | 訊號 | 重構建議 |
| :--- | :--- | :--- |
| 大型函式（> 50 行） | scoring/signals 函式肥大 | Extract Method：拆出 indicator 計算 |
| Magic Number | scoring 內 hardcode `5`、`0.10` | 改用 `StrategyConfig` 欄位 |
| 重複的 normalize 邏輯 | 三個 `_normalize_*` 都有 `pd.to_datetime` 處理 | Extract Helper `_to_date_col` |
| 條件式爆炸 | `_evaluate_priority` 7 個 if-block | （目前可接受，因為每個條件對應一個獨立訊號）若再多訊號 → 抽 Strategy Pattern |
| Pydantic schema 散落 | schemas 跨檔重複定義 | 集中到 `data/schemas.py` |
| pure / impure 混雜 | strategy 函式呼叫 IO | 立即重構：IO 移到 application 層 |

---

## 重構策略

| 策略 | 適用 |
| :--- | :--- |
| **Extract Method** | `compute_signals` 內 walk-loop 可能可拆 `_step(i)` |
| **Extract Variable** | 複雜布林條件先存 local `is_strong_buy_today = ...` |
| **Replace Magic with Config** | hardcode 改為 `StrategyConfig.xxx` |
| **Replace Conditional with Polymorphism** | M2 三模型進場 → IEntryModel 介面 + 三實作 |
| **Introduce Parameter Object** | `evaluate_bar` 收 21 個參數 → `EvaluateBar` dataclass（已做） |
| **Move Method** | 若 `_evaluate_priority` 邏輯被 engine 需要 → 移到 `signals.py` 公開 API |

---

## PR / Commit 模板

### Commit message（沿用 root CLAUDE.md）

```
<type>(<optional scope>): <subject>

<WHY — 背景與動機>

<WHAT — 關鍵變更摘要>

<IMPACT — 影響範圍與破壞性變更>
```

範例：

```
feat(strategy): add IC-weighted scoring as alternative to equal-weight sum

WHY: 蘇格拉底審查指出等權加總假設四因子獨立，未經實證。
v2.2 IC 測試將提供因子 IC，需有 IC 加權版本可切換。

WHAT:
- 新增 strategy.scoring.compute_scores_ic_weighted
- StrategyConfig 加 use_ic_weighting flag（預設 False，保持向後相容）
- 對應 ic_weights dict 透過 config 注入

IMPACT:
- 既有等權路徑不變
- compute_signals 不需改（讀 total_score 不在乎來源）
- v2.md 2.3.1 標註 IC 加權為可選方案

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

### PR Body 範本

```markdown
## 摘要
[1–2 句變更說明]

## 變更類型
- [ ] Bug 修復
- [ ] 新功能
- [ ] 重構（行為不變）
- [ ] 文檔更新
- [ ] 破壞性變更（升級 MAJOR）

## 動機
[WHY — 為何要做]

## 變更細節
- 主要修改 1
- 主要修改 2

## 影響
- 影響模組：
- 破壞性變更：
- v2.md 相關段落：

## 測試
- [ ] 單元測試通過（pytest）
- [ ] integration 測試（如有 DB 改動）
- [ ] 手動 end-to-end 驗證（pipeline run）
- [ ] 文檔更新

## 檢查清單
- [ ] 符合 ruff / mypy
- [ ] 自我審查 git diff
- [ ] 對應 dev_docs 已更新
- [ ] 無 secrets / 大檔
```

---

## 品質關卡

### 合併前
- [ ] `pytest` 全綠
- [ ] `ruff check` 通過
- [ ] 至少看過自己的 diff 一遍
- [ ] 對應 dev_docs 同步
- [ ] v2.md 對應段落同步（若策略邏輯變動）

### 合併後（M5 後實盤）
- [ ] paper trading 一週無異常
- [ ] 監控指標無告警
- [ ] 訊號頻率與預期相符

---

## 特殊規則（量化專案）

### 1. 策略邏輯的 WHY 必須留證
任何 scoring / signals 改動必須在 commit body 中說明：
- v2.md 的哪一條對應變更
- 是修 bug、套用 PASS 區結論、還是新增實驗

### 2. 參數調整必走 changelog
即使是 `box_period = 60 → 90` 也要：
- 更新 `StrategyConfig` Field 預設
- 在 `v2.md` Part 6.3 留下時間戳 + 動機 + 預期影響
- 升 v2.x MINOR 版本

### 3. 訊號邏輯破壞性變更
- 升 v3 MAJOR
- 重跑完整 OOS 驗證
- Paper trading 1 個月以上才能切實盤

### 4. 不在 OOS 反覆調參數
- OOS 用過一次就「燒掉」
- 想再驗證 → 等新資料累積一年

### 5. DSR N 必須記錄
- 任何參數測試（包括 git 上沒留的 jupyter 嘗試）都算
- 寫進 `strategy/research/experiment_log.md`
