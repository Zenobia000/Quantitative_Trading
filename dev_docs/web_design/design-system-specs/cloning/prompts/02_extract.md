# Prompt: 02 Extract

> 用途：把 raw 素材轉成 AI 易讀的結構化中繼資料
> 執行者：Claude 主對話

---

## 給 Claude 的 Prompt

```
任務：讀取 design-system-specs/cloning/clones/{slug}/raw/ 下所有檔案，
產出結構化中繼資料到 clones/{slug}/extracted/。

這個階段【只做結構化，不做設計判斷】。

產出 4 個檔案：

1. extracted/dom-tree.md
   讀 raw/dom.html，產出簡化 DOM 樹：
   - 只保留語意結構，移除文字內容（用 {...} 代替）
   - 每個節點標註：tag、class（前 2 個）、語意角色（header/nav/hero/section/card/cta/footer）
   - 巢狀層級用縮排表達
   - 最多 200 行

2. extracted/css-vars.json
   讀 raw/css-vars-raw.json + raw/computed-styles.json，產出：
   {
     "colors": [{ "value": "#2563EB", "frequency": 12, "usage": ["button.primary", "link"] }],
     "fonts": [{ "family": "Inter", "weights": [400, 500, 600, 700] }],
     "font-sizes": [{ "value": "16px", "frequency": 23, "usage": ["body"] }],
     "spacings": [{ "value": "24px", "frequency": 18 }],
     "radii": [{ "value": "8px", "frequency": 9 }],
     "shadows": [{ "value": "0 1px 3px rgba(0,0,0,.1)", "frequency": 4 }]
   }
   按 frequency 降序排列。

3. extracted/media-queries.json
   讀 raw/media-queries.json，整理成：
   [
     { "breakpoint": "768px", "direction": "min-width", "rule_count": 42 }
   ]

4. extracted/assets-inventory.md
   清單：
   - 字型（家族、來源 CDN/本地、字重）
   - Icon 風格判斷（line / filled / duotone）
   - 圖片風格判斷（illustration / photo / 3D / abstract）

紅線：
- 不抽取文字內容（避免文案複製）
- 不抽取圖片 URL
- 出現 "TBD" 表示無法判定，不要瞎猜
```

---

## 驗收

- [ ] `extracted/` 4 個檔案齊全
- [ ] css-vars.json 的 colors 至少 3 種
- [ ] dom-tree.md 不含目標網站文案
