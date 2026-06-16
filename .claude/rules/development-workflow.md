# 開發工作流

## 鐵律：先開分支，再動程式碼

> **本節是「開分支策略」的操作層真相源（single source of truth）。**
> 全局 `~/.claude/CLAUDE.md` 只保留通用原則（一句話鐵律），不複製此表；
> 分支命名 / 生命週期 / merge 策略見 `git-workflow.md`。三者交叉引用、不重複內容，避免 drift。

**任何修改程式碼的動作之前，必須確認在正確的工作分支上。**

收到開發任務時，第一步永遠是：

```
git branch --show-current
git status
```

### 當前狀態 → 行動對照表

| 當前狀態 | 行動 |
| :------- | :--- |
| 在 `main`/`master` 上 | **停止。** 詢問：建新分支還是切既有分支?（**瑣碎變更亦然 —— 保護分支永不直接改碼**）|
| 功能分支、乾淨、且分支名與任務匹配 | **繼續。** 瑣碎低風險變更免再確認（見下方定義）。|
| 功能分支但有未提交、且**與本次任務無關**的變更 | **停止。** 詢問：先 commit、移到對的分支、還是放棄? |
| 跨任務：現有分支主題與新任務不符 | **停止。** 一分支一任務 —— 詢問是否開新分支。|
| 使用者說「改這個」沒提分支 | 非瑣碎 → **停止**問分支策略；瑣碎且已在乾淨功能分支 → 直接做並於回覆中告知所在分支。|

> **「瑣碎低風險變更」定義（2026-06-16 放寬起手摩擦）**：單一檔案小幅修改、文件 / 註解更新、dependency lock 自動同步，**且同時滿足** —— 不跨任務邊界、不在保護分支、無未提交的不相關變更。符合者免走完整 STOP-詢問流程；其餘一律走完整流程。此放寬與 `git-workflow.md` 收尾「commit → push → PR 一氣呵成」的低摩擦哲學對齊（起手與收尾同步放寬，哲學一致）。

### 禁止行為

- 禁止在 `main`/`master` 上直接修改程式碼（瑣碎變更也不例外）
- 禁止用 `git stash` 作為工作流（stash 是臨時工具，不是分支替代品）
- 禁止在一個功能分支上混做不相關的任務
- 禁止跳過分支直接開始寫程式碼

### 多 session 並行協調（2026-06-01 教訓）

使用者可能同時跑多個 Claude Code session 在同一個 repo。**任何 git 寫操作前，必須驗證 ref 沒被別處推進**，否則會產生 duplicate cherry-pick、stale branch、ahead-of-origin main 等問題（曾累積 39 commits ahead 才被發現）。

執行 commit / branch / merge / rebase / cherry-pick / push 前：

```bash
git branch --show-current             # 確認分支沒換
git log --oneline -3                  # 確認 tip 沒移動
git status                            # 確認工作樹預期狀態
ps aux | grep [g]it                   # 是否有別的 git process 在跑
```

警示訊號（出現任一就 STOP 並詢問使用者）：
- 工作樹有不認得的 modified / untracked 檔
- 看到 duplicate commit subject 不同 SHA（cherry-pick 跨 session 殘留）
- 分支 tip 跟你上次看到的不同
- 出現未追蹤的 backup tag 或 sibling branch
- HEAD 指向不認得的 commit

### 根治多 session 競態：用 git worktree 隔離（2026-06-16 教訓）

上述「寫前驗 ref」是**反應式偵測**，無法根治兩個 session 共用**同一 working tree / 同一 HEAD / 同一 index** 的競態。實際事故：B session 在 A 進行 review 的中途 stage 了檔案並把共用 HEAD 從 `feat/...` 搬到 `main`，導致 A 的 `git checkout -b` 從錯誤 base 長出、`git add` 污染到對方 index 裡 staged 的檔案。

**根治法：每個並行 session 用獨立 git worktree（共用同一 `.git`，但 HEAD / index / 工作樹完全獨立）。**

```bash
git worktree add ../Quantitative_Trading-<task> -b <type>/<task>   # 開隔離工作區
# 各 session 在自己的 worktree 工作，互不干擾
git worktree remove ../Quantitative_Trading-<task>                 # 收尾移除
```

何時必用 worktree（出現任一）：
- 已知有另一個 Claude session 正在同 repo 工作（`ps aux | grep [c]laude` 看到 2+ 個）
- 需要在多個分支間並行推進、互不阻塞
- 任務會大量改動工作樹、頻繁 commit / 切分支

偵測到共用工作樹衝突時的**應急程序**（非根治）：
1. 立即停止所有 git 寫操作
2. 把 HEAD / index 還原成對方 session 離開時的狀態（勿動對方 staged 檔案）
3. 通知使用者協調 —— 暫停某 session，或改用上述 worktree 隔離

### Destructive 操作必先 backup tag

執行 `reset --hard`、`push --force`、`branch -D` 前必須先：

```bash
git tag -a backup/<branch>-<YYYY-MM-DD> -m '安全快照, tip <oid>'
```

恢復路徑：`git reset --hard backup/<branch>-<YYYY-MM-DD>`。

### Tangled history 恢復策略

當 local main 已大幅領先 origin 且包含散落的工作：

| 場景 | 推薦策略 |
| :--- | :--- |
| 單人專案、無 review 需求 | 把 local main 整批包成「wrapper PR」推上 origin/main（含 `.gitattributes` 標準化等收尾改動）|
| 多人協作或需 review | Tag backup → reset main → cherry-pick 工作到 feature branch → stacked PR |
| 行尾飄移造成假 diff | 先 `git diff --ignore-all-space --stat` 驗證；若全是 EOL，加 `.gitattributes` 一次解決 |

### 詢問模板

當使用者要求修改但未指定分支時：

```
開始前需要確認分支策略：

目前在：<branch-name>
未提交變更：<有/無>

建議：
1. 建新分支 <type>/<suggested-name>（推薦）
2. 在目前分支繼續（僅限已在正確功能分支上）
3. 切到既有分支 ___

請選擇，或告訴我你偏好的分支名稱。
```

## 功能實作流程

分支確認完成後，依以下順序執行：

### 0. 研究與重用（任何新實作前必做）
- 先搜 GitHub 找現有實作和模式
- 再查官方文檔確認 API 行為
- 搜套件庫（npm/PyPI/crates.io）找現成方案
- 優先採用經驗證的方案而非全新撰寫

### 1. 先規劃
- 載入 sunnydata-design skill
- 探索意圖與需求 → 撰寫實作計畫 → 依檢查點執行

### 2. TDD 方法
- 遵循 TDD 流程（詳見 testing.md）

### 3. 程式碼審查
- 寫完程式碼後載入 sunnydata-code-review skill
- 處理 CRITICAL 和 HIGH 問題

### 3.5 文件同步（強制）
- 依 `code-doc-sync.md` 觸發對映表盤點受影響 dev_docs
- 此步驟與 code 屬同一 commit / 同一 PR，禁止「以後再補」
- 16 WBS（單一狀態真相源）永遠要更新進度欄

### 4. 提交
- 遵循 git-workflow.md 的 WHY/WHAT/IMPACT 標準
- 一個 commit 做一件事
- 載入 sunnydata-branch-lifecycle skill 完成分支收尾
