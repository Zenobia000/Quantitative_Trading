# Prompt: 03 Analyze — L0 Foundations

> 用途：把 extracted 資料映射到 `00_foundations_spec.md` 的結構
> 執行者：Claude 主對話

---

## 給 Claude 的 Prompt

```
任務：讀取 clones/{slug}/extracted/ 與 raw/screenshots/，
輸出 clones/{slug}/analysis/L0_foundations.md。

格式必須對齊 design-system-specs/00_foundations_spec.md 的章節結構。

必填章節：

## 1. Grid & Layout System
- Container max-width
- Breakpoints（從 media-queries.json 抽）
- Grid 欄數（從截圖視覺判斷）
- Section 間距

## 2. Color System
- Brand：primary / secondary / accent（從 frequency top 3 + 截圖視覺判斷）
- Neutral：grey 階層（黑→白）
- Semantic：success / warning / error / info（若可辨識）
- 全部用 token 命名：color.brand.primary、color.neutral.900 等

## 3. Typography System
- Font Family（從 fonts.json）
- Type Scale：display / h1 / h2 / h3 / body-lg / body / caption
  每條包含 size / line-height / weight
- 全部 token 命名：font.size.h1 等

## 4. Spacing System
- Base unit（通常 4px 或 8px）
- Scale: xs / sm / md / lg / xl / 2xl
- 從 frequency 推斷，標註信心度

## 5. Border & Radius System
- Radius scale: none / sm / md / lg / full
- Border width: 1px / 2px

## 6. Elevation & Shadow System
- Shadow scale: sm / md / lg / xl
- 從 extracted/css-vars.json 的 shadows 抽

## 7. Iconography
- 風格（line / filled / duotone）
- 標準尺寸（從截圖判斷）

## 8. Motion & Animation
- Duration（若 css-vars 有 transition 相關）
- Easing
- 標註「TBD - 需動態擷取」若靜態抽不到

規則：
- 每個 token 必須給出實際 value
- 抽不到的欄位寫 TBD，不要瞎掰
- 結尾附「來源信心度」表（每章節 high/med/low + 為什麼）
```

---

## 驗收

- [ ] L0_foundations.md 八章節齊全
- [ ] Color / Typography / Spacing 至少有具體值
- [ ] 來源信心度表存在
