# 程式碼 ↔ 文件同步

## 鐵律

**實作 code 與更新 docs 屬同一個任務、同一個 PR**。寫完 code 就立刻盤點受影響的 dev_docs 並一併修改，**禁止「以後再補文件」**。經驗顯示「之後再補」幾乎都會忘，最後產生 doc drift（曾累積到需要 5 個 commit 的 sweep 才補完）。

## 何時觸發同步檢查

在以下時機強制執行 §「觸發對映表」檢查：

1. **每次 commit 前** — 列出該 commit 動到的程式碼類型，對映需動的 docs
2. **每次 PR 前** — 總覽整批 commits 影響的 docs，補齊跨 commit 的整體影響
3. **使用者問「文件還有什麼要改」前** — 主動做完不該等使用者問

## 觸發對映表（本專案）

下表是 code 變更類型 → 必查 docs 的對應。**任一觸發欄成立就必須去檢查右側對應 docs**（不一定要改，但要看過確認是否需動）。

| Code 變更類型 | 必查 docs |
| :--- | :--- |
| 新增 / 移除 / 改名 `src/backtest_platform/<module>/` 模組 | 08（結構）、09（依賴）、17 §5（M2+ 目錄樹）|
| 新增 / 移除 ADR-worthy 決策（升版、換引擎、換通道等）| `adrs/ADR-NNN-*.md` 新增、INDEX 階段 2 表計數、INDEX 階段 7 ADR 表、02 PRD §決策沿革表 |
| Pydantic schema / DDL / Bundle 結構變更 | 21（資料契約）、09（依賴）|
| 新增 / 移除 / 升版 `pyproject.toml` 依賴 | 02 PRD §依賴、ADR（若重大升級）、ADR-012（uv 用法若改變）|
| 環境變數新增 / 改名 | `.env.example`、08 §環境變數表 |
| 新 API endpoint / CLI 子命令 | 06（API 設計）、`README.md` |
| 新測試類別（performance / e2e 等）| 22（測試策略）、03（BDD）|
| Docker / 部署拓撲變更 | 14（部署運維）、23（部署拓撲）|
| 風控 / 熔斷 / Heat 邏輯 | 24（風控規格）、13（安全清單）|
| Dashboard / Streamlit / 告警通道 | 20（儀表板規格）、ADR-009/010 |
| Sprint milestone 任務完成 / 狀態變化 | 16 WBS（**單一狀態真相源**，永遠要動）|
| 跨多檔重構 / 結構大改 | 05（架構文件版本 banner）、17（master plan banner）、08（結構）|
| Spike 結果 / Gate Review | `sprint_*_gate_review.md`、16 WBS 進度欄 |

## 工作流融入

在 `development-workflow.md` §「功能實作流程」之間插入 §「3.5 文件同步」：

```
1. 先規劃
2. TDD 方法
3. 程式碼審查
3.5 文件同步 ← 本規則；對映表檢核
4. 提交
```

並在 `git-workflow.md` §「PR 前置條件」加入：

```
- [ ] 已對映 `code-doc-sync.md` 觸發表，確認受影響 docs 全部更新
```

## 漏動文件的後果（為什麼必須遵守）

- 新人 / 未來自己讀 doc 走錯路（如 17 還寫 rqalpha 主骨架）
- Doc drift 累積後須整批 sweep（成本 ×N，且容易再漏）
- ADR 與實作脫節，「為何這樣做」失去追溯
- WBS 失去 single-source-of-truth 地位

## 例外（允許延後同步的情境）

- **純內部重構**，無對外介面、無架構文件描述：可不動 docs（但仍要更新 16 WBS 進度）
- **WIP commit**（branch 內 squash 前）：可暫不同步，但 PR 提出前必須補齊
- **dependency lock 自動更新**（`uv.lock` 等）：不需動 docs

## 自我檢查模板（每次 commit / PR 前唸過）

```
[ ] 這個 commit 動了哪幾類 code？
[ ] 對應觸發表，需要動哪些 docs？
[ ] 已動 / 已確認不需動 / 還沒動？
[ ] 16 WBS 進度欄已更新？
[ ] ADR 已寫或已 cross-ref？
```

任一欄不過就**不可送 PR**。
