# 開發工作流

## 鐵律：先開分支，再動程式碼

**任何修改程式碼的動作之前，必須確認在正確的工作分支上。**

收到開發任務時，第一步永遠是：

```
git branch --show-current
git status
```

| 當前狀態 | 行動 |
| :------- | :--- |
| 在 `main`/`master` 上 | **停止。** 詢問使用者：要建新分支還是切到既有分支？ |
| 在功能分支但有未提交變更 | **停止。** 詢問使用者：先 commit 還是放棄這些變更？ |
| 在功能分支且乾淨 | 確認分支名稱與任務匹配，繼續 |
| 使用者直接說「改這個」沒提分支 | **停止。** 詢問使用者分支策略 |

### 禁止行為

- 禁止在 `main`/`master` 上直接修改程式碼
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
