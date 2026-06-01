# Validation — xai

> 執行 `checklists/validation_checklist.md`。擷取 2026-06-01。

## 法律與倫理

- [x] 無複製商標 / logo / 品牌名（僅抽結構化 token，未存 logo）
- [x] 無複製文案內容（dom-tree 文字以 {…} 代替；extract 階段 strip 文案）
- [x] 無複製圖片 / 插畫資產（capture 不下載圖片；僅記錄風格類型）
- [x] 來源網站已標註於 spec 開頭（「inspired by x.ai」+ 擷取日）

## 設計完整性

- [x] L0 Foundations 八章節齊全
- [x] L1 至少 5 個元件含完整變體（Button/Link/Card/Nav/Badge/Stat/Footer = 8）
- [x] L2 至少 3 個 pattern 有具體描述（8 個）
- [x] L3 至少 1 個 template 含 Mermaid（Landing template flowchart）
- [x] L4 sitemap 對應原型（Frontier-AI Company Site，含 Mermaid 路由圖）

## 差異化驗證

- [x] differentiation.md 四章節齊全（KEEP/DROP/OVERRIDE/IMPROVE）
- [x] IMPROVE 至少 3 條（5 條）
- [x] OVERRIDE 至少包含主色與字型（primary #0A0A0A→#0E7490；font universalSansDisplay→Inter）
- [x] DROP 項目已從 spec 移除（60px display、大留白、漸層裝飾、number-flow 均未進 spec）

## 技術品質 — 對比度驗算（WCAG，工具計算）

| 前景 | 背景 | 比值 | 結果 |
|------|------|------|------|
| text.primary `#E6EDF5` | base `#0B1220` | 15.87:1 | AAA ✓ |
| text.primary `#E6EDF5` | raised `#131C2B` | 14.48:1 | AAA ✓ |
| text.secondary (.65) | base | 7.10:1 | AAA ✓ |
| text.muted (.55) | base | 5.38:1 | AA ✓（來源 .45 僅 4.03 → 已修正） |
| btn primary `#fff` | teal `#0E7490` | 5.36:1 | AA ✓ |
| text.primary.light `#0B1220` | base.light `#F8FAFC` | 17.89:1 | AAA ✓ |
| gain `#22C55E` | raised | 7.50:1 | AAA ✓ |
| loss `#F87171` | raised | 6.18:1 | AA ✓ |
| loss.aaa `#FCA5A5` | raised | 9.01:1 | AAA ✓ |
| info `#60A5FA` | base | 7.36:1 | AAA ✓ |

- [x] 顏色對比度 WCAG AA 全通過（關鍵數值達 AAA；loss 紅在深底 AA 達標、AAA 用 `color.loss.aaa`）
- [x] Token 命名對齊 `00_foundations_spec.md`（`color.brand.primary`、`breakpoint.sm`、`font.h1`…）
- [x] Token 完整度 ≥ 80%（L0 八章節對齊 00_spec 之 8 大類）
- [x] Token 引用層級正確（L1 引 L0 色/字、L2 引 L1 元件、spec 引 differentiation OVERRIDE）

## Pipeline 接入

- [x] spec 結構對齊 `global/BASE_DESIGN_SYSTEM.md`（PRODUCT/BRAND/VISUAL/UX/INTERACTION/TECH/DATA/EXAMPLE 分層）
- [x] 與既有 `00_foundations_spec.md` 衝突已解決（沿用其 breakpoint/container/命名）
- [x] 執行指令範本可貼給 Lovable / Claude Code（spec 結尾）
- [x] 已對應 `references/website_recipes.md` 新原型建議（L4：Frontier-AI Company Site）

## 限制與誠實聲明

- ⚠️ grok.com（Grok app 本體）受 Cloudflare managed challenge 保護，headless 無法擷取；本 clone 以 **x.ai 行銷頁**為素材，app 內部介面（chat/empty/loading 等真實狀態）為 `TBD`。
- ⚠️ Container max-width、section 間距為截圖視覺估算（med 信心度）。
- ⚠️ Motion timing 靜態擷取不到（low）。
- ⚠️ x.ai robots.txt 宣告 `Content-Signal: ai-input=no`（草案標準）。本流程僅做**結構化設計啟發 + 差異化重建**，不複製內容/資產，符合 playbook 信條；惟此信號已記錄於 README，後續若擴大使用請再評估。

## 結論

**全項通過**（含一條工具驗算修正：muted/gain/loss 色值已調整至達標）。spec 可被 Pipeline Orchestrator 引用。
