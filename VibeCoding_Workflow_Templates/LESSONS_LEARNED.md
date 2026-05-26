# VibeCoding 模板實戰教訓

> **建立日期：** 2026-05-26
> **來源：** backtest_platform 專案套用模板後的蘇格拉底審查
> **目的**：把套用過程中暴露的模板盲點記錄下來，避免下個專案重蹈覆轍

---

## 教訓 1：C4 與業務分層撞名是高頻地雷

### 情境
backtest_platform 的策略本身有「四層共振戰法」，計分系統用 L1（結構）/ L2（法人）/ L3（籌碼）/ L4（動能）。套 C4 模板後寫文件馬上撞名 — 讀者分不清「C4 的 L2」與「策略的 L2」。

### 教訓
任何專案啟動架構文件前，**強制**填一張命名防呆表，明確區分：
- C4 L1–L4（架構縮放）
- 業務 / DDD layer
- Clean Architecture layer

模板已加入：`05_architecture_and_design_document.md` §1.1.0

### 規則
**業務術語撞 C4 命名 → 強制加前綴**（如 `v2 L1` vs `C4 L1`，C4 章節改用全稱 `System Context`、`Container`）。

---

## 教訓 2：L2 把 Python 檔當 Container

### 情境
初版 backtest_platform 的 L2 圖把 `scoring.py`、`signals.py`、`pipeline.py` 都畫成 Container，導致 L2 圖變成「程式碼依賴圖」，沒有任何 runtime 意義。

### 教訓
**Container = 可獨立部署 / 執行的 runtime 單位**：
- Python process（CLI / API server / worker）
- DB instance
- 檔案儲存
- 容器 / 排程服務

不是：module、package、function、class、layer name。

### 規則（已加進模板）
L2 範例只能含：Process、DB、檔案儲存、排程服務、UI。明確列出禁止項。

---

## 教訓 3：L3 跨 Container 是違規

### 情境
初版 backtest_platform 的「元件圖」混了 Application module + DB table + 外部 FinMind，變成 component-level 的「資料流圖」。

### 教訓
**鐵律：一張 L3 圖對應且僅對應一個 L2 Container**。

要呈現跨 Container 互動 → 用 **Sequence Diagram**，不是 L3。

### 規則
- L3 圖標題必含父 Container 名（如 `L3-A — Component (zoom: Application)`）
- 跨 Container 的元素只能以「邊界節點」出現，不能畫進內部 subgraph
- DB 內部 table 改去 §4.1 ER，不在 L3 重複

---

## 教訓 4：Partial Disclosure 是最常見的隱形 bug

### 情境
backtest_platform 的 L1 / L2 只畫了「主流程」會用到的外部系統。後續審查發現缺：
- Telegram bot（告警通道，M4+）
- GCS / S3（備份，M5）
- GCP Compute Engine（託管，M5）
- TWSE 公開資訊（下市股 backup）

這些都在其他文件（13 安全、14 部署、16 WBS）有提到，**唯獨 05 架構文件沒畫** → 看 05 的人會誤以為系統就只有那些。

### 教訓
05 是架構契約 — **任何模組在 05 沒出現 = 不存在**。其他文件提到但 05 沒提 → **05 有 bug**。

### 規則
模板已加：「L1 含**所有**外部系統（資料源、交易、推送、備份、雲端 IaaS 五類）」明列五大類，缺一就視為 partial disclosure。

---

## 教訓 5：DDD 限界上下文圖箭頭常畫成 data flow

### 情境
初版的「限界上下文圖」箭頭是 `資料 → 策略 → 回測 → 驗證 → 監控`，看起來像 data flow 不像 strategic relationship。

### 教訓
DDD Context Map 的箭頭應該是 **Strategic Relationship**：
- **CS** (Customer-Supplier)
- **ACL** (Anti-Corruption Layer)
- **SK** (Shared Kernel)
- **CF** (Conformist)
- **PL** (Published Language)
- **OHS** (Open Host Service)

### 規則
模板已加 Strategic Relationship 縮寫表 + 範例圖（箭頭強制標 PL / CS / ACL 等）。

---

## 教訓 6：DDD 戰術設計常被忽略

