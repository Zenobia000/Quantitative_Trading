# Frontend Reset — Playwright Screenshot Audit 審查與簽核

- **日期**: 2026-07-05
- **審查者**: Codex
- **標的**: `dev_docs/ui_audit/codex_2026-07-05/`（Codex UI audit run 產生的 23 route × 3 viewport 截圖 + `manifest.json`）
- **對應 WBS**: `18_refactor_wbs.md` §7.5「Playwright screenshot audit 完成」；FE-R5 交付項
- **對應驗收**: §7.4 Codex-style operations console 驗收準則

## 1. 方法

已用 `frontend/e2e/audit/screenshot.config.ts`（`npm run audit:screens`）對重設計後的前端跑過截圖 audit，涵蓋 desktop(1440)/laptop(1280)/mobile(390) 三 viewport、23 條 route，輸出至 `codex_2026-07-05/`。本文件補上 audit review：解析 `manifest.json` 全 route 狀態 + 逐 viewport 目視關鍵頁面，對照 §7.4 Codex-style 驗收準則出結論。

## 2. 關鍵發現：audit 在「後端全 500」的降級狀態下截圖

`manifest.json` 顯示 **23/23 route 皆 `error_or_degraded`**，且**每一個後端 API endpoint 都回 500**（`/strategies`、`/runs`、`/monitor/*`、`/research/*`、`/system/*`、`/home/*`、`/gate/spec` 全掛；另 `runId: NO_RUN_SEEDED` / `reportEvaluationId: NO_EVAL_SEEDED`）。

**根因 = audit 環境，非前端缺陷、非後端 code bug：**

- API 需 PostgreSQL（`config/settings.py` + `require_postgres` 拒絕 shipped 預設密碼）。本次 audit 後端（`127.0.0.1:8083`）未接上可用的 Postgres/seed，故所有 DB-backed endpoint 500。
- 後端 code 本身健康：`pytest -o addopts=""` **1443 passed / 3 skipped / 0 failed**；`lint-imports` 3 kept / 0 broken；`check_openapi_drift.py` `[OK] live spec matches frontend/openapi.json`。
- 前端未 crash：**23/23 route `isNotFound: false`**，無白屏。

## 3. 逐 viewport 目視結論（對照 §7.4）

即使後端全 500，重設計後的前端在三個 viewport 都**正確渲染並優雅降級**：

| §7.4 驗收準則 | 判定 | 證據 |
| :--- | :--: | :--- |
| Seven-layer IA（Data/Research/Governance/Trading/Risk/Operations/System 一等區） | ✅ | 左 rail 七層分區（資料/研究/治理/交易/風控/營運/系統），每區帶鍵位提示 |
| Top market/risk status bar | ✅ | 交易日 EOD · 風控 CLEAR · 資料 PENDING · 模式 PAPER 常駐頂列 |
| Dense first、無行銷 hero | ✅ | Command Center 為密集 grid（RISK LOCK / MODE / DATA BUNDLE / BROKER）+ Layer Readiness 八格，非行銷卡片 |
| Low-latency 視覺語言（深色台、細格線、monospace 數字、有限功能色） | ✅ | near-black 底、hairline 格線、tabular monospace 數字、gain/warn/crit 有限色 |
| Evidence over decoration / pending 不造假 | ✅ | 「SOURCE: GOLDEN SEVEN-LAYER CONSOLE」as-of 標註；deferred producer 明示「端點尚未接線，先不顯示數字」不捏造 |
| Risk visible / graceful error | ✅ | 500 以行內「載入失敗：伺服器回應異常（500）」+「重試」呈現，不白屏、不吞錯 |
| 響應式（mobile） | ✅ | mobile 收成單欄 + MENU rail 收合，狀態列保留，無水平捲動 |

**目視樣本**: `laptop/home.png`、`laptop/research_strategies.png`、`mobile/home.png`（模式一致，其餘 route 同構）。

## 4. 簽核

- **Frontend reset 重設計（§7.4 shell / IA / 美學 / 韌性）：✅ PASS。** 三 viewport × 23 route 一致達標；重設計甚至以「500 優雅降級」反證了 §7.4「pending 不造假 / graceful」原則。
- **限制（誠實揭露）**：本 audit 在後端全 500 下截圖，故只驗到 **shell / IA / error / pending / empty** 狀態；**populated dense ledger/table 的資料密度未被實測**（需 seeded 後端）。此與本專案既有「data-state baseline」audit 慣例（commit `8bab301`）一致。

## 5. 後續（follow-up，非本簽核阻塞項）

1. **Seeded happy-path 重跑（選作）**：`docker-compose up` Postgres + 設真 `POSTGRES_PASSWORD` + migrate + seed（runs/evals/strategies）+ 隔離 port 重跑 `audit:screens`，補驗 populated ledger 密度。因需 evaluate pipeline seed（本次亦 `NO_RUN_SEEDED`），建議於乾淨窗口執行，避免多 session 搶 port/DB。
2. **`dev_docs/25_fe_be_rest_contract.md` 缺檔**：使 `check_openapi_drift.py` 一項 inventory 檢查 ERROR（pre-existing，與本次無關），待補。

## 影響評估

- **嚴重度**: LOW（無阻塞缺陷；redesign 通過簽核）
- **影響範圍**: 前端 FE-R5 audit 交付項完成審查半場；WBS §7.5 最後一項可打勾（附 populated-data 限制註記）
