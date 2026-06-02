# L0 Foundations — grok（忠實還原，v2 重建）

> 對齊 `00_foundations_spec.md` 結構 ｜ 目標：`https://grok.com`（Grok app）
> **路徑 2 公開知識重建**：基調/版面為 high 信心；**精確 hex / 字型為 `TBD`**（CF 擋下無法擷取，approximation 標註）。

---

## 1. Grid & Layout System

| 屬性 | 值（重建） | 信心度 |
|------|-----------|--------|
| 整體佈局 | 左側可收合 **sidebar**（對話歷史）+ 主對話置中限寬欄 + 極簡頂列 | high |
| 招牌元素 | **置中、大圓角的 prompt 輸入框**（空狀態主角，周圍大量留白） | high |
| 容器 | 對話欄限寬置中（~`max-w-3xl`）；輸入框寬度受限 | med |
| RWD | 桌機 sidebar 展開；手機 sidebar 收為 drawer、對話全寬 | high |
| 留白 | 大（極簡、聚焦對話） | high |

## 2. Color System（**單色 monochrome / dark-first**）

> 核心：**近黑底 + 白/灰文字，幾乎無彩色品牌色**（不像 ChatGPT 綠）。hex 為**重建近似值，TBD 待擷取確認**。

### Dark（預設）
| Token | ≈值（TBD 近似） | 用途 | 信心度 |
|-------|----------------|------|--------|
| `color.bg.base` | `#0F0F0F`（近黑，非純黑） | 頁面底 | high（暗）/ 值 TBD |
| `color.bg.surface` | `#1A1A1A` | sidebar / 卡片 / 訊息區 | med |
| `color.bg.input` | `#1E1E1E` | 輸入框底 | med |
| `color.border` | `rgba(255,255,255,.08–.12)` ≈ `#2A2A2A` | 細淡分隔 | med |
| `color.text.primary` | `#F5F5F5` 近白 | 主文字 | high |
| `color.text.secondary` | `rgba(255,255,255,.70)` | 次文字 | med |
| `color.text.muted` | `rgba(255,255,255,.55–.60)` | 註腳/placeholder | med |
| `color.brand` | **單色** — 主按鈕常見**白底深字 pill**（`#F5F5F5` bg / `#0F0F0F` text） | high（單色）/ 值 TBD |
| `color.accent` | **無彩色強調**；focus / 互動以白/灰明度區分 | high |

### Light（次要模式）
- off-white 底（≈`#FAFAFA`）+ 近黑文字（≈`#0F0F0F`）。`TBD`。

> **關鍵**：Grok 不靠彩色建立識別，靠**單色 + 留白 + 大圓角**。彩色僅在內容（如生成圖、連結）出現。

## 3. Typography System

| Token | 重建 | 信心度 |
|-------|------|--------|
| 字型家族 | 乾淨無襯線 grotesk（**家族 TBD**，未擷取無法確認；視覺近似 Inter/系統 grotesk） | med |
| 階層 | 對話內文舒適閱讀級（~15–16px）；標題克制；UI 文字小（~13–14px） | med |
| 字重 | 少（regular + medium 為主） | med |

## 4. Spacing System

- 大量留白、舒適行距；base unit 推測 4px（Tailwind 慣例）。`TBD` 精確 scale。

## 5. Border & Radius System（**大圓角是 Grok 招牌**）

| Token | 重建 | 信心度 |
|-------|------|--------|
| `radius.input` | 大圓角 / pill（輸入框） | high |
| `radius.card` | 大（~16px，訊息/卡片） | med |
| `radius.button` | pill 或 ~12px | med |
| border | 1px 細淡、低對比 | med-high |
| 投影 | 極少；靠 surface 明度 + 細邊框分層 | med |

## 6. Elevation & Shadow

- 極簡，幾乎無 drop shadow；以底色明度階（base→surface→input）分層。`med`

## 7. Iconography

- 線性、單色、細筆畫；尺寸克制。`med`

## 8. Motion & Animation

- 訊息串流（streaming）、輕微淡入；克制。`TBD` 精確 timing。

---

## 來源信心度

| 章節 | 信心度 | 說明 |
|------|--------|------|
| Layout | high | sidebar + 置中輸入框為 Grok 公認特徵 |
| Color 基調 | high（單色 dark）/ 值 TBD | 暗 + 單色確定；精確 hex 需擷取 |
| Typography | med | 家族 TBD |
| Radius | high（大圓角）/ 值 TBD | 大圓角為招牌 |
| 其餘 | med–TBD | 重建，待手動擷取補正 |

> **此檔為路徑 2 重建**。若日後取得 grok.com DevTools dump，依 `02_extract` → 本檔升級為實測值、移除 TBD。
