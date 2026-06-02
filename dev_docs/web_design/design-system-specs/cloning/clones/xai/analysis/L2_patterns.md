# L2 Patterns — xai

> 對齊 `02_patterns_spec.md` 結構
> 來源：https://x.ai/ ｜ 擷取日期：2026-06-01
> Pattern = 多元件組合出的可重複互動/版面結構。

---

## Pattern 1：Typography-led Hero（排版主導英雄區）

**結構**：置中、無大圖、極大 display 標題（60px/500/lh 1.0/字距 −1.5px）+ 一行 muted 副標（18px/45% 透明）+ 一對 pill CTA（primary + secondary）。

```
[小標籤 pill]
 超大 Display 標題（兩行，字距收緊）
 muted 副標一行
 [primary pill] [secondary pill]
```

**為什麼有效**：以字型力度建立權威感，零插畫降低載入與維護成本。
**狀態**：靜態；CTA hover 微調透明度。

## Pattern 2：Alternating Feature Section（左右交替能力區）

**結構**：每個能力一個 section，左文字（icon + 標題 + 說明 + check 列表）／右視覺（截圖、終端機、漸層示意），下一段左右對調。mobile 全 stack（視覺在上或下）。

**用到的元件**：line icon、h2/h3、check list、demo-card。
**RWD**：desktop 2 欄（`grid-cols-2`），<1024px stack。

## Pattern 3：Stat Band（數據條）

**結構**：3 欄並排超大數字（400M+ / 200K / 1）+ caption。進場 number-flow 動畫。
**為什麼**：用數據量級建立可信度；極簡無裝飾。

## Pattern 4：Card Grid（News / 多卡）

**結構**：等寬卡片橫向排列（desktop 4 欄 → mobile 1–2 欄），每卡 = 深色漸層縮圖 + 標題 + 日期，全卡點擊。
**狀態**：hover 卡片微抬/邊框加深（flat，無大投影）。

## Pattern 5：Dual Gateway CTA（雙路徑收尾）

**結構**：「Choose how to get started」→ 兩張並排卡：自助（feature check 列表 + primary CTA）vs 找業務（contact）。
**為什麼**：分流自助開發者 vs 企業客戶。

## Pattern 6：Sticky Glass Header + Mega Menu

**結構**：sticky 半透明毛玻璃 header（blur 12px / 85% 白），hover 展開多欄 mega-menu。
**RWD**：<1024px 收合為 hamburger drawer。

## Pattern 7：Comprehensive Footer

**結構**：5 欄連結群 + 底部 logo/版權/社群。資訊密度高但用 14px muted 文字 + 大行距維持呼吸感。

## Pattern 8：Code / Terminal Showcase

**結構**：深色 codeblock（#121212）視窗，GeistMono 等寬字，語法高亮；可附 tab（Python/TypeScript/cURL）。
**為什麼**：對開發者受眾展示 API 真實樣貌。

---

## Feedback / Empty / Loading 狀態

- 行銷站未展示完整 feedback 系統；語意色（success/warning/error/info）已在 token 定義。
- Empty/Loading：`TBD - 行銷頁不適用，需從 app（grok.com）擷取，但其受 Cloudflare 保護無法擷取`。

## 覆蓋度

≥ 3 個 pattern 有具體描述 ✅（實際 8 個）。
