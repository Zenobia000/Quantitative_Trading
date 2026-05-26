# 文檔與維護指南 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26

---

## 1. 文檔類型

| 類型 | 內容 | 位置 | 格式 |
| :--- | :--- | :--- | :--- |
| **策略契約** | 四層共振戰法規格 | `strategy/v2.md` | Markdown |
| **策略研究** | DOE 模板、IC 測試計畫 | `strategy/research/` | Markdown |
| **工程文檔** | 架構、模組、API、ADR | `dev_docs/`（本目錄） | Markdown + Mermaid |
| **C4（嚴格）** | 嚴格 C4 規則、L1–L3 圖、PR Checklist | `dev_docs/05_architecture_and_design_document.md` §1.1 | Markdown + Mermaid |
| **工程運維** | M1/M2/... milestone setup | `backtest_platform/docs/` | Markdown |
| **API 規範** | CLI + Python API | `dev_docs/06_api_design_specification.md` | Markdown |
| **使用者文檔** | README + quick start | `README.md`、`backtest_platform/README.md` | Markdown |
| **開發者文檔** | code review、style | `dev_docs/11`、`.claude/rules/` | Markdown |

---

## 2. 文檔即程式碼

### 目錄結構

```
/Quantitative_Trading/
│
├── README.md                          # 專案總覽
├── strategy/
│   ├── v2.md                          # 策略契約（單一真相）
│   ├── archive/
│   │   └── v1_chatlog.md              # 歷史對話原稿
│   └── research/
│       ├── v2.2_ic_test_plan.md
│       ├── doe_research_template.md
│       └── scripts/
│           ├── finmind_poc.py
│           └── README.md
│
├── backtest_platform/
│   ├── README.md                      # 平台 quick start
│   ├── docs/                          # 工程運維文檔
│   │   ├── M1_setup.md
│   │   ├── m1_data_audit_2330_2024_11.md
│   │   └── M2/M3/M4/M5_*.md           # 待補
│   └── src/                           # 內含 docstring（Google style）
│
└── dev_docs/                          # 開發工程文檔（本目錄）
    ├── INDEX.md
    ├── 01_workflow_manual.md
    ├── 02_project_brief_and_prd.md
    ├── ...
    └── adrs/
        ├── ADR-001-engine-rqalpha-plus-vectorbt.md
        ├── ADR-002-timescaledb-for-time-series.md
        ├── ADR-003-pure-function-strategy-layer.md
        └── ADR-004-pydantic-frozen-config.md
```

### 撰寫規範

- **簡潔明瞭**：直接切入重點（Linus 式：「don't waste my time」）
- **主動語態**：「設定 token」非「token 應被設定」
- **包含範例**：可直接複製跑的範例
- **定期更新**：每個 milestone 完成必更新
- **版本控制**：跟著 git history 走
- **WHY > WHAT**：解釋為何，不只描述行為

### 不要做

- ❌ 寫「is_active 是 boolean」這種廢話（型別已經寫在 code）
- ❌ ASCII art 圖（用 Mermaid）
- ❌ TODO 留 6 個月沒處理（要嘛刪、要嘛排上去做）
- ❌ 重複（cross-reference 用連結）

---

## 3. 維護排程

### 每完成一個 milestone

- [ ] 更新對應的 `backtest_platform/docs/M*_*.md`
- [ ] 更新 `dev_docs/02_project_brief_and_prd.md` 進度表
- [ ] 更新 `dev_docs/16_wbs_development_plan.md` 完成百分比
- [ ] 更新 `dev_docs/01_workflow_manual.md` 當前狀態
- [ ] 如有架構變更，新增 ADR 到 `dev_docs/adrs/`
- [ ] 更新 `dev_docs/05_architecture_and_design_document.md` §1.1 C4 圖（含 Checklist）

### 每變更策略邏輯

- [ ] 更新 `strategy/v2.md` 對應條款
- [ ] 在 `strategy/v2.md` Part 6.3 留下 changelog entry
- [ ] 升級版本號（MAJOR / MINOR / PATCH）
- [ ] 同步更新 `backtest_platform/src/` 程式碼
- [ ] 同步更新 `dev_docs/07_module_specification_and_tests.md`

### 每月

- [ ] 審查 `dev_docs/INDEX.md` 是否仍與實際檔案一致
- [ ] 檢查 dev_docs 內所有 git/file path 連結是否仍有效
- [ ] 更新 README 中的 milestone 狀態
- [ ] `pip list --outdated` 檢查依賴

