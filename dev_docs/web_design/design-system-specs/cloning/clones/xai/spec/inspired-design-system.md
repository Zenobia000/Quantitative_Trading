# Inspired Design System — backtest_platform（inspired by x.ai）

> **來源致謝**：設計決策啟發自 https://x.ai/（擷取 2026-06-01）。本規格為**差異化重建**，不含來源之文案、商標、logo、字型檔或圖片資產。
> **目標產品**：Quantitative_Trading / backtest_platform 儀表板與行銷頁。
> **結構對齊**：`global/BASE_DESIGN_SYSTEM.md` 分層。
> 標註圖例：`[inspired by: xai]` 學自來源 ｜ `[original]` 我方新增 ｜ `[override]` 來源有但已改。

---

## [PRODUCT CONTEXT LAYER]

- 產品：量化交易回測平台。核心畫面為**資料密集儀表板**（績效曲線、持倉、交易明細、風險指標）+ 輕量行銷/文件頁。
- 受眾：策略開發者、量化研究者、自託管使用者。
- 模式：**dark-first**，light 為次。 `[override]`（來源僅 light）

## [BRAND & VOICE LAYER]

- 個性：沉穩、精準、可信賴（金融工具，非炫技 AI）。
- 視覺語氣：克制、資訊密集、降噪。`[inspired by: xai]`（學其克制）

## [VISUAL DESIGN SYSTEM LAYER]

### 配色 (Color Tokens)

> 採**單一墨色 + 透明度階層**做文字層級。`[inspired by: xai]`
> HSL/hex 已過對比度檢核（見 §INTERACTION）。

```
# Brand
color.brand.primary      #0E7490   teal-700    [override] (來源 #0A0A0A)
color.brand.primary.hover #0C6173  teal-800    [original]
color.brand.accent       #F59E0B   amber       [override] (僅警示，來源橘為品牌色)

# Neutral — dark-first（paper = dark mode 的「墨」反相）
## dark mode
color.surface.base       #0B1220   近黑藍灰     [override] (來源純黑→改近黑藍灰，降對比硬度)
color.surface.raised     #131C2B   卡片底       [original]
color.border             #243044   1px 分隔     [inspired by: xai] (來源 1px border 分層)
color.text.primary       #E6EDF5   paper        [override]  (對比 15.87:1 AAA)
color.text.secondary     rgba(230,237,245,.65)  [inspired by: xai] (透明度階層；7.10:1 AAA)
color.text.muted         rgba(230,237,245,.55)  [inspired by: xai] [override: .45→.55] (修正至 5.38:1 AA；來源 .45 僅 4.0:1 不達標)
## light mode
color.surface.base.light #F8FAFC               [override] (來源暖白→冷白)
color.text.primary.light #0B1220               [override]

# Semantic
color.success            #22C55E   [inspired by: xai] (--success)
color.warning            #E9A60C   [inspired by: xai] (--warning)
color.error              #EF4444   [inspired by: xai] (--error)
color.info               #60A5FA   [override] (來源 breeze 偏淺，提高對比)

# Finance-specific（dark mode 上色值已對比驗證）
color.gain               #22C55E   上漲/獲利   [original]  (7.50:1 on raised → AAA ✓)
color.loss               #F87171   下跌/虧損   [original]  (6.18:1 on raised → AA；來源 #DC2626 在深底僅 3.54 不達標)
color.loss.aaa           #FCA5A5   loss 需 AAA 的關鍵數值 [original] (9.01:1 → AAA ✓)
color.surface.code       #0D1117   程式碼/終端 [inspired by: xai] (--color-codeblock)
```

### 排版 (Typography)

> 字重僅 2–3 級。`[inspired by: xai]`（來源只用 400/550）

```
font.family.heading   Inter / Geist Sans          [override] (來源 universalSansDisplay 為專有)
font.family.body      Inter / Geist Sans          [override]
font.family.mono      Geist Mono (tabular-nums)   [override] (來源 GeistMono；數值欄位強制等寬對齊) [original-rule]

# Type scale（儀表板收斂，砍掉 60px 行銷 display）[override]
font.h1     28px / 600 / lh 1.2          [override] (來源 60px display → DROP)
font.h2     22px / 600 / lh 1.25
font.h3     18px / 600 / lh 1.3
font.body   14px / 400 / lh 1.5          [inspired by: xai] (來源 UI 主力 14px)
font.label  13px / 500 / lh 1.4
font.caption 12px / 500 / lh 1.3
font.metric 數值用 mono + tabular-nums   [original] (價格/績效對齊)
```

### 元件風格

