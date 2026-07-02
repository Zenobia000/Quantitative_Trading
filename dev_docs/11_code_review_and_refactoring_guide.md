# 程式碼審查與重構指南 — backtest_platform

---

## 審查前自我檢查

- [ ] `uv run pytest` 全綠、coverage ≥ 80%（CI 三 job 綠）
- [ ] `ruff check .` 無 error
- [ ] `mypy --strict src/` 無 error
- [ ] 對應的 dev_docs 已更新（依 `code-doc-sync.md` 觸發表，含 16 WBS 進度）
- [ ] 已自我 review：`git diff main...HEAD`
- [ ] 無殘留 `print` debug / 未寫清楚的 `TODO`
- [ ] 新增程式碼有對應單元測試

---

## 審查重點

### 1. 程式碼品質

| 項目 | 檢查 |
| :--- | :--- |
| 可讀性 | 命名清楚，函式 < 50 行，巢狀 < 4 層 |
| 一致性 | 遵循 `08_project_structure_guide.md` 命名慣例 |
| 複雜度 | 複雜邏輯有 docstring 說明 WHY |
| pure function | `strategies/` 內策略邏輯無副作用（IO 在呼叫端） |
| 不可變 | Pydantic config frozen，不修改既有物件 |

### 2. 架構與設計

| 項目 | 檢查 |
| :--- | :--- |
| 依賴方向 | Domain 不依賴 Infrastructure（見 [09](./09_file_dependencies_template.md)）；策略不反向 import 別的策略私有函式 |
| SOLID | 新類別檢核 SOLID 5 條 |
| 邊界驗證 | 外部輸入（HTTP body / CLI overrides）走 `model_validate`，不用 `model_copy(update=)` 繞過 frozen + validator |
| 配置外部化 | 無 hardcode 的 path / token / DB credential；路徑走 `config/settings.py` |
| 不靜默吞錯 | `except Exception: continue` 需能區分「空資料」與「真錯誤」，全空即 raise 而非回 0 分假判決 |

### 3. 策略契約（ADR-027/028/029）

策略是消耗品、平台是資產——審查確保新策略乾淨接入契約，不腐蝕平台。

| 項目 | 檢查 |
| :--- | :--- |
| StrategyRunner 契約 | 新策略提供 `runner.py`，`run()` 回 `StrategyRun`；不繞過契約直接被引擎掛載 |
| registry 註冊 | 經 `register_strategy` 註冊；`config_model` / `title` ClassVar 完整（feeds `GET /strategies`） |
| conformance gate | `check_strategy(name)` 通過（parametrized CI 覆蓋所有已註冊策略） |
| research_config 完整性 | 宣告 `UNIVERSE` / `DOE` / `GO_GATES` / `TRUTH_GATE` / `PAPER_REPLAY`，frozen Pydantic；作者只填參數，不寫工作流邏輯 |
| dispatch 純度 | 工作流走 `get_strategy(name).run()`，**絕不** `import` 策略的 backtest 函式（AST 測試守門） |
| gate 隨策略 dispatch | 策略宣告自己的 GateSpec；審判用該策略的 gate，非四層專屬 DEFAULT_GATE |
| gate health ⊆ metrics | gate 引用的 health 指標必須 ⊆ 該策略 runner 產出的 metrics keys（conformance 斷言） |
| 空結果完整性 | 策略空結果（`_EMPTY_METRICS`）需含 gate 所需全部 keys，避免判成假 INCOMPLETE |

### 4. 審判庭變更（gate / DSR / oracle）— 特殊審查

審判庭是唯一護城河，改動風險最高，額外要求：

- **判決級 oracle 測試必須先 RED**：改 gate / DSR / two_stage_gate 前，先寫一個釘住已知期望的測試（含已知 REJECTED 案例，如年化 SR 0.333 → DSR ≤ 0.95），跑到失敗，再改實作到通過。禁止只有 shape-only（型別 + 0-1 範圍）測試放行判決級 bug。
- **單位一致性**：DSR 用 per-period SR + cross-trial variance；輸入單位不符即 fail-fast，不靜默算錯。
- **OOS holdout 真評估**：宣告的 OOS 窗口必須被實際讀取並入判，不可只寫窗口卻只跑 IS。
- **survivorship 由資料決定**：`survivorship_clean` 由 universe 建構器輸出，禁止寫死 True。

