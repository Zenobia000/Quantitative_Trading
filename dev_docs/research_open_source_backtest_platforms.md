# 開源回測平台地毯式搜尋報告

> 日期：2026-05-31
> 搜尋者：Claude (general-purpose agent)
> 用途：backtest_platform 選型參考
> 既定路線：rqalpha + vectorbt（驗證/比對中）
> 標的：台股 100 檔 × 10 年 portfolio；資料源 FinMind + TWSE；M4 後接 Shioaji

---

> ## 📌 後續決策 Follow-up（2026-05-31 補註）
>
> 本報告所建議的「**TQuant-Lab 主骨架 + vectorbt 副引擎 + 自寫 PBO/DSR**」方案**已被採納**，並擴充為完整的 M2-M5 交易系統規劃（含 FinLab 付費資料源、三模式統一、雙儀表板）。
>
> **正式決策請參閱**：
> - [ADR-005: 主骨架選定 TQuant-Lab](./adrs/ADR-005-mainframe-tquant-lab-zipline-fork.md)（Supersedes ADR-001）
> - [ADR-006: 資料源改 FinLab 付費版](./adrs/ADR-006-data-source-finlab-paid.md)
> - [ADR-007: 雙引擎策略](./adrs/ADR-007-dual-engine-zipline-vectorbt.md)
> - [ADR-008: 三模式共用 strategy code](./adrs/ADR-008-tri-mode-shared-strategy-code.md)
> - [ADR-009: 雙儀表板 + Telegram 告警](./adrs/ADR-009-dual-dashboard-telegram-monitoring.md)
> - [17_m2_to_m5_master_plan.md](./17_m2_to_m5_master_plan.md)（完整 M2-M5 規劃）
>
> 本報告作為決策依據保留，內容不再更新。

---

## 一、TL;DR — 給 backtest_platform 的建議

1. **既定的 rqalpha + vectorbt 組合在 2026 年仍是合理選擇**，但 **rqalpha 的價值主要是「事件驅動骨架 + Mod Hook 擴展介面」**，其對台股的支援需要使用者自行撰寫資料源 mod；而 **vectorbt 才是真正能 hit 100 檔 × 10 年 < 30 分鐘性能目標的引擎**。
2. **強烈建議直接評估 TQuant-Lab (TEJ 官方 zipline fork)** — 這是目前 GitHub 上**唯一已經把台股交易日曆、TEJ 資料源、Shioaji 範例都接通的開源框架**，MIT 授權，能省下 4-6 週的台股資料整合工作。但綁定 TEJ API 金鑰是劣勢。
3. **vectorbt 的開源版本已停止大更新**（v1.0.0 是 2026/04 但屬最終整理版），新功能都進 vectorbt PRO（$20/月）。若預算許可，PRO 在 portfolio 多參數掃描、Walk-Forward 上明顯更強。
4. **不要直接用 rqalpha 做台股回測** — rqalpha 的骨架是為中國 A 股 + 期貨 + 期權設計的，台股的漲跌停、零股、ETF 配息、現金股利機制完全不同，整合成本可能比自己用 vectorbt + 自寫 portfolio engine 還高。
5. **PBO/DSR 必須自己接 pypbo（小眾）或從《Advances in Financial Machine Learning》照抄實作**。mlfinlab 已轉商業授權，empyrical-reloaded + quantstats 不含這兩項指標。

**最終建議：**
- 主引擎：**vectorbt (open source) + quantstats 報表 + pypbo 統計驗證**
- 台股資料源/日曆參考：**借鑑 TQuant-Lab 但不直接依賴**（避免綁 TEJ）
- 實盤：**直接接 Shioaji 官方 SDK**，不走 rqalpha live trading（rqalpha 沒有 Shioaji broker mod）
- rqalpha：**捨棄，或僅作為事件驅動結構的設計參考**

---

## 二、總覽表（按相關性排序）

