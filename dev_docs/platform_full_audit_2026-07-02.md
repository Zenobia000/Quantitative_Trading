# 全平台多視角審查報告（Full Platform Audit）

> **日期**：2026-07-02 | **方法**：4 階段 16-agent workflow（六區域全掃描 → 四路競品研究 → PM/架構/設計模式/QA/UIUX 五視角平行審查 → 交叉綜合）
> **證據狀態**：Top 5 CRITICAL 指控已由主審逐一實地覆核（檔案:行號級），全部成立（見 §3 標注 ✅）
> **配套文件**：[競品分析與視角附錄](./competitive_analysis_2026-07-02.md) | 狀態真相源仍為 [16 WBS](./16_wbs_development_plan.md)

---

## 1. 產品定位（正名）

【產品正名】本產品不是「四層共振戰法回測平台」（PRD v3.0 的過期敘事），而是一座「個人量化 edge 驗證工廠 + 晉升管線」：single-user、standalone、台股專用的策略真偽審判與 backtest→paper→live 營運系統。策略是可拋棄的消耗品（四層共振已判負 edge 廢止、動能/多因子/long-short/資金流四結構撞 ~0.9 Sharpe survivorship-clean 牆），平台的核心資產是審判庭本身——能誠實殺掉壞策略、讓極少數真 edge 走不可逆晉升管線的能力。連續 NO-GO 不是產品失敗，而是產品正常運作的最強證據。

【Persona】唯一使用者是開發者本人，單人雙帽：研究時段是「策略研究者」（CLI-first 跑 DOE/truth-gate/sweep，GUI 檢視 runs/報告/比較），運維時段是「艦隊運維者」（看 Fleet 監控、收 Discord 告警、處置退化）。部署假設：單機自託管、內網 localhost、無多人協作、無合規審批——此假設必須寫入 PRD 正式化，據此裁決 auth（內網靜態 token 即足）、路徑、備份等長期懸置的三方矛盾。

【價值主張：唯一護城河是「驗證信心」】競品研究證實 >90% 策略上線即失效，但零售市場沒有任何 SaaS 把 PBO/DSR/WFA/survivorship-clean 做成強制 gate（FinLab 只做 lookahead 偵測、TradingView/Composer 幾乎不做、QuantConnect 止於 power gauge 警告）；學術級防過擬合在開源生態也近乎空白（MLFinLab 已閉源）。本專案的兩段式驗證閘（真偽閘 hard-fail + 配置閘連續 sizing）+ 試驗計數 DSR deflate + OOS sealed vault 是全市場罕見的差異化——前提是審判庭自己必須先可信（目前 truth_gate 的 DSR 單位錯誤、OOS holdout 未評估、survivorship 寫死三缺陷正在架空這個價值主張，是 P0 中的 P0）。

【該像機構的部分（縮小規模照抄）】(1) PIT/bi-temporal 資料紀律：survivorship-clean 已做對，補上 run 記 bundle hash/git_sha 的血統可稽核與 parquet 不可變快照（中期評估 ArcticDB）；(2) 風控前置：pre-trade gate + 三級熔斷 + kill switch，且 paper/live 必須看見真實組合狀態；(3) 單一真相源：runs ledger 與 position/risk state 層三模式共用；(4) 不可變版本化研究產出 + 假設預先註冊；(5) 型別安全換可靠性：Pydantic schema 貫穿邊界（Jane Street 精神的 Python 版）。

【該像散戶工具的部分（保持 lite）】單機部署免 DevOps、CLI-first + 薄 GUI（17 頁收斂至 ~9 活躍頁）、Discord 單通道告警、cron 級排程器而非企業 scheduler、JSONL ledger 在單人規模合理。明確不做（Won't，與「做」同等正式）：多市場/期權/多帳戶、跨人 leaderboard/staking、分散式掃描叢集、自建計算圖引擎、hosted notebook、完整 champion/challenger registry、多人簽核、K8s。艦隊營運層維持 gated 於「≥1 策略完成 3 個月 paper」。

【成功指標兩層分列】平台 KPI：判決可重現性（inst_flow 的 TRUTH GATE REAL 必須能在標準化工作流下重現）、新策略假設→真偽判決 lead time（ADR-027 已降至複製 4 檔+1 行，應量測）、每次驗證成本；策略 KPI：ADR-025 兩段閘判準。範圍界線的下一個價值里程碑：修好審判庭 → 用可信的閘重驗 inst_flow → after-close 排程器開始收 live OOS → 3 個月 paper → M5 小倉位實盤（2027-05）。

---

## 2. 一頁結論

| 視角 | 一句話判決 |
| :--- | :--- |
| 產品經理（PM）視角 | 實質產品（edge 驗證工廠）與文件宣稱產品（四層共振回測平台）已分裂；PRD 依現行判準會判專案「失敗」，敘事真空是最大產品風險 |
| 首席架構師視角 | 判決層（validation/risk/monitoring）品質優異、ADR-027 契約縫畫對了；但舊縫殘骸（engines↔strategies↔research 三角依賴）未清、三模式一致性與資料血統保證尚未成立 |
| 軟體設計模式視角 | 兩個世界並存：純函式核心達教科書水準，接縫層（collaborators、API overrides、外部呼叫）的 pattern 要麼是假的要麼缺席 |
| QA / 測試策略視角 | 93.15% 覆蓋率不是灌水但也不是它看起來的保證——行覆蓋≠判決覆蓋，shape-only 測試放過 DSR 單位錯誤級 CRITICAL；且完全沒有 CI |
| UI/UX 使用者旅程視角 | IA 骨架忠實落實「研究迴圈優先」，但實質承載完全反轉：研究區（旅程核心）在 GUI 內無法完成任何一個完整循環，煞車唯讀、油門可寫 |

