# L1 Components — xai

> 對齊 `01_components_spec.md` 結構
> 來源：https://x.ai/ ｜ 擷取日期：2026-06-01
> 變體/狀態同屬一個元件，不拆成多個元件。

---

## 1. Button

最具辨識度的元件：**全圓 pill（radius 9999px）+ 14px/500 字 + universalSans**。

| 變體 | 背景 | 文字 | 邊框 | padding | 用途 |
|------|------|------|------|---------|------|
| `primary` | `#0A0A0A`（jet） | `#FFFFFF` | 無 | 8px 16px | 主行動（Try for free / Get API Access） |
| `secondary` | 透明 | `#0A0A0A` | `0 0 0 1px rgba(10,10,10,.15)` ring | 8px 16px | 次行動（View Documentation / Read Docs） |
| `ghost / nav` | 透明 | `rgba(10,10,10,.5)` | 無 | 0 | nav 連結、低層級 |
| `icon-affix` | — | — | — | `0 12px 0 8px`，radius `0 9999px 9999px 0` | 帶箭頭 → 的複合按鈕右半 |

狀態：
- `hover`：primary 微亮（`--foreground-hover`）；secondary ring 加深。
- `focus-visible`：`--tw-ring` 系統（藍色 ring `#3b82f680`）。
- `disabled`：`TBD`（首頁未出現）。

## 2. Link

| 變體 | 色 | size/weight |
|------|-----|-------------|
| `default` | `#0A0A0A` | 16px / 400 |
| `muted` | `rgba(10,10,10,.5)` | 14px / 500（footer、nav 次層） |

- 無底線，hover 改透明度。

## 3. Card

| 屬性 | 值 |
|------|-----|
| 背景 | `#F9F8F4`（ivory）或白 |
| 邊框 | 1px `#D5D9E2`（border token） |
| radius | ~8–12px（med，視覺） |
| 投影 | 無（flat，靠 border + 底色分層） |
| 內距 | 24–32px |

子類：
- `demo-card`：內嵌產品截圖/終端機視窗。
- `news-card`：深色漸層縮圖（16:9）+ 標題 + 日期，全卡可點。
- `gateway-card`：「Build on your own / Get extra support」雙欄，內含 feature check 列表 + CTA。

## 4. Input（搜尋/對話框）

| 屬性 | 值 | 信心度 |
|------|-----|--------|
| radius | full pill 或 large radius | med |
| 邊框 | 1px border token | med |
| 背景 | 白 / ivory | med |
| 右側 | 嵌入 icon 按鈕（送出/麥克風） | high（grok chat mock 可見） |

> 完整 computed 值 `TBD`（首頁 input 為裝飾性 mock，非真實表單）。

## 5. Navigation Bar

| 屬性 | 值 |
|------|-----|
| 高度 | 64px (`--site-header-h`) |
| 背景 | `hsl(0 0% 100% / .85)` + `blur 12px`（毛玻璃 sticky） |
| 結構 | 左 logo｜中 menu（Products/Solutions/Developer/Company/Pricing/News，含下拉）｜右 Contact Sales + primary pill |
| 下拉 | mega-menu（Products 等展開多欄） |

## 6. Badge / Tag / Pill label

- 小型 pill（radius full）+ 12–14px 文字，灰底或描邊；用於「Grok Build Beta」「New」等標記。

## 7. Stat / Number display

- 超大數字（400M+ / 200K / 1），universalSansDisplay，**number-flow 滾動動畫**進場。
- 下方小 caption（14px muted）。

## 8. Footer link group

- 5 欄連結群（Products / Solutions / Developers / Company / Legal…），標題 14px muted + 連結清單。

---

## 元件清單覆蓋度（vs `01_components_spec.md`）

| 元件 | 狀態 | 變體齊全度 |
|------|------|-----------|
| Button | ✅ | primary/secondary/ghost/icon-affix |
| Link | ✅ | default/muted |
| Card | ✅ | demo/news/gateway |
| Input | ⚠️ | mock-only，states TBD |
| Nav | ✅ | logo/menu/cta/mega-dropdown |
| Badge | ✅ | label pill |
| Stat | ✅ | number-flow |
| Footer group | ✅ | — |

> ≥ 5 個元件含完整變體 ✅（驗收門檻通過）。
