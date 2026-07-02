# 文檔與維護指南 — backtest_platform

---

## 1. 文檔類型

| 類型 | 內容 | 位置 | 格式 |
| :--- | :--- | :--- | :--- |
| **策略契約** | `StrategyRunner` 輸出契約 + registry（ADR-027/028） | `src/.../strategies/protocol.py` | Python |
| **策略宣告** | 每隻策略的 UNIVERSE/DOE/GO_GATES/TRUTH_GATE/PAPER_REPLAY | `strategies/<name>/research_config.py` | Python (frozen Pydantic) |
| **工程文檔** | 架構、模組、API、ADR | `dev_docs/`（本目錄） | Markdown + Mermaid |
| **C4（嚴格）** | 嚴格 C4 規則、L1–L3 圖、PR Checklist | [05](./05_architecture_and_design_document.md) §1.1 | Markdown + Mermaid |
| **工程運維** | milestone setup / runbook | `backtest_platform/docs/`、`dev_docs/runbooks/` | Markdown |
| **API 規範** | CLI + Python API | [06](./06_api_design_specification.md) | Markdown |
| **REST 契約** | 前後端契約唯一真相源 | [25](./25_fe_be_rest_contract.md) + OpenAPI | Markdown |
| **使用者文檔** | README + quick start | `README.md`、`backtest_platform/README.md` | Markdown |

---

## 2. 文檔即程式碼

### 目錄結構

```
/Quantitative_Trading/
│
├── README.md                          # 專案總覽（快覽 + 指向 16 WBS）
├── strategy/
│   └── v2.md                          # legacy 四層共振規格（已廢止，ADR-023；保留為歷史）
│
├── backtest_platform/
│   ├── README.md                      # 平台 quick start
│   ├── docs/                          # 工程運維文檔（M*_setup）
│   └── src/backtest_platform/
│       └── strategies/                # ★ 現行策略契約源（protocol.py + 各策略 research_config.py）
│
└── dev_docs/                          # 開發工程文檔（本目錄）
    ├── INDEX.md
    ├── 01_workflow_manual.md
    ├── 02_project_brief_and_prd.md
    ├── ...
    └── adrs/                          # 架構決策記錄（ADR-001~032）
```

### 撰寫規範

- **簡潔明瞭**：直接切入重點（Linus 式：「don't waste my time」）
- **寫現在**：文檔描述**現行狀態**，不堆疊 migration 敘事；歷史留給 git log 與 ADR（見 §10）
- **主動語態**：「設定 token」非「token 應被設定」
- **包含範例**：可直接複製跑的範例
- **WHY > WHAT**：解釋為何，不只描述行為
- **連結而非複製**：跨檔資訊用 cross-reference

### 不要做

- ❌ 寫「is_active 是 boolean」這種廢話（型別已在 code）
- ❌ ASCII art 圖（用 Mermaid）
- ❌ 在檔首疊加版本 changelog banner（v2.x → v3.x 堆疊）——寫現在
- ❌ TODO 留 6 個月沒處理（要嘛刪、要嘛排上去做）

---

## 3. 維護排程

### 每完成一個 milestone / sprint task

- [ ] **更新 [16_wbs_development_plan.md](./16_wbs_development_plan.md)**（唯一狀態源，見 §10）
- [ ] 如有架構變更，新增 ADR 到 `dev_docs/adrs/`
- [ ] 依 `code-doc-sync.md` 觸發表盤點並更新受影響 dev_docs（同一 PR）

> ⚠️ **不要**手動更新 02 PRD / 01 workflow / README 等檔的「狀態」欄 — 這些一律 cross-ref `16 WBS`（見 §10）

### 每新增 / 變更策略

- [ ] 新增或修改 `strategies/<name>/research_config.py`（參數宣告）
- [ ] 通過 `check_strategy(name)` conformance gate
- [ ] 若產生判決（REAL / REJECTED / NO-GO），寫成 ADR（如 ADR-023 動能 NO-GO）
- [ ] 同步 [07](./07_module_specification_and_tests.md)（若契約層變動）

### 每月

- [ ] 審查 [INDEX.md](./INDEX.md) 是否仍與實際檔案一致
- [ ] 檢查 dev_docs 內所有 cross-ref 連結是否仍有效
- [ ] `uv pip list --outdated` 檢查依賴（ADR-012）
- [ ] 抽 10 個檔頭跑 §10.4 一致性檢查指令

### 每季

- [ ] 全面文檔稽核（檢查內容是否與程式碼脫鉤）
- [ ] 更新架構圖（如有重大演進）
- [ ] 重新整理 quick start（新人能否 30 分鐘上手）

---

## 4. README 模板