```
button.primary    bg color.brand.primary / text #fff / radius 8px / 8px 16px / 14px 500
                  [inspired by: xai 的 pill 結構] [override: radius 9999px→8px]
button.secondary  透明 / 1px ring color.border / text primary
                  [inspired by: xai] (ring 而非實線 border)
button.ghost      透明 / text.muted（低層級導覽）
card              bg surface.raised / 1px border / radius 8px / **無 drop shadow**
                  [inspired by: xai] (flat，border+底色分層)
input             radius 8px / 1px border / 右側可嵌 icon button
nav.header        sticky / 高 56px / **實心** surface.base（不透明）
                  [override: 來源半透明 glass → 實心，保對比] [IMPROVE-1]
badge/tag         radius full pill / 12px 500（小標記仍可用 pill）[inspired by: xai]
table             desktop 橫向；<1024px 轉 card list [original] [IMPROVE-3]
                  數值欄右對齊 + mono；gain/loss 上色
```

### RWD / Grid

```
breakpoints  sm640 / md768 / lg1024 / xl1280 / 2xl1536   [inspired by: xai] (與 00_spec 一致)
container    max 1280px（行銷頁）；儀表板 fluid 100%      [override]
section gap  24–48px                                     [override: 來源 96–128px → DROP 大留白]
grid         儀表板 12-col；卡片 auto-fit minmax(280px,1fr)
策略         mobile-first；table→card / sidebar→drawer @<1024px
```

## [UX PATTERN LAYER]

### 常用佈局 Pattern（保留來源的，加我方資料 pattern）
- **Sticky header + 導覽**（實心版）`[inspired by: xai P6]`
- **Stat band / KPI 列**：績效指標橫排，數值 mono，gain/loss 上色，**即時切換無滾動動畫** `[override: 來源 number-flow → DROP]`
- **Alternating feature**（僅行銷頁）`[inspired by: xai P2]`
- **Table ↔ Card 響應**：desktop 表格、mobile 卡片 `[original] [IMPROVE-3]`
- **Comprehensive footer**（行銷頁）`[inspired by: xai P7]`

### 狀態設計規則
- 每個資料區塊必須定義 4 態：`loading（skeleton）/ empty / error / populated` `[original]`（來源行銷頁未展示，我方補齊）
- 語意色：success/error/warning/info + gain/loss。

## [INTERACTION & ACCESSIBILITY]

- **對比度**：全文字 ≥ WCAG AA(4.5:1)；關鍵數值（價格/績效）≥ **AAA(7:1)**。`[IMPROVE-1]`（修正來源 muted 文字僅 ~4.0:1 的缺陷）
- **Dark/Light**：兩模式 token 完整，`prefers-color-scheme` + 手動切換。`[IMPROVE-2]`
- **鍵盤**：所有互動元件 keyboard-operable + `focus-visible` ring（對比達標）。`[IMPROVE-5]` `[inspired by: xai ring 系統]`
- **Motion**：完整 `prefers-reduced-motion`；即時數據更新**預設無動畫**。`[IMPROVE-4]` `[inspired by: xai reduced-motion]`

## [TECH & CONSTRAINT LAYER]

- Stack：React + Tailwind（token → CSS variables / tailwind theme）。
- 字型：開源可商用（Inter / Geist），自託管，**不使用 xAI 專有字型**。
- Token 機制：CSS vars 以 `--background`/`--card`/`--border`/`--accent` shadcn 慣例 + mode 切換。`[inspired by: xai]`

## [DATA PATTERN LAYER] `[original]`
- 數值：`tabular-nums` mono、千分位、正負號 + gain/loss 色。
- 長列表：虛擬滾動。
- 圖表：沿用語意色；gain/loss 對應漲跌；grid line 用 `color.border`。
- 即時更新：節流 + 無進場動畫，避免抖動。

## [EXAMPLE PATTERNS]

### Pattern 1：KPI Stat Row（儀表板頂部）
12-col → 4 張 KPI 卡（總報酬 / 夏普 / 最大回撤 / 勝率），數值 mono + gain/loss 色，1px border、無陰影。

### Pattern 2：Equity Curve + Trades（主視圖）
左 2/3 績效曲線（語意色），右 1/3 交易明細表（desktop）；<1024px 垂直堆疊、表格轉卡片。

---

## 【執行指令範本】（貼給 Lovable / Claude Code）

```
請依以下 design system 建立 React + Tailwind 專案（dark-first，含 light mode）：

{貼上本檔全文}

要求：
1. 先建 tailwind.config.js：把上方 color/typography/spacing/radius/breakpoint token
   寫入 theme.extend，並用 CSS variables 實作 dark/light 雙模式（class 策略）。
2. 建立基礎元件：Button(primary/secondary/ghost)、Card、Input、Badge、
   StatCard、DataTable（含 table↔card 響應）、AppHeader（實心 sticky）。
3. 所有文字對比度達 WCAG AA；價格/績效數值達 AAA，使用 Geist Mono + tabular-nums。
4. 數值正負以 color.gain / color.loss 上色；即時更新不加進場動畫。
5. 每個資料區塊實作 loading(skeleton)/empty/error/populated 四態。
6. 完整 prefers-reduced-motion 與 focus-visible 支援。
不要使用 xAI 的專有字型、商標、文案或圖片。
```
