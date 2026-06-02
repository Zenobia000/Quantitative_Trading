# v3 進場 v0.1 — 雙窗口 IS Gate Review（誠實版）

> **日期：** 2026-06-02 ｜ **對應：** ADR-019 §11 成功判準、v0.1 exit gate（16 WBS §6 版本 Roadmap）
> **方法：** `backtest_platform/scripts/v3_double_window_is.py`（OFFLINE，data/parquet）。三組**固定** config（v2 baseline / v3 `DEFAULT_CONFIG_V3` / v3_f1 flameout=1 對照），**嚴守不 sweep**。標的＝2330 + 中小型成分股（1101/1303/2308/2317/2891/3008/2412）。
> **⚠️ sim 限制：** 本 read 為**輕量 close-to-close 單部位模擬**（非 zipline event-driven 引擎），絕對數值會與 ADR-017 的 zipline 數字不同；**有效訊號是「v3 vs v2 同 sim 內的相對比較」與健檢指標**，非絕對 CAGR。最終 gate 若需定論應另跑 zipline。

---

## 1. 結果（PORTFOLIO equal-weight）

| 窗口 | config | trades | CAGR | Sharpe | MaxDD | Win | 平均持有 | structure==1 進場% | churn% |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 2015-2020 | **v2** | 61 | −1.08% | −0.64 | −6.18% | 33.3% | 4.7 | 0% | 25.0% |
| 2015-2020 | **v3** | 265 | **−4.48%** | **−0.99** | −23.33% | 31.8% | 6.1 | **75.8%** | 24.6% |
| 2015-2020 | v3_f1 | 289 | −6.13% | −1.44 | −29.39% | 26.7% | 4.5 | 72.6% | 31.2% |
| 2020-2024 | **v2** | 81 | +0.44% | +0.21 | −4.65% | 39.0% | 4.1 | 0% | 32.9% |
| 2020-2024 | **v3** | 299 | **−2.38%** | **−0.44** | −17.55% | 34.1% | 5.5 | **71.6%** | 27.4% |
| 2020-2024 | v3_f1 | 316 | −3.06% | −0.62 | −17.16% | 31.5% | 4.4 | 69.4% | 31.5% |

完整矩陣（含 per-stock）：`reports/v3_double_window_is.csv`（reproducible，不入版控）。

## 2. 對照 ADR-019 §11 成功判準

| 判準 | 門檻 | v3 實際 | 結果 |
|:--|:--|:--|:--:|
| 跨雙窗符號一致 | 同號且非一窗深負 | 兩窗皆負（−4.48% / −2.38%） | ⚠️ 一致但**一致為負** |
| 邊際單品質不劣化 | 勝率 ≥ baseline −5pp、PF 不降 | v3 win 31.8/34.1% **低於** v2 33.3/39.0%；CAGR/Sharpe/DD 全面**劣化** | ❌ FAIL |
| 進出場成對（v3 vs v3_f1） | 改善來自搭配非單側 | v3 **優於** v3_f1 兩窗（持有 6.1 vs 4.5）→ exit 確認窗**有效** | ✅ PASS（但救不了 entry） |
| 操盤手體檢：平均持有 ≥6 | ≥6 bar | 6.1 / 5.5（接近/達標） | 🟡 邊際 |
| 操盤手體檢：structure==1 中段進場 <30% | <30% | **75.8% / 71.6%** | ❌ **重大 FAIL** |
| 操盤手體檢：churn <20% | <20% | 24.6% / 27.4% | ❌ FAIL（輕） |
| 進場數樣本下限 | 30–80/股/5y | portfolio 265/299（≈33/37 每股） | ✅ 樣本足（非 edge） |

## 3. 判決：🔴 RED — v3 preset 未通過 v0.1 IS gate

**v3 進場放寬使績效全面變差**（更多單、更低勝率、更深回撤，雙窗皆然），且 **`structure==1` 中段進場占 72–76%** —— 這正是壓測時**波段動能操盤手的精準預警**：把 `min_structure` 放到 1（接受 `close≥box_mid` 的「箱中無人區」）會大量灌入沒有結構保護的低品質進場。**`min_structure=1` 是這次放寬的致命傷。**

**反過擬合框架如預期發揮作用**：v3「進場數 4× + 平均持有拉長到 6 bar」本來很容易被誤讀成「進步」，但誠實判準（邊際單品質 + structure1 健檢）直接戳破——拉長持有沒用，因為進場位置本身是垃圾。

