# Quantitative_Trading

四層共振戰法 — 台股中小型股的短中期波段量化交易策略研究專案。

> ⚠️ **此專案為策略研究紀錄，非投資建議。**
> 所有策略假設與門檻**尚未通過實證驗證**。實盤前需完成 `strategy/research/doe_research_template.md` 全部 DOE。

---

## 專案目標

驗證假設：**台股中小型股的短中期波段，受四種獨立力量同時推動時，會出現高機率的續漲行情。**

| 層 | 維度 | Edge 假設 |
| :--- | :--- | :--- |
| L1 | 結構 | 突破壓力區 → 賣壓被消化 |
| L2 | 法人方向 | 外資+投信同步買 → 資金共識 |
| L3 | 籌碼強度 | 主力買盤占有效成交量 > 10% |
| L4 | 技術動能 | 多均線多頭排列 + 動能指標同向 |

詳見 [`strategy/v2.md`](strategy/v2.md)。

---

## 目錄結構

```
.
├── strategy/                          # 策略規格與研究
│   ├── v2.md                          # 主規格書（v2.1.0）
│   └── research/
│       ├── v2.2_ic_test_plan.md       # IC 驗證計畫
│       ├── doe_research_template.md   # 完整 DOE 模板（10 個 DOE）
│       └── scripts/
│           ├── finmind_poc.py         # FinMind 資料源 POC
│           └── README.md
├── backtest_platform/                 # 回測平台（建置中）
│   ├── src/
│   ├── tests/
│   ├── docker/
│   ├── docker-compose.yml
│   └── pyproject.toml
└── .claude/                           # Claude Code 設定（agents/rules/skills）
```

---

## 當前狀態

> **狀態真相源**：[`dev_docs/16_wbs_development_plan.md`](dev_docs/16_wbs_development_plan.md)
>
> 本 README 不再重複寫 milestone 進度，避免不一致。WBS 為單一狀態源，每週更新一次。

快覽（詳細見上方連結）：

| 階段 | 狀態 |
| :--- | :--- |
| M0 策略規格 | ✅ v2.1.0 |
| M1 資料 + 策略骨架 | ✅ 完成 (44 unit tests 全綠) |
| M2 預備 (Sprint 0 scaffolding + 結構重組 + Discord) | ✅ 完成 |
| M2 Sprint 0 spike 執行 | ⏳ 待跑 |
| M2 IS 回測 | ⏳ |
| M3 OOS + 統計驗證 | ⏳ |
| M4 Paper Trading | ⏳ |
| M5 實盤 | ⏳ |

---

## 介面

三種介面，完整規範見 [`dev_docs/06_api_design_specification.md`](dev_docs/06_api_design_specification.md)：

- **CLI（Click）** — ETL / 回測 / 研究迴圈（`run-is` / `runs` / `sweep` / `compare`）
- **Python API** — pure functions + Pydantic models（程式內呼叫）
- **HTTP API（FastAPI，v0.6）** — 研究迴圈 + 驗證後端的 HTTP 投影：

  ```bash
  uv sync --extra api
  uv run uvicorn backtest_platform.api.app:app --reload --port 8000
  # OpenAPI 文件： http://localhost:8000/docs
  ```

  端點：`/runs`（ledger 讀寫 + `/compare`）、`/gate`（審判庭 spec/evaluate）、
  `/metrics`（A/B/C/E 指標）、`/presets`。統一信封 `{success,data,error,meta}`，詳見 06 §9。

---

## 核心哲學

引用 Linus 式實用主義：

1. **解決真實問題** — 不為理論完美而堆疊條件
2. **消除特殊情況** — 沒有 if/else 例外才是好品味
3. **不破壞既有部位** — 風控訊號永遠優先
4. **驗證 > 直覺** — 所有條件必須能在歷史資料上量化驗證

---

## 開發紀律

- **預註冊（Pre-registration）**：所有 DOE 跑前鎖死假設、設計、通過標準
- **OOS 一次性**：Out-of-Sample 驗證資料用過不再用
- **誠實記錄 N**：所有測試組合數記入 `experiment_log.md`，用於 DSR 計算
- **失敗即止**：上層 DOE 失敗，下層不必跑

---

## License

MIT — 但請注意策略本身**未經驗證**，任何使用造成的損失自負。

---

## 致謝

策略研究方法論受以下啟發：
- López de Prado《Advances in Financial Machine Learning》— PBO、CSCV、DSR
- Grinold & Kahn《Active Portfolio Management》— IC、IR 框架
- Van Tharp《Trade Your Way to Financial Freedom》— R-multiple、position sizing
- Linus Torvalds — 實用主義、good taste、never break userspace
