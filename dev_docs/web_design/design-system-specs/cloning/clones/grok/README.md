# Clone Target: grok

> Grok 產品頁複製。**與 `../xai/` 共用同一套 xAI 設計系統**，本 clone 聚焦產品頁特有的 Template / Sitemap 差異，foundations/components/patterns 指向 xai。

---

## 基本資訊

| 欄位 | 值 |
|------|-----|
| Slug | `grok` |
| Target URL | `https://x.ai/grok`（Grok 產品行銷頁） |
| 擷取日期 | 2026-06-01 |
| 操作者 | Claude Code（Playwright headless） |
| 法律檢查 | [x] robots.txt（允許 `/grok`）/ [x] 僅公開頁面 |

> ⚠️ **原定目標 `grok.com`（Grok app 本體）受 Cloudflare managed challenge 保護，headless 無法通過**（三斷點皆卡 "Just a moment..."，見 `raw/`-曾擷取後改用 x.ai/grok）。故以 xAI 官方 Grok 產品頁作為「Grok 產品視覺語言」代理素材。app 內真實對話介面（訊息泡泡、串流、empty/loading）為 `TBD`。
> ⚠️ 內容信號同 xai（`ai-input=no`）；僅結構化啟發、不複製資產。

## 為什麼複製這個

- 看上它什麼？**產品頁如何用「能力分區（Chat/Multi-agent/Search/Imagine）+ feature grid + 三路徑 Get started」組織一個 AI 產品的賣點。**
- 想學的核心：**Template（產品能力頁骨架）+ Sitemap（產品 IA 分區）**
- 對應到我哪個產品？**backtest_platform 的「功能介紹頁 / 上手引導頁」**

## 預設輸出範圍

- [ ] L0 Foundations → 見 [`../xai/analysis/L0_foundations.md`](../xai/analysis/L0_foundations.md)（共用）
- [ ] L1 Components → 見 [`../xai/analysis/L1_components.md`](../xai/analysis/L1_components.md)（共用）
- [ ] L2 Patterns → 見 [`../xai/analysis/L2_patterns.md`](../xai/analysis/L2_patterns.md)（共用）
- [x] L3 Templates（產品頁，本 clone 特有）
- [x] L4 Sitemap（Grok 產品 IA，本 clone 特有）

## 進度追蹤

| 階段 | 狀態 | 完成日 | 備註 |
|------|------|--------|------|
| 1. Capture | ✅ | 2026-06-01 | x.ai/grok 3 斷點 + DOM(171KB) + 97 CSS vars（grok.com 本體 CF 擋下） |
| 2. Extract | ✅ | 2026-06-01 | dom-tree / css-vars / media-queries / assets-inventory |
| 3. Analyze | ✅ | 2026-06-01 | L0–L2 共用 xai；L3/L4 本 clone 產出 |
| 4. Differentiate | ✅ | 2026-06-01 | 產品頁特有 delta（共用 xai 的 token OVERRIDE） |
| 5. Specify | ✅ | 2026-06-01 | 共用 [`../xai/spec/inspired-design-system.md`](../xai/spec/inspired-design-system.md) + 本檔 template 延伸 |
| 6. Validate | ✅ | 2026-06-01 | 見 validation.md |

## 必避開的設計
- app 內部介面臆測（未擷取到，標 TBD，不瞎掰）
