# 安全與生產準備檢查清單 — backtest_platform

> **版本：** v1.0 | **更新：** 2026-05-26 | **審查：** Self
> **適用範圍：** M1 已過、M5 實盤前必過

---

## A. 核心安全原則

- [x] **最小權限**：FinMind token 只給 ETL 用、Shioaji token 只給 live 用，互不共用
- [x] **縱深防禦**：.env + .gitignore + 程式內 fail-fast 三層
- [x] **預設安全**：DB 預設 password = `change_me_in_production`，看到字串就會 trigger 改密碼
- [x] **攻擊面最小化**：M1–M3 不開 HTTP port（純本機）；M5 才暴露 API

---

## B. 資料安全與隱私

### 資料分類

| 類別 | 範例 | 處理 |
| :--- | :--- | :--- |
| 公開（市場資料） | 股價、法人籌碼 | 不需加密、可寫 disk |
| 個人（API token） | FINMIND_TOKEN、SHIOAJI_API_SECRET | env 變數，不入 git，不入 log |
| Audit（交易紀錄） | trades 表 | 永久保留，不可改寫 |

### 資料收集

- [x] 只收集策略需要的資料（不抓不必要的 indicators）
- [x] 無使用者 PII 收集（單人專案，不適用）

### 傳輸安全

- [x] FinMind API 使用 HTTPS（套件強制）
- [x] TimescaleDB 本機連線（local socket / 127.0.0.1）
- [ ] Shioaji 強制 TLS（M5 須驗證）

### 儲存安全

- [x] secrets 從 env 載入，不寫入檔案
- [x] DB 預設 password 故意設為 `change_me_in_production`，部署時必改
- [ ] M5 backup 加密（待規劃）

### 資料生命週期

- [x] log 不印 token（grep "TOKEN" + "SECRET" 確認）
- [ ] 資料保留期：daily_bars / institutional / broker_chips 永久保留
- [ ] equity_snapshots：M5 上線後保留 3 年
- [ ] data_quality_log：保留 1 年
- [ ] M5 引入 retention policy（TimescaleDB 內建支援）

---

## C. 應用程式安全

### 認證

- [ ] M5 HTTP API 加 token-based auth
- [ ] Shioaji 帳號 password 使用環境變數
- [ ] M5 開啟 IP 白名單（只允許自己 IP）

### 授權

- 不適用（單人專案、單一角色）

### 輸入驗證

- [x] CLI 參數透過 Click 型別驗證
- [x] FinMind 回應透過 Pydantic schema 驗證
- [x] DB 寫入透過 `_upsert_frame` 檢查 columns
- [x] `StrategyConfig` Field 驗證所有參數範圍

### API 安全（M5）

- [ ] FastAPI endpoints 全部需認證
- [ ] Rate limit（防止意外 DoS 自己）
- [ ] 參數白名單嚴格驗證
- [ ] 回應不洩露 stack trace

### 依賴安全

- [x] `pip install` 時不裝來源不明套件
- [ ] M2 引入 `uv.lock` lock file（ADR-012）
- [ ] M3 引入 `pip-audit` 定期掃描
- [ ] M3 引入 Dependabot（如果 repo 是 public）

---

## D. 基礎設施安全

- [x] docker-compose ports 只 expose 必要的
  - TimescaleDB: 5432（M5 可關掉只走 docker network）
  - Prefect: 4200（內部用，M5 加 reverse proxy）
  - Grafana: 3000（內部用，M5 加 reverse proxy + auth）
- [x] Secrets 不硬編碼（grep 過：clean）
- [ ] M5 容器以非 root 執行
- [ ] M5 容器映像最小化（distroless / alpine）
- [ ] M5 安全事件日誌（auth 失敗 / shioaji 異常）

---

## E. 合規性

| 法規 | 適用 | 處理 |
| :--- | :---: | :--- |
| 個資法 | ❌ | 無第三方使用者資料 |
| GDPR | ❌ | 無歐盟使用者 |
| SOC2 | ❌ | 個人專案 |
| 證券交易所紀律 | ✅ | 不做拉抬、不做高頻 quote stuffing |
| 個人所得稅（證券交易） | ✅ | 自行申報 |
| 健保補充保費 | ✅ | 單筆 > 2 萬時自動扣繳 |

---

## F. 審查結論（當前狀態）

| # | 行動項 | 優先級 | 預計 milestone |
| :--- | :--- | :---: | :--- |
| 1 | 引入 `uv.lock`（ADR-012） | P1 | M2 |
| 2 | 引入 `pip-audit` 排程掃描 | P2 | M3 |
| 3 | M5 backup 加密策略 | P0 | M5 前 |
| 4 | M5 HTTP API auth + rate limit | P0 | M5 前 |
| 5 | Shioaji TLS 驗證 | P0 | M5 前 |
| 6 | TimescaleDB retention policy | P1 | M5 |
| 7 | 容器非 root + 最小映像 | P2 | M5 |
| 8 | 監控告警分級 | P1 | M4 |

**整體評估：M1–M4 階段可繼續開發。M5 上線前必須完成 P0 行動項。**

---

## G. 生產準備就緒（M5 上線前 Checklist）

### 可觀測性

- [ ] Grafana 監控儀表板已建立（策略健康度 / 資料延遲 / 部位 heat）
- [ ] SLI 已定義
  - 訊號生成延遲 < 30 sec after 17:00 資料齊
  - 訊號重現率 > 99%
- [ ] 結構化日誌（Loguru JSON format）接入中央位置
- [ ] 關鍵告警（Discord，見 ADR-010）：
  - 連虧 5 筆
  - 單日 DD > 5%
  - 資料源延遲 > 1 小時

### 可靠性