### 情境
初版只畫了 DDD 戰略（限界上下文），完全沒提戰術元素。但 code 裡明明有：
- Value Object：`StrategyConfig`
- Aggregate Root：`ETLBundle`
- Domain Service：`compute_scores`、`evaluate_bar`
- ACL：`_normalize_*` 函式

讀者看不出 code 與 DDD 概念的對應。

### 教訓
DDD 戰略 + 戰術**都要揭露**：
- 戰略：限界上下文 + Context Map
- 戰術：Entity / Value Object / Aggregate / Domain Service / Domain Event / Repository / ACL / Specification

### 規則
模板已加 §1.2.5 DDD 戰術設計表（必填）。若某類缺席（例如沒有 Entity），**明確說明為什麼**。

---

## 教訓 7：缺 Sequence Diagram

### 情境
初版的「關鍵使用者旅程」是純文字步驟：
```
1. User → CLI
2. → fetch_bundle
3. → write_parquet
4. → compute_scores
...
```

無法呈現：
- 平行 vs 序列
- 同步 vs 非同步
- 失敗分支
- 跨多 Container 的協作時序

### 教訓
**跨多 Container 的主要 use case 必須用 sequenceDiagram**，不是純文字。

### 規則
模板已加 §3.4 強制要求 mermaid sequenceDiagram + 範本，含 actor、participant、protocol 標籤、`alt` 失敗分支。

---

## 教訓 8：Deployment Diagram 不能等於 L2

### 情境
初版 §5.1 部署視圖只是把 L2 圖換個 layout 重畫，沒任何 Node 屬性。

### 教訓
**Deployment Diagram = L2 的物理實體化**：
- 每個 logical Container instantiate 到具體 Deployment Node（PC / VM / Container Engine）
- 標 Node 屬性（OS、規格、scaling）
- 標 instance（含版本、port）
- 跨 Node 連線標 protocol + port

### 規則
模板已加 §5.1.1 / 5.1.2 結構：分當前環境 + 目標環境兩張圖，含 Node 屬性表。

---

## 教訓 9：箭頭無 protocol 標籤

### 情境
初版 L2 / 部署圖很多箭頭只是裸線，看不出是 HTTPS / SQL / file I/O / in-proc。

### 教訓
**所有跨 Container / 跨 Node 箭頭都要標 protocol + 動詞 + 目的**。例如：
- `HTTPS pulls daily bars`
- `libpq / TCP :5432 reads`
- `file I/O writes parquet`
- `in-proc call`
- `WebSocket TLS submit order`

### 規則
模板已在所有圖的範例加 protocol 標籤示範。

---

## 教訓 10：跨文件不一致

### 情境
- 08 結構文件列了 `live/paper_trader.py`、`live/shioaji_executor.py`
- 09 依賴文件列了 `live/` 在 Application 層
- 14 部署文件提到 Telegram bot、GCS backup
- **但 05 架構文件全部沒畫**

→ 文件互相打臉。

### 教訓
05 是上游契約，下游文件（07/08/09/10/14）的所有元素都必須能在 05 找到對應。

### 規則
模板已加附錄「跨文件一致性檢查表」：
- 新增 Container → 08 / 09 / 14 必同步
- 新增 module → 07 / 08 / 09 / 10 必同步
- 新增外部系統 → 06 / 13 / 14 必同步
- 變更 protocol → 06 / 13 / 14 必同步
- 變更 DDD 限界上下文 → 02 / 07 必同步

**鐵律**：05 是架構契約 — **任何下游有、05 沒有 → 05 有 bug**。

---

## 教訓 11：Future State 沒有獨立圖

### 情境
初版 L2 用虛線標 M4+/M5，但沒有獨立的 future state 圖。看 L2 圖時，虛線太多反而看不清「全部上線時長怎樣」。

### 教訓
**任何有明顯 milestone 的專案（v1/v2/M5）必須有一張獨立 future state 圖**，全部實線呈現完整視野。

### 規則
模板已加 §1.1.2.5 Future State 必填段落。

---

## 教訓 12：每個 L2 Container 應該都有 L3

### 情境
初版只畫了 Application 的 L3，TimescaleDB / Parquet / Prefect / Grafana 都沒有對應 L3。