### 5. 效能與安全

| 項目 | 檢查 |
| :--- | :--- |
| pandas vectorize | 避免 `df.iterrows()` 除非必要 |
| Secrets | 從 env / `settings.py` 讀，不入 git、不入回應或前端 bundle |
| SQL injection | parameterized query（psycopg2 + execute_values） |
| ETL idempotent | 重跑結果一致；parquet 快取部分覆蓋走 read-merge-write，不覆寫既有歷史 |
| 大資料 | 大檔（parquet > 100MB）gitignore |

### 6. 測試覆蓋

| 項目 | 檢查 |
| :--- | :--- |
| 新函式有測試 | happy / boundary / failure 三類 |
| 對應 BDD scenario | [03](./03_behavior_driven_development_guide.md) 有對應 Gherkin |
| 可重現 | 不用 sleep / 未 seeded 的 random |
| integration 標記 | 需 DB / API 的測試標 `@pytest.mark.integration` |

---

## 程式碼風味（code smells）

| Smell | 訊號 | 重構建議 |
| :--- | :--- | :--- |
| 大型函式（> 50 行） | 策略 sim / 工作流函式肥大 | Extract Method 拆子步驟 |
| Magic Number | 門檻 hardcode 在函式內 | 改用 config 欄位 |
| 反向 import 私有函式 | 策略 A 挖策略 B 的 `_helper` | 抽至 `strategies/common`（ADR-026） |
| 假的邊界驗證 | `model_copy(update=dict)` 套外部輸入 | 改 `model_validate`，讓 frozen + validator 生效 |
| 靜默吞錯 | `except Exception: continue` | 收集失敗、全空即 raise |
| Schema 散落 | Pydantic model 跨檔重複 | 集中到 `data/schemas.py` |

---

## 重構策略

| 策略 | 適用 |
| :--- | :--- |
| **Extract Method** | walk-loop 內邏輯拆 `_step(i)` |
| **Extract Variable** | 複雜布林條件先存 local |
| **Replace Magic with Config** | hardcode 改為 config 欄位 |
| **Introduce Parameter Object** | 多參數函式收成 dataclass / Pydantic model |
| **Move to common** | 被 2+ 策略需要的機制上移 `strategies/common`（ADR-026） |

---

## PR / Commit 模板

Commit message 沿用 `git-workflow.md` 的 WHY / WHAT / IMPACT 三段式；結尾加：

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

PR Body 四區段：**Background**（動機）/ **Changes**（決策取捨，非 file list）/ **Impact**（破壞性變更、migration）/ **Test Plan**（驗證步驟 checklist）。

---

## 品質關卡

### 合併前
- [ ] `uv run pytest` 全綠、CI 三 job 綠
- [ ] `ruff check` / `mypy --strict` 通過
- [ ] 自我 review diff 一遍
- [ ] 對應 dev_docs 同步（含 16 WBS）
- [ ] 審判庭級變更有先 RED 的 oracle 測試

### 合併後（M5 後實盤）
- [ ] paper trading 一週無異常
- [ ] 監控指標無告警
- [ ] 訊號頻率與預期相符

---

## 特殊規則（量化專案）

1. **策略是消耗品，透過 `research_config.py` 宣告**：新增策略只寫 config + runner + research_config，不新增一次性腳本。
2. **OOS 用過一次就燒掉**：不在 OOS 反覆調參；想再驗證等新資料累積一年。
3. **試驗計數必記錄**：任何參數測試（含未進 git 的嘗試）都計入 n_trials，餵給 DSR deflate。
4. **門檻不因單一策略放寬**：gate 是紀律；救策略不得改閘（ADR-023）。
5. **血統可稽核**：每個 run 記 bundle hash / git_sha，判決可在標準化工作流下重現。
