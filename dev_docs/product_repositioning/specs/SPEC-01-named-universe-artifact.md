# SPEC-01：具名股票池實體（Named Universe Artifact）與資料下載對接

> 狀態: Draft | 日期: 2026-07-05 | 作者: 資料管理討論收斂 | 關聯: ADR-007、ADR-032、ADR-006
>
> 觸發來源: 前端資料管理四輪討論（資料字典 / 資料匯入 / 股票池建置 / 資料集清單 的角色、對接缺口、篩選邏輯）。
>
> 本 spec 是「該確認 + 該修正」事項的單一整理處。凡涉及 finlab SDK 的判斷，皆以本機 finlab 2.0.0 實測為據（見 §2），不以記憶臆測。

---

## 1. 問題陳述（四輪討論收斂）

現況有四個資料管理面向，但彼此**斷線**：

| # | 使用者觀察 | 根因（程式碼實測） |
| :--- | :--- | :--- |
| Q1 | 「有些資料看得到卻下不了」 | 資料字典是 key 層級的策展快照；本地 bundle 只有三表（`daily_bars`/`institutional`/`broker_chips`）。財報/月營收/融資融券**無 ingest 落地路徑**，永遠 `not_cached`。 |
| Q2 | 「股票池是搜尋範圍？該放研究？」 | 股票池 = 回測母體（survivorship-clean）。**build** 屬資料層（重、共享、可重現），**select** 屬研究層——但研究層 New Run 只有自由文字 `stocks`，**選不到既有池**。 |
| Q3 | 「篩選邏輯太少？」 | build 只有 `top_n`(市值) + `min_turnover`(流動性) 兩刀。缺的是**可交易性/資格**排除（全額交割/處置/板別/ETF），這些不是策略訊號，該放 universe。 |
| Q4 | 「策略↔股票池該勾選對接」 | 對接今天藏在各策略 `research_config.py` 程式碼裡（自由宣告 symbols）。前端無任何機制表達「策略 X 用池 Y」。 |

**核心洞察（資料結構優先）**：四個提案本質是在要**同一個今天不存在的實體——一等的「具名股票池（Named Universe）」**。加這一個對的抽象，四個特殊情況一起消失。

---

## 2. finlab SDK 實測（先確認再下判斷）

環境：`finlab 2.0.0`（本機已裝，`uv run python`）。`finlab.data.search(keyword)` **離線可用**（走 Firestore catalog cache，無需 token 即回真實 key），故所有 key 存在性均已驗證。

### 2.1 現有策展 catalog 13 個宣稱 key — 全數存在 ✅

`price:收盤價`、`etl:adj_close`、`etl:market_value`、`fundamental_features:ROE稅後`、`price_earning_ratio:{本益比,股價淨值比,殖利率(%)}`、`monthly_revenue:{當月營收,去年同月增減(%),上月比較增減(%)}`、`margin_transactions:{融資今日餘額,融券今日餘額,融資使用率}`、`institutional_investors_trading_summary:{投信買賣超股數,外陸資買賣超股數(不含外資自營商)}` — 逐一 `search` 命中。**現有 `finlab_catalog.py` 準確，無需修正（寧缺勿錯策展生效）。**

### 2.2 Eligibility（可交易性/資格）資料源 — 全數可得 ✅

Q3 缺的排除條件，finlab **原生已提供**，不需自建：

| 資格條件 | finlab 來源（實測） | 性質 |
| :--- | :--- | :--- |
| 全額交割股 | `change_transaction:變更交易`（全額交割是「變更交易方式」之一）；上櫃另有 `tpex_cmode:變更交易` | 每日變動狀態 → 時變遮罩 |
| 處置股 | `esb_attention_disposal:處置有價證券`（+ `處置原因/開始時間/結束時間`） | 每日變動狀態 → 時變遮罩 |
| 注意股 | `esb_attention_disposal:注意有價證券` | 每日變動狀態 → 時變遮罩 |
| 板別（上市/上櫃） | `data.set_universe(exchange='TWSE'|'TPEx')`（backing: `security_categories`） | 靜態屬性 |
| 產業排除 | `data.set_universe(exclude_sector=...)` | 靜態屬性 |
| ETF / 特別股排除 | `data.set_universe(asset_type='ETF'|'STOCK')` | 靜態屬性 |

