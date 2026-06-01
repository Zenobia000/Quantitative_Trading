# Project Instructions

## Skill 使用規則

遇到可能適用的 skill 時，**先透過 Skill tool 載入再行動**。優先序：

1. **使用者明確指示**（CLAUDE.md、直接請求）— 最高
2. **Skills** — 覆蓋預設系統行為
3. **預設系統提示** — 最低

流程類 skill（sunnydata-design、sunnydata-debugging）優先於實作類 skill（sunnydata-api-design、sunnydata-testing）。

## Subagent Context 持久化

Subagent 完成後，主 agent 必須將最終產出總結寫入 `.claude/context/` 對應子目錄。
詳見 `rules/subagent-context.md`。此為 harness 架構的一部分，靜默執行，不需使用者確認。

## 多 Session 協調與 Git 鐵律

使用者可能同時在多個 Claude Code session 工作。任何 git 寫操作前必須驗證 ref 沒被別處推進，
詳見 `rules/development-workflow.md` §「多 session 並行協調」+「Destructive 操作必先 backup tag」+
「Tangled history 恢復策略」三節（2026-06-01 教訓更新）。