### 教訓
**每個 L2 Container 都應有 L3**，**或在 Container 表明確說明跳過理由**。常見可略：
- 純檔案儲存 → 無 internal component
- 第三方服務（Grafana / Telegram bot）→ 依賴第三方規範

### 規則
模板已在 §1.1.2 Container 表加「L3 圖」欄位，必填狀態（✅ / 表代圖 / 略，附理由）。

---

## 應用本教訓的清單

下個專案套 VibeCoding 模板時，PR 必過以下檢核（已整合進 `05_architecture_and_design_document.md` §1.1.3 Checklist）：

```
□ 命名防呆表已填（C4 vs 業務 vs Clean Arch）
□ L1 含五大類外部系統（資料源、交易、推送、備份、雲端 IaaS）
□ L2 含所有規劃 Container（虛線標 milestone）
□ Future State 獨立圖已畫
□ 每個 L2 Container 都有 L3（或明說跳過理由）
□ Sequence Diagram 至少一張（跨多 Container use case）
□ Deployment Diagram 含 Node 屬性
□ 所有箭頭標 protocol
□ DDD 戰略圖箭頭標 Strategic Relationship
□ DDD 戰術設計表已填
□ 跨文件一致性檢查表已過
```

---

---

## v3.0 新增的現代架構維度（2026-05-26）

v2.0 補了 C4 嚴格 + DDD 雙層 + 跨檔一致性，但仍缺**現代架構文件的「可驗證 / 可演進 / 組織映射」三維度**。v3.0 補齊：

### 教訓 13：NFR 寫成「P95 < 200ms」太抽象

**情境**：v2.0 的非功能需求表只有「性能 P95 < 200ms」這種一行陳述，無法測也無法 review。

**教訓**：用 **QAS (Quality Attribute Scenario)** 格式 — Source / Stimulus / Artifact / Environment / Response / Measure 六欄。

**規則**（已加進模板 §2.3）：至少覆蓋 Performance + Availability + Security 三類 QAS。

### 教訓 14：架構規則只在文字，不會被執行

**情境**：「Domain 不可 import Infrastructure」「測試覆蓋 > 80%」這種規則寫文字 → 靠人工 review → 會漏。

**教訓**：應變成 **Architecture Fitness Function** = code（`import-linter` / `pytest-cov` / `ruff`） → CI gate。

**規則**（已加進模板 §9）：每個架構規則都有對應 fitness function；PR 過全綠 = 規則沒違反。

### 教訓 15：缺 Resilience Patterns 專節

**情境**：v2.0 提到 Telegram alert / 自動 retry 但散落在 6.1 / 14_deployment，沒有對每個外部依賴明確列 pattern。

**教訓**：每個外部依賴與跨服務呼叫**必須**明列套用的 resilience pattern（Timeout / Retry / Circuit Breaker / Bulkhead / Fallback / Idempotency Key / Rate Limit）。

**規則**（已加進模板 §3.5）：失敗模式表 + Pattern 速查表。

### 教訓 16：忘記寫「不做什麼」（Anti-Decisions）

**情境**：團隊每隔幾月就有人問「為什麼不用微服務 / GraphQL / K8s」，每次都得重新解釋。

**教訓**：**Anti-Decisions** 必須明確記錄，含「重新評估觸發」（否則就是「永遠不做」）。

**規則**（已加進模板 §3.7）：必填表格 — 決策 / 為何拒絕 / 重新評估觸發。

### 教訓 17：安全段只有 checklist 沒有 Threat Model

**情境**：v2.0 的 6.2 安全只列「TLS 1.3+, JWT」，沒系統性威脅分析。

**教訓**：對每個 L2 Container 跑 **STRIDE**（Spoofing / Tampering / Repudiation / Info disclosure / DoS / Elevation of privilege）。

**規則**（已加進模板 §6.2.1）：必填 STRIDE 矩陣。

### 教訓 18：Observability 只列工具，沒方法論

**情境**：v2.0 列了「Loguru、Prometheus、Jaeger」但沒說怎麼用。

**教訓**：採 **3 Pillars (Logs / Metrics / Traces) + Correlation ID + RED Method (服務) + USE Method (資源) + 告警分級**。

**規則**（已加進模板 §6.1）：完整 framework。