### 2.3 架構結論：finlab 原生 universe 與自建 builder 互補，不重造

`finlab.data.set_universe(exchange, sector, exclude_sector, industry, asset_type, category, exclude_category)` 是**靜態資格層**；`data.universe(...)` 為其 context-manager 版。我們的 `research/workflows/universe.py` + `finlab_universe.select_survivorship_universe` 是**動態 size/liquidity/survivorship 選股層**。兩者職責分明：

```
finlab set_universe（靜態資格）  →  survivorship 選股（動態 size+liquidity）  →  eligibility 時變遮罩（處置/注意/變更交易）
        板別/產業/ETF                    top_n / min_turnover                    每日狀態排除
```

**不得**用自建篩選重造 finlab 已有的 exchange/sector/asset_type 過濾。

> ✅ **frame 形狀已 token 實抓確認（2026-07-05）**：三個 status frame 皆 **wide `date × stock`**，可直接以 as-of 遮罩用，無需 pivot：
> - `change_transaction:變更交易` — `Float64`，`1.0` = 變更交易（含全額交割）、`0.0` = 否（dense，~4700 日 × ~515 檔）。
> - `esb_attention_disposal:處置有價證券` / `:注意有價證券` — `bool`，`True` = 處置/注意期間（sparse 事件視窗，末列帶顯式 `False` → ffill/as-of 正確）。
> 落地：`ineligible_asof(frames, ts)` 取 as-of（`_asof` ffill，嚴格無 look-ahead）後收集 truthy 欄；`1.0`/`True` 皆算、`0.0`/`False`/NaN 不算。auth 注意：finlab 2.x `login(api_token=)` 於 2026/08/01 後 deprecated，改 `python -m finlab login`（見 `finlab_source.login`）。

---

## 3. 目標資料結構

```
Universe（具名產物 — 一等實體）
  ├─ id / name              ← 可被選、可被引用（消掉自由打 symbols / 自由打 strategy）
  ├─ symbols[]              ← 下載動作的「幫誰抓」
  ├─ span (start, end)      ← 下載動作的「抓哪段」
  ├─ build params           ← top_n / min_turnover（動態選股）
  ├─ eligibility filters    ← exchange/sector/asset_type（靜態）+ 處置/注意/變更交易（時變）
  ├─ cache_dir              ← parquet 落地位置
  └─ manifest（provenance）  ← 已存在：universe_manifest.json

策略  ──references──▶  Universe        （N:1；多策略共用因子中性池，非 1:1）
資料字典 presence/download  ──相對於──▶  Universe + span
研究 New Run  ──selects──▶  Universe
```

**N:1 是鐵律**：`reversal` 與 `inst_flow` 共用同一因子中性池（程式碼註解實證："universe is factor-agnostic... only the signal differs"）。做成 1:1 會產生內容雷同的重複 parquet 快取，違背設計。今日 `universe_manifest.json` 把 `strategy` 記成**單數**是既有 smell，本 spec 修正為 `strategies[]` 或改記 universe 自身 name（見 §4 slice 1）。

---

## 4. 落地切片（TDD，每片獨立可 review / 可 revert）

> 順序原則：先立資料結構 seam（後端讀模型），再接前端選用，最後補 eligibility。前兩片**全離線可測**（不碰 finlab 網路）。

### Slice 1 — 後端：具名 Universe 讀模型 + 端點（keystone）
- 新增 `UniverseRef` 讀模型（`id`/`name`/`symbols_count`/`span`/`params`/`strategy(es)`/`cache_dir`），投影自既有 `bundle_registry.BundleInfo`（`kind="universe"` 已具 `strategy`/manifest）。
- `GET /system/universes` — 掃 manifest 列出具名池（degrade→typed-empty，比照 `/system/bundles`）。
- manifest schema：`strategy: str` → 允許 `strategies: list[str]`（N:1），保留舊欄位讀相容。
- 測試：manifest 掃描、typed-empty、N:1 讀相容。**無網路。**

