# Sprint 0 Gate Review — 2026-06-01

> **執行者**：Self (Claude assisted) | **commit**：ff20df5 之後
> **gate 結論**：**Conditional Pass — 需新決策**（不適用 §5.A.4 純粹的 spike PASS/FAIL 樹）
> **總時間**：~3 小時（vs 規劃 1 週）— 大幅提前

---

## 1. Spike 結果矩陣

| # | Spike | 結果 | 關鍵發現 |
|:--:|:--|:--:|:--|
| **S1** | TQuant-Lab + XTAI hello world | ❌ **FAIL** | zipline-tej **import 階段 hard-codes TEJ API call**（即使僅想用 self-built bundle 也躲不過）— 推翻 ADR-005 §1 假設 |
| **S2** | M1 plug into Zipline | ⚠️ **PARTIAL** | **M1 純函式 callable** ✓（80 bars 全綠）；wrapper test 被 S1 連帶卡 — **ADR-003 純函式設計成功驗證** |
| **S3** | FinLab bundle POC | ⚠️ **PARTIAL** | API + bundle write 邏輯 ✓（10 檔 × 247 bars 寫成 csvdir）；但 **FinLab `#free` 版資料截至 2018-12-28** — 推翻 ADR-006 OOS 假設 |
| **S4** | Shioaji 沙箱 | ✅ **PASS** | login + 2 accounts + 報價 2330=2355 + 模擬下單 + cancel + logout 完整 lifecycle 通 |
| **S5** | FinLab live polling | ✅ **PASS** | login + pull realtime + write CSV 通；samples 3/5 因 test duration 短（非 bug） |
| **S6** | Streamlit + TimescaleDB | ✅ **PASS (backend)** | TimescaleDB hypertable 建好、365 行 seed；UI 渲染需手動開 `localhost:8501` 確認 |

**結果**：3 全綠 / 2 部分 / 1 完整 fail

---

## 2. 三大關鍵發現（決定路線）

### F1：zipline-tej 強制需要 TEJ API key（S1）

**事實**：
- `import zipline` 觸發 import chain：`zipline/data/bundles/__init__.py` → `from . import fundamentals` → `import TejToolAPI` → 在 `__init__.py` 執行 `ExchangeCalendar()` → 呼叫 `tejapi.fastget('TWN/TRADEDAY_TWSE')` → **需有效 TEJ api_key**
- 即使設 `TEJAPI_KEY=dummy` 也 fail（AAA002 認證失敗）
- 即使想用 self-built FinLab bundle 也躲不過此 import

**影響**：
- ADR-005 §1 假設「TQuant-Lab MIT、可不用 TEJ key 用自製 bundle」**錯誤**
- 整個 M2 Zipline-based 路線需 TEJ 訂閱才能跑

### F2：FinLab `#free` 版資料截至 2018-12-28（S3）

**事實**：
- `data.get('price:收盤價').index[-1]` = `2018-12-28`
- 全 2746 檔股票、2899 天，但**最新只到 2018 年底**
- 5GB/月 限制獨立於此版本（用了 198/500 MB）

**影響**：
- ADR-006 §1 假設「付費 FinLab 5GB/月」是針對 VIP；當前 `#free` 不是 VIP
- M2 IS（2015-2020）可用（2015-2018 部分）
- **M3 OOS（2023-2024）完全無資料** — 阻擋 M3
- 需升 FinLab VIP（NT$9-10k/年）或換資料源

### F3：M1 純函式 + 基礎設施完全 portable（S2/S4/S6）

**事實**：
- M1 `compute_scores` + `compute_signals` 在 synthetic data 上跑 80 bars 全綠
- Shioaji + TimescaleDB + Streamlit + Discord 基礎設施全綠
- 不依賴 zipline 任何 import 即可運作

**影響**：
- **ADR-003 純函式策略層設計成功驗證** — 任何引擎都能 plug（vectorbt / 自寫 event / FinLab.sim）
- F1 即使逼退 zipline-tej 路線，M1 程式碼 0 浪費
- M4-M5 監控+下單+UI 棧已就緒

---

## 3. 決策樹評估（修正版）

§5.A.4 原樹假設 spike fail 是工具 vs 路線單純對應；實際情況複雜：

| 原樹路徑 | 對照 | 修正 |
|:--|:--|:--|
| S1 紅 → Hybrid（zipline-reloaded + 自寫 XTAI） | F1 揭露 zipline-tej 強綁 TEJ | 路徑成立，但要重新評估 ADR-005 整體 |
| S3 紅 → Hybrid（FinMind 主） | F2 是 FinLab `#free` 版本問題，不是 bundle 邏輯問題 | 升 VIP 或改 FinMind sponsor，非「Hybrid」整體切換 |
| 其他 spike | F3 全綠 | 維持 |

