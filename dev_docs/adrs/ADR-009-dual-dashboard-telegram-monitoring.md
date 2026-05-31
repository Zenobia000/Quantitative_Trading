# ADR-009: 雙儀表板 + Telegram 告警（L7 監控架構）

> **狀態：** 已接受（部分被取代） | **日期：** 2026-05-31 | **決策者：** Self
> **Superseded（部分）：** § 3「Telegram 告警等級」段落與 § 5 步驟 6 之「Telegram bot」
> 已由 [ADR-010](./ADR-010-discord-alerter-supersedes-telegram.md) 取代為 Discord bot；
> 雙儀表板（Streamlit + Grafana）決策維持有效。
> **Related：** ADR-002（TimescaleDB 時序儲存）、ADR-010（Discord 告警通道）

---

## 1. 背景與問題

- **上下文**：使用者明確要求「監控績效儀表板」是首版必要交付物（plan § 0），L7 監控層在 7 層 reference 中對應「Monitor & Attribution」。
- **問題**：
  - 「策略績效」與「系統健康」是兩種完全不同性質的資訊（事件式快照 vs 時序流式），單一 dashboard 強塞會兩邊都做不好
  - 純被動 dashboard 無法處理夜間 / 盤中異常（人不會盯著螢幕）
  - 既有 `docker-compose.yml` 已配置 Grafana 容器，需對齊善用
- **驅動因素 / 約束**：
  - 策略績效需高互動（過濾、下鑽、自訂期間）
  - 系統健康需高刷新頻率、時序聚合、跨指標告警
  - 異常須主動推播（不能依賴使用者主動查看）
  - 受眾僅一人（單人開發），但同一人在不同情境用不同 device
  - 與 TimescaleDB（ADR-002）儲存層整合

---

## 2. 考量的選項

### 選項一：單一 Streamlit dashboard 塞所有面板
- **描述**：策略績效 + 系統健康 + 告警全部塞進 Streamlit
- **優點**：單一技術棧、開發簡單
- **缺點**：
  - Streamlit 不適合高頻時序刷新（每秒 metrics 不可行）
  - Prometheus / 系統指標生態無法善用
  - 無主動告警能力（必須開瀏覽器才看得到）
  - 既有 `docker-compose.yml` Grafana 容器閒置浪費
- **成本/複雜度**：中（但能力嚴重不足）

### 選項二：單一 Grafana 處理所有面板
- **描述**：策略績效也走 Grafana
- **優點**：時序處理強、原生 alerting
- **缺點**：
  - Grafana 對「事件式快照」（如今日訊號、持倉表）展示能力弱
  - 互動式探索（下鑽、自訂期間 backtest）需另寫 plugin
  - 策略 PM 視角的「績效歸因」面板 Grafana 不擅長
- **成本/複雜度**：中（但體驗不佳）

### 選項三：雙儀表板分層 + Telegram 主動告警 ★採納
- **描述**：分三層，技術棧依資料性質與刷新節奏分工
  - **Streamlit**（策略績效，事件式快照，5 面板 A-E）
  - **Grafana + Prometheus**（系統健康，時序流式，4 面板 F-I）
  - **Telegram bot**（主動告警，3 等級 Critical / High / Info）
- **優點**：
  - 技術棧匹配資料性質
  - 與既有 `docker-compose.yml` Grafana 容器對齊
  - 主動告警補足被動 dashboard 盲點
  - 業界標準分層（觀察類 / 監控類 / 告警類）
- **缺點**：
  - 三套技術棧需要維護
  - 跨棧資料一致性需注意（共用 TimescaleDB 為單一真相）
- **成本/複雜度**：中

### 選項四：付費 SaaS（Datadog / New Relic）
- **描述**：用商用 APM 工具
- **優點**：開箱即用
- **缺點**：
  - 月費高（超出 plan 整體預算）
  - 策略績效歸因仍需自寫
  - 引入外部依賴
- **成本/複雜度**：低開發 / 高運營成本

---

## 3. 決策

**選擇：選項三（雙儀表板分層 + Telegram 主動告警）**