- [ ] `/health` 健康檢查端點（M5 API）
- [ ] 優雅停機（SIGTERM 處理）
- [ ] 外部呼叫（FinMind / Shioaji）有 timeout + retry（指數退避）
- [ ] 備份與恢復演練（pg_dump / restore 全流程跑過）
- [ ] 熔斷規則自動執行（DD 25% → 全平、月績效 < -15% → 停機）

### 效能與擴展

- [x] 端到端 pipeline 單檔 2 年資料 < 5 秒（M1 實測 OK）
- [ ] Portfolio 100 檔 10 年回測 < 30 分鐘（M2 驗證）
- [ ] vectorbt 參數網格 24 cells × 30 windows < 1 小時（M3 驗證）
- 服務本身為單機批次，無水平擴展需求

### 可維護性

- [ ] M5 Runbook（出問題怎麼處理）
- [x] CI/CD 為 local script（M1 / 個人專案 OK）
  - 建議 M3 引入 GitHub Actions 跑 pytest
- [x] 配置集中於 `StrategyConfig` + `.env`
- [ ] M5 重大變更使用 git tag + 回滾流程文件化

---

## H. 已發現的安全狀況（自評）

### 正向

- ✅ secrets 都在 env，repo 內無洩漏
- ✅ 程式碼層級無 SQL injection（execute_values + parameterized）
- ✅ Pydantic 驗證在所有邊界
- ✅ pure function 設計減少狀態相關 bug
- ✅ `_evaluate_priority` 風控優先序硬寫死，沒辦法繞過

### 待改進

- ⚠️ DB password 預設值雖然故意醒目但仍是 plaintext，建議 M5 用 Docker secrets / Vault
- ⚠️ 無自動化漏洞掃描（M3 補）
- ⚠️ 無依賴 lock file（M2 補）
- ⚠️ 無 backup 機制（M5 前必補）
- ⚠️ 無 SOP 文件給「如果 strategy 大虧怎麼處理」（M5 前必補）

---

## I. 緊急狀況處理（M5 上線後）

| 情境 | 立即行動 | 後續 |
| :--- | :--- | :--- |
| 連虧 5 筆 | Discord alert + 自動暫停新進場 | 1 週冷卻後檢討 |
| 單日 DD > 5% | 觀察、不自動行動 | 隔日盤前評估 |
| 單日 DD > 10% | 自動降倉 50% | 暫停 1 週 |
| DD > 25% | 全平 + 停機 | 書面檢討 |
| 資料源中斷 | 暫停訊號生成 | 切備用源或人工 |
| Shioaji 異常 | 不下新單、現有單照常 | 修復或暫停 |
| 程式 bug | 立即停機 + 回滾 | 修復 → paper 1 週 → 再上線 |

完整流程詳見 M5 Runbook（待寫）。

---

## J. 風險管理規範（總覽，詳見 24 號文件）

> **2026-05-31 增補**：本章節為 24 號文件的高層摘要。**完整風控規範（兩階段框架、12 條 ex-ante 規則細節、3 級熔斷狀態機、4 個 SOP 步驟、kill_switch.sh 腳本） → 詳見 [24_risk_management_spec.md](./24_risk_management_spec.md)**。

### J.1 風控框架（兩階段）

| 階段 | 何時 | 失敗動作 |
| :--- | :--- | :--- |
| **Ex-ante**（事前）| 訊號 → broker submit 之前 | reject 訂單、寫 data_quality_log、Discord HIGH |
| **Ex-post**（事後）| 每筆 fill 後 + 每 5 分鐘 + 收盤 | 觸發熔斷 L1/L2/L3、Discord CRITICAL |

### J.2 Ex-ante 規則表（12 條，詳見 24 §2）

| Rule ID | 名稱 | 閾值 | M |
| :--- | :--- | :--- | :---: |
| EX-001 | 單筆下單金額上限 | < NT$ 500k（M5 小倉）/ < 5% equity（全倉）| M4 |
| EX-002 | 單檔持倉比例上限 | < 8% equity | M4 |
| EX-003 | 產業集中度上限 | < 35% equity（單產業）| M4 |
| EX-004 | Portfolio Heat 上限 | < 6%（v2.md §6）| M4 |
| EX-005 | 現金保留下限 | > 10% equity | M4 |
| EX-006 | 漲跌停價檢查 | 限價 ±10% from prev_close | M4 |
| EX-007 | 最大同時持倉檔數 | ≤ 15（v2.md §2.2）| M4 |
| EX-008 | 最小停損距離 | stop_loss ≥ entry × 0.95 | M4 |
| EX-009 | 訂單頻率上限 | < 30 訂單 / minute（防 bug 暴衝）| M4 |
| EX-010 | 流動性檢查 | qty ≤ 20% × 20D 平均日成交量 | M5 |
| EX-011 | 黑名單檢查 | stock_id ∉ blacklist | M4 |
| EX-012 | 風控熔斷狀態 | breaker.state != HALTED | M4 |

### J.3 熔斷規則（3 級）

| Level | 觸發 | 動作 |
| :--- | :--- | :--- |
| **L1 暫停** | DD > 限額 1.0x | 暫停加碼，仍允許停損 |
| **L2 減倉** | DD > 限額 1.5x | 強制減半部位 + Discord CRITICAL |
| **L3 全停** | DD > 限額 2.0x | 全部出場 + 停機 + 通知 |

### J.4 設計鐵律

1. 風控不可繞過：所有 signal 必經 `risk_gate.evaluate()`
2. 熔斷自動執行：L2/L3 觸發 → 自動下單，不等人工確認
3. 保守優先：拿不準時拒單
4. 可追溯：每次拒單寫 audit trail（rule_id + context_json）

完整實作邏輯（gate 評估順序、SOP 應變、kill_switch.sh）詳見 24 號文件。
