# Assets Inventory — xai (x.ai homepage)

> 來源：https://x.ai/ ｜ 擷取日期：2026-06-01
> 僅清單化資產「類型與風格」，不下載任何圖片/字型檔，不記錄圖片 URL。

## 字型（來自 fonts.json）

| 家族 | 角色 | 字重 | 樣式 | 來源判斷 |
|------|------|------|------|----------|
| `universalSansDisplay` | Display / 標題 | 400, 550 | normal + italic | 自託管（custom，非 Google Fonts） |
| `universalSans` | 內文 / UI | 400, 550 | normal + italic | 自託管（custom） |
| `GeistMono` | 等寬 / 程式碼 | 100–900 (variable) | normal | Vercel Geist Mono（開源） |
| `*Fallback` | 系統 fallback | normal | normal | 本地 metric fallback |

- 字重極簡：實際只用 **400 / 550**（550 為自訂中粗，介於 medium/semibold）。
- Display 與 Text 為同源雙視光學尺寸（optical sizing）— 標題用 Display 版，內文用 Text 版。

## Icon 風格

- 風格：**line（線性）** 為主，1.5px 筆畫，圓角端點。
- 功能列表（feature list）前綴用線性 check / 小圖示。
- 標準尺寸：判斷約 16–20px（內聯於 14px 文字旁）。
- 來源：判斷為自訂 SVG sprite（非 FontAwesome/Lucide 之類可一眼辨識的庫）。`TBD - 需逐一比對 SVG path`。

## 圖片 / 視覺資產風格

| 類型 | 風格判斷 |
|------|----------|
| Hero | 無大圖，純排版（typography-led） |
| 產品演示卡 | 螢幕截圖嵌入圓角卡 + 深色終端機視窗 |
| 抽象視覺 | **漸層**：紫→洋紅聲波（waveform）、橘→紅→粉的程式碼卡背景 |
| News 縮圖 | 深色為底的抽象/3D 漸層縮圖（16:9 圓角） |
| 插畫 | 無傳統插畫；以 gradient + code/terminal 真實截圖為主 |

## 漸層調色（視覺判斷）

- Purple→Magenta：對應 token `twilight (255°) / dusk (263°)`。
- Orange→Red→Pink：對應 token `sunset/accent (22°)`。
- 用途：僅出現在「產品能力示意」區塊，作為點綴，不進入 UI chrome。

## 信心度

| 項目 | 信心度 | 說明 |
|------|--------|------|
| 字型家族/字重 | high | 直接來自 `document.fonts` |
| Icon 風格 | med | 視覺判斷，未逐一比對 SVG |
| 圖片風格 | high | 三斷點截圖佐證 |
| 漸層色相 | high | 對應到 raw CSS 命名變數 |