**核心矛盾（全案主軸）**：本產品唯一護城河是「驗證信心」——但審判庭自己目前不可信（DSR 單位錯誤、OOS holdout 未評估、survivorship 寫死、配置閘零接線）。唯一 paper-ready 候選 inst_flow 的「TRUTH GATE REAL」判決來自已刪除的 scripts，現行程式路徑無法重現。修好審判庭 → 重驗 inst_flow → 收 live OOS 是唯一的價值關鍵路徑。

---

## 3. 缺陷與矛盾 Top 25（跨視角去重、按影響排序）

### #1 [CRITICAL] ✅已覆核 審判庭 DSR 計算單位錯誤：DSR>0.95 核心通縮檢查退化為符號檢查

research/workflows/truth_gate.py:50-62 把年化 Sharpe（×√252）+ 日報酬變異數餵進需要 per-period SR + cross-trial variance 的 DSR 公式；實測年化 Sharpe 0.333 → DSR=1.000000（正確應 0.503 REJECTED），n_trials 通縮完全失效。同 codebase validation/full_report.py:37-40 有正確實作卻未被 production 路徑使用。唯一 paper-ready 候選 inst_flow 的「TRUTH GATE REAL」判決來自已刪除的 scripts，現行程式路徑無法重現——產品唯一策略資產的證據鏈斷裂，價值主張級缺陷。

*來源視角：backend-research-strategies、pm-positioning、architect、design-patterns、qa-coverage*

### #2 [CRITICAL] ✅已覆核 兩段閘只落實半段：OOS holdout 從未評估 + survivorship_clean 寫死 + SizingGate 零呼叫者

run_truth_gate 全檔未引用 cfg.is_end，宣稱的 OOS=[oos_start, is_end] 資料零讀取（WFA/DSR/滑價全在 IS 區間內）；truth_gate.py:73 對任意 universe 寫死 survivorship_clean=True，two_stage_gate 的 hard precondition 永遠亮綠；ADR-025 第二段 SizingGate（compute_position_size/evaluate_two_stage/fleet_correlation）在 src+tests 零呼叫——「兩段式」命名與 wiring 矛盾，通過真偽閘的策略無任何程式路徑產生倉位權重。

*來源視角：backend-research-strategies、pm-positioning、architect、qa-coverage*

### #3 [CRITICAL] ✅已覆核 Paper 風控以空倉位快照評估：組合層規則全數失效 + side 詞彙不相容

orchestration/collaborators.py:39-41 每日建 AccountState(positions=(), equity=cash)，EX-002 單股上限/EX-003 產業集中/EX-004 heat/EX-007 持股數永遠看不到既有部位；同批多筆 buy 對同一現金快照檢查不遞減。另 risk gate 接受 add/reduce 但 PaperBroker 只認 buy/sell，approved 單在下單階段拋 ValueError 使整日 halt。M4 三個月 paper 的核心驗證目的（風控與執行摩擦）在現行實作下無法達成，是 inst_flow 進 paper 前的硬 blocker。

*來源視角：backend-platform、architect、design-patterns、pm-positioning*

### #4 [CRITICAL] ✅已覆核 runs 表 DDL（preset）與 db_writer（strategy）不相容：研究血統寫入 TimescaleDB 必炸

已實地確認 docker/timescaledb/init.sql:103 仍為 preset TEXT NOT NULL（migrations/002 同），db_writer._RUNS_COLS 已改 strategy——INSERT 必 undefined column + NOT NULL violation。且 doc 21 §4.2b 的「已更新」DDL 自含重複 params 欄（無效 SQL）、schema 防漂移測試恰好不斷言此欄、DB integration 測試預設 skip——文件/測試/migration 三層防線同時失守，ADR-028 blast radius 漏了 DDL 層。

*來源視角：devdocs-adrs-specs、architect、qa-coverage*

### #5 [CRITICAL] ✅已覆核 前端研究主線全斷：NewRun 必 422、RunsTable/RunReport 滿版「—」、Compare 永不渲染

frontend/openapi.json stale（仍含已刪的 /presets），NewRunPage 送廢棄 preset 欄對 extra=forbid 後端必然 422；RunsTable/RunReport 讀 strategy_id/status/created_at/頂層 metrics（後端實為 strategy/gate_status/巢狀 metrics），「送驗證」鈕永久 disabled；ComparePage 把物件回應當陣列判定恆 null。GUI 內無法完成任何一個研究循環，「CLI 執行、GUI 檢視」分工失敗，GUI 對單人使用者產生負價值。

*來源視角：frontend、uiux-journey、pm-positioning、qa-coverage*

### #6 [HIGH] 測試綠燈系統性掩蓋缺陷：行覆蓋非判決覆蓋、mock 形狀即錯誤形狀

