# Prompt: 04 Differentiate

> 用途：差異化決策 — 從複製跨越到原創
> 執行者：Claude 主對話 + 人類最終判斷

---

## 給 Claude 的 Prompt

```
任務：讀取 clones/{slug}/analysis/L0–L4 五個檔案，
產出 clones/{slug}/differentiation.md。

這份檔案是【複製工作流的價值核心】。
沒有差異化，複製就是抄襲；有了差異化，複製是養分。

需要使用者提供（請先問）：
1. 你的品牌主色 hex
2. 你的目標受眾（vs 目標網站的受眾）
3. 你的產品定位差異（更專業/更親切/更技術/更精簡？）
4. 必須避開的設計（你不喜歡 / 不適合的）

產出格式：

# Differentiation — {slug}

## 來源網站定位
- 受眾：{}
- 風格：{}
- 強項：{}

## 你的產品定位
- 受眾：{}
- 風格：{}
- 差異點：{}

---

## ✅ 值得保留（KEEP）

| 設計決策 | 為什麼好 | 如何納入 |
|----------|----------|----------|
| 例：Hero 用左文右圖非對稱 | 視覺有節奏、文字易讀 | 採用相同骨架 |
| ... | ... | ... |

至少 3 條。

## ⚠️ 不適合（DROP）

| 元素 | 為什麼不適合 |
|------|--------------|
| 例：過於企業感的灰藍色 | 你的受眾偏年輕、需要更活潑 |
| ... | ... |

至少 2 條。

## 🎨 品牌覆蓋（OVERRIDE）

來源 Token → 你的 Token：

| 來源 | 來源值 | 你的 Token | 你的值 |
|------|--------|------------|--------|
| color.brand.primary | #2563EB | color.brand.primary | #7C3AED |
| font.family.heading | Inter | font.family.heading | {你的選擇} |

## 💡 改進機會（IMPROVE）

至少 3 條 — 你能比來源網站做得更好的地方：

1. **{Accessibility}**：來源網站對比度只有 4.2，你做到 7+
2. **{Performance}**：來源 LCP 3.5s，你目標 < 2s
3. **{Interaction}**：來源沒有 keyboard nav，你補上
4. **{Empty States}**：來源沒設計，你加上

## 結論

> 一段話總結：你從這個來源學到什麼，要做什麼不一樣的產品。
```

---

## 驗收

- [ ] KEEP / DROP / OVERRIDE / IMPROVE 四章節齊全
- [ ] IMPROVE 至少 3 條
- [ ] 結論段存在且具體
