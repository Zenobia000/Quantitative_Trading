# Capture Checklist

每次擷取前後執行。

## 擷取前

- [ ] 確認 robots.txt 允許目標路徑
- [ ] 目標僅為公開頁面（無需登入）
- [ ] 已建立 `clones/{slug}/raw/` 目錄
- [ ] 已填寫 `clones/{slug}/README.md` 的基本資訊

## 擷取中

- [ ] 三斷點截圖（375 / 768 / 1440）
- [ ] dom.html 已存
- [ ] css-vars-raw.json 已存
- [ ] computed-styles.json 已存
- [ ] fonts.json 已存
- [ ] media-queries.json 已存

## 擷取後

- [ ] 檢查無 PII 殘留
- [ ] 檢查無下載到圖片素材檔案
- [ ] 檔案大小合理（dom.html > 10KB）
- [ ] README 進度表打勾「Capture」