### Slice 2 — New Run 股票池選單 + 後端解析（接 Q2/Q4/Q5）✅ 已落地
- `NewRunPage` 自由文字 `stocks` → **股票池下拉**（`GET /system/universes`）；「自訂 symbols」為 fallback。
- **後端解析**（`RunCreateRequest` 加 `universe`、`stocks` 改選填；`runs._resolve_stocks`）：精度序 explicit stocks > named universe（`universe_registry.symbols_for`）> `DEFAULT_UNIVERSE`；未知 universe → 422。**survivorship-clean 保證隨選擇走**，消除自由打不乾淨清單。
- **Q5**：策略不必設池——不設即用系統預設 + 產品提示（UI hint）。
- 測試：後端 resolver 4 案 + 前端選單 2 案（預設不送 stocks/universe、選具名池送 universe）。

### Slice 2.5 — 資料字典/策略頁 UX（使用者回饋批次）✅ 已落地
- **反向索引搬家**：資料字典移除 `used_by` chip（多策略會擠爆）；改在**策略詳情頁** `UsedDatasetsSection` 呈現「此策略用的資料卡」（複用 `/system/datasets` 前端過濾，`used_by` 資料仍保留）。
- **資料字典教用法**：卡片展開顯示 `data.get('<key>')` 取數呼叫 + 複製 + finlab DB 文件連結（非只複製 key）。
- **収合**：每張卡改 `<details>`（收起一行、展開才顯示用法/說明），解「畫面太長」。

### Slice 3 — 後端：Eligibility 篩選層（接 Q3）✅ 已落地
- `UniverseConfig` / `UniverseBuildRequest` 加 `exchange`（透傳 finlab `set_universe` 靜態板別）+ `exclude_flagged`（全額交割/處置/注意時變遮罩），**皆 opt-in、預設 off = 行為不變**。
- build workflow：`_finlab_getter(exchange)` 套 `set_universe`（靜態）→ `_eligibility_frames` 抓三 status frame（defensive skip）→ `select_survivorship_universe(exclude_frames=...)` 每個再平衡日剔除。
- **frame 形狀已 token 確認**（§2.3）；`ineligible_asof` 純函式、fixture 離線測試。
- 前端 `UniverseBuildCard` 加板別下拉 + 排除 flagged checkbox（含 hint）。
- 測試：`ineligible_asof` 3 案 + `select_survivorship_universe(exclude_frames)` 2 案 + workflow opt-in 1 案。

### Slice 4 — 資料下載對接資料字典（接 Q1，最後做）
- 資料字典 presence 由「全域 category 二元」→「相對選定 Universe + span」。
- 卡片 `not_cached` → 一鍵補該表（symbols 來自池、span 來自 manifest）。
- 對三類無 ingest 路徑者（財報/月營收/融資融券）：**先明確標示「此類不入本地 bundle，執行時 `data.get` 即抓」或開 ingest 表**——二選一由 ADR-007 決策後定。

### 非目標（本 spec 不做）
- 不搬 build 到研究區（§Q2：build 留 Data，只在研究補 select）。
- 不為單一策略造專屬池（§3 N:1）。
- 不用自建篩選重造 finlab exchange/sector/asset_type（§2.3）。

---

## 5. 文件同步清單（code-doc-sync 觸發）

- [x] 本 spec（specs/SPEC-01）
- [x] ADR-007（golden 產品層，`04_architecture_decision_records.md`）— 具名 Universe 實體 + N:1 + eligibility 用 finlab 原生 + Q1 三類資料落地策略
- [x] 16 WBS — WP10 任務列（單一狀態真相源）
- [x] 06 API 設計 — `GET /system/universes` 契約（Slice 1 落地時）
- [ ] 21 資料契約 / manifest schema — `strategy`→`strategies[]`（Slice 1）
- [ ] `finlab_catalog.py` — eligibility 分類與 key（Slice 3；含 `change_transaction`/`esb_attention_disposal`）
