# Prompt: 03 Analyze — L2 Patterns

> 用途：抽取互動模式對齊 `02_patterns_spec.md`
> 執行者：Claude 主對話

---

## 給 Claude 的 Prompt

```
任務：讀取 clones/{slug}/extracted/ 與 raw/screenshots/，
輸出 clones/{slug}/analysis/L2_patterns.md，對齊 02_patterns_spec.md。

Patterns ≠ Components。
Pattern 是【元件如何組合解決使用情境】，例如：
- Form Pattern：label 在哪、error 顯示位置、validation 時機
- Nav Pattern：主選單結構、mobile 收合方式、breadcrumb 用法
- Empty State Pattern：圖 + 標題 + 描述 + CTA 的版面

必填章節：

## 1. Form Patterns
- Label 位置（top / left / float）
- 必填標示方式
- Error 顯示時機（onBlur / onSubmit）
- Error 訊息位置（inline / toast / summary）
- 提交按鈕位置與狀態

## 2. Navigation Patterns
- 主導航結構（top bar / side nav / hybrid）
- Mobile 收合（hamburger / bottom tab / drawer）
- Breadcrumb 用法
- Active state 標示方式

## 3. Table / List Patterns
- 排序方式
- 篩選 UI 位置
- 分頁 vs 無限滾動
- Row action（hover 浮現 / 永遠顯示）
- Empty / Loading / Error 狀態

## 4. Feedback Patterns
- Toast 出現位置與停留時間
- Modal vs Drawer vs Inline 的選用邏輯
- Loading 指示（spinner / skeleton / progress）
- Confirmation flow（destructive action 二次確認）

## 5. Onboarding / Empty State
- 首次使用引導
- 空狀態的視覺與 CTA

紅線：
- 抽不到的 pattern 寫 "未在公開頁面觀察到"
- 每個 pattern 標註觀察來源（哪張截圖 / 哪段 DOM）
```

---

## 驗收

- [ ] 五個 pattern 章節齊全（可標未觀察）
- [ ] 至少 3 個 pattern 有具體觀察來源