### 每季

- [ ] 全面文檔稽核（檢查內容是否與程式碼脫鉤）
- [ ] 更新架構圖（如有重大演進）
- [ ] 重新整理 quick start（新人能否 30 分鐘上手）

---

## 4. README 模板

每個重要目錄都應有 README，內容包含：

```markdown
# [目錄名稱]

## 描述
[1–2 句說明這個目錄是什麼]

## 內容
- `xxx.py` — [一句說明]
- `yyy/` — [一句說明]

## 使用方式
[最少的範例]

## 相關
- 上層 README: [連結]
- 對應 dev_docs: [連結]
```

當前已有 README 的位置：
- `/README.md`（專案總覽）
- `/backtest_platform/README.md`（平台快速開始）
- `/strategy/research/scripts/README.md`（POC 腳本）
- `/dev_docs/INDEX.md`（文檔索引）

---

## 5. CHANGELOG 模板

### 策略本身

放在 `strategy/v2.md` Part 6.3：

```markdown
### v2.x.x — YYYY-MM-DD
- 變更：[做了什麼]
- 原因：[為什麼]
- 預期影響：[IS / OOS 預估變化]
- 實際影響：[實測結果，事後補]
- 變更人：[誰]
```

### 程式碼套件

未來放在 `backtest_platform/CHANGELOG.md`：

```markdown
# Changelog

## [Unreleased]
### 新增
### 變更
### 修復
### 棄用
### 移除
### 安全

## [0.2.0] - 2026-XX-XX
### 新增
- M2 rqalpha engine integration

## [0.1.0] - 2026-05-26
### 新增
- 初版：四層計分、訊號狀態機、ETL、universe、pipeline CLI
```

---

## 6. Docstring 規範（Python 程式碼內）

採用 **Google style**，重點在 docstring 開頭一句話 + 為何（why）：

```python
def compute_scores(df: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
    """Return df augmented with the four layer scores and total score.

    Input is assumed sorted ascending by date with no duplicate dates.
    All required columns must be present (see REQUIRED_COLUMNS).
    Warmup bars (first box_period rows) will have NaN scores.

    Args:
        df: DataFrame with REQUIRED_COLUMNS (OHLCV + 法人 + 籌碼)
        config: Strategy parameters

    Returns:
        DataFrame copy with score columns added

    Raises:
        ValueError: if any required column is missing

    Example:
        >>> scored = compute_scores(merged_df, StrategyConfig())
        >>> scored["total_score"].describe()
    """
```

**不要**寫純複述型 docstring：

```python
def compute_scores(df, config):
    """Compute scores for df with config."""  # ❌ 廢話
```

---

## 7. 最佳實踐

1. **隨開發同步撰寫**：寫 commit 時順手更新對應文檔
2. **文檔也要 Review**：PR diff 必含對應 dev_docs 更新
3. **單一真相**：策略邏輯只在 `strategy/v2.md`，工程細節只在 `dev_docs/`
4. **連結而非複製**：跨檔資訊用 `[xxx](path/to/file.md)` 引用
5. **保留歷史**：archive 過舊檔到 `archive/`，不刪除

---

## 8. 文檔健康度檢查（每月跑）

```bash
# 找出最近 6 個月沒更新的檔
find dev_docs/ -name "*.md" -mtime +180

# 找出 dead links
grep -r "\[.*\](.*\.md)" dev_docs/ | while read line; do
  # 解析每個 link，檢查檔案存在
  ...
done

# 找出 TODO 與 FIXME
grep -rn "TODO\|FIXME\|XXX" dev_docs/ strategy/ backtest_platform/docs/
```

---

## 9. 翻譯與一致性

- 本專案文檔以**繁體中文**為主
- 程式碼註解 / docstring 用**英文**
- 術語對照：見 `dev_docs/05_architecture_and_design_document.md` 1.2 通用語言

| 中文 | 英文（代碼用） |
| :--- | :--- |
| 結構分 | structure_score |
| 法人方向分 | direction_score |
| 籌碼強度分 | chip_score |
| 動能分 | momentum_score |
| 總分 | total_score |
| 強多 | strong_buy |
| 續抱 | hold |
| 警告 | warning |
| 熄火 | flameout |
| 標的池 | universe |
| 訊號 | signal |
| 部位 | position |
| 停損 | stoploss |
| 停利 | takeprofit |
| 加碼 | add |
| 減碼 | reduce |
| 賣出 | exit |
| 買進 | buy |