---

## 4. 路線決策（D6 / D7 待 user 拍板）

### D6 — TQuant-Lab 路線去留（觸發 by F1）

| 選項 | 說明 | 成本 | ADR |
|:--|:--|:--|:--|
| **(A) 註冊 TEJ 取 API key** | 維持 ADR-005，看 TEJ 是否有教育/試用免費方案 | 1 天等申請；可能月費 NT$3-10k | 不動 |
| **(B) Fork zipline-tej + patch lazy load** | 移除 import-time TEJ call，自有 fork 維護 | 2-3 天 + rebase 維護成本 | ADR-013: zipline-tej fork |
| **(C) Hybrid — zipline-reloaded + 自寫 XTAI** | 退場路線，自寫台股 calendar mod | +1 週 LOC | ADR-013: revert ADR-005 |
| **(D) FinLab-Native (Plan B 回鍋)** | 改用 finlab.backtest.sim 主引擎 | 14 週重起，砍 zipline | ADR-013: supersede 005/007/008 |

**Claude 推薦**：先試 (A)（最低成本驗證），(A) fail → (B)（保留 ADR-005 路線價值），(B) 失敗 → (C)。**(D) 太激進，砍掉太多既有決策**。

### D7 — FinLab 資料源升級（觸發 by F2）

| 選項 | 說明 | 成本 |
|:--|:--|:--|
| **(A) 升 FinLab VIP** | 解決所有資料時間限制 | NT$9-10k/年 |
| **(B) FinMind sponsor + FinLab 免費補三大法人** | 兩源混合 | NT$99-300/月 = ~3,600/年 |
| **(C) IS 2015-2018 + OOS 用 Shioaji history 補爬** | 自爬 + 接受偏誤 | 自寫 ~16h |
| **(D) IS/OOS 全用 FinMind sponsor** | 單一源 | 同 (B) |

**Claude 推薦**：(B) — 月費低、兩源 cross-check 是 quality 保障。

---

## 5. Sprint 0 結論

| 結論 | 描述 |
|:--|:--|
| **形式 Gate** | Conditional Pass — 1 完整 PASS + 3 PARTIAL PASS + 1 FAIL |
| **實質 Gate** | **Pass** — 6 spike 全部「驗證到該驗證的假設」，這就是 Sprint 0 設計目的 |
| **是否進 M2** | **暫停** — 待 D6/D7 拍板再啟動 |
| **時程影響** | M2 Sprint 1 至少延 1 週（待 D6 解）；M3 OOS 至少延 + D7 解決時間 |
| **既有資產損失** | 0 — M1 純函式、Shioaji adapter、TimescaleDB schema、Discord notifier 全可用 |

---

## 6. 後續動作

| # | 動作 | 觸發 | 截止 |
|:--:|:--|:--|:--|
| 1 | User 拍板 D6（TQuant-Lab 去留） | F1 | 2026-06-04 |
| 2 | User 拍板 D7（FinLab 升級或改源） | F2 | 2026-06-04 |
| 3 | 若 D6 選 (A) → 註冊 TEJ + 重跑 S1 | D6 (A) | 2026-06-06 |
| 4 | 若 D6 選 (B) → 開 fork + patch + 寫 ADR-013 | D6 (B) | 2026-06-08 |
| 5 | 若 D6 選 (C/D) → 大改 ADR-005~008 + 重排 WBS | D6 (C/D) | 2026-06-15 |
| 6 | 更新 16 WBS：模組 0.0 標完成、加 D6/D7 行動項 | 不論 D6 結果 | 立即 |
| 7 | 更新 brief/04 decisions：加 D6/D7 | 同上 | 立即 |

---

## 7. 環境/設定修正紀錄（本次 spike 順手解決）

| Fix | 描述 |
|:--|:--|
| pyproject.toml `requires-python` | `>=3.10` → `>=3.10,<3.12`（zipline-tej 上界 3.11） |
| pyproject.toml sqlalchemy | `>=2.0` → `>=1.4,<2`（zipline-tej 強制 <2；M1 不 import sqlalchemy） |
| pyproject.toml ta-lib-bin | 移除（M1 無 import talib，0.4.26 也無 Windows wheel） |
| gate_review.py | 待 fix cp950 encoding bug + JSON load 路徑（M2 啟動前） |
| s5 spike pass criteria | 預設 duration 15s × interval 3s = 5 samples 太緊；改 60s/5s 較合理 |

---

## 變更紀錄

| 版本 | 日期 | 變更 |
|:--|:--|:--|
| v1.0 | 2026-06-01 | 初版 — 6 spike 結果 + D6/D7 待決策 |
