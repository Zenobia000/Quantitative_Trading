# Integrated Master Prompt — Validate gate 驗證守門 (Research · Validate Gate)

> 由 `global/02_backtest_platform_brand_system.md`（壓縮 Tokens v2.0）+ `pages/research_07_validate_gate.md` 組裝的最終 Prompt。
> 可直接貼給 Lovable / Claude。對應 `guides/lovable_組裝.md` SOP，格式同 `assembly/monitor_a_performance_integrated.md`。
> **取代原 Panel E**（唯讀展示 → 不可逆 gate 工作流）；IS-vs-OOS scatter 圖型複用。

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

**最高準則聲明**：Grok 單色 dark-first、無彩色品牌色、flat 1px border #2A2A2A 無陰影、數值一律 Geist Mono tabular-nums、漲跌/PASS-FAIL 以「顏色 + ↑↓/✓✗ 文字」雙編碼、focus 單色白環、即時數據無進場動畫；此區段為唯一真實來源，不得被下游任務覆寫。

---

## === CURRENT TASK: BUILD Validate gate 驗證守門 (Validate Gate) ===

實作研究迴圈中段的不可逆 gate 工作流（route `/research/validate`）：IS gate 逐條硬門檻 → IS PASS 解鎖 OOS sealed vault → WFA/CPCV → PBO/DSR（吃試驗次數 deflate）紅線自動擋晉升 → 事前承諾對照，pass/fail 寫 promotion_audit。對應後端 `gate_state.py` + OOS sealed vault。完整規格見 `pages/research_07_validate_gate.md`，以下為 sections 重點摘要（勿重貼整份 spec）。

**Sections（由上至下，6 個，依不可逆狀態機順序）**

1. **gate_status_header**：GateStepper(Draft→IS→WFA→OOS→Validated，已過 gain/當前白/未解鎖灰 色+文字) + CandidateRef(run_id+lineage) + TrialsBadge + PowerGauge(三軸)。
2. **is_gate_checklist**：逐條 K1 CAGR>18% / K2 Sharpe>1.0 / K3 滑點 Sharpe>1.0 / min-trades / turnover / sub-period / HHI，PASS gain✓ / FAIL loss✗ + 差距值；FAIL 顯 FailHint + BackToM0Button(→ New Run 帶 context)。
3. **oos_sealed_vault**：IS 未過整段上鎖 + lock icon「前置 gate 未過不可讀/不可跑」；AccessLogNote(存取計次留痕)；IS PASS 顯 UnsealCta「解封並執行 validate oos（僅一次）」；超限 ThrottleNote 擋關。
4. **wfa_fold_view**：IsOosScatter(X=IS Sharpe Y=OOS Sharpe + y=x 對角線，上方=穩健) + FoldTable(各 fold IS/OOS + purge/embargo + 一致性) + RobustLegend(色+文字)。
5. **overfitting_redline**：PboKpi(>0.5 error+文字) + DsrKpi(吃 trials deflate, <1.0 warning/error+文字) + MtrlKpi + RedlineVerdict「PBO>0.5 或 DSR<1.0 或 OOS<門檻 → 自動 FAIL 擋 approved」。
6. **commitment_signoff**：3-up 預期 vs 實際 OOS 對照 + RiskSignoff(白 pill, 不可逆 approved；任一 gate 未過 disabled) + AuditNote(寫 promotion_audit)。

**互動重點**：stepper 反映 gate_state；IS FAIL 下游全鎖、計入試驗、導回 M0；IS PASS 解封 vault（計次）；紅線命中自動 FAIL 擋 approved 寫 audit(FAIL)；全綠 → 風控核准 → approved + 解鎖 Promote paper 觀察期。

**RWD**：Desktop stepper 全寬 + checklist/vault 兩欄；Tablet/Mobile 單欄、fold 表橫向捲動、scatter 觸控 tooltip、signoff 固定底部。

---

## === EXCEPTION RULES ===

- IS-vs-OOS scatter 與 fold 表沿用既有漲跌 / PASS-FAIL 雙編碼（gain/loss + ✓/✗），不引入新彩色語彙。
- fold 表在 @<1024px 橫向捲動（研究級表，不轉 card）。
- **重定位**：本頁取代原監控區 Panel E（唯讀展示 → gate 工作流）；舊 teal token 已收斂為 v2.0 單色（§10 GAP-4）。
- 其餘完全遵循 Global Guideline。

---

## === OUTPUT REQUIREMENTS ===

1. **結構確認**：先列出 6 個 sections 及關鍵元件（gate stepper / IS checklist / OOS sealed vault / WFA fold scatter / PBO-DSR redline / signoff）。
2. **一致性落實**：stepper/checklist/badge 色+文字雙編碼、KPI Geist Mono AAA、vault lock 態、紅線自動 FAIL、flat border #2A2A2A、focus 單色白環。
3. **程式碼**：產出完整可運行 React + Tailwind + Recharts/Plotly.js 代碼，含不可逆 stepper、IS gate 逐條綠/紅+差距、OOS vault 鎖定/解封/超限擋關、WFA scatter + fold 表、PBO/DSR 紅線判定、承諾對照、簽核 disabled 邏輯、四態、RWD。

---

*組裝日期: 2026-06-03 | 使用 backtest_platform Design System (Grok 單色 dark v2.0) | Validate gate (M3, 取代 Panel E)*