後端 93.15% coverage 下，工作流測試 shape-only（只驗型別與 0-1 範圍）放過 DSR 單位錯誤等判決級 CRITICAL；前端 44 個 vitest 的 mock 用的正是 drift 後的錯誤欄名（RunsTablePage.test.tsx:32），綠燈直接掩蓋 422 與滿版「—」。無 checked-in golden master、hypothesis 零使用、雙引擎對拍依賴本地 parquet cache（fresh checkout 即 skip）且 harness 被 omit 出 coverage。

*來源視角：qa-coverage、frontend、backend-research-strategies*

### #7 [HIGH] CI 完全不存在：所有品質閘門與契約治理靠本地自覺

已確認 .github/workflows/ 不存在。doc 22 §8 CI YAML、ADR-021/025 的 OpenAPI CI diff、doc 25 §9 契約治理全是紙上草案。runs DDL drift、openapi.json stale、doc 25 registry 漂移三起已發生事故的共同根因即無機器守門。後端全量測試僅 33 秒，完全可進 CI——這是全清單回報率最高的單項投資。

*來源視角：qa-coverage、devdocs-adrs-specs、architect、pm-positioning*

### #8 [HIGH] Gate 不隨策略 dispatch：非四層策略永遠 INCOMPLETE，旗艦策略在自己的平台上看起來是壞的

is_harness.py:130/176 在 gate=None 時一律用四層專屬 DEFAULT_GATE（struct1_pct/churn_pct/avg_hold 只有四層 sim 產出）；MOMENTUM_GATE 已定義但無 production 呼叫點。經 API/GUI 觸發的 momentum/inst_flow run 永遠 INCOMPLETE——GUI 判定與 CLI truth-gate 判定互相矛盾，摧毀驗證區可信度。ADR-027 把 runner/config/research_config 都 dispatch 化，唯獨審判標準漏了，是「下一個 10 隻策略」的第一個斷點。

*來源視角：backend-platform、architect、design-patterns、uiux-journey*

### #9 [HIGH] 研究血統造假鏈：engine 欄被持久化但從不 dispatch、--config v3 靜默忽略、n_trials 手填漂移

RunConfig.engine 接受 zipline 並納入 run_id hash 與 ledger，但 _run_is_core 永遠跑 sim——同參數兩 engine 兩個 run_id 相同 metrics，ledger 失真；zipline CLI 設 STRATEGY_PRESET 但全 codebase 無讀取者、演算法硬編碼 StrategyConfig()（註解還宣稱已修復），v3 校準結論全部失真；inst_flow n_trials 註解寫 24 但同檔 _GRID 實為 16，DOE 不接 trials_counter_store 審計軌。run 也不記 bundle hash/git_sha——「每個 run 可重現可稽核」三處落空。

*來源視角：backend-platform、backend-research-strategies、architect、design-patterns、pm-positioning*

### #10 [HIGH] parquet 快取部分覆蓋時整段重抓覆寫：付費資料資產可被一次 ingest 毀掉歷史

parquet_cache.py:79-91 在快取未完整覆蓋請求區間時只抓請求區間然後直接覆寫三個 parquet（finmind_etl.py write_parquet 無合併邏輯）：已有 2020-2023 再 ingest 2024 → 快取只剩 2024。與 docstring「day-incremental」宣稱矛盾。配合 8.E/8.F 備份與 DR 完全缺席，FinLab 付費 ingest 資產、reports/runs.jsonl 研究血統、TimescaleDB telemetry 均無保護——單人專案不可再生資產裸奔。

*來源視角：backend-platform、architect、pm-positioning*

### #11 [HIGH] 系統邊界驗證被整套繞過：API/CLI overrides 用 model_copy(update=) 使 Pydantic 全部失效

api/routers/research_workflows.py:70 與 research/cli.py:295-303 以 model_copy(update=req.overrides) 套用 HTTP body/CLI 的不受限 dict——實測可注入錯型別（is_start='not-a-date'）、extra=forbid 應擋的未知欄位、is_start>is_end 非法窗序，錯值進 background job 深處才爆炸或靜默算錯。精心設計的 frozen+validator 在唯一外部輸入路徑上形同虛設。修復成本極低（改 model_validate），是全案最高槓桿單點修復。

*來源視角：backend-research-strategies、design-patterns*

### #12 [HIGH] GUI 煞車唯讀、油門可寫：可在零 gate 證據下一路晉升 live

設計文件（web_design/03 §2.3）的核心論點是「唯讀展示≠工作流強制」，但前端把反模式倒過來實作：ValidateGatePage 只顯示靜態 spec + PendingNote（useGateState/useValidateWfa hooks 已寫好未接），PromotePage 的 advance mutation 卻完整可用且無任何 gate 前置檢查——draft→paper→live 可零證據晉升。後端 gate_machine/trials_counter/two_stage_gate 存在但 GUI 零接線，比原本被批判的唯讀 Panel E 更危險。

*來源視角：uiux-journey*

### #13 [HIGH] engines↔strategies↔research 三角依賴 + import 副作用註冊：脆弱循環與層次倒掛

