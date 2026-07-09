# 專案簡報與產品需求文件 PRD - 個人級 EOD 量化交易平台

> 版本: v1.0 | 日期: 2026-07-05 | 狀態: Golden baseline

## 1. 專案總覽

| 項目 | 內容 |
| :--- | :--- |
| 專案名稱 | Personal EOD Quant Trading Platform |
| 產品定位 | golden SAD 七層權威架構的個人級 EOD 版本 |
| 目標使用者 | 單一散戶 / 個人量化研究者 |
| 交易頻率 | EOD / 日線 / 低頻再平衡 |
| 實作前提 | 乾淨新專案，不受現有程式碼約束 |
| 核心限制 | 不做 Tick、Order Book、HFT、機構 EMS、K8s |

## 2. 商業目標

| 目標 | 說明 | KPI |
| :--- | :--- | :--- |
| 策略研究資產化 | 所有假設、回測、失敗、發布都可追溯 | 100% run 有 `bundle_ref` + `config_hash` |
| 安全下單 | 研究與下單隔離，所有交易經 Governance/Risk | 100% order intent 有 risk decision |
| 個人可維運 | 單人能監控、回滾、停機、恢復 | CRIT alert < 5 分鐘送達 |
| 可重建 | 新機可用文件與 IaC 重建 | RTO <= 4h，RPO <= 1 trading day |

## 3. 使用者故事與允收標準

### Epic A: Data Platform

| ID | 使用者故事 | 允收標準 |
| :--- | :--- | :--- |
| US-DATA-001 | As a researcher, I want EOD/財報/籌碼資料被版本化 so that 回測可重現。 | 每個 bundle 有 hash、coverage、calendar、source manifest。 |
| US-DATA-002 | As an operator, I want DQ gate 擋住缺資料 so that 錯誤資料不會進入交易。 | DQ fail 時禁止 release / trading。 |

### Epic B: Research & Validation

| ID | 使用者故事 | 允收標準 |
| :--- | :--- | :--- |
| US-RES-001 | As a researcher, I want 用因子與規則產生選股清單 so that 我能驗證 Alpha。 | 產出 `AlphaSignal`、`TargetPortfolio`、`BacktestReport`。 |
| US-RES-002 | As a researcher, I want WFA/DSR/PBO so that 我不被過擬合騙。 | sweep trials 全留存，不只保存最佳結果。 |
| US-RES-003 | As an operator, I want 驅動 Claude Code（dev-time）撰寫策略並跑 research 閉環 so that 不必手刻每個 package。 | agent 用 `research.cli` + finlab SDK 產出通過 conformance 的策略；execution off-limits；跑越多 trial 越誠實 increment trials counter（ADR-009 / SPEC-03）。 |

### Epic C: Governance & Release

| ID | 使用者故事 | 允收標準 |
| :--- | :--- | :--- |
| US-GOV-001 | As an approver, I want 發布前凍結策略定義 so that 實盤使用的版本可追。 | `ApprovedStrategyPackage` immutable，含 rollback plan。 |
| US-GOV-002 | As an operator, I want paper/watch 階段 so that 真錢前先觀察 live OOS。 | paper ledger 每日記錄 signal、target、PnL proxy。 |

### Epic D: Strategy / Portfolio / Risk / Execution

| ID | 使用者故事 | 允收標準 |
| :--- | :--- | :--- |
| US-TRADE-001 | As an operator, I want approved package 產生 target position so that 下單來源受控。 | 未核准 package 不可產生 order intent。 |
| US-TRADE-002 | As a risk owner, I want pre-trade gate so that 超限交易被擋。 | risk decision = Pass/Block/Reduce/Escalate。 |
| US-TRADE-003 | As an operator, I want fill 為單一真相 so that PnL/position 可對帳。 | position/equity 只能由 fill fold。 |

### Epic E: Monitoring & Operations

| ID | 使用者故事 | 允收標準 |
| :--- | :--- | :--- |
| US-OPS-001 | As an operator, I want 每日摘要 so that 我知道策略健康。 | 每交易日推送 PnL、position、risk、job status。 |
| US-OPS-002 | As an operator, I want kill switch so that 異常時停止交易。 | CRIT 預設 halt affected strategy。 |

## 4. 範圍與限制

| 類別 | 範圍內 |
| :--- | :--- |
| Data | EOD OHLCV、財報、籌碼、月營收、公司行動、trading calendar、bundle lineage |
| Research | 因子、選股、進出場、停利停損、加減碼、portfolio simulation、backtest、WFA；策略撰寫經 Claude Code dev-time harness（ADR-009） |
| Governance | strategy definition、parameter store、approval、paper/watch、version、rollback |
| Production | strategy runtime、portfolio engine、risk gate、personal execution、broker adapter |
| Monitoring | PnL、drawdown、decay、reconciliation、alert、runbook |
| Foundation | Docker Compose、systemd、PostgreSQL/TimescaleDB、object storage、secrets、backup |

| 類別 | 非範圍 |
| :--- | :--- |
| Market Data | Tick、Order Book、逐筆委託成交 |
| Strategy | HFT、Market Making、微結構 Alpha |
| Execution | 機構級 EMS、VWAP/TWAP/POV optimal execution |
| Infra | K8s、co-location、multi-region HA |
| Org | 多人 RBAC、formal compliance desk |

## 5. 成功指標

| 指標 | 目標 |
| :--- | :--- |
| 可重現性 | 任一 released strategy 可重建 backtest report |
| 邊界安全 | Research code 0 broker dependency |
| 風控覆蓋 | 100% order intent 經 risk gate |
| 對帳 | 每交易日 EOD reconciliation pass 或 halt |
| 可觀測性 | 100% critical jobs 有 alert |
| 維運 | 新機 restore <= 4 小時 |

## 6. 待辦決策

| ID | 決策 | 預設 |
| :--- | :--- | :--- |
| D-001 | 券商 adapter 第一版 | Shioaji seam，但以抽象介面設計 |
| D-002 | DB 第一版 | PostgreSQL + TimescaleDB extension |
| D-003 | 前端框架 | React + TypeScript |
| D-004 | 排程 | systemd timers，scale-up 才重評 Airflow |

