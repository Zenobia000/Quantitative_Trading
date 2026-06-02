# L0 Foundations — xai

> 對齊 `00_foundations_spec.md` 結構
> 來源：https://x.ai/ ｜ 擷取日期：2026-06-01
> 資料基礎：`raw/css-vars-raw.json`(101 vars) + `raw/computed-styles.json` + `extracted/css-vars.json` + 三斷點截圖

---

## 1. Grid & Layout System

| 屬性 | 值 | 信心度 |
|------|-----|--------|
| Container max-width | ~1280px（內容置中，左右大量留白） | med |
| Section 垂直間距 | 視覺判斷 96–128px（desktop） / 48–64px（mobile） | med |
| Grid 欄數 | Feature 區塊 desktop 2–3 欄；footer 5 欄；mobile 全 stack | high |
| Header 高度 | `--site-header-h: 4rem` (64px) | high |
| Header 背景 | `--site-header-bg: hsl(0 0% 100% / .85)` + `--site-header-blur: 12px`（半透明毛玻璃、sticky） | high |

### Breakpoints（來自 `media-queries.json`，Tailwind 預設）

| Token | 值 | 規則密度 | 說明 |
|-------|-----|----------|------|
| `breakpoint.sm` | 640px | 169 條 | 主要 mobile→tablet 切換 |
| `breakpoint.md` | 768px | 86 條 | 中間調整 |
| `breakpoint.lg` | 1024px | 181 條 | **最大行為變化點**（tablet→desktop） |
| `breakpoint.xl` | 1280px | 27 條 | desktop 標準 |
| `breakpoint.2xl` | 1536px | 5 條 | wide |
| （自訂） | 2000px | 1 條 | 超寬螢幕微調 |

> RWD 策略：Mobile-first，重斷點在 **640 與 1024**。

## 2. Color System

> 原始值為 HSL 三元組（搭配 `hsl()` 使用）。hex 為換算近似值。
> **核心模式：單一墨色 `ink/jet` + 透明度階層**（rgba(10,10,10,/.8/.5/.3)）構成幾乎所有文字層級，而非多個灰階 token。

### Brand / Accent
| Token | 來源變數 | HSL | ≈Hex | 用途 |
|-------|----------|-----|------|------|
| `color.brand.primary` | `--color-jet` | 0 0% 4% | `#0A0A0A` | 主行動（黑色 pill 按鈕）、主文字 |
| `color.brand.accent` | `--accent` / `--color-sunset` | 22 100% 51.6% | `#FF6A0A` | 橘色強調（漸層、極少量點綴） |
| `color.brand.secondary` | `--color-dusk` | 263 70% 50.4% | `#7C3AED` | 紫色（產品示意漸層） |
| （漸層亮紫） | `--color-twilight` | 255 92% 76% | `#A98BFB` | waveform / 漸層 |

### Neutral（暖白 + 冷灰雙軌）
| Token | 來源變數 | HSL | ≈Hex |
|-------|----------|-----|------|
| `color.neutral.0` | `--background` / `--color-white` | 0 0% 100% | `#FFFFFF` |
| `color.neutral.50` | `--card` / `--color-ivory` | 40 18% 97% | `#F9F8F4`（暖白，卡片底） |
| `color.neutral.100` | `--color-nimbus` | 228 21.7% 95.5% | `#EEF0F5`（冷白） |
| `color.neutral.200` | `--border` | 222 19% 86% | `#D5D9E2`（邊框） |
| `color.neutral.400` | `--color-pewter` | 213 12% 70% | `#ABB2BC` |
| `color.neutral.700` | `--color-evenfall` | 214 16% 28% | `#3C4953` |
| `color.neutral.800` | `--color-steel` | 216 4% 22% | `#363B3E` |
| `color.neutral.900` | `--color-ink` | 213 11% 16% | `#242931` |
| `color.neutral.950` | `--color-jet` | 0 0% 4% | `#0A0A0A` |
| `color.surface.code` | `--color-codeblock` | 0 0% 7% | `#121212`（深色程式碼/終端機） |

### Semantic
| Token | 來源變數 | HSL | ≈Hex |
|-------|----------|-----|------|
| `color.success` | `--success` | 142 71% 45% | `#22C55E` |
| `color.warning` | `--warning` | 45 93% 47% | `#E9A60C` |
| `color.error` | `--error` | 0 84% 60% | `#EF4444` |
| `color.info` | `--info` / `--color-breeze` | 214 48.9% 73.9% | `#9CB8DE` |

> Hover 階層：`--foreground-hover` / `--background-hover` / `--secondary-hover` 顯示互動狀態以「同色微調」處理。