### 教訓 19：架構與團隊邊界沒對齊

**情境**：Conway's Law — 「組織通訊結構決定系統架構」。團隊邊界與 Container 邊界錯位 → 高溝通成本 → 隱形 bug。

**教訓**：必須有 **Team Topology** 映射（Stream-Aligned / Enabling / Complicated-Subsystem / Platform 四類）。

**規則**（已加進模板 §7.3）：團隊類型 + 互動模式 + 與 C4 Container 對應。

### 教訓 20：缺 Migration Path（從當前 → 目標）

**情境**：v2.0 有 Future State 圖，但沒有「怎麼走過去」的步驟。

**教訓**：**Migration Path** 必填，含步驟 / 觸發條件 / 風險 / rollback plan。

**規則**（已加進模板 §7.4）：演進步驟表。

### 教訓 21：Cross-Cutting Concerns 散落

**情境**：logging / auth / cache / rate limit / tracing 等散在多個段落，沒專節。

**教訓**：**Cross-Cutting Concerns** 必填專節，列「關注點 → 實作位置 → 工具」。

**規則**（已加進模板 §3.6）。

### 教訓 22：Data Architecture 只有 ER + 一致性

**情境**：v2.0 缺現代資料概念（CDC / Event Streaming / OLTP-OLAP 分離 / 保留策略）。

**教訓**：加 **Data Lifecycle** 章節（流向機制 + OLTP/OLAP 分離 + 保留策略）。

**規則**（已加進模板 §4.4）。

### 教訓 23：成本與架構決策脫鉤

**情境**：成本只是個總數，沒連到具體架構選擇。

**教訓**：**Cost-Architecture Linking**（每個決策的月成本 + 替代方案的成本差）+ **Capacity Planning**（當前 / 預估 / 升級閾值）。

**規則**（已加進模板 §5.3）。

### 教訓 24：缺 ASRs（Architecturally Significant Requirements）

**情境**：所有 FR / NFR 平等對待，但其實只有幾個會「逼架構長這樣」。

**教訓**：**ASRs** 必填 — 標出驅動架構決策的關鍵需求，連結到 ADR。

**規則**（已加進模板 §2.1）。

### 教訓 25：Tech Selection 沒 lifecycle

**情境**：技術選型表只列「選什麼 + 為什麼」，沒標生命週期狀態。

**教訓**：標 **Tech Radar lifecycle**（Adopt / Trial / Assess / Hold）。

**規則**（已加進模板 §1.4）。

### 教訓 26：只用 Mermaid，複雜圖難看

**情境**：複雜 C4 圖在 Mermaid 很醜，但模板沒提替代工具。

**教訓**：明列 Diagram-as-Code 工具選型（Mermaid / Structurizr DSL / PlantUML / drawio / d2）。

**規則**（已加進模板 §10）。

---

## 更新後的 PR Checklist（19 條，v3.0）

```
# C4 結構（5）
□ L1–L3 各至少一張圖
□ L3 對應且僅對應一個 L2 Container
□ 每個 L2 Container 有對應 L3（或明說跳過）
□ 至少一張 Sequence Diagram
□ Deployment 含 Node 屬性

# 完整性（4）
□ L1 含五大類外部系統
□ L2 含所有規劃 Container
□ 有獨立 Future State 圖
□ §1.1.2 Container 表與圖雙向核對

# 命名 / DDD（3）
□ C4 與業務層級無命名混用
□ DDD 限界上下文圖箭頭採 Strategic Relationship
□ DDD 戰術元素表已填

# 現代架構（5，v3.0 新增）
□ ASRs 已列且連結 ADR
□ QAS 至少覆蓋 Performance + Availability + Security
□ 每個外部依賴有對應 Resilience Pattern
□ Anti-Decisions 有「重新評估觸發」
□ Fitness Functions 至少含依賴方向 + 覆蓋率

# 跨文件 / 演進（2）
□ 異動已對照附錄 A 同步檢查
□ Migration Path 含 rollback plan
```

---

## 後續維護

本檔每次套模板做新專案、發現新地雷時應更新：
1. 新增「教訓 N」段落
2. 對應到模板的修改點
3. 更新「應用本教訓的清單」