engines/protocol.py 宣稱 engine-agnostic 卻 import 四層策略具體 StrategyConfig 與 is_harness 五個私有 helper（Lava Flow，已被 ADR-027 實質取代）；三隻策略 research_config 反向 import finmind_bundle 只為 DEFAULT_UNIVERSE，連帶 import zipline + 觸發 bundle 全域註冊副作用；策略註冊靠 import runners 副作用且聚合點在 research 層而非 strategies 自身。違反 dev_docs/09 明訂的 DIP/ADP/SDP，僅靠 loader 延遲載入避免爆炸。

*來源視角：backend-platform、backend-research-strategies、architect、design-patterns*

### #14 [HIGH] 三模式「共用策略碼」只在純函式層成立：backtest 與 paper 組合機制分岔且零對拍

研究側走 panel rebalance 向量化模擬，paper 側走 daily_flow 離散逐單撮合，兩路徑無任何 reconciliation 測試（9 個 integration 全是 zipline vs vectorbt/M1，無 sim vs paper 對拍）；時間戳雙時鐘（ledger naive now() vs telemetry UTC+8）。ADR-008 的核心承諾缺機器證據，paper 3 個月 OOS 若無法回溯對拍 backtest，M4 gate 證據力大打折扣。雙引擎容差門檻三份文件三個數字（0.1%/0.5%/1%+10bps）無收斂。

*來源視角：architect、devdocs-core、qa-coverage*

### #15 [HIGH] PRD 與上游文件全面過期：依現行 PRD 判準專案已「失敗」，敘事真空是最大產品風險

02 PRD 仍以已判死刑的四層共振為產品主軸（專案名/商業目標/US-001~006/ADR-016 binary 門檻），ADR-023~029 七個定義現今產品的決策全部缺席；01 仍寫 TQuant-Lab/ADR-005；05 承諾的 v2.0 重畫未兌現（FastAPI=M5、React=M6+ 與實況相反）；17 反清單「不寫 React」被推翻、17 週排程 vs 實際 2027-08 差 4 倍；20/22/23 凍結在 2026-05-31。16 §5 明列「個人興趣變動＝致命，緩解=文檔完整可重啟」——現行文件會把中斷後回來的使用者導向錯誤理解。

*來源視角：devdocs-core、devdocs-adrs-specs、pm-positioning、architect*

### #16 [MEDIUM] 16 WBS 單一狀態真相源自我矛盾 + 門檻數字四處漂移

16 自身 §1 banner（86%/990h/1053 pass）與 §4 進度摘要（80%/905h/786 pass）打架；§6 里程碑 M2 ❌「退場回 M0」與 M3/M4 交付物照建的兩套現實並存、Sprint 0 Gate 仍標 ⏳、M3 交付物仍寫 Streamlit；§7 Sprint 看板 reconciliation 自 v2.9 拖欠。ADR-018 擋門數字（PBO>0.5/DSR<1.0）與 ADR-016/025/doc 24/實作（0.30/0.95）矛盾從未 amend；ADR-009 Prometheus 被 doc 20/實際部署靜默換成 InfluxDB 無 ADR 記錄。gate 即紀律的產品，門檻漂移直接損害判決權威性。

*來源視角：devdocs-core、devdocs-adrs-specs、pm-positioning*

### #17 [MEDIUM] after-close 排程器（收 live OOS 唯一 blocker）未做 + paper 階段介面覆蓋率趨近零

16 banner 自認 after-close 排程器是收 live OOS 的唯一剩餘 blocker，卻持續為部署層 stub——這卡住產品下一個價值里程碑（inst_flow paper 前移的兌現）。paper daemon 只能以 python 呼叫，GUI/CLI 皆無啟停、replay 進度、觀察期倒數入口；PromotePage 無強制觀察期概念。M4（2027-02）主活動的介面覆蓋率是整條旅程最低的一站。個人 standalone 不需企業排程器，一條 systemd timer/cron + Discord 通知即可。

*來源視角：pm-positioning、uiux-journey、devdocs-core*

### #18 [MEDIUM] 靜默吞錯讓閘門對「不存在的資料」出判決

strategies/common/panel.py 逐 symbol except Exception: continue——parquet 目錄整個不存在時全部 symbol 被跳過、panel 為空、runner 回 _EMPTY_METRICS，go_gates/truth_gate 得到 sharpe=0 的「合法」FAIL/REJECTED 判決而非報錯；loader.py 把巢狀 import 錯誤摺疊成「缺 research_config」誤導修復方向；truth_gate 的 _add_slippage 用 hasattr duck-typing 猜欄位，未知欄名時 K3 壓力測試靜默變 no-op（契約已有 with_extra_slippage/slippage_sharpe 卻另造第三套）。違反「絕不靜默吞噬錯誤」規範。

*來源視角：backend-research-strategies、design-patterns、architect*

### #19 [MEDIUM] 全平台 CWD 相對硬編碼路徑 + 設定三軌並存：同一系統兩份現實

data/parquet、reports/runs.jsonl、reports/jobs.jsonl、data/zipline 等五處以上 CWD 相對硬編碼——uvicorn 與 CLI 從不同目錄啟動會讀寫不同 ledger/快取；config/settings.py 只集中一項且不讀 .env、DiscordSettings 讀 .env、UNIVERSE_FINMIND/STRATEGY_PRESET 走 env side-channel 三種慣例並存；postgres_password 預設 change_me_in_production 雙處 drift 且無啟動期驗證。對「一個人在一台機器上跑」是高頻事故源。