## 3. Typography System

字型：`universalSansDisplay`（標題）、`universalSans`（內文/UI）、`GeistMono`（程式碼）。實際只用 **400 與 550** 兩種字重。

| Token | Family | Size | Weight | Line-height | Letter-spacing | 來源 |
|-------|--------|------|--------|-------------|----------------|------|
| `font.display` | universalSansDisplay | 60px | 500 | 60px (1.0) | −1.5px | h1 computed |
| `font.h1` | universalSansDisplay | 48px | 400 | 48px (1.0) | tight | h2#0 computed |
| `font.h2` | universalSansDisplay | 30px | 400 | 36px (1.2) | normal | h2#1 computed |
| `font.h3` | universalSansDisplay | 24px | 500 | ~32px | normal | frequency |
| `font.body-lg` | universalSans | 18px | 400 | 29.25px (1.625) | normal | p#0 computed |
| `font.body` | universalSans | 16px | 400 | ~24px | normal | a#0 / freq |
| `font.ui` | universalSans | 14px | 500 | 20px | normal | **最高頻 27×**（按鈕/nav/列表） |
| `font.caption` | universalSans | 12px | 500 | ~16px | normal | freq |

> 重點：**大標題行高壓到 1.0、字距收緊（−1.5px）** 是此系統的標誌性 display 風格；內文行高放寬到 ~1.6。UI 文字統一 14px/500。

## 4. Spacing System

Base unit：**4px**（Tailwind 標準），主力節奏 8 的倍數。

| Token | 值 | 信心度 |
|-------|-----|--------|
| `space.xs` | 4px | high |
| `space.sm` | 8px | high（按鈕垂直 padding） |
| `space.md` | 16px | high（按鈕水平 padding 8/16） |
| `space.lg` | 24px | med |
| `space.xl` | 32–48px | med |
| `space.2xl` | 96–128px（section 間距） | med（視覺） |

特殊：`--home-hero-pt-gap: 2.25rem` (36px)、`--scroll-size: 6px`。

## 5. Border & Radius System

| Token | 值 | 信心度 | 說明 |
|-------|-----|--------|------|
| `radius.none` | 0px | high | **最高頻 29×**（多數區塊、卡片用直角或極小圓角） |
| `radius.full` | 9999px | high | **15×**（所有按鈕、pill、tag） |
| `radius.md` | ~8–12px | med | 演示卡/輸入框（視覺判斷） |
| Border width | 1px | high | `--border` 色，1px ring（`box-shadow inset 0 0 0 1px`） |

> 標誌性：**radius 雙極化** — 不是直角就是全圓 pill，幾乎沒有中間值。次要按鈕用 1px ring 而非實線 border。

## 6. Elevation & Shadow System

| Token | 值 | 信心度 |
|-------|-----|--------|
| `shadow.ring` | `0 0 0 1px rgba(10,10,10,.15)` | high（次要按鈕的 1px ring） |
| `shadow.sm` | 極淺或無 | high（整體偏平面 flat design） |
| `shadow.md/lg` | TBD | low（首頁幾乎不用投影，靠 border + 底色分層） |

> 此系統**刻意避免 drop shadow**，用 1px 邊框 + 暖白底色（ivory）做層次。

## 7. Iconography

- 風格：**line（線性）**，約 1.5px 筆畫、圓角端點。
- 標準尺寸：16–20px（內聯於 14px UI 文字）。
- 來源：自訂 SVG，非可辨識的開源 icon 庫。`TBD - 需逐一比對 path`。

## 8. Motion & Animation

- `prefers-reduced-motion` 有完整支援（8 條 no-preference 規則 + reduce 降級）→ 動效是 progressive enhancement。
- `--angle: 0deg`、`--_number-flow-*` → 有「數字滾動（number-flow）」動畫（對應首頁 400M+/200K 大數字）。
- Duration / Easing 具體值：`TBD - 需動態擷取`（靜態 computed style 抽不到 transition timing）。

---

## 來源信心度

| 章節 | 信心度 | 為什麼 |
|------|--------|--------|
| Grid | med | container/section 為視覺估算；breakpoints 為實測 high |
| Color | high | 直接來自 101 個 CSS 變數 + computed frequency |
| Typography | high | computed style 直接讀到 size/weight/lh/字距 |
| Spacing | med | 按鈕值 high，section 值為視覺 |
| Radius | high | frequency 明確（0px 29× / 9999px 15×） |
| Shadow | high | 確認系統偏平面、用 ring |
| Icons | med | 視覺判斷，未比對 SVG path |
| Motion | low | 靜態擷取無 timing；僅知有 reduced-motion 與 number-flow |
