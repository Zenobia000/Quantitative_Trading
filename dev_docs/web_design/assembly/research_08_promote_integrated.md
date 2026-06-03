# Integrated Master Prompt — Promotion stepper 晉升 (Research · Promote)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_08_promote.md` 組裝的最終 Prompt。
> 可直接貼給 Lovable / Claude。對應 `guides/lovable_組裝.md` SOP，格式同 `assembly/monitor_a_performance_integrated.md`。

---

## === GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===

你是 backtest_platform 的資深前端產品架構師。以下為最高準則，所有元件必須繼承此處定義的配色、字體、形狀與間距；除非 EXCEPTION RULES 明確說明，否則不得違反。

```
# backtest_platform Design System — Compressed Tokens (Grok 單色 dark v2.0)
COLORS (monochrome — 無彩色品牌色)  primary/text #F5F5F5 ; 白底 pill 按鈕 text 用 base 深色
  bg-base #0F0F0F / bg-surface #1A1A1A / bg-input #1E1E1E / bg-code #161616 / border #2A2A2A
  text #F5F5F5 / text-secondary rgba(245,245,245,.65) / text-muted rgba(245,245,245,.55)
  gain #22C55E(配↑) / loss #F87171(配↓) / loss-aaa #FCA5A5
  success #F5F5F5+✓(不用綠以免與 gain 混) / warning #E9A60C / error #EF4444
  dataviz 單色優先: strategy #F5F5F5 實線 / benchmark rgba(255,255,255,.40) 虛線 ; 多序列用明度+線型
  受控例外(僅資料區, §6.1): Categorical 8-色盤(低飽和 WCAG) / Diverging gain↔灰↔loss / Sequential 灰階
TYPE  H1 28/600 H2 22/600 H3 18/600 Body 14/400 Label 13/500 Caption 12/500
  Metric 20-32/600 Geist-Mono tabular-nums ; UI font Inter / Noto Sans TC ; mono Geist Mono
SHAPE radius sm4 md8 lg12 ; NO shadow (1px border #2A2A2A) ; button 白底 pill radius 12px
GRID fluid 100% ; bp sm640 md768 lg1024 xl1280 ; section-gap 16-24px ; table→card & sidebar→drawer @<1024px
RULES Grok 單色 dark-first ; 無彩色品牌色 ; 文字 AA / KPI 數值 AAA ; 漲跌=色+↑↓文字雙編碼(唯一彩色) ; 即時數據無進場動畫 ; flat 分層 ; focus-visible 單色白環 rgba(245,245,245,.7)
```

**最高準則聲明**：Grok 單色 dark-first、無彩色品牌色、flat 1px border #2A2A2A 無陰影、數值一律 Geist Mono tabular-nums、漲跌/狀態以「顏色 + 文字」雙編碼、focus 單色白環、即時數據無進場動畫；此區段為唯一真實來源，不得被下游任務覆寫。

---

## === CURRENT TASK: BUILD Promotion stepper 晉升 (Promote) ===

實作不可逆晉升狀態機（route `/research/promote/:strategy_id`）：Draft→Backtested→Validated→Paper→Live→Retired，每個轉換有硬門檻 checklist、試驗次數、OOS sealed vault，每階段綠燈才解鎖下一階段主 CTA + 明確降級路徑。完整規格見 `pages/research_08_promote.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，5 個）**

1. **promotion_stepper**：6 StageNodes(Draft/Backtested/Validated/Paper/Live/Retired，已過 gain✓/當前白/未解鎖灰 色+文字) + RollbackEdges(降級路徑 isGate/wfaGate/oosGate FAIL→Draft、paper 差→Draft、live 退化→Paper) + ImmutableBadge(snapshot ref)。
2. **current_stage_checklist**：當前轉換硬門檻逐條綠/紅(如 Validated→Paper：OOS pass+承諾達標+風控核准；Paper→Live：觀察期綠燈+勝率/cone) + BlockReason + 「全綠才解鎖下一階段主 CTA」。
3. **paper_observation**（Paper 階段）：ObservationProgress(已觀察 X/60 交易日) + PaperEquity(標 paper 起點邊界 + 預期 cone) + DegradeVerdict(退出 cone/勝率退化 → 打回 Draft，雙編碼)。
4. **promote_action**（sticky）：PromoteButton(白 pill, 全綠才亮, 不可逆二次確認 modal) + DemoteButton(Live→Paper) + RetireButton(→Retired 唯讀) + DeriveButton(Retired 衍生新變體 → New Run)。
5. **audit_log**：promotion_audit 表（時間/動作/操作者/metrics 快照/run snapshot ref，Geist Mono）+ SnapshotLink + 「紀錄不可竄改」。

**互動重點**：stepper 反映 validation_status；未達 Validated 導回 Validate gate；checklist 全綠才解鎖主 CTA；晉升不可逆二次確認；Paper 退化可降級回 Draft；Live 退化降回 Paper；退役凍結唯讀可衍生新變體；每次轉換寫 promotion_audit；Live 交監控 A–E 子視圖接管。

**RWD**：Desktop stepper 水平 + checklist/paper 兩欄；Tablet stepper 橫向捲動；Mobile stepper 垂直、audit 表橫向捲動、二次確認全屏 modal。

---

## === EXCEPTION RULES ===

- paper_observation 的 equity cone band 沿用既有漲跌語義（gain/loss + 邊界文字標籤），不引入新彩色。
- audit 表在 @<1024px 橫向捲動（研究級表，不轉 card）。
- **刻意不做**（§4.5）：跨人競賽 leaderboard、多人簽核、champion/challenger registry、staking 真錢——用三狀態 + 不可逆 gate + 強制 paper 觀察期替代。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 sections 及關鍵元件（stepper + 回退邊 / stage checklist / paper observation / promote action / audit log）。
2. **一致性落實**：stepper/checklist 色+文字雙編碼、cone 沿用漲跌語義、數值 Geist Mono、不可逆二次確認、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind + Recharts 代碼，含不可逆 stepper + 降級回退邊、當前階段 checklist 解鎖式 CTA、paper 觀察期進度+cone、二次確認 modal、audit 表、四態、RWD（stepper 垂直化 + 橫向捲動）。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | Promotion stepper (M5)*