*來源視角：backend-platform、architect、design-patterns*

### #20 [MEDIUM] auth 承諾三方矛盾：doc 25 要求 Bearer、後端零實作、前端硬編碼 dev-token 進 bundle

doc 25 §4 宣告 M3.0 起全端點 static Bearer，後端 api/ 全目錄無任何 Authorization 檢查、無 CORS，前端 http.ts 硬編碼 fallback 'dev-token'；.env.example 的絕對 URL 又會繞過 vite proxy 直撞無 CORS 後端。單人內網部署實際風險有限，但「承諾了沒做」比「決定不做」更傷文件可信度——應以 ADR 正式二擇一（localhost-only 宣告或 20 行 static Bearer dependency）。

*來源視角：frontend、devdocs-adrs-specs、architect、pm-positioning*

### #21 [MEDIUM] 台股微結構缺口：漲跌停 TradingControl 未實作、停牌零測試——回測系統性偏樂觀

taiwan_stock_rules.py:94-98 明文承認 ±10% 漲跌停 reject 未以 TradingControl 實作，limit-up 日 zipline 預設 fill_at_open 樂觀成交；停牌/暫停交易無任何測試與實作；signal 層無 look-ahead leak detector（inst_flow 法人資料 T 日盤後公布，lag=1 仍有隔夜樂觀偏差待敏感度對照）。對標 freqtrade 的 lookahead-analysis/recursive-analysis 自動偵測是可直接抄的補強方向。

*來源視角：backend-platform、qa-coverage、oss-backtest-engines(競品)*

### #22 [MEDIUM] 韌性缺口：DB 寫入無 Unit of Work、外部 API 零 retry、jobs 去重競態

make_db_sink 三次 upsert 各開各的連線交易，signals 成功 fills 失敗會留下不一致 telemetry；FinMind/FinLab 呼叫僅 time.sleep 限速、零重試零退避（諷刺的是專案自有高品質 CircuitBreaker 沒用在唯一真正的外部依賴）；jobs submit 以確定性 job_id 卻不查既有狀態即開新 thread，同 key 並發重複執行且 JSONL 無鎖交錯寫。paper daemon 日常穩定性的直接風險。

*來源視角：design-patterns、backend-platform、architect*

### #23 [MEDIUM] 過度工程 vs 個人剛需錯配：死碼與空殼大面積存在，違反 ADR-018 自訂鐵律

ADR-018 明訂「補齊研究迴圈前不擴張監控」，實際交付順序相反：67 端點（monitor/system 大面積 typed-empty stub）、17 頁 SPA（M4 前逾 5 頁無資料可看、真正可用互動僅 ~5 個）先建完，而判決引擎帶 CRITICAL 上線。死碼清單：_StubEngine 幻影引擎、空殼套件 dashboard//data_bundle/data_feed、src 下 multi_factor __pycache__ 殘留、前端 zustand/recharts/plotly/monaco 四依賴零使用、WiredPage 死碼、ETLConfig/hypothesis_prefix 死欄位。

*來源視角：architect、frontend、uiux-journey、pm-positioning、design-patterns*

### #24 [MEDIUM] 已 shipped 的後端能力被前端錯標「待後端」：hooks 寫好未接、PendingNote 陳述過期