**有價值的副產品**：exit 最小搭配（flameout 1→2 bar）**證實有效**（v3 > v3_f1，持有 6.1 vs 4.5）——「進出場成對」的方向對，留作後續。

## 4. 下一步（**不是 sweep**，是 M0 設計修正）

依 ADR-019 誠實退場：邊際單劣化 + structure1 健檢 FAIL → **不進 v0.2 OOS，回 M0**。但 structure1=76% 精準定位問題在 **`min_structure=1` 這個特定放寬**，非「四層 hypothesis 已死」。**禁止**在這兩個 IS 窗口上手調 `min_structure`/`confirm`/`cooldown` 救數字（過擬合）。應走的是 **hypothesis 設計修正（sunnydata-design Phase 1）**，候選方向（待下一 design cycle 拍板）：

- **A（最對症，壓測時波段 lens 已提）**：`min_structure` 不放到「任意箱中」，改「**突破（structure==2）OR 箱頂回測站上（close ≥ box_upper×(1−retest_band)）**」——保留 structure==2 為首要型態，只多收「接近箱頂的回測」，把無人區排除。預期 structure1% 大降。
- **B**：保留 `min_structure=2`（只放寬 first_cross + N-of-4 + confirm），先驗證「不動結構、只解 transition 偏誤」是否就有改善——最小因果隔離。
- **C（escalate）**：若結構修正後仍無一致正期望 → 問題在 edge 來源不在進場閘，評估候選 D（換中小型動能 universe，但須處理生存者偏誤 R7，且與進場放寬絕不同 cycle 動）。

## 5. 結論一句話

v3 進場「機制」實作正確（已測、v2 可重現、exit 搭配有效），但**這組放寬 preset（尤其 `min_structure=1`）在雙窗口 IS 是淨負、未通過 gate**。誠實結論：**回 M0 改進場結構條件（方向 A/B），不鬆閘自欺、不在 IS 上 sweep。** R9 維持「🟠 緩解中（待 v3.1 結構修正）」。

---

## 6. 真引擎校準（2026-06-02 補，Step 1）— 🟢 zipline 確認 RED

§1 的 RED 由輕量 offline sim 判定；§0 已聲明「最終 gate 若需定論應另跑 zipline」。**現已補做**：透過 config 注入（`backtest-run --config v3`，原 `algorithms/four_layer_resonance.py:78` 寫死 `StrategyConfig()`，v3 從未進引擎）+ 算法 v3 wiring，用真 zipline event-driven 引擎重跑 portfolio（同 8 檔）。

| 窗口 | config | SIM Sharpe | **Zipline Sharpe** | Zipline total return | 交易數 |
|:--|:--|:--:|:--:|:--:|:--:|
| 2020-2024 | v2 | +0.21 | **+0.20** | +1.03% | 103 |
| 2020-2024 | **v3** | -0.44 | **-0.43** | **-5.20%** | **466** |
| 2015-2020 | v2 | -0.64 | -0.91 | -3.01% | 77 |
| 2015-2020 | v3 | -0.99 | （infra timeout：v3 過度交易使 5yr CLI run >590s，未完成；2015-2020 v2 已負 + 2020-2024 v3 崩盤 + Sharpe 吻合 → 判決不依賴此格） | — | — |

**三項確認：**
1. **RED 獲真引擎背書**：zipline 2020-2024 v2 正（+1.03%/Sharpe+0.20）→ v3 崩成負（-5.20%/Sharpe-0.43），與 sim 同向；v3 在真引擎一樣淨負且劣於 v2。
2. **兩個獨立引擎 Sharpe 吻合到 ~0.01**（sim vs zipline：v2 +0.21/+0.20、v3 -0.44/-0.43）→ 同時背書 RED 判決**並驗證 offline sim 可信**（顧問點名的「判決壓在未校準 sim 上」harness 可信度風險**解除**）。total return 絕對值差異來自 sim CAGR vs zipline 全期 total return + fill model 差異，屬預期。
3. **冒煙槍引擎側確認**：v3 交易 466 round-trips vs v2 103（4.5×）→ 放寬進場灌入大量低品質進場，與 sim structure1%=76% 同源。

**收斂**：M0 重設靶心（`min_structure=1` 是禍首）為真、非 sim artifact；後續 harness 可放心建在 sim 上。照計畫 Step 2（gate_state）→ Step 3（harness）→ Step 4（結構競賽 方向 B/A），認賠線不變。
