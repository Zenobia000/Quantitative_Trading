# ADR-011: M2 目錄結構與模組邊界

> **狀態：** 已接受 | **日期：** 2026-05-31 | **決策者：** Self
> **追溯實作：** commit `ae869f5` (refactor structure)
> **關聯：** ADR-005~008（路線決策）、ADR-009（監控）、`08_project_structure_guide.md` v1.1

---

## 1. 背景與問題

- **上下文**：M1 目錄結構（`strategy/`、`engines/`、`validation/`、`live/` 規劃但未建）是 v1.0 規劃時為單策略 + rqalpha 設計，無法承載 ADR-005~009 帶入的多新元件
- **問題**：ADR-005~009 引入大量新模組（TQuant-Lab 主骨架、FinLab/FinMind/Shioaji adapters、雙引擎、三模式 broker、Streamlit/Grafana/Discord 監控），若塞進 M1 平面目錄會破壞單一職責與依賴方向；但 ADR-005~009 本身**只決策「用什麼」**，沒明確決策「目錄怎麼切」
- **驅動因素 / 約束**：
  - 必須支援多策略並存（ADR-008 隱含）
  - 必須隔離廠商鎖定點（每個 adapter 獨立檔，可替換）
  - 必須符合 Clean Architecture 依賴方向（Domain 不依賴 Infrastructure）
  - 須能讓 `data/` (M1 既有) 與新 `adapters/` 共存而不衝突
  - 改動量最小化（M1 既有 962 LOC 不重寫）

---

## 2. 考量的選項

### 選項一：扁平加新目錄（最小改動）

`strategy/` + 新增 `engines/`、`live/`、`monitor/`、`ui/` 直接掛 backtest_platform/ 下。

- **描述**：保留 `strategy/` 不改名，新需求各加一個頂層目錄
- **優點**：M1 既有 imports 完全不動
- **缺點**：
  - `strategy/` 命名暗示單策略（多策略時混亂）
  - 廠商接口（FinLab/FinMind/Shioaji）散在 `data/` 與 `live/` 兩處
  - `monitor/` 與 `ui/` 兩個顆粒度太細
- **成本/複雜度**：低（但長期負擔大）

### 選項二：按角色分層（Clean Architecture 嚴格）

`domain/`、`application/`、`infrastructure/`、`presentation/` 四大頂層 + 子模組依職責歸位。

- **描述**：完全照 Clean Architecture 教科書切
- **優點**：依賴方向清晰、入門新人容易理解
- **缺點**：
  - 一個策略相關檔散三層（`domain/strategy.py` + `application/strategy_service.py` + ...），瀏覽辛苦
  - 過度抽象，單人專案養不起
  - 與 M1 既有 `data/` `strategy/` 既有命名衝突大
- **成本/複雜度**：高

### 選項三：按功能分組 + namespace 預留（採納）

`strategies/<strategy_name>/`（複數 + 子目錄）+ `adapters/<vendor_type>/` + `orchestration/` + `monitoring/` + `dashboard/` 並列。

- **描述**：
  - `strategies/four_layer_resonance/` — 多策略 namespace，每策略獨立子目錄
  - `adapters/{data_bundle,data_feed,brokers}/` — 廠商接口三大類分組
  - `monitoring/`（metric emitter + alerter）與 `dashboard/`（UI 渲染）分離 — 不同生命週期
  - `orchestration/`（cli + daily_flow）與 `pipeline.py` 共存 — pipeline 作 backward-compat shim
  - 既有 `data/`、`config/`、`engines/`、`validation/` 保留
- **優點**：
  - M1 既有檔 0 重寫（只搬路徑改 import）
  - 多策略未來擴充零阻力（新增 `strategies/new_strategy/` 即可）
  - 廠商鎖定隔離在 adapter 層，core 不感知
  - `monitoring/` vs `dashboard/` 對應 ADR-009 三層告警設計
- **缺點**：
  - 比扁平多 2-3 個目錄層級
  - 部分人會覺得 `adapters/data_bundle/` 路徑長
- **成本/複雜度**：中（一次性 migration ~30 分鐘）

### 選項四：等需要時再拆

維持 M1 結構，M3-M5 各 milestone 各自決定。

- **缺點**：每個 milestone 都重做選型決策、imports 反覆改、永遠堆技術債
- **成本/複雜度**：低眼前、高長期

---

## 3. 決策

**選擇：選項三（按功能分組 + namespace 預留）**

**理由**：
- ADR-005~009 同時引入 6+ 新模組，必須一次定義邊界，否則散落寫死
- 多策略 namespace 是 ADR-008（tri-mode shared strategy code）的隱含前提
- adapter 分組對應 ADR-006（FinLab/FinMind 共存）與 ADR-008（broker 三模式切換）
- M1 既有 962 LOC 不重寫是強約束 → 排除選項二
- 與 plan v1.0 (17 §5) 規劃結構 100% 對齊

---

## 4. 後果

### 正面