**理由**：
- 「策略績效」與「系統健康」是兩種不同性質資訊，分層才能各取所長
- 業界標準做法（López de Prado《Advances in Financial ML》第 22 章 Production Monitoring + SRE Golden Signals）
- Streamlit 5 面板（A 績效總覽 / B 部位狀態 / C 訊號日誌 / D 風控指標 / E 統計驗證）對應策略 PM 視角
- Grafana 4 面板（F ETL 健康 / G API quota / H 排程作業 / I 系統資源）對應 SRE 視角
- Telegram 3 等級告警補足「不在螢幕前」的盲點
- 與既有 `docker-compose.yml` Grafana 容器對齊，不浪費既有 infra
- 詳見 plan `C:\Users\xdxd2\.claude\plans\maintain-calm-blossom.md` § 4

### 三層職責對照

| 層 | 工具 | 資料節奏 | 受眾情境 | 面板 |
|:--|:--|:--|:--|:--|
| 1 | Streamlit | 事件式快照（分鐘） | 桌機，主動探索 | A 績效總覽 / B 部位狀態 / C 訊號日誌 / D 風控 / E 統計驗證 |
| 2 | Grafana + Prometheus | 時序流式（秒） | 桌機，被動監看 | F ETL / G API quota / H 排程 / I 資源 |
| 3 | Telegram bot | 事件觸發（即時） | 手機，主動推播 | Critical / High / Info |

### Telegram 告警等級

| 等級 | 觸發條件 |
|:--|:--|
| Critical | 實盤下單失敗、Shioaji 斷線、熔斷觸發 |
| High | ETL 失敗、訊號缺漏、部位偏離 > 5%、FinLab 流量剩餘 < 500MB |
| Info | 每日收盤後績效摘要、buy/sell 訊號 |

---

## 4. 後果

- **正面**：
  - 三層技術棧各司其職，無功能勉強
  - 與既有 `docker-compose.yml` Grafana 容器對齊
  - 主動告警讓系統可在無人值守時穩定運行（M4 paper 3 個月、M5 live 必要條件）
  - 與 TimescaleDB（ADR-002）單一真相對接，無資料重複
- **負面**：
  - 三套技術棧（Streamlit + Grafana + Prometheus + Telegram bot）維護
  - 告警規則需持續調校避免「告警疲勞」
  - 三層 UI / UX 風格不一致（可接受，受眾僅一人）
- **影響範圍**：
  - `dashboard/streamlit_app.py`（新增 ~400 LOC，5 面板 A-E）
  - `dashboard/grafana_dashboards.json`（新增 ~200 LOC，4 面板 F-I）
  - `dashboard/db_schema.sql`（新增 ~150 LOC，TimescaleDB tables: equity_snapshots / positions / signals / fills / risk_metrics / validation_runs）
  - `monitoring/metrics_emitter.py`（新增 ~80 LOC，Zipline Algorithm hook 寫 metrics）
  - `monitoring/alerter.py`（新增 ~100 LOC，Telegram bot + 規則引擎）
  - `docker-compose.yml`（補 Prometheus 容器、確認 Grafana data source）
- **重新評估觸發**：
  - Telegram 告警 1 週內超過 50 條 → 觸發「告警疲勞」審查，調整閾值
  - Streamlit 面板載入時間 > 5 秒（驗收門檻 2 秒）→ 評估換 Dash / Panel
  - Grafana / Prometheus 維運成本超出單人負擔 → 評估降級為 Loki + 簡化告警
  - Telegram API 停服 / 政策變更 → 切 Discord / LINE Notify

---

## 5. 執行計畫

1. **Sprint 0（W1）**：S6（Streamlit 連 TimescaleDB 渲染 equity curve < 2 秒）spike 必須綠
2. **M3 W2**：`dashboard/db_schema.sql` TimescaleDB tables 建立
3. **M3 W3**：`dashboard/streamlit_app.py` 面板 A（績效總覽）+ B（部位狀態）+ C（訊號日誌）上線
4. **M4 W1**：`monitoring/metrics_emitter.py` 接 Zipline Algorithm hook，Prometheus exporter 暴露 metrics
5. **M4 W2**：`dashboard/grafana_dashboards.json` 4 面板 F+G+H+I 上線
6. **M4 W3**：`monitoring/alerter.py` Telegram bot + 3 等級規則引擎上線
7. **M4 W4**：三層聯動測試（手動觸發 ETL 失敗 → Grafana 紅燈 + Telegram High 推播）
8. **M5 W3**：`dashboard/streamlit_app.py` 補面板 D（風控）+ E（統計驗證）
9. **持續**：每 milestone 結束盤點告警頻率，避免疲勞

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-31 | Self | 初版 |