每個重要目錄都應有 README：

```markdown
# [目錄名稱]

## 描述
[1–2 句說明這個目錄是什麼]

## 內容
- `xxx.py` — [一句說明]

## 使用方式
[最少的範例]

## 相關
- 對應 dev_docs: [連結]
```

當前已有 README 的位置：`/README.md`、`/backtest_platform/README.md`、`/dev_docs/INDEX.md`、`strategies/_template/README.md`（策略撰寫骨架）。

---

## 5. CHANGELOG 模板

### 策略判決與參數

策略是消耗品，沒有長壽命的 per-strategy changelog：

- **判決**（REAL / REJECTED / NO-GO）寫成一次性、不可變的 ADR（如 [ADR-023](./adrs/ADR-023-momentum-no-go-hold-gate.md) 動能 NO-GO、[ADR-024](./adrs/ADR-024-institutional-flow-candidate-strategy.md) 資金流 FAIL）。
- **參數**宣告在 `strategies/<name>/research_config.py`，變更歷史由 git log 承載，不另立 changelog 檔。

### 程式碼套件

放在 `backtest_platform/CHANGELOG.md`（[Keep a Changelog](https://keepachangelog.com) 格式）：

```markdown
# Changelog

## [Unreleased]
### 新增
- research/workflows/universe.py：survivorship-clean universe 建構工作流（ADR-032）
### 修復
- truth_gate DSR 單位錯誤 → per-period SR + cross-trial variance（ADR-030）
### 移除
- scripts/inst_flow_*.py 一次性腳本 → research/workflows/ 通用工作流（ADR-029）
```

---

## 6. Docstring 規範（Python 程式碼內）

採用 **Google style**，重點在開頭一句話 + 為何（why）：

```python
def run_truth_gate(cfg: TruthGateConfig) -> TruthGateResult:
    """Judge a strategy through the two-stage truth gate (ADR-025/030).

    Stage 1 (hard-fail): PBO / DSR(deflated) / WFA OOS breadth / survivorship-clean.
    Stage 2 (continuous): sizing from Sharpe / correlation / capacity.
    OOS holdout [oos_start, is_end] is actually evaluated, not just declared.

    Args:
        cfg: pre-registered窗口 + n_trials（frozen）

    Returns:
        TruthGateResult with verdict REAL / REJECTED and reasons

    Raises:
        ValueError: if DSR input units are inconsistent (fail-fast, no silent miscompute)
    """
```

**不要**寫純複述型 docstring（`"""Compute scores for df with config."""` ❌ 廢話）。

---

## 7. 最佳實踐

1. **隨開發同步撰寫**：寫 commit 時順手更新對應文檔（同一 PR）
2. **文檔也要 Review**：PR diff 必含對應 dev_docs 更新
3. **單一真相**：狀態只在 16 WBS、架構決策只在 ADR、REST 契約只在 doc 25
4. **連結而非複製**：跨檔資訊用 cross-reference
5. **寫現在**：不保留過時敘事於正文；歷史由 git log 與 ADR 承載

---

## 8. 文檔健康度檢查（每月跑）

```bash
# 找出最近 6 個月沒更新的檔
find dev_docs/ -name "*.md" -mtime +180

# 找出 TODO 與 FIXME
grep -rn "TODO\|FIXME\|XXX" dev_docs/ backtest_platform/docs/
```

---

## 9. 翻譯與一致性

- 本專案文檔以**繁體中文**為主
- 程式碼註解 / docstring 用**英文**
- 術語對照：見 [05](./05_architecture_and_design_document.md) §1.2 通用語言

| 中文 | 英文（代碼用） |
| :--- | :--- |
| 標的池 | universe |
| 訊號 | signal |
| 部位 | position |
| 停損 | stoploss |
| 停利 | takeprofit |
| 真偽閘 | truth gate |
| 配置閘 | sizing gate |
| 晉升管線 | promotion pipeline |
| 血統 | lineage / provenance |

---

## 10. 狀態真相源規則 + AI slop 預防

### 10.0 核心原則：文件寫現在

**禁止 migration 敘事累積。** 文檔正文描述**現行狀態**；「為何從 A 演化到 B」屬歷史，留給 git log 與 ADR，不在正文疊加版本 banner / 決策沿革轉述 / changelog 堆疊。ADR 只需一行 cross-ref。這是本檔最高規則，違反即 doc drift 的根源。

### 10.1 三類資訊、三個唯一源

| 資訊類型 | 唯一源 | 其他檔做什麼 |
|:--|:--|:--|
| **進度狀態**（M 完成 / sprint task）| [`16_wbs_development_plan.md`](./16_wbs_development_plan.md) | cross-ref，禁止重寫狀態欄 |
| **架構決策**（為何選 X、模組邊界）| `dev_docs/adrs/ADR-*.md` | 提及時 cross-ref `[ADR-XXX]`，禁止重複論述 |
| **策略契約與參數**（門檻/參數/判決）| `StrategyRunner` 契約（ADR-027）+ `strategies/<name>/research_config.py`；判決寫 ADR | 對應 code 改動 commit 引用 ADR / research_config |
| **REST 契約**（envelope/端點/錯誤碼）| [`25_fe_be_rest_contract.md`](./25_fe_be_rest_contract.md) + OpenAPI | 06 §9 等為便覽，歧異以 25 為準 |

### 10.2 更新流程

**進度狀態**：完成 task → 更新 16 WBS（一次寫對：task ✅ + 進度百分比 + §6/§7 若切 milestone/sprint）→ commit 引用 WBS 條目 → 禁止同時改 README/01/02 狀態描述。

**架構決策**：重大選擇前寫 ADR-XXX（背景/選項/決策/後果）→ 舊 ADR superseded 時加 "Superseded by ADR-YYY" → 對應 commit 引用 ADR 編號 → 文件提及用 cross-ref。

**策略**：改 `research_config.py`（參數）或寫 ADR（判決）→ 通過 conformance gate → commit 引用 ADR / research_config → 不在文檔正文硬編碼策略門檻。

### 10.3 禁止 AI slop 的具體規則

**Hard rule（PR review 駁回標準）**：

| 違反行為 | 駁回理由 |
|:--|:--|
| 在檔首疊加版本 changelog banner（v2.x → v3.x 堆疊） | 違反 §10.0；壓成「當前狀態」+ 一行「歷史見 git log」 |
| 在 README/01/02/05 等非 WBS 檔加「milestone 狀態」欄 | 違反 §10.1；改 cross-ref |
| 同一架構決策在 2+ 文件論述 | 違反 §10.1；保留 ADR、其他 cross-ref |
| 同一策略門檻在 2+ 處硬編碼 | 違反 §10.1；改宣告於 research_config |
| commit message 不引用 WBS / ADR / research_config | 違反 §10.2；補引用 |
| AI 產文檔含過時狀態（與 WBS 不一致） | 違反 §10.3；移除或 cross-ref |
| 新模組 / 新目錄無對應 ADR | 違反 §10.2；補 ADR |
| 修改現有 ADR 正文（除非標 superseded / 補 audit footer） | 違反 ADR 不可變原則；新寫 ADR 取代 |

**Soft rule（review 警告）**：

- 跨文檔重複描述同一主題 > 50 字 → 拆 single source + cross-ref
- 文檔描述「行為」但 code 已不一致 → 修文檔或修 code（不能兩者都對）
- 文檔中「TODO/FIXME」超過 30 天 → 排上 WBS 或刪除

### 10.4 一致性檢查指令（每月跑）

```bash
# 1. 找出 dev_docs 中除 WBS 外仍有 milestone 狀態字樣的檔
grep -rn "M[1-5]\s*完成\|M[1-5]\s*啟動\|✅\|⏳\|🚧" dev_docs/ --include="*.md" \
  | grep -v "16_wbs_development_plan.md" \
  | grep -v "cross-ref\|詳見 16\|單一狀態"

# 2. 找出有架構決策論述但無對應 ADR / cross-ref 的段落
grep -rn "決策\|考慮的選項\|為什麼選\|trade-off" dev_docs/ --include="*.md" \
  | grep -v "adrs/" | grep -v "ADR-" | grep -v "cross-ref\|詳見"

# 3. 找出 dead cross-ref（指向不存在的 ADR / 文件）
grep -rno "(ADR-[0-9]\{3\}\|[0-9]\{2\}_[a-z_]\+\.md)" dev_docs/ \
  | while IFS=: read -r file lineno match; do
      target=$(echo "$match" | tr -d '()')
      if [[ "$target" == ADR-* ]]; then
          ls dev_docs/adrs/"$target"*.md >/dev/null 2>&1 || echo "MISSING: $file:$lineno → $target"
      else
          [ -f "dev_docs/$target" ] || echo "MISSING: $file:$lineno → $target"
      fi
  done
```

### 10.5 例外狀況

允許重複的場景：

- **快覽性質**：README 列里程碑「快覽」OK，但須註明「詳見 16 WBS」
- **歷史備份**：舊 commit 中的狀態描述不需追溯改
- **教學/onboarding**：quickstart 可重述少量狀態，但加「截至 YYYY-MM-DD」時間戳
- **PR/issue**：跨工具溝通可重述，不算 in-tree slop
