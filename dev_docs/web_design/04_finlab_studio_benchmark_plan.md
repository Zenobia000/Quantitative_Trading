# FinLab Studio 對標與前端優化計畫

> **日期**：2026-07-03 | **對標對象**：studio.finlab.finance（Schedule / Data Catalog / Market Pulse / 策略頁）+ FinLab SDK 分析模組
> **服務分支**：`refactor/frontend-uiux-finlab-benchmark`
> **定位前提**：FinLab 是多租戶 SaaS、notebook-first、報酬導向；本平台是 single-user localhost（ADR-031）、GUI-first、**判決導向**（edge 驗證工廠，PRD v4.0）。對標原則：資料卡模式照抄、績效圖挑著抄再加審判庭視覺、沙盒依威脅模型重新裁決。

---

## 1. 核心結論（一句話版）

| FinLab 功能 | 裁決 | 理由 |
| :--- | :--- | :--- |
| Data Catalog 資料卡 | **照抄模式，authoring-first** | 策略作者的資料字典（如 XQ 後台）：搜 key→複製→寫策略；加「本地有無 + 策略庫誰在用」兩個狀態，快取/staleness 不進 UI |
| SDK 績效圖（report/analysis 模組） | **挑六樣抄，加四樣獨有** | 通用圖直接參考；判決視覺（DSR 標尺/封存段/WFA strip）是我們的差異化，置頂 |
| AI 分析 + Pyodide 沙盒 | **P0 不做，先做 Open-in-notebook** | 他們沙盒是多租戶必需；我們是單人 localhost，威脅模型不同。Pyodide 留 P2 綁 AI chat |
| Studio IA / 元件 | **抄 URL 深連結 + 策略軸 + 體檢表** | 最大 IA 收穫是「策略中心頁」——現行 IA 以 run 為軸、策略軸弱 |

---

## 2. 資料卡牆（Data Catalog → System/Data 升級）

> **2026-07-03 設計糾偏（使用者 feedback）**：資料卡是「策略作者的資料字典」（如 XQ 後台：搜尋有什麼資料可以寫策略），**不是快取運維儀表板**。staleness/coverage/manifest 全部退出 UI；新鮮度守門留在使用點（after-close 的 `check_panel_freshness` 已做）。

### 2.1 資訊架構（authoring-first）

每張卡 = 一個 FinLab dataset key，回答「這是什麼、怎麼用、我用了沒」：

```
┌──────────────────────────────────────────────┐
│ 外資買賣超  institutional_investors:外資     │  ← key 一鍵複製
│ [籌碼] chip · 日頻 · 歷史自 2012              │
│ 「三大法人每日買賣超金額…」                   │  ← 欄位說明
│ ● 本地已有   ⚡ inst_flow、momentum 使用中    │  ← 唯二狀態
│ [複製 data.get(...)] [下載到本地]             │
└──────────────────────────────────────────────┘
```

- **全目錄**搜尋/分類瀏覽（FinLab 有的全部列出，不只本地有的）——回答「有哪些數據可以寫策略」
- 狀態唯二：**本地已有/未下載**（檔案存在的二元判斷）+ **策略庫反向索引**（掃 `strategies/*/` 程式碼找 data key 引用）——「我的策略庫在用哪些資料」是 XQ 沒有的差異化
- 「下載到本地」接既有 async ingest job + 輪詢

### 2.2 後端

- `GET /system/datasets`：FinLab catalog 靜態目錄（key/中文名/分類/頻率/歷史起點/說明——可從 FinLab 文檔整理成靜態 JSON，隨版本更新）× 本地檔案存在性 × 策略引用反向索引
- **不查** FinLab 端更新時間（效能殺手且對 authoring 無用）；**不讀** manifest

### 2.3 Manifest 的定位（明訂，避免誤用）

manifest（`manifest.json` 血統 hash）**保留但完全退出 UI**——只服務後端研究血統（`runs.bundle_ref`）。存在理由的真實案例：**還原股價（adj_close）歷史會在每次除權息後整條重寫**、財報偶有重編——「同一 run 重跑結果變了」時，血統 hash 讓審判庭能回答「資料變了，非程式壞了」。已知弱點（另列工項，非本 plan 範圍）：讀取端不驗 hash、稽核未閉環、併發寫入無鎖。

## 3. 績效頁自研（Run Report / 策略中心）

### 3.1 從 FinLab SDK 抄的六樣