| 專案 | Stars | 最近活躍 | License | 語言 | 類型 | 台股支援 | 推薦度 |
|---|---|---|---|---|---|---|---|
| [vectorbt](https://github.com/polakowo/vectorbt) | 7.7k | 2026-04 v1.0.0 | Apache-2.0 + Commons Clause | Python (Numba/Rust) | 向量化 | 自己接 | ★★★★★ |
| [TQuant-Lab](https://github.com/tejtw/TQuant-Lab) | 84 | 活躍 (2025-2026) | MIT | Python (zipline fork) | 事件驅動 | **原生** | ★★★★★ |
| [quantstats](https://github.com/ranaroussi/quantstats) | 7.2k | 2026-01 v0.0.81 | Apache-2.0 | Python | 報表分析 | N/A | ★★★★★ |
| [zipline-reloaded](https://github.com/stefan-jansen/zipline-reloaded) | 1.8k | 2025-07 v3.1.1 | Apache-2.0 | Python | 事件驅動 | 需自接 | ★★★★ |
| [rqalpha](https://github.com/ricequant/rqalpha) | 6.4k | 2026-05 v6.1.5 | Apache-2.0 | Python | 事件驅動 | 需大量改寫 | ★★★ |
| [microsoft/qlib](https://github.com/microsoft/qlib) | 43.7k | 2025-08 v0.9.7 | MIT | Python | ML-Quant 全棧 | 中/美 | ★★★ |
| [nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | 23.2k | 2026-05 | LGPL-3.0 | Rust + Python | 機構級事件驅動 | 無 | ★★★ |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | 19.5k | 活躍 | Apache-2.0 | C# + Python | 機構級 | 無 | ★★ |
| [backtesting.py](https://github.com/kernc/backtesting.py) | 8.4k | 緩慢維護 | AGPL-3.0 | Python | 簡易事件驅動 | 自接 | ★★★ |
| [pmorissette/bt](https://github.com/pmorissette/bt) | (約 2k) | 2026-03 v1.1.5 | MIT | Python | Portfolio 模組化 | 自接 | ★★★ |
| [pypbo](https://github.com/esvhd/pypbo) | 133 | 不確定 | AGPL-3.0 | Python | PBO/DSR 統計 | N/A | ★★★★ |
| [empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded) | 小型 | 活躍 (v0.9.9) | Apache-2.0 | Python | 風險指標 | N/A | ★★★ |
| [pyfolio-reloaded](https://github.com/stefan-jansen/pyfolio-reloaded) | 小型 | 活躍 (v0.9.7) | Apache-2.0 | Python | 報表分析 | N/A | ★★★ |
| [FinMind](https://github.com/FinMind/FinMind) | 2.6k | 活躍 | Apache-2.0 | Python | 資料源 + 簡易 BT | **原生** | ★★★★ |
| [Sinotrade/Shioaji](https://github.com/Sinotrade/Shioaji) | 444 | 2026-05 v1.5.1 | 商業 SDK | Python (C++ binding) | 實盤 API | **原生** | ★★★★★ (實盤必備) |
| [FinRL](https://github.com/AI4Finance-Foundation/FinRL) | 15.3k | 2026-03 v0.3.8 | MIT | Python | RL 平台 | Sinopac 資料源 | ★★ |
| [vnpy](https://github.com/vnpy/vnpy) | 41.1k | 2026-05 v4.4.0 | MIT | Python | 全棧量化平台 | 無 (CTP 為主) | ★★ |
| [Yvictor/polars_backtest_extension](https://github.com/Yvictor/polars_backtest_extension) | 10 | 2026-01 v0.1.6 | PolyForm Noncommercial | Python (Polars) | 向量化 | (台灣作者) | ★★★ (實驗性) |
| [hikyuu](https://github.com/fasiondog/hikyuu) | 3.2k | 活躍 | Apache-2.0 | C++/Python | 高速 BT | 無 (僅 A 股) | ★★ |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | 19.5k | 活躍 | Apache-2.0 | C#+Python | 機構級 | 無 | ★★ |
| [QSTrader](https://github.com/quantstart/qstrader) | (約 4k) | 緩慢 | MIT | Python | 事件驅動 | 自接 | ★★ |
| [backtrader (原版)](https://github.com/mementum/backtrader) | 21.8k | **已棄維護 (2018+)** | GPL-3.0 | Python | 事件驅動 | 自接 | ★★ (僅學習價值) |
| [fastquant](https://github.com/enzoampil/fastquant) | (約 1.7k) | 2026-03 | MIT | Python | 簡易 BT | 無 | ★ |
| [freqtrade](https://github.com/freqtrade/freqtrade) | 50.9k | 2026-04 | GPL-3.0 | Python | **僅加密貨幣** | 不適用 | ★ (架構參考) |
| [jesse](https://github.com/jesse-ai/jesse) | 7.6k | 活躍 | MIT | Python | **僅加密貨幣** | 不適用 | ★ |
| [hummingbot](https://github.com/hummingbot/hummingbot) | 16.9k | 活躍 | Apache-2.0 | Python | **僅加密貨幣 MM** | 不適用 | ★ |
| [tensortrade](https://github.com/tensortrade-org/tensortrade) | (約 5k) | 緩慢 | Apache-2.0 | Python | RL | 無 | ★ |
| [scrtlabs/catalyst](https://github.com/scrtlabs/catalyst) | (約 2k) | **已棄 2022** | Apache-2.0 | Python | 加密貨幣 BT | 不適用 | ✗ |
| [pyfolio (原版)](https://github.com/quantopian/pyfolio) | 6.3k | **2019 後棄維護** | Apache-2.0 | Python | 報表 | N/A | ✗ (用 reloaded 版) |
| [zipline (原版)](https://github.com/quantopian/zipline) | (高) | **2020 Quantopian 關閉** | Apache-2.0 | Python | 事件驅動 | N/A | ✗ (用 reloaded 版) |
| [PyAlgoTrade](https://github.com/gbeced/pyalgotrade) | (中) | 已不活躍 | Apache-2.0 | Python | 事件驅動 | 無 | ✗ |
| [mlfinlab](https://github.com/hudson-and-thames/mlfinlab) | (高) | 商業化 | 已轉商業 | Python | ML for Finance | N/A | ✗ (考慮 mlfinpy fork) |

說明：Stars 數標「(約 X)」者為公開資料推估；無「2026」標註者表搜尋未能取得最新精確時間。

---

## 三、Tier 1 — 強烈建議深入評估

### 3.1 vectorbt (polakowo) ★★★★★

- **GitHub**: https://github.com/polakowo/vectorbt
- **Stars**: 7.7k｜**License**: Apache-2.0 + Commons Clause（**注意：禁止「銷售軟體」**）
- **最近**: v1.0.0 (2026-04-22)

**優勢：**
- 真正能解決「100 檔 × 10 年 portfolio < 30 分鐘」的引擎 — Numba JIT + Rust 加速，向量化 portfolio simulation
- 內建 quantstats 整合、interactive Plotly 視覺化
- 適合**參數網格搜尋**（你需要做 IS/OOS 與 Walk-Forward）
- AI agent 友善（v1.0.0 後 API 更穩定）

**劣勢：**
- **學習曲線陡** — 思維要從「for-loop 一檔一檔跑」切到「pandas/numpy 矩陣化」
- **事件驅動能力弱** — 不適合複雜 broker 模擬、撮合邏輯（你 M4 要接 Shioaji 時這會是斷層）
- **Commons Clause 限制** — 若未來想商業化「軟體本身」會卡，但「用它跑策略賺錢」沒問題
- **PRO 版才有 parallelization 與 Walk-Forward 完整實作**，open source 版本要自己拼

**適合性：★★★★★（核心引擎）**
- 100 檔 portfolio 性能目標只有 vectorbt 一個能輕鬆達成
- IS/OOS、PBO 都需要大量參數掃描，vectorbt 是最佳選擇
- **整合難度：中** — 需要寫自己的台股 data loader (FinMind → vectorbt 接口)

---

### 3.2 TQuant-Lab (TEJ 台灣經濟新報) ★★★★★

- **GitHub**: https://github.com/tejtw/TQuant-Lab
- **Stars**: 84｜**License**: MIT｜**配套**: zipline-tej, pyfolio-tej, exchange_calendars

**優勢：**
- **唯一原生支援台股的 zipline fork**
- 已內建台股交易日曆 (TEJ_XTAI)、Pipeline 工廠、營收成長/超級趨勢等範例策略
- 範例倉庫**已示範如何接 Shioaji 實盤**（TQuant Lab 超級趨勢策略_永豐 Shioaji.ipynb）
- 直接解決你 M4 要接 Shioaji 的整合斷層
- MIT 授權無商業限制

**劣勢：**
- **資料源綁定 TEJ**（需 TEJ_API_KEY）— TEJ 為付費資料商，免費額度有限
- Stars 才 84，社群很小，遇到問題只能靠 TEJ 官方支援
- Zipline 本身是事件驅動，**100 檔 portfolio 跑 10 年可能慢於你的 30 分鐘目標**（zipline 在這量級通常需要 30-90 分鐘）
- Walk-Forward / PBO / DSR 需自接

**適合性：★★★★★（台股 reference architecture）**
- 即使最終不用，**強烈建議先 git clone 研究其 exchange_calendars 與資料 ingest 邏輯**
- 適合做：研究階段、需要嚴格交易日曆、要與 Shioaji 接通的 paper trading

**整合策略建議：**
- A 方案：直接用 TQuant-Lab + TEJ API（最快，但綁付費資料）
- B 方案：抽出其 exchange_calendar_xtai 部分，搭配 FinMind 資料源餵 vectorbt（推薦）

---

### 3.3 quantstats (ranaroussi) ★★★★★

- **GitHub**: https://github.com/ranaroussi/quantstats
- **Stars**: 7.2k｜**License**: Apache-2.0
- **最近**: v0.0.81 (2026-01-13)

**優勢：**
- 一行 `qs.reports.html(returns)` 產出完整 tearsheet（Sharpe, Sortino, Calmar, MDD, monthly heatmap）
- 與 vectorbt 原生整合（vectorbt.portfolio 可直接 `.stats(metrics='quantstats')`）
- 維護穩定，社群大

**劣勢：**
- **無 PBO / DSR / Combinatorial Purged CV**
- Monte Carlo 簡單但不夠專業
- 缺乏 multi-asset attribution 分析

**適合性：★★★★★（報表必備）**
- 直接整合，無替代方案
- PBO/DSR 另接 pypbo 補上

---

### 3.4 pypbo (esvhd) ★★★★

- **GitHub**: https://github.com/esvhd/pypbo
- **Stars**: 133｜**License**: AGPL-3.0

**優勢：**
- **GitHub 上唯一現成的 PBO + Deflated Sharpe Ratio + PSR + MinTRL/MinBTL 實作**
- 直接照 Bailey & Lopez de Prado 論文實作
- 程式碼短小，可審計

**劣勢：**
- Stars 只有 133，維護不確定
- **AGPL-3.0 — 若你的回測平台對外提供 SaaS 會被傳染**
- API 不夠 friendly

**適合性：★★★★（核心統計驗證，但要小心 license）**
- 建議：**抽出關鍵函式（pbo、deflated_sharpe）改寫成內部 module**，避免 AGPL 傳染
- 或：自行根據論文重寫（程式邏輯很短，<200 行）

---

## 四、Tier 2 — 值得借鑑架構/元件

### 4.1 rqalpha (Ricequant) ★★★

- **GitHub**: https://github.com/ricequant/rqalpha
- **Stars**: 6.4k｜**License**: Apache-2.0｜**最近**: v6.1.5 (2026-05-21)

**優勢：**
- **Mod Hook 架構非常乾淨** — 資料源、撮合、broker、analyser 都是可替換模組
- 中國 A 股、期貨、期權支援完整，事件驅動模型成熟
- 文件齊全（簡中）

**劣勢（針對台股場景）：**
- **沒有現成的台股 mod**，要自己寫 `rqalpha_mod_taiwan` （交易日曆、漲跌停 10%、零股、現金股利、配股）
- 撮合模型是 A 股 T+1，台股是 T+2 結算（雖然多數策略只看 T+0 即可，但完整實盤需處理）
- 6.x 版本對舊 mod 有 breaking change
- **沒有 Shioaji broker mod**（中國只有 CTP / XTP / SimNow）

**適合性：★★★（值得借鑑架構，不建議直接使用）**
- **借鑑點**：Mod 系統的 plugin 註冊機制、event_bus 的設計
- **不採用原因**：寫完台股 mod 的時間 ≈ 自己用 vectorbt + 自寫 event engine

---

### 4.2 zipline-reloaded ★★★★

- **GitHub**: https://github.com/stefan-jansen/zipline-reloaded
- **Stars**: 1.8k｜**License**: Apache-2.0｜**最近**: v3.1.1 (2025-07)

**優勢：**
- 維護活躍，Stefan Jansen（《Machine Learning for Algorithmic Trading》作者）
- **Pipeline API 是業界最優秀的 factor research 框架之一**，定義動態 universe 超方便
- 100 檔 portfolio 的 daily rotation 是它強項
- empyrical-reloaded + pyfolio-reloaded 配套完整

**劣勢：**
- **預設用 NASDAQ/NYSE 日曆**，台股要自己用 `exchange_calendars` 註冊 XTAI
- 安裝困難（C extension）
- 100 檔 × 10 年事件驅動性能可能落在 30-60 分鐘之間，邊緣達標
- **TQuant-Lab 已經做完上述整合**，直接看 TQuant-Lab 即可

**適合性：★★★★（如果不用 TQuant-Lab，這是次佳）**

---

### 4.3 nautilus_trader (Nautech Systems) ★★★

- **GitHub**: https://github.com/nautechsystems/nautilus_trader
- **Stars**: 23.2k｜**License**: LGPL-3.0｜**最近**: 1.227.0 Beta (2026-05-18)

**優勢：**
- **Rust core + Python API，性能與正確性都頂級**
- 機構級事件驅動，nanosecond resolution，回測=實盤同一份程式碼
- 18+ 個交易所/數據商整合（含傳統市場）

**劣勢：**
- **沒有 Taiwan 交易所整合**（沒有 Shioaji adapter）
- LGPL-3.0 — 比 AGPL 寬鬆但仍有義務
- 學習曲線非常陡，文件對初學者不友善
- 100 檔 portfolio 是其能力範圍但設定複雜
- Rust 核心 = 自己改原始碼成本高

**適合性：★★★（若目標是「日後上機構級」可考慮，但與 rqalpha+vectorbt 路線衝突）**

---

### 4.4 microsoft/qlib ★★★

- **GitHub**: https://github.com/microsoft/qlib
- **Stars**: 43.7k｜**License**: MIT｜**最近**: v0.9.7 (2025-08)

**優勢：**
- **ML-Quant 全棧**：資料 → 因子工程 → ML 訓練 → 回測 → 組合最佳化
- 微軟出品，論文水準的 baseline（Alpha158、Alpha360）
- 已整合 RD-Agent（LLM 自動 R&D）

**劣勢：**
- **資料源主要是中國 A 股 + 美股**，台股需自己寫 dataset
- 偏 ML / RL，**對傳統 rule-based 策略（你的 backtest_platform 主要場景）overkill**
- 安裝重，依賴複雜

**適合性：★★★（若你的策略以 ML 為主，直接用；否則大砲打蚊子）**

---

### 4.5 pmorissette/bt ★★★

- **GitHub**: https://github.com/pmorissette/bt
- **Stars**: 約 2k｜**License**: MIT｜**最近**: v1.1.5 (2026-03)

**優勢：**
- 設計哲學是 **Algo 組合**（WeighEqually + RunMonthly + SelectWhere），portfolio 邏輯極清晰
- 維護穩定
- Python 3.14 支援，純 Python 易讀

**劣勢：**
- 速度普通（純 Python），100 檔 × 10 年沒問題但別期待向量化
- 範例與文件不及 vectorbt 豐富
- 缺乏統計驗證工具

**適合性：★★★（適合做 Portfolio Construction 原型，但跑大量參數掃描還是 vectorbt）**

---

### 4.6 backtesting.py (kernc) ★★★

- **GitHub**: https://github.com/kernc/backtesting.py
- **Stars**: 8.4k｜**License**: **AGPL-3.0**

**優勢：**
- API 極簡，3 行寫完一個 strategy
- Bokeh 互動式視覺化漂亮
- 適合教學與原型

**劣勢：**
- **單一資產為主**，portfolio 支援弱
- AGPL-3.0 — 對商業/SaaS 化致命
- 原作者 kernc 維護緩慢，社群 fork (lucit-backtesting) 補位

**適合性：★★★（POC 階段可用，正式選型不採）**

---

### 4.7 FinMind ★★★★

- **GitHub**: https://github.com/FinMind/FinMind
- **Stars**: 2.6k｜**License**: Apache-2.0

**優勢：**
- **台股資料源的事實標準**（>50 個 dataset）
- 內建簡易 backtest 範例 (`example/backtest.md`)
- 你已預定使用 — 沒有更好的替代

**劣勢：**
- **內建 backtest 簡陋**，不能當主引擎
- API 速率限制 (300 req/hr 免費版)

**適合性：★★★★（資料層必選；backtest 部分忽略）**

---

### 4.8 Sinotrade/Shioaji ★★★★★

- **GitHub**: https://github.com/Sinotrade/Shioaji
- **Stars**: 444｜**License**: 商業 SDK（免費使用）｜**最近**: v1.5.1 (2026-05-28)

**優勢：**
- **永豐金證券官方 Python SDK，台股實盤唯一選擇之一**（另一為元大 Yuanta API）
- 跨語言支援（Python, Go, Rust, C#）
- v1.5.x 已支援 Claude Code agent skill

**劣勢：**
- **不含 backtest** — 純實盤 API
- 撮合行為與真實 broker 有差異，paper trading 需另模擬

**適合性：★★★★★（M4 實盤必備，無替代）**

---

## 五、Tier 3 — 已知但不適合

| 專案 | 不適合原因 |
|---|---|
| **backtrader 原版** | 2018 後原作者棄維護，社群 fork 多但無權威主線；若要用請選 `backtrader2` 或 `backtrader_next` 而非 `mementum/backtrader` |
| **zipline 原版 (quantopian)** | Quantopian 已於 2020 關閉，倉庫凍結。用 `zipline-reloaded` 取代 |
| **pyfolio 原版** | 2019 後棄維護，依賴與現代 pandas 不相容。用 `pyfolio-reloaded` |
| **PyAlgoTrade** | 老舊，不活躍，無 portfolio 支援 |
| **scrtlabs/catalyst** | 2022 後棄維護，且為加密貨幣專用 |
| **freqtrade** | 純加密貨幣，CCXT 為基底，**無傳統股市撮合邏輯** |
| **jesse** | 純加密貨幣，無台股 |
| **hummingbot** | 純加密貨幣 market making，與 portfolio backtest 場景完全不同 |
| **tensortrade / tensortrade-ng** | RL 框架，活躍度低，且 RL ≠ 你的主要使用情境 |
| **mlfinlab** | Hudson-Thames 已轉商業授權，免費版功能受限。`mlfinpy` 是社群 fork 但不完整 |
| **vnpy** | 41k stars 強平台，但 **gateway 完全聚焦中國市場（CTP/XTP）**，無台股 gateway，且為實盤平台非 backtest 平台 |
| **hikyuu** | C++ 性能優秀但 A 股專用，台股整合成本高於收益 |
| **QSTrader** | 設計乾淨但社群小、文件少、無台股支援，相比 vectorbt 沒有獨特優勢 |
| **fastquant** | 簡化 wrapper，產品方向偏教學，不適合嚴肅回測 |
| **QuantConnect/Lean** | C# 為主，Python 是綁定層；如果不用 QuantConnect 雲端，本地部署複雜；無台股 data feed |
| **FinRL** | 純 RL 平台，雖然 data source 包含 Sinopac 但只取 OHLCV，與 portfolio backtest 無直接重疊 |

---

## 六、統計驗證工具盤點

### 6.1 報表類

| 工具 | 用途 | 推薦 |
|---|---|---|
| **quantstats** | HTML tearsheet, Sharpe/Sortino/Calmar/MDD | ★★★★★ 主用 |
| **pyfolio-reloaded** | 詳細 attribution、bayesian analysis | ★★★ 補充 |
| **empyrical-reloaded** | 純風險指標計算 (annualized return, alpha, beta) | ★★★ quantstats 已包含多數 |

### 6.2 統計顯著性 / Overfitting 驗證

| 工具 | 用途 | 推薦 |
|---|---|---|
| **pypbo** | PBO、Deflated Sharpe、PSR、MinTRL、MinBTL | ★★★★ 唯一現成（小心 AGPL） |
| **mlfinlab (paid)** | Combinatorial Purged CV、PBO、各種 ML for Finance 工具 | ✗ 商業 |
| **mlfinpy** | mlfinlab 社群開源 fork | ★★★ 不完整，待社群成熟 |
| 自己實作 | 照 Bailey & Lopez de Prado 論文，CPCV ≈ 200 行 | ★★★★★ 推薦長期方案 |

### 6.3 Walk-Forward Analysis

**目前 GitHub 上沒有「即用級」獨立 WFA 套件**，多數內嵌於各 BT 框架：
- vectorbt: 透過 `vbt.Splitter` 或自己用 sklearn `TimeSeriesSplit`
- vectorbt PRO: 內建完整 WFA pipeline（明顯優於開源版）
- backtrader: 第三方 `backtrader-walkforward` 但維護差
- TQuant-Lab: 範例倉庫有 WFA notebook 但需自己拼

**建議：自己寫一個 100 行的 `WalkForwardSplitter` class**，依時間窗滑動切 train/test，輸出 OOS 績效。比依賴第三方更可控。

---

## 七、台股 / 中文圈專屬資源

| 資源 | 性質 | 用途 |
|---|---|---|
| **TQuant-Lab (tejtw)** | zipline fork | 完整台股回測框架（綁 TEJ） |
| **zipline-tej** | TQuant-Lab 底層 | 台股交易日曆 + 資料 ingest |
| **pyfolio-tej** | pyfolio fork | 台股版本，配 TQuant-Lab |
| **FinMind** | 資料 API | 50+ 台股 dataset，免費版 300req/hr |
| **Shioaji** | 實盤 API | 永豐金，唯一現代 Python SDK |
| **finlab (商業)** | SaaS 平台 | pip install finlab，台股策略平台，有免費版但功能受限 |
| **finlab_crypto** | finlab 開源副產品 | 加密貨幣，台股部分閉源 |
| **Yvictor/polars_backtest_extension** | 個人專案 | 台灣作者，Polars-based，10 stars 但效能宣稱很強 |
| **Yvictor/polars_ta_extension** | TA-Lib for Polars | 配套技術指標 |
| **chuangtc/shioaji_api, ypochien/Shioaji_Example** | Shioaji 範例 | 入門參考 |
| **tejtw/TEJAPI_Python_Medium_Application** | TEJ + Shioaji 範例 | **包含「TQuant Lab + 永豐 Shioaji」整合 notebook** |
| **akshare** | 中港台美股資料 | 比 FinMind 廣但台股深度不及 |
| **rqalpha** | 中國 A 股骨架 | 架構參考 |
| **vnpy** | 中國實盤平台 | 不適用台股 |
| **hikyuu** | C++/Python A 股 | 不適用台股 |
| **qlib** | 微軟 ML-Quant | 主要中/美股 |

**台股 GitHub 生態的痛點：**
- **官方框架極少**，TQuant-Lab 是少數認真維護的，但綁 TEJ 商業資料
- **沒有「完全免費 + 完整台股交易日曆/微結構模型 + 接 Shioaji」的開源框架**
- 這正是你的 `backtest_platform` 的機會 — 填補這個 gap

---

## 八、最終選型建議

### 三個選項

#### 選項 A：維持原計畫（rqalpha + vectorbt）

**評估：不推薦**

- rqalpha 對你的場景**幾乎全部要重寫**（台股 mod、Shioaji broker mod、漲跌停、零股）
- vectorbt 才是性能的真正貢獻者
- 等於用了 rqalpha 但只用其 5% 功能（事件 loop），重複造輪子

**風險：** rqalpha 的 6.x 版本對舊 mod API 不穩，未來升級可能斷裂

---

#### 選項 B：改用 TQuant-Lab + Shioaji（最快上線）

**評估：適合 prototype / 短期目標**

- **優點：** 4-6 週可上線 paper trading；範例已示範 TEJ + Shioaji 整合
- **缺點：**
  - 綁 TEJ_API_KEY，每月 1500-3000 NTD 起跳
  - Zipline 底層性能可能達不到 100 檔 × 10 年 < 30 分鐘
  - 廠商鎖定（vendor lock-in）
- **適合誰：** 想快速驗證商業模式、不在意資料成本

---

#### 選項 C（強烈推薦）：Hybrid — vectorbt 核心 + 借鑑 TQuant-Lab 微結構

**架構：**

```
┌────────────────────────────────────────────┐
│  backtest_platform (你的程式碼)             │
│  ┌──────────────────────────────────────┐  │
│  │  Strategy Layer                       │  │
│  │  - 你的策略類別                       │  │
│  └──────────────┬───────────────────────┘  │
│                 │                            │
│  ┌──────────────▼───────────────────────┐  │
│  │  Backtest Engine: vectorbt           │  │
│  │  - portfolio simulation              │  │
│  │  - 參數網格、IS/OOS                  │  │
│  └──┬──────────────────────────────┬────┘  │
│     │                              │        │
│  ┌──▼────────┐  ┌────────────────▼──────┐ │
│  │ Data      │  │ Validation             │ │
│  │ FinMind + │  │ - quantstats (報表)    │ │
│  │ TWSE      │  │ - pypbo (PBO/DSR)      │ │
│  │ + 自寫    │  │ - 自寫 WFA splitter    │ │
│  │ Calendar  │  │                        │ │
│  │ (借鑑     │  │                        │ │
│  │ TQuant-   │  │                        │ │
│  │ Lab)      │  │                        │ │
│  └───────────┘  └────────────────────────┘ │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │  Paper / Live Trading                │  │
│  │  - Shioaji 官方 SDK                   │  │
│  │  - 自寫 OrderManager 橋接策略 ←→ broker│ │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**捨棄 rqalpha 的理由：**
1. 沒有現成台股 mod，寫一個的時間 ≈ 寫整個 backtest_platform
2. vectorbt 才是性能保證
3. Shioaji 整合 rqalpha 沒有現成方案，你要自己寫 broker mod
4. 直接用 Shioaji SDK 控制更直接

**保留 vectorbt 的理由：**
1. **唯一能 hit 性能目標的引擎**
2. quantstats 原生整合
3. 參數網格、portfolio simulation 內建
4. 社群大，問題容易查

**借鑑 TQuant-Lab 的點：**
1. **`exchange_calendars` 註冊 XTAI** — 直接 fork 他們的台股日曆定義
2. 漲跌停、零股、配息處理邏輯（看 `zipline-tej` 源碼）
3. Shioaji 接通範例（看 TEJAPI_Python_Medium_Application notebook）

**新增/自寫的部分：**
1. FinMind → vectorbt 資料 adapter (~300 行)
2. WalkForwardSplitter (~100 行)
3. PBO/DSR module（自實作，避開 pypbo 的 AGPL；~200 行）
4. OrderManager: 策略訊號 → Shioaji 下單（~500 行）
5. Paper Trading 模擬器（M4 前用 vectorbt event driven 模擬，M4 後接 Shioaji 模擬環境）

**預估時程：**
- M1 (資料層): 2 週
- M2 (回測引擎 + 報表): 3 週
- M3 (統計驗證 PBO/DSR/WFA): 2 週
- M4 (Paper trading + Shioaji): 3 週
- 緩衝 + 文件: 2 週
- **合計 ~12 週**

---

### Top 3 必裝清單

1. **vectorbt** (open source) — 主引擎
2. **quantstats** — 報表
3. **Shioaji** — 實盤 API

### Top 3 必看 reference

1. **TQuant-Lab** — 台股微結構 reference
2. **tejtw/TEJAPI_Python_Medium_Application** — TQuant + Shioaji 整合範本
3. **pypbo** — PBO/DSR 實作參考（看完自己重寫）

### 一個值得實驗的黑馬

- **Yvictor/polars_backtest_extension** — 台灣作者，Polars-based，宣稱「2000 支股票 17 年 1200 萬列」級別效能。Stars 才 10，但若 vectorbt 的 pandas 路線在你 100 檔 portfolio 上出現瓶頸，這是值得實驗的 Plan B。注意：**PolyForm Noncommercial 授權，商用要洽談**。

---

## 九、被排除的（重要說明）

- **mementum/backtrader** — 雖然 Stars 21.8k 看似最大，但**原作者 2018 後棄維護**，社群 fork 分散且無權威主線，不適合長期專案依賴。
- **vnpy 41.1k stars** — 雖然名氣大，但**完全是中國市場 gateway（CTP/XTP/SimNow）**，無台股支援，且定位為實盤平台非 backtest 平台。
- **freqtrade 50.9k stars** — 純加密貨幣 + CCXT，與台股場景無重疊。

---

## 附錄：搜尋資料來源

主要 GitHub 倉庫：

- [polakowo/vectorbt](https://github.com/polakowo/vectorbt)
- [tejtw/TQuant-Lab](https://github.com/tejtw/TQuant-Lab)
- [tejtw/zipline-tej](https://github.com/tejtw/zipline-tej)
- [tejtw/pyfolio-tej](https://github.com/tejtw/pyfolio-tej)
- [ricequant/rqalpha](https://github.com/ricequant/rqalpha)
- [microsoft/qlib](https://github.com/microsoft/qlib)
- [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader)
- [QuantConnect/Lean](https://github.com/QuantConnect/Lean)
- [stefan-jansen/zipline-reloaded](https://github.com/stefan-jansen/zipline-reloaded)
- [stefan-jansen/empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded)
- [stefan-jansen/pyfolio-reloaded](https://github.com/stefan-jansen/pyfolio-reloaded)
- [kernc/backtesting.py](https://github.com/kernc/backtesting.py)
- [pmorissette/bt](https://github.com/pmorissette/bt)
- [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats)
- [esvhd/pypbo](https://github.com/esvhd/pypbo)
- [FinMind/FinMind](https://github.com/FinMind/FinMind)
- [Sinotrade/Shioaji](https://github.com/Sinotrade/Shioaji)
- [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL)
- [vnpy/vnpy](https://github.com/vnpy/vnpy)
- [fasiondog/hikyuu](https://github.com/fasiondog/hikyuu)
- [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade)
- [jesse-ai/jesse](https://github.com/jesse-ai/jesse)
- [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot)
- [Yvictor/polars_backtest_extension](https://github.com/Yvictor/polars_backtest_extension)
- [hudson-and-thames/mlfinlab](https://github.com/hudson-and-thames/mlfinlab)
- [tejtw/TEJAPI_Python_Medium_Application](https://github.com/tejtw/TEJAPI_Python_Medium_Application)
- [finlab-python](https://github.com/finlab-python)
- [quantstart/qstrader](https://github.com/quantstart/qstrader)
- [mementum/backtrader](https://github.com/mementum/backtrader)
- [scrtlabs/catalyst](https://github.com/scrtlabs/catalyst)
- [quantopian/pyfolio](https://github.com/quantopian/pyfolio)
- [enzoampil/fastquant](https://github.com/enzoampil/fastquant)
- [tensortrade-org/tensortrade](https://github.com/tensortrade-org/tensortrade)
- [skfolio/skfolio](https://github.com/skfolio/skfolio)
- [wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant)
- [wangzhe3224/awesome-systematic-trading](https://github.com/wangzhe3224/awesome-systematic-trading)

---

> **報告完成於 2026-05-31。** 所有 stars 與最後 release 數據基於本日抓取的 GitHub 公開頁面，可能有 1-2 週時間差。最終決策請依實際 POC 測試結果調整。
