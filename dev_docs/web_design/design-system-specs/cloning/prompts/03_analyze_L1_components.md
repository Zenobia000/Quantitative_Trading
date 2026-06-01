# Prompt: 03 Analyze — L1 Components

> 用途：抽取元件庫對齊 `01_components_spec.md`
> 執行者：Claude 主對話

---

## 給 Claude 的 Prompt

```
任務：讀取 clones/{slug}/extracted/dom-tree.md 與 raw/screenshots/、computed-styles.json，
輸出 clones/{slug}/analysis/L1_components.md。

格式對齊 01_components_spec.md。

抽取流程：
1. 從 dom-tree 找出重複出現的語意元件
2. 對每個元件，從 computed-styles.json 找對應的 class
3. 從截圖視覺確認狀態與變體

每個元件用統一格式：

## Button

### 變體（Variants）
| Variant | 背景 | 文字 | Border | 用途 |
|---------|------|------|--------|------|
| primary | color.brand.primary | white | none | 主要 CTA |
| secondary | transparent | brand.primary | 1px brand | 次要 |
| ghost | ... | ... | ... | ... |

### 尺寸（Sizes）
| Size | Padding | Font Size | Height |
|------|---------|-----------|--------|
| sm | 8 16 | 14 | 32 |
| md | 12 20 | 16 | 40 |
| lg | 16 24 | 18 | 48 |

### 狀態（States）
- default / hover / active / disabled / loading
- 列出每個狀態的視覺差異

### Radius / Shadow
- 對應的 token

---

必抽元件清單（抽不到就標 N/A）：
- Button
- Input / TextArea / Select
- Card
- Badge / Tag / Chip
- Avatar
- Modal / Dialog
- Tooltip
- Tabs
- Dropdown / Menu
- Toast / Alert
- Pagination
- Breadcrumb

紅線：
- 不複製目標品牌的圖示資產
- 元件數量寧缺勿濫（抽 5 個準確 > 12 個瞎猜）
- 結尾給「元件信心度」表
```

---

## 驗收

- [ ] 至少 5 個元件有完整變體/尺寸/狀態
- [ ] 每個元件引用 L0_foundations 的 token
- [ ] 元件信心度表存在