依據：[策略分析模組](https://www.finlab.finance/docs/details/analysis_modules/)、[finlab.report](https://doc.finlab.tw/reference/report/)。

| # | 圖 | 內容 | 優先 |
| :--- | :--- | :--- | :--- |
| 1 | equity vs benchmark + drawdown 同框 | 對 0050/加權指數；runs sidecar 資料現成 | **P0** |
| 2 | 月報酬熱圖 | 年×月 grid，時期穩定性（PeriodStatsAnalysis） | **P0** |
| 3 | **Liquidity 表** | 漲停買入% / 跌跌停賣出% / 低量% / 警示·處置·全額交割佔比——**正中審查缺陷 #21 微結構缺口**，把可成交性做成報告一級公民 | P1 |
| 4 | Drawdown 事件表 | top-N 回撤：起訖 / 深度 / 回復天數（比單一 max DD 誠實） | P1 |
| 5 | MAE/MFE 精選三圖 | 12 子圖只抽：MAE vs Return 散點（停損位證據）、Edge ratio、持有期分佈 | P2 |
| 6 | AlphaBeta 年度拆解 | 市場中性候選（ADR-025 配置閘）評估需要 | P2 |

### 3.2 我們獨有的四樣（全部置頂，這是差異化）

1. **判決卡**：REAL / 🟡 PAPER_WATCH / REJECTED + 四條 hard-fail 燈號 + **DSR 在 0.90/0.95 標尺上的位置**（ADR-033 band 視覺化）
2. equity 依 **IS / OOS-holdout / live 分段著色**，sealed 邊界畫垂直線——「這段是封存的」是本平台敘事
3. **WFA fold strip**：5 折 OOS Sharpe 小條圖
4. **成本敏感疊圖**：base vs K3 slip 兩條 equity（PR #148 成本誠實化後才有資格畫）

### 3.3 架構決策

- **不學** FinLab「SDK 跑策略時直接 render」（notebook-first）；維持 headless（sidecar + REST）+ React 渲染
- 圖表庫：**lightweight-charts v5**（時序類，#166 已引入）+ 自製輕 SVG（熱圖/strip/散點）；**不引 Plotly**
- 後端：`GET /runs/{id}/report` 聚合端點（或沿用既有小端點組合），統一 envelope
- **前置依賴（P1 blocker）**：Liquidity/MAE 需逐筆 trades 含 date/price/symbol——#166 已知 panel 策略 trades sidecar 缺此欄位，**先補 trades schema 才能做 P1**

---

## 4. AI 分析與沙盒裁決

FinLab 用 Pyodide 因為多租戶：使用者代碼絕不能碰他家後端。本平台單人 localhost：貼的碼＝自己的碼跑自己的機器，「後台開沙盒」的威脅模型基本消失；但「API 上開任意代碼執行端點」仍違反邊界驗證原則、且是未來 remote 化的現成大洞。

| 選項 | 裁決 |
| :--- | :--- |
| 後端直接執行使用者代碼 | ❌ 永不 |
| **Open-in-notebook** | ✅ **P0**：Run Report / 策略中心加按鈕，生成預填 run_id + 資料載入碼的 `.ipynb`（使用者本有 venv+Jupyter）。一天做完、零風險、零維運 |
| Pyodide 前端沙盒 | 🟡 **P2 實驗性、綁 AI chat 一起做**：真隔離、零後端風險；代價 ~15MB WASM 首載、資料只能經 REST 拿 JSON。完整故事是「AI 產生分析碼 → 沙盒直接跑」，單獨存在價值不高。若做：iframe sandbox + CSP 只放行本機 API + 超時守門 |

---

## 5. IA 與元件優化

> **後續演進**：本 §5 的策略軸 IA 洞察已被 [rebuild_ia_spec_2026-07-03.md](./rebuild_ia_spec_2026-07-03.md)（rebuild Goal 1）擴充為五 zone 三旅程完整藍圖 —— 該檔為 Wave B/C IA 實作真相源；本節保留為對標依據。

### 5.1 IA（從 studio 偵察所得：頂部 tabs Schedule/Data Catalog/Market Pulse + My Strategies + 策略表）

1. **策略中心頁（strategy hub）——本次對標最大收穫**：現行 IA 以 run 為軸、策略軸弱。新增以策略為軸的聚合頁：該策略的 runs / 歷次判決時間線 / 觀察艙狀態 / K 線覆盤入口 / Open-in-notebook。URL 深連結 `/research/strategy/:name`（對標 `?strategy_id=`）
2. **艦隊體檢表（Market Pulse 翻譯版）**：艦隊總控升級為「一張表看全部策略＋自訂排序」，但欄位 verdict-first：Gate 狀態 / DSR / 觀察艙進度 / live vs backtest 落差——**不是報酬排行榜**（ADR-022 反跨人 leaderboard；自家策略體檢表是另一物種）
3. **排程總覽**：WatchPage 擴充涵蓋 after-close + backup 兩個 timer 的最後執行/下次預期（對標 Schedule 頁）

### 5.2 元件級

- 統一 `MetricCell`（數字 + 方向色 + Geist Mono 右對齊）、`VerdictBadge`、`CoverageBar`、`StatusChip`
- 指令複製塊（WatchPage 已有 pattern）提升為共用元件
- 表格：sticky header、數字右對齊、Custom Sort（對標 studio 策略表）
- 空態：維持現行四態頁模式（studio 的裸 "No market data available." 是反例）

---

## 6. 執行順序

```
P0（真正的日常剛需）
 ├─ Run Report v1：判決卡 + 分段 equity/DD + 月熱圖（觀察艙三個月的日常介面）
 └─ Open-in-notebook 按鈕

P0.5
 ├─ 資料卡牆 v1（authoring-first：全目錄 + 本地有無 + 策略反向索引）
 └─ 策略中心頁（上線即退役 StrategyLibrary，避免頁面膨脹）

P1（有前置依賴）
 ├─ trades schema 補欄（date/price/symbol）← blocker
 ├─ Liquidity 呈現層（事後統計 fills 撞漲跌停比例）——與模擬層擋單（審查 #21，另立工項、會改歷史數字）明確切開
 ├─ DD 事件表 + 艦隊體檢表（艦隊總控升級）
 └─ 排程總覽併入 Watch 頁

P2（實驗性/加分）
 ├─ MAE/MFE 精選三圖 + AlphaBeta 年度拆解
 ├─ Pyodide 沙盒（與 AI chat 同梯）
 └─ 資料卡 sparkline
```

## 7. 參考來源

- [FinLab 策略分析模組文檔](https://www.finlab.finance/docs/details/analysis_modules/)（六大分析模組 + MAE/MFE 12 子圖）
- [finlab.report](https://doc.finlab.tw/reference/report/)、[finlab.plot](https://finlab.finance/docs/reference/plot/)
- [FinLab 資料庫](https://ai.finlab.tw/database/)
- studio.finlab.finance 偵察（2026-07-03）：tabs Schedule/Data Catalog/Market Pulse；策略表欄位 Custom Sort / Last Updated / Q.Ret / Annual Return / Sharpe / Max Drawdown