SweepPage 對已實作的 POST /research/sweep 顯示「待後端」（api/sweep.ts+useSweep.ts 已寫好無人引用）；ValidateGatePage 未用已存在的 gate-state/WFA hooks；AlertsPage 對已 shipped 的 /system/alerts/* 顯示 pending；StrategyLibrary→Runs 過濾全程 no-op、無分頁（DOE 一次 16-24 configs，50 筆截斷一週內讓研究主頁失效）。修復成本極低、ROI 最高的旅程修復。

*來源視角：frontend、uiux-journey*

### #25 [MEDIUM] ADR-029 標準化研究工作流在 GUI IA 完全缺位：前端敘事停在一個世代前

現行研究方法真相源是 doe/go_gates/truth_gate/paper_replay 四個泛用工作流（CLI+HTTP 已 shipped），但 nav/router/任何頁面都沒有入口，GUI 還是 run-centric 舊敘事；web_design/03 旅程圖與 doc 12/25 未反映 ADR-028/029（NewRunPage 的 preset 錯誤正是照舊文件寫出來的）——設計文件本身成為錯誤實作的生產源。

*來源視角：uiux-journey、frontend、devdocs-adrs-specs*

---

## 4. 三階段路線圖

### Phase 1（立即修正，~2-4 週）：修復審判庭與日常主迴圈——讓產品的核心承諾重新為真

**主題**：審判庭可信度 + 研究血統 + GUI 主線 + 機器守門

- 修復審判庭四缺陷並用修正後的閘重驗 inst_flow：DSR 改走 full_report 正確路徑（per-period SR + cross-trial variance，缺誠實來源即 raise）、接上 cfg.is_end 真正評估 OOS holdout、survivorship_clean 改由 universe 建構器輸出、SizingGate 接線或 ADR 明文降級；補判決級 oracle 測試（先 RED 釘住 bug）→ 對應缺陷 #1 #2 #6
- Paper 風控真實化：make_risk_check 接 broker.positions 與總權益、批次內遞減現金、side 詞彙轉換層（add→buy 等）；補「兩筆合計超限被 EX-002 攔下」整合測試 → 對應缺陷 #3
- runs DDL migration 003（preset→strategy+params）+ 修 doc 21 重複 params 無效 DDL + schema 防漂移測試補 runs 欄斷言 → 對應缺陷 #4
- 前端主線救援（一次 commit）：從活後端重生 openapi.json + gen:api，修 NewRun/RunsTable/RunReport/Compare 四頁欄位對齊，測試 mock 改真實形狀 → 對應缺陷 #5 #6
- 封住 overrides 驗證洞：model_copy(update=) 改 model_validate，補 422 行為測試 → 對應缺陷 #11
- parquet 快取改 read-merge-write + ingest manifest（bundle_hash/git_sha 入 runs record）+「先 ingest 舊再 ingest 新歷史仍在」回歸測試 → 對應缺陷 #10 #9
- 最小 CI（GitHub Actions 單 workflow）：pytest+coverage gate、vitest（補裝 @vitest/coverage-v8）、OpenAPI diff、init.sql↔_RUNS_COLS 對齊斷言 → 對應缺陷 #7 #6

### Phase 2（短期補強，~1-2 個月）：接通晉升管線、開始收 live OOS、償還敘事債

**主題**：Gate dispatch + 血統誠實化 + 排程器 + PRD v4.0 + 對拍護欄

- Gate 納入策略契約：research_config/StrategyRunner 宣告 GateSpec，run_and_judge/paper_replay/promotion_service/gate router 依策略 dispatch（MOMENTUM_GATE 接線）；conformance 補「gate health 指標 ⊆ 策略 metrics keys」斷言 → 對應缺陷 #8
- 血統誠實化：RunConfig.engine 二擇一（拒收 zipline 或真 dispatch）、STRATEGY_PRESET 接通或下架 --config、n_trials 改由 DOE 接 trials_counter_store 自動記錄 → 對應缺陷 #9
- 拆三角依賴：DEFAULT_UNIVERSE 下沉中立模組、finmind_bundle register 改顯式 ensure_registered()、engines/protocol.py 廢止（需 ADR）、註冊聚合移入 strategies/__init__ → 對應缺陷 #13
- after-close 排程器最小版（systemd timer/cron + Discord 成敗通知），在 paper 風控修復後開跑 inst_flow live OOS 收集 → 對應缺陷 #17
- 備份最小版（每日 pg_dump + rsync parquet/reports）+ 路徑集中入 settings.py + 密碼啟動期驗證 → 對應缺陷 #10 #19
- PRD v4.0 重寫（正名 edge 驗證工廠、persona 正式化、平台/策略 KPI 分列、補 ADR-023~029、standalone 安全假設明文）+ 16 WBS 自我對帳 + 上游文件 tombstone banner + auth 裁決 ADR → 對應缺陷 #15 #16 #20
- backtest↔paper 對拍 reconciliation 測試（inst_flow 固定 config 一個月窗口，統一容差為相對 1%/絕對 10bps 並回寫三份文件）+ checked-in 合成 golden bundle 讓對拍脫離本地 cache → 對應缺陷 #14 #6
- 前端接線 sprint：useSweep/useGateState/useValidateWfa 接上頁面、清過期 PendingNote、Promote advance 加 gate 前置檢查（前後端雙防線）、Runs Table 分頁+URL filter → 對應缺陷 #12 #24
- 消滅靜默吞錯：panel.py 收集 failed+全空即 raise、loader.py 區分錯誤型別、truth_gate 滑價改走契約路徑 → 對應缺陷 #18

### Phase 3（中期演進，M4 前 ~3-6 個月）：收斂介面、強化韌性、把差異化做成工具

**主題**：IA 收斂 + 台股微結構 + 韌性 + 防過擬合工具化 + 文件償還

- 頁面收斂 17→~9 活躍頁（Compare+Sweep 合併、Validate+Promote 串成 gate 管線、monitor 5→2、system 2→1）+ ADR-029 工作流入 GUI（策略卡觸發 DOE/truth-gate）+ recharts 最小圖表組（equity 疊 IS/OOS/live_start_date 邊界、drawdown、sweep heatmap）+ paper daemon 狀態卡與觀察期進度 → 對應缺陷 #23 #25 #17
- 台股微結構補課：±10% 漲跌停 TradingControl（先 xfail 釘住期望）、停牌合成資料測試、signal 層反事實 leak detector；借鏡 freqtrade lookahead-analysis/recursive-analysis 工具化為 CI 級 gate → 對應缺陷 #21
- 韌性補強：db_writer 單交易 Unit of Work、FinMind/FinLab 呼叫加 tenacity retry、jobs 提交冪等去重+檔案鎖 → 對應缺陷 #22
- hypothesis property-based 測試導入 validation/risk（DSR 對 n_trials 單調、WFA fold 不重疊、RiskGate 排列不變等 15-20 條）+ per-path coverage gate（validation ≥90%）+ 1-2 條 Playwright 使用者旅程 E2E（webServer 進 CI）→ 對應缺陷 #6
- 死碼清理：_StubEngine、空殼套件、multi_factor 殘留、前端零使用依賴、WiredPage、死欄位；typed-empty stub 逐一標註 WBS 工項或刪端點 → 對應缺陷 #23
- 架構文件償還（P0/P1 重構完成後一次 sweep）：09 依賴 DAG 重畫、05 C4 v2.0 兌現、23 拓撲對齊 FastAPI+React 現實、10 補 StrategyRunner/GateSpec 類別圖、22 重寫對齊實際測試體系 → 對應缺陷 #15 #16
- 研究資料層演進評估：ArcticDB 作 PIT 版本化快照層（補充 TimescaleDB）、統一 UTC clock 注入、JSONL 壓實或遷 runs 表——在 10 年資料回填與多策略掃描前就位 → 對應缺陷 #9 #14 #19

---

## 5. 平行開發工作包（git worktree 切分）

切分原則：各包檔案零重疊、可獨立 PR / 獨立 revert。WP1-WP5 已於 2026-07-02 以隔離 worktree 平行啟動實作。

### WP1：`fix/truth-gate-judgement` 🔨 實作中（2026-07-02 啟動）

審判庭修復：truth_gate DSR 改走 full_report 正確路徑、接上 cfg.is_end 評估 OOS holdout、survivorship_clean 改參數化、SizingGate 接線或明文降級、dsr.py 加輸入衛兵；補判決級 oracle 測試（含已知 REJECTED 案例）；完成後重跑 inst_flow truth-gate 驗證判決可重現

**檔案範圍**：
- `backtest_platform/src/backtest_platform/research/workflows/truth_gate.py`
- `backtest_platform/src/backtest_platform/research/workflows/config.py`
- `backtest_platform/src/backtest_platform/validation/dsr.py`
- `backtest_platform/src/backtest_platform/validation/two_stage_gate.py`
- `backtest_platform/tests/research/workflows/`
- `backtest_platform/tests/validation/`
- `dev_docs/adrs/ADR-030-truth-gate-dsr-fix.md`

**平行性論證**：只動 research/workflows 與 validation 子樹及其測試；不碰 orchestration/adapters（WP2）、data/docker（WP3）、frontend（WP4）、engines/strategies research_config（WP6）、is_harness/gate_state（WP7）

### WP2：`fix/paper-risk-integrity` 🔨 實作中（2026-07-02 啟動）

Paper 風控真實化：make_risk_check 從 broker.positions/portfolio_snapshot 建 AccountState、批次內遞減現金、make_place 加 side 詞彙轉換（add→buy、reduce/exit/stoploss→sell）；統一 collaborators 時鐘輸出帶 tz；補「合計超限被 EX-002 攔下」與 side 轉換整合測試

**檔案範圍**：
- `backtest_platform/src/backtest_platform/orchestration/collaborators.py`
- `backtest_platform/src/backtest_platform/orchestration/daily_flow.py`
- `backtest_platform/src/backtest_platform/adapters/brokers/paper_broker.py`
- `backtest_platform/tests/orchestration/`
- `backtest_platform/tests/adapters/`

**平行性論證**：只動 orchestration/adapters 子樹；risk/ 純函式模組保持唯讀（狀態注入修在呼叫端），與審判庭（WP1）、資料層（WP3）、前端（WP4）零檔案交集

### WP3：`fix/runs-ddl-and-parquet-lineage` 🔨 實作中（2026-07-02 啟動）

資料層血統與完整性：migration 003（runs 表 preset→strategy+params）、init.sql 對齊、修 doc 21 §4.2b 重複 params 無效 DDL、test_init_sql_schema 補 runs 欄斷言；parquet_cache 改缺口 fetch+merge 寫回、write_parquet 原子寫、ingest 產 manifest.json（bundle_hash）；補「舊歷史不被新 ingest 毀掉」回歸測試

**檔案範圍**：
- `backtest_platform/docker/timescaledb/init.sql`
- `backtest_platform/migrations/003_runs_strategy.sql`
- `backtest_platform/src/backtest_platform/data/db_writer.py`
- `backtest_platform/src/backtest_platform/data/finmind_etl.py`
- `backtest_platform/src/backtest_platform/engines/zipline_adapter/bundles/parquet_cache.py`
- `backtest_platform/tests/data/`
- `dev_docs/21_data_contract.md`

**平行性論證**：只動 data/、docker/、migrations/ 與 bundles/parquet_cache.py；不碰 finmind_bundle.py（WP6 所有）、research/（WP1/WP7）、orchestration/（WP2）

### WP4：`fix/frontend-contract-realign` 🔨 實作中（2026-07-02 啟動）

前端主線救援：從活後端重生 frontend/openapi.json + api.gen.ts；NewRunPage 改送 strategy+params、RunsTable/RunReport 改讀 strategy/gate_status/巢狀 metrics、ComparePage 接物件回應+run_ids；接上 useSweep/useGateState/useValidateWfa 三組已寫好的 hooks、清過期 PendingNote；Promote advance 加 gate 前置 disabled；測試 mock 全部改真實形狀

**檔案範圍**：
- `frontend/openapi.json`
- `frontend/src/types/api.gen.ts`
- `frontend/src/features/research/pages/`
- `frontend/src/features/research/api/`
- `frontend/src/features/system/pages/`
- `frontend/src/features/home/`

**平行性論證**：純 frontend/ 子樹（package.json 除外，歸 WP5）；後端只讀不寫（openapi dump 為讀操作），與所有後端 WP 零檔案交集

### WP5：`chore/minimal-ci` 🔨 實作中（2026-07-02 啟動）

最小 CI：單一 GitHub Actions workflow——後端 uv run pytest（--cov-fail-under=80）、前端 tsc+vitest（devDependencies 補 @vitest/coverage-v8）、drift 檢查（app.openapi() vs frontend/openapi.json diff、init.sql↔db_writer 欄位對齊斷言腳本）；Playwright config 加 webServer 供後續 E2E 進 CI

**檔案範圍**：
- `.github/workflows/ci.yml`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/e2e/audit/playwright.config.ts`
- `scripts/check_openapi_drift.py`

**平行性論證**：全部是新建檔案 + frontend/package.json（其他 WP 均不碰 package.json）；CI 內容只執行既有測試，不修改任何 src；可最先合併，讓其餘 WP 的 PR 都被守門

### WP6：`refactor/dependency-untangle` 📋 待排程

拆三角依賴：新建 config/universe.py 承接 DEFAULT_UNIVERSE，三隻 strategies/*/research_config.py 改 import 新位置（順帶修 inst_flow n_trials 24→16 或接計數器）；finmind_bundle.py 的 register() 移入顯式 ensure_registered() 只在 zipline CLI 入口呼叫；engines/protocol.py 標記 deprecated 並移除對 is_harness 私有 helper 的依賴；註冊聚合 import 移入 strategies/__init__.py

