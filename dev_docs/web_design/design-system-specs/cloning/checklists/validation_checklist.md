# Validation Checklist

最終驗收。全項通過才能把 spec 接入 Prompt Architect Pipeline。

## 法律與倫理

- [ ] 無複製商標 / logo / 品牌名
- [ ] 無複製文案內容
- [ ] 無複製圖片 / 插畫資產
- [ ] 來源網站已標註於 spec 開頭

## 設計完整性

- [ ] L0 Foundations 八章節齊全
- [ ] L1 至少 5 個元件含完整變體
- [ ] L2 至少 3 個 pattern 有具體描述
- [ ] L3 至少 1 個 template 含 Mermaid
- [ ] L4 sitemap 對應到 `WEBSITE_MODULE_MATRIX.md` 某原型

## 差異化驗證

- [ ] differentiation.md 四章節齊全
- [ ] IMPROVE 至少 3 條
- [ ] OVERRIDE 至少包含主色與字型
- [ ] DROP 項目已從 spec 移除

## 技術品質

- [ ] 顏色對比度 WCAG AA 通過（自動工具驗證）
- [ ] Token 命名對齊 `00_foundations_spec.md` 命名規範
- [ ] Token 完整度 ≥ 80%（與 00 spec 條目數比）
- [ ] 所有 token 引用層級正確（L1 引 L0、L2 引 L1...）

## Pipeline 接入

- [ ] spec 結構對齊 `global/BASE_DESIGN_SYSTEM.md`
- [ ] 與既有 `00_foundations_spec.md` 衝突已解決
- [ ] 執行指令範本可貼給 Lovable / Claude Code
- [ ] 已建立連結到 `references/website_recipes.md`（若新增原型）

---

未通過 → 回到對應階段修正。
全通過 → 在 README 進度表打勾「Validate」，spec 可被 Orchestrator 引用。
