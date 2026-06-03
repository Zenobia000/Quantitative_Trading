# Integrated Master Prompt — New Run 設定頁 (Research · New Run Config)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_02_run_new.md` 組裝的最終 Prompt。
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

**最高準則聲明**：Grok 單色 dark-first、無彩色品牌色、flat 1px border #2A2A2A 無陰影、數值一律 Geist Mono tabular-nums、漲跌以「顏色 + ↑↓ 文字」雙編碼、focus 單色白環、即時數據無進場動畫；此區段為唯一真實來源，不得被下游任務覆寫。

---

## === CURRENT TASK: BUILD New Run 設定頁 (New Run Config) ===

實作單頁三段式 run config 表單（route `/research/runs/new`）：預先註冊假設、參數化（值或 range/step）、成本+引擎+IS/OOS 區間，提交前估算 run 數與成本後異步提交。對應後端 `run_configs` schema + CLI `backtest-run`。完整規格見 `pages/research_02_run_new.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，5 個）**

1. **hypothesis_section**（pre-registration）：ThesisInput(單一論點 ≤200 字, required) + ExpectedSharpe/WinRate/MaxDD 三門檻(required, Geist Mono)；「提交後門檻鎖定，OOS 完成自動紅/綠對照」。
2. **parameters_section**：13 個 ParamPill（值/range-step toggle）+ UniverseFilter + CodeEditor(Monaco, bg-code #161616, 邏輯與參數分離, 唯讀 diff 模式)。
3. **cost_engine_section**：成本攤平（手續費/滑點/漲跌停 switch/T+2 唯讀）+ EngineSelect(zipline|vectorbt) + BundleRef(鎖快照)。
4. **period_section**：IsRangePicker(研究者自選) + OosLockedRange(系統鎖死 + lock icon，sealed vault：前置 gate 未過不可讀/不可跑)。
5. **submit_bar**（sticky bottom）：EstimateLabel「will run N configs, est M min」+ TrialsBadge(累計試驗 N | DSR) + SubmitButton(白 pill)；N 過大 SubmitGuard 警示。

**互動重點**：range/step 切換即重算 N（笛卡爾積）；Submit 觸發 RunConfig Pydantic schema 驗證，失敗逐欄 inline 紅框留本頁不丟輸入；通過寫 run_configs、產 run_id（git-sha+bundle+序號）、status=queued，跳 Run Report；衍生變體預填 baseline。

**RWD**：Desktop 各 section 2 欄 + submit sticky bottom；Tablet section 單欄、pill 2 欄；Mobile 全單欄、CodeEditor 全寬可摺疊。

---

## === EXCEPTION RULES ===

- **CodeEditor** 使用 Monaco 預設 dark 主題微調的語法高亮 — 屬「chrome 單色之上、code 內容區受控例外」，僅限 code 區，不擴散至頁面 chrome。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 5 個 sections 及關鍵元件（hypothesis 三門檻 / 13 ParamPill + CodeEditor / cost+engine / period 鎖 OOS / submit estimate）。
2. **一致性落實**：配色僅取自 Tokens（Grok 單色）、數值/估算 Geist Mono、required 欄位驗證、OOS lock icon、CodeEditor 語法高亮僅限 code 區、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind + Monaco 代碼，含表單驗證（RunConfig schema，失敗逐欄 inline 紅框）、range/step 即時估算、OOS 鎖死、提交異步產 run_id、RWD 三斷點。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | New Run 設定頁 (M3)*