**檔案範圍**：
- `backtest_platform/src/backtest_platform/config/universe.py`
- `backtest_platform/src/backtest_platform/strategies/__init__.py`
- `backtest_platform/src/backtest_platform/strategies/four_layer_resonance/research_config.py`
- `backtest_platform/src/backtest_platform/strategies/momentum/research_config.py`
- `backtest_platform/src/backtest_platform/strategies/inst_flow/research_config.py`
- `backtest_platform/src/backtest_platform/engines/protocol.py`
- `backtest_platform/src/backtest_platform/engines/zipline_adapter/bundles/finmind_bundle.py`
- `backtest_platform/src/backtest_platform/engines/zipline_adapter/cli.py`
- `backtest_platform/tests/engines/`

**平行性論證**：動 engines/ 與 strategies 的 research_config/__init__；不碰 strategies/protocol.py 與 is_harness（WP7 所有）、parquet_cache.py（WP3 所有）、research/workflows（WP1 所有）——與 WP7 需依序 merge（同屬契約層但檔案不重疊）

### WP7：`feat/gate-per-strategy-dispatch` 📋 待排程

Gate 入契約：strategies/protocol.py 增 GateSpec 宣告（各策略 research_config 或 ClassVar 定義 gate），is_harness run_and_judge / promotion_service / paper_replay / api gate router 的 gate=None 分支改依策略 dispatch（MOMENTUM_GATE 接線）；is_harness 時間戳改注入式 UTC clock、刪 engines/protocol 用的私有 re-export；conformance 補「gate health 指標 ⊆ 策略 metrics keys」斷言

