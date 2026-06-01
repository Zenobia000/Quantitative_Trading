# Lovable 實戰組裝手冊 (The Playbook)

> Lovable 專屬的執行指南。通用建置策略見 `guides/vibe_coding_build_strategy.md`。
> 本文件聚焦於「把 Pipeline 產出的 Prompt 餵進 Lovable 時的注意事項」。

---

## 核心心法：玩具城理論

- **Global Layer (靈魂)**：玩具城的規則書（房子什麼顏色、門長怎樣、路多寬）
- **Page Layer (骨架)**：每一棟房子的設計圖（醫院、學校還是超商？幾層樓？）
- **Assembly Layer (心臟)**：拿著規則書 + 設計圖去指揮機器人（Lovable）

---

## 一、Lovable 組裝 SOP

### 前置準備（完成 Pipeline Step 1-5）

確認以下文件已備齊：
1. `global/XX_brand_system.md` — 你的品牌 Design System
2. `pages/XX_page.md` — 當前要做的頁面規格
3. （可選）`references/website_recipes.md` 中的 Lovable 提示詞起手式

> 不確定前置文件？查 `references/prereq_document_checklist.md` 確認 P0 打勾。

### Step 1：壓縮 Global Tokens

從 `global/XX_brand_system.md` 提取**當前頁面需要的** Tokens：

```
只放：色值表 + 字級表 + 間距值 + 圓角值 + 斷點
不放：設計原則解釋、品牌故事、元件完整 states 清單
```

> Token 節省技巧：Lovable 的 Context Window 有限，Global 區段壓縮到 30-50 行以內。

### Step 2：組裝 Master Prompt

使用 `assembly/PIPELINE_ORCHESTRATOR.md` 的結構：

```markdown
=== GLOBAL PROJECT GUIDELINE (DO NOT OVERRIDE) ===
[壓縮版 Global Tokens]

重點：
- 本區段定義整個專案的設計系統，為最高準則。
- 所有組件必須繼承此處定義的配色、圓角與間距。

=== CURRENT TASK: BUILD [PAGE_NAME] ===
本次任務：根據上方 Global Guideline，實作以下頁面。

[貼上 pages/XX_page.md 的規格內容]

=== EXCEPTION RULES ===
[如有例外，在此說明]

=== OUTPUT REQUIREMENTS ===
1. 確認結構：先列出本頁 Sections 與元件清單。
2. 設計說明：簡述如何落實一致性。
3. 生成程式碼：產出完整可運行的前端代碼。
```

### Step 3：餵入 Lovable + 驗收

1. 將 Master Prompt 整段貼入 Lovable
2. 檢查產出是否符合 Design System
3. 用 `guides/quality_checklist.md` 逐項驗收
4. 用追加 Prompt 微調細節

---

## 二、Lovable 特有注意事項

### 2.1 Context Window 管理

| 狀況 | 解法 |
|------|------|
| Global 太長，AI 遺漏後半段細節 | 壓縮至只放色值+字級+間距，不放解釋文字 |
| 頁面太複雜，一次做不完 | 拆成 2-3 個 section group 分次做 |
| 跨頁面風格漂移 | 每次都先貼 Global Tokens，不要省略 |

### 2.2 常見錯誤與解決

| 錯誤現象 | 原因分析 | 解決方法 |
|---------|---------|---------|
| 視覺風格漂移 | Page Prompt 寫了太多細節樣式 | 刪除 Page 中的樣式描述，強化 Global 指令 |
| AI 遺漏功能 | Assembly Prompt 太長 | 精簡 Global，只保留該頁面相關的 Tokens |
| 交互邏輯錯誤 | 缺乏狀態定義 | 在 Page Spec 中明確定義 Loading/Error/Empty |
| RWD 沒做 | 沒有指定斷點行為 | 在 Page Spec 的 RWD 行為差異表中明確描述 |
| 顏色亂用 | Tokens 太多 AI 混淆 | 只列當前頁面用到的 5-8 個色值 |

### 2.3 迭代修改技巧

追加 Prompt 的有效寫法：

```
修改 [Section Name]：
- 將 [元件A] 的間距從 16px 改為 24px
- 將 [元件B] 的狀態補上 Loading skeleton
- 保持其他部分不變
```

不要重新描述整個頁面，只針對需要修改的部分下指令。

---

## 三、版本控管與迭代

1. **版本號同步**：
   - Global 變更（如主色調調整）→ 更新版本號
   - Page 註記：`Using Global System v{X.X}`
2. **元件回饋環 (Feedback Loop)**：
   - Lovable 生成了優秀的客製化元件 → 將其 Pattern 寫回 `global/XX_brand_system.md`
   - 下一頁就能繼承這個元件風格

---

## 四、品質門哨 (Quality Gates)

在 Lovable 產出後，對照 `guides/quality_checklist.md` 快速檢查：

- [ ] 配色是否完全來自定義的 Tokens？
- [ ] 是否有完善的 Loading / Error / Empty 狀態？
- [ ] RWD 在所有定義的斷點是否行為正確？
- [ ] 字級/間距是否符合 Design System？
- [ ] 語氣是否符合 Brand & Tone？

---

最後更新：2025-03-02 | 維護：Prompt Architect Team
