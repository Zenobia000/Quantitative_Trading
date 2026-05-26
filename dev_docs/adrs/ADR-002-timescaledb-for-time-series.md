# ADR-002: 採用 TimescaleDB 而非 InfluxDB / Plain Postgres

> **狀態：** 已接受 | **日期：** 2026-05-26 | **決策者：** Self

---

## 1. 背景與問題

- **上下文**：需要儲存 10 年 × 100+ 檔台股的日線 + 法人 + 籌碼資料
- **問題**：選擇支援時間序列查詢的儲存
- **驅動因素 / 約束**：
  - 資料筆數估算：100 stocks × 250 days × 10 years × 3 tables = 750,000 列
  - 需支援高效的 time-range query
  - 需支援 JSONB（trade audit trail 需要存 scores / prices / position 物件）
  - 偏好開源、Docker 友善、SQL 介面

---

## 2. 考量的選項

### 選項一：Plain PostgreSQL
- **描述**：用普通 Postgres 加 B-tree 索引
- **優點**：最熟悉、Docker image 標準
- **缺點**：時間序列查詢沒原生優化、partitioning 需手動
- **成本/複雜度**：低

### 選項二：TimescaleDB
- **描述**：Postgres extension，加 hypertable 自動 partition
- **優點**：與 Postgres 100% 相容（SQL、psycopg2、SQLAlchemy 都能用）、自動時間 partition、高效 time-range query
- **缺點**：需用 timescale docker image（不能用 vanilla Postgres）
- **成本/複雜度**：低

### 選項三：InfluxDB
- **描述**：專用時間序列 DB
- **優點**：時間序列原生
- **缺點**：自己的 query language（Flux）、JSONB 支援弱、與 pandas 整合需 plugin
- **成本/複雜度**：中

### 選項四：DuckDB + Parquet
- **描述**：純 file-based，DuckDB 做查詢
- **優點**：零維護、可移植
- **缺點**：不適合並發寫入、實盤監控需要 DB
- **成本/複雜度**：低

---

## 3. 決策

**選擇：選項二（TimescaleDB） + 選項四（DuckDB/Parquet 作為快取層）**

**理由**：
- TimescaleDB = 「Postgres + 時間序列優化」，學習曲線零
- `daily_bars`、`institutional_flows`、`broker_chips`、`equity_snapshots` 都 `create_hypertable` 自動 partition
- `trades` 與 `data_quality_log` 用 JSONB 存複雜物件
- Parquet 作為 ETL cache（避免重複 call FinMind），DuckDB 作為快速 EDA 工具
- 雙層儲存：parquet（disk cache，cheap）+ TimescaleDB（query, indexes）

---

## 4. 後果

- **正面**：
  - SQL 查詢效能好（time-range scan）
  - 自動 retention policy（可設定 5 年自動 drop）
  - 與 Grafana 內建整合（M5 監控）
- **負面**：
  - 比 plain Postgres 稍微吃資源
  - timescale docker image 比 vanilla postgres 大
- **影響範圍**：`docker-compose.yml`、`docker/timescaledb/init.sql`、`data/db_writer.py`
- **重新評估觸發**：資料量達 10 億列 → 評估是否切到 ClickHouse 或 BigQuery

---

## 5. 執行計畫

1. ✅ M1：docker-compose 加入 timescaledb 服務
2. ✅ M1：init.sql 定義 hypertable + JSONB schema
3. ✅ M1：`db_writer.py` 實作 idempotent upsert
4. M2：定期 backup 腳本（pg_dump → S3 或本地）
5. M5：retention policy（5 年自動 drop）

---

| 日期 | 審核人 | 備註 |
| :--- | :--- | :--- |
| 2026-05-26 | Self | 初版 |