**檔案範圍**：
- `backtest_platform/src/backtest_platform/strategies/protocol.py`
- `backtest_platform/src/backtest_platform/strategies/conformance.py`
- `backtest_platform/src/backtest_platform/research/is_harness.py`
- `backtest_platform/src/backtest_platform/research/promotion_service.py`
- `backtest_platform/src/backtest_platform/research/workflows/paper_replay.py`
- `backtest_platform/src/backtest_platform/validation/gate_state.py`
- `backtest_platform/src/backtest_platform/api/routers/gate.py`
- `backtest_platform/tests/strategies/`
- `backtest_platform/tests/api/`

**平行性論證**：動 strategies/protocol、is_harness、gate_state、gate router；不碰 truth_gate.py/dsr.py/two_stage_gate.py（WP1）、research_config 檔（WP6）、collaborators（WP2）——與 WP1 在 validation/ 目錄相鄰但檔案不重疊（WP1 owns dsr/two_stage_gate，本包 owns gate_state）

### WP8：`docs/prd-v4-and-doc-debt` 📋 待排程

敘事償還：02 PRD v4.0 重寫（正名 edge 驗證工廠、persona 正式化、平台/策略 KPI 分列、決策沿革補 ADR-023~029、standalone 安全假設明文、❌ 清單矛盾收斂）；16 WBS §1/§4/§6/§7 自我對帳；01/05/17/20/22/23 加 tombstone 凍結 banner；doc 25 §6 registry 對齊 /strategies 與 /research/workflows/*；auth 裁決寫成 ADR-031（localhost-only 或 static Bearer 二擇一）

**檔案範圍**：
- `dev_docs/02_project_brief_and_prd.md`
- `dev_docs/16_wbs_development_plan.md`
- `dev_docs/01_workflow_manual.md`
- `dev_docs/05_architecture_and_design_document.md`
- `dev_docs/17_m2_to_m5_master_plan.md`
- `dev_docs/25_fe_be_rest_contract.md`
- `dev_docs/adrs/ADR-031-auth-decision.md`
- `dev_docs/adrs/INDEX.md`

**平行性論證**：純 dev_docs/（不含 21，已歸 WP3；不含 ADR-030，已歸 WP1），零程式碼交集；唯一協調點是 WP1 重驗 inst_flow 後 16 WBS banner 需補一行結果，建議本包最後 merge 收尾
