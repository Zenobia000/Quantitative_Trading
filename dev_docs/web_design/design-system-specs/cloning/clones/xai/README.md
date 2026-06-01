# Clone Target: xai

> 每個複製專案的入口檔案。

---

## 基本資訊

| 欄位 | 值 |
|------|-----|
| Slug | `xai` |
| Target URL | `https://x.ai/`（公司/產品首頁） |
| 擷取日期 | 2026-06-01 |
| 操作者 | Claude Code（Playwright headless 擷取） |
| 法律檢查 | [x] robots.txt 確認（允許 `/`，僅擋 `/tools/`）/ [x] 僅公開頁面 |

> ⚠️ **內容信號**：x.ai robots.txt 宣告 `Content-Signal: ai-input=no, ai-train=no`（草案標準）。本流程僅萃取**結構化設計 token / 版面模式**並差異化重建，不複製文案/商標/logo/圖片/字型檔，符合 CLONE_WORKFLOW 信條。

## 為什麼複製這個

- 看上它什麼？**用極簡排版 + 單色透明度階層 + flat 分層做出高級克制感，且 token 系統乾淨可直接映射。**
- 想學的核心：**Token（色彩/字重克制）+ Component（pill/ring 按鈕）+ Pattern（typography hero、stat band）**
- 對應到我哪個產品？**backtest_platform 儀表板 + 行銷頁**（學其克制，反轉其留白為資料密度）

## 預設輸出範圍

- [x] L0 Foundations
- [x] L1 Components
- [x] L2 Patterns
- [x] L3 Templates
- [x] L4 Sitemap

## 進度追蹤

| 階段 | 狀態 | 完成日 | 備註 |
|------|------|--------|------|
| 1. Capture | ✅ | 2026-06-01 | Playwright headless，3 斷點 + DOM + 101 CSS vars + computed + fonts + mq |
| 2. Extract | ✅ | 2026-06-01 | dom-tree / css-vars(freq) / media-queries / assets-inventory |
| 3. Analyze | ✅ | 2026-06-01 | L0–L4 齊全 |
| 4. Differentiate | ✅ | 2026-06-01 | KEEP/DROP/OVERRIDE/IMPROVE，5 條 IMPROVE |
| 5. Specify | ✅ | 2026-06-01 | inspired-design-system.md，token 標來源 + 執行範本 |
| 6. Validate | ✅ | 2026-06-01 | 全項通過，對比度工具驗算（3 色值修正） |

## 你的品牌覆蓋（給 Differentiate 階段參考）

- 主色：`#0E7490`（teal-700，取代來源 #0A0A0A）
- 次色：`#F59E0B`（amber，僅警示）
- 字型：Inter / Geist（開源，取代專有 universalSans）
- 受眾：量化交易研究者 / 策略開發者
- 風格定位：dark-first、資料密集、沉穩可信

## 必避開的設計

- 60px 超大行銷 display 標題（儀表板無空間）
- 96–128px 大留白（要資訊密度）
- 漸層裝飾 / number-flow 滾動動畫（交易介面要降噪）
- 來源 muted 文字 .45 透明（對比未達 AA）

## 產出檔案

```
xai/
├── README.md                       ← 你在這裡
├── raw/                            ← Playwright 原始擷取
│   ├── screenshots/{mobile,tablet,desktop}.png
│   ├── dom.html (252KB) · css-vars-raw.json (101) · computed-styles.json
│   └── fonts.json · media-queries.json · capture-report.json
├── extracted/  dom-tree · css-vars(freq) · media-queries · assets-inventory
├── analysis/   L0_foundations · L1_components · L2_patterns · L3_templates · L4_sitemap
├── differentiation.md
├── spec/inspired-design-system.md  ← 最終交付（可貼給 Claude Code/Lovable）
└── validation.md
```