- **多策略零阻力**：新增策略 = 複製 `strategies/four_layer_resonance/` 為 `strategies/<new>/`，registry 加一行
- **廠商可替換**：FinLab 倒/漲價 → 改 `adapters/data_bundle/finlab_bundle.py` 為 finmind_bundle 1 行設定
- **依賴方向強制**：`strategies/` 不能 import `adapters/`，由 Pyright + code review 把關
- **與 plan 對齊**：plan v1.0 §5 規劃可直接執行，無 surprise
- **既有測試 0 影響**：44 個 M1 unit test 重組後仍全綠（驗證見 commit `ae869f5`）

### 負面

- **路徑變長**：`backtest_platform.strategies.four_layer_resonance.scoring` vs 原 `backtest_platform.strategy.scoring`（多 25 字元）
- **intra-package 須改 relative import**：`strategies/four_layer_resonance/scoring.py` 內 import indicator 須用 `from .indicators import ...` 而非絕對路徑
- **新人需理解 5 個並列目錄職責**（strategies / adapters / engines / validation / orchestration / monitoring / dashboard）

### 影響範圍

- **程式碼**：`src/backtest_platform/` 全層、`tests/` 同步改名
- **文檔**：08 v1.1（結構樹）、09 v1.1（依賴 banner）、06 v1.1（import 範例）
- **未來 PR 規範**：新增模組必須先決定屬哪一層；跨層 import 違反方向 → review 駁回

### 重新評估觸發

- 新增策略時，若發現 `strategies/<name>/` 內又要分子目錄 → 表示策略本體太複雜，考慮重切
- `adapters/` 內某子分類（如 `data_bundle/`）若只有 1 個檔超過半年 → 考慮提升為頂層 adapter
- 任何 PR 試圖加新頂層目錄 → 必須新 ADR

---

## 5. 執行計畫

實作已於 commit `ae869f5` 完成（2026-05-31）：

1. ✅ `mkdir strategies/four_layer_resonance/`，`git mv strategy/*` 進入
2. ✅ `mkdir adapters/{data_bundle,data_feed,brokers}/` + 各自 `__init__.py`
3. ✅ `mkdir orchestration/ monitoring/ dashboard/` + `__init__.py`
4. ✅ 改 10 處 imports（pipeline.py / spike / tests / intra-package）
5. ✅ intra-package 改用 relative imports
6. ✅ `tests/strategy/` → `tests/strategies/four_layer_resonance/` 同步
7. ✅ 驗證：13 個 module importlib 全 OK、44 unit tests 全綠
8. ✅ 文檔同步：08 v1.1、09 v1.1 banner、06 §4.6/4.7（commit `466eda1`）

---

## 6. 模組邊界詳細規則

### 6.1 目錄職責

| 目錄 | 職責 | 可被 import | 不可 import |
|:--|:--|:--|:--|
| `config/` | Pydantic 純資料 | 所有人 | 任何模組 |
| `data/` | M1 FinMind ETL（fallback adapter）| `adapters/data_bundle/finmind_bundle.py` | `strategies/`、`adapters/`（避循環） |
| `strategies/<name>/` | Domain 純函式 | `engines/`、`adapters/brokers/`、`orchestration/` | `data/`、`adapters/`、`monitoring/`、`dashboard/` |
| `adapters/data_bundle/` | Zipline bundle ingester | `engines/`、`orchestration/` | `adapters/brokers/`（不跨類）|
| `adapters/data_feed/` | 即時資料 polling | `adapters/brokers/`、`orchestration/` | 同上 |
| `adapters/brokers/` | 下單接口 | `orchestration/` | 同上 |
| `engines/` | vectorbt 副引擎 wrapper | `orchestration/`、`validation/` | `adapters/brokers/` |
| `validation/` | 統計驗證（PBO/DSR/WFA）| `orchestration/`、`dashboard/` | 業務模組 |
| `orchestration/` | CLI + 排程編排 | （頂層，無人 import）| — |
| `monitoring/` | Metric emitter + alerter | （側邊掛接，被 Algorithm hook 呼叫）| 業務模組 |
| `dashboard/` | UI 渲染 | （頂層，獨立 process）| 業務模組 |

### 6.2 命名規則

- `strategies/<strategy_name>/` — snake_case，與策略 v2.md 對齊
- `adapters/<vendor_type>/<vendor_name>_<role>.py` — 例 `finlab_bundle.py`、`shioaji_broker.py`
- `monitoring/<emitter|alerter|...>.py` — 動詞或角色
- `dashboard/<framework>_<role>.py` — 例 `streamlit_app.py`、`grafana_dashboards.json`

### 6.3 Adapter 三類劃分理由

| 類別 | 啟用 M | 為何獨立 |
|:--|:---:|:--|
| `data_bundle/` | M2 | 一次性歷史回填（Zipline bundle ingest）；無狀態 |
| `data_feed/` | M4 | 即時資料 polling；長連線 + 狀態管理 |
| `brokers/` | M4-M5 | 下單接口；OMS 狀態機 + 安全規則 |

三者生命週期不同，混在一起會違反單一職責。

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-31 | Self | 初版；追溯 commit `ae869f5` 已實作 |
