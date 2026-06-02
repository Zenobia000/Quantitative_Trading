# Prompt: 05 Specify

> 用途：把 analysis + differentiation 合成可執行的規格書
> 執行者：Claude 主對話

---

## 給 Claude 的 Prompt

```
任務：讀取 clones/{slug}/analysis/L0–L4 + clones/{slug}/differentiation.md，
產出 clones/{slug}/spec/inspired-design-system.md。

這份輸出必須能【直接交給 Lovable / Claude Code】產出程式碼。

結構必須對齊 global/BASE_DESIGN_SYSTEM.md（讀那份檔案先確認結構）。

關鍵規則：

1. 套用 differentiation.md 的 OVERRIDE
   - 凡是 differentiation 列出的覆蓋，spec 用你的值，不用來源值

2. 每個 token 標註來源
   - [inspired by: {slug}] — 從來源學到的
   - [original] — 你的差異化新增
   - [override] — 來源有但你改了

3. 套用 KEEP，移除 DROP
   - DROP 清單裡的元素不出現在 spec

4. IMPROVE 清單變成 spec 的【強化規範】
   - 例：對比度要求 WCAG AAA（不只 AA）
   - 例：所有互動元件必須支援 keyboard

5. 結尾附【執行指令範本】
   給 Lovable / Claude Code 用的開場 prompt：
   "請根據以下 design system 建立 React + Tailwind 專案：
   {貼上整份 spec}
   先建立 tailwind.config.js 與基礎元件。"

紅線：
- 不複製來源網站的文案、商標、圖片資產
- 所有顏色經過對比度驗算
- 所有 token 命名遵循 00_foundations_spec.md 的命名規範
```

---

## 驗收

- [ ] spec 結構對齊 BASE_DESIGN_SYSTEM.md
- [ ] 每個 token 有來源標註
- [ ] DROP 項目確實已移除
- [ ] IMPROVE 已轉為強化規範
- [ ] 執行指令範本存在
