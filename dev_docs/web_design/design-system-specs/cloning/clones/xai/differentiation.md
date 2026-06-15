# Differentiation — xai

> 來源：https://x.ai/ ｜ 我方產品：**Quantitative_Trading / backtest_platform 儀表板與行銷頁**
> 信條：萃取設計決策，差異化重建。不抄文案/商標/logo。

---

## 來源網站定位
- 受眾：開發者 + 企業 + 一般大眾（廣）
- 風格：極簡、排版主導、單色 + 克制漸層、高留白、權威感
- 強項：用字型力度與留白建立高級感；零插畫降低維護；token 系統乾淨（HSL + 語意命名）

## 我方產品定位
- 受眾：量化交易研究者 / 策略開發者 / 自託管使用者（窄而專業）
- 風格：**資料密集（data-dense）**、儀表板優先、需在小空間呈現大量數值與圖表
- 差異點：我們是**工具型產品儀表板**，不是行銷官網；資訊密度遠高於 x.ai；需 dark mode 為一等公民（盯盤久、降低眼睛疲勞）

---

## 值得保留（KEEP）

| 設計決策 | 為什麼好 | 如何納入 |
|----------|----------|----------|
| 單一墨色 + 透明度階層 | 比維護 5 階灰更簡單、層級一致 | 採 `ink + alpha` 文字系統（dark mode 改為 `paper + alpha`） |
| Pill 主按鈕 + 1px ring 次按鈕 | 視覺輕、層級清楚、無投影負擔 | 主行動用實心、次要用 ring；但**圓角收斂**（見 OVERRIDE） |
| 字重只用 2 級（400/550） | 降低字型載入、視覺克制 | 我方用 2–3 級即可 |
| Flat（無 drop shadow，用 border+底色分層） | 資料密集介面投影易雜亂 | 儀表板卡片一律 1px border + 底色，不用陰影 |
| 語意色 token（success/error/warning/info） | 直接對應交易盈虧/警示 | 保留，並擴充 `gain/loss` 對齊金融語境 |
| Tailwind 斷點 + mobile-first | 與本專案 00_spec 一致 | 直接沿用 640/768/1024/1280/1536 |
| Sticky glass header | 導覽常駐、節省空間 | 儀表板頂列沿用（但不透明，見 IMPROVE 對比度） |
| GeistMono 等寬呈現程式碼/數字 | 數字對齊、財務數據可讀 | **數值欄位（價格/績效）一律 tabular mono** |

## 不適合（DROP）

| 元素 | 為什麼不適合 |
|------|--------------|
| 60px 超大 display + 字距 −1.5px | 行銷英雄區用；儀表板沒有空間，會擠壓資料 |
| 大量留白（96–128px section gap） | 工具型介面要資訊密度，留白要砍到 24–48px |
| 漸層裝飾（waveform / 橘紅 code 卡） | 行銷視覺；交易介面要降噪、避免分心 |
| number-flow 滾動動畫 | 即時數據頻繁更新時，滾動動畫造成抖動/分心 → 數值用即時切換 |
| 純黑 #0A0A0A 大面積 | dark mode 大面積純黑對比過硬，改用近黑藍灰 |

## 品牌覆蓋（OVERRIDE）

| 來源 Token | 來源值 | 我方 Token | 我方值 | 理由 |
|------------|--------|------------|--------|------|
| `color.brand.primary` | `#0A0A0A`（jet） | `color.brand.primary` | `#0E7490`（teal-700） | 金融工具用沉穩 teal 建立信任，與「橘色 AI」區隔 |
| `color.brand.accent` | `#FF6A0A`（橘） | `color.brand.accent` | `#F59E0B`（amber，僅警示用） | 橘留給警示，不當品牌色 |
| `font.family.heading` | universalSansDisplay（自託管） | `font.family.heading` | `Inter`（或 `Geist Sans`，開源可商用） | 避免使用 xAI 自託管專有字型 |
| `font.family.mono` | GeistMono | `font.family.mono` | `Geist Mono`（開源） | 同源開源版，數值 tabular |
| `color.surface.base`（light） | `#F9F8F4` 暖白 | `color.surface.base` | dark: `#0B1220` / light: `#F8FAFC` | dark-first，近黑藍灰非純黑 |
| `radius.full`(按鈕) | 9999px | `radius.button` | `8px` | pill 在密集表格旁太搶眼；收斂為 8px |
| `color.gain` | （無） | `color.gain` | `#16A34A` | 金融專屬：上漲/獲利 |
| `color.loss` | （無） | `color.loss` | `#DC2626` | 金融專屬：下跌/虧損 |

## 改進機會（IMPROVE）

1. **Accessibility（對比度）**：x.ai 的 muted 文字用 `rgba(10,10,10,.45)` 在白底約 4.0:1，**未達 WCAG AA（4.5:1）**。我方強制：所有文字 ≥ AA，關鍵數值（價格/績效）≥ **AAA(7:1)**。半透明 header 改為實心或加深底色確保文字對比。
2. **Dark mode 一等公民**：x.ai 行銷頁僅 light。我方 **dark-first**，雙模式皆完整定義 token（`--background` 等用 mode 切換），盯盤場景降低眩光。
3. **Data density / 響應**：新增 x.ai 沒有的 **table → card 轉換 pattern**、**虛擬滾動長列表**、**即時數值無動畫切換**（取代 number-flow），對齊 `20_dashboard_specification.md` 的資料呈現需求。
4. **Motion 降噪**：完整 `prefers-reduced-motion` 支援（沿用 x.ai 的好習慣），且即時數據更新**預設無動畫**，動效僅用於導覽轉場。
5. **鍵盤可達**：所有互動元件（按鈕/輸入/表格列）必須 keyboard-operable + focus-visible ring（沿用 x.ai 的 ring 系統並確保對比）。

## 結論

> 學 x.ai 的**克制**（單色+透明度、2 級字重、flat 分層、pill/ring 按鈕、乾淨 token 系統），但徹底**反轉它的留白與裝飾**——把行銷站的「呼吸感」換成工具站的「資訊密度」，把 light-only 換成 dark-first，把橘色 AI 品牌換成 teal 金融信任色，並修掉它在 muted 文字上的對比度缺陷。
