# Differentiation — grok

> 來源：https://x.ai/grok ｜ 我方產品：backtest_platform 功能介紹頁 / 上手引導頁
> Token 層 OVERRIDE 與 xai 共用，見 [`../xai/differentiation.md`](../xai/differentiation.md)。本檔聚焦**產品頁模板**的差異化。

---

## 來源定位
- 受眾：AI 產品潛在使用者（廣）
- 風格：能力分區堆疊 + 密集 feature grid + 三路徑上手，促轉換
- 強項：用統一的能力區塊節奏 + 三路徑降低啟動門檻

## 我方產品定位
- 受眾：量化策略開發者（評估「這個回測平台能做什麼」）
- 差異點：能力 = 回測引擎 / 數據接入 / 風險分析 / 視覺化儀表板；上手 = 自託管 / Docker / CLI

## ✅ KEEP
| 設計決策 | 如何納入 |
|----------|----------|
| Capability Stack（能力分區統一結構） | 我方功能頁用同一節奏列 4 大能力 |
| Three-path Onboarding | 改為「自託管 / Docker / 試用 Demo」3 路徑 |
| Feature Grid 密集長尾 | 列出指標/資料源/匯出格式等長尾能力 |
| Closing CTA Band（深色反差） | 收尾導向「閱讀文件 / 開始回測」 |

## ⚠️ DROP
| 元素 | 為什麼 |
|------|--------|
| 「Try Grok / SuperGrok」訂閱式 CTA | 我方為自託管工具，無訂閱層級；改「Get Started / Docs」 |
| 大量留白的能力區塊 | 工具受眾要更快看到實質；收緊間距 |

## 🎨 OVERRIDE
- 共用 xai 的色彩/字型/radius OVERRIDE（teal 主色、Inter/Geist、8px radius、dark-first）。
- 雙色 hero 標題：保留結構，但 muted 次行改用達標的 `text.secondary(.65)` 而非來源 .45。

## 💡 IMPROVE
1. **能力區塊可達性**：每個 capability section 給語意 `<section aria-labelledby>`，check 列表用真 `<ul>`。
2. **三路徑卡鍵盤可達**：整卡可 focus + Enter 觸發主 CTA。
3. **對比修正**：hero 次行、feature grid 說明文字一律 ≥ AA（來源 muted 偏淺）。

## 結論
> 借 Grok 產品頁的**資訊組織骨架**（能力分區 + 密集網格 + 三路徑上手 + 深色收尾），套上 xai clone 已定義的 teal/dark-first token，產出我方「回測平台功能頁」模板。
