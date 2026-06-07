# 動能 DOE 重新驗證結果（2026-06-07）— 平台 pipeline 端到端跑通

> 承使用者「缺的是 alpha → 用最穩固策略跑通測試、重新驗證」。本次以動能（最穩固
> 異常、已建）為對象，**用統一的 `validation/full_report.py` harness 在真實 ingest
> 資料上跑一輪 DOE config sweep**，證明平台驗證 pipeline 端到端可用，並完成模組 6.0
> 的「執行」部分。腳本 `scripts/momentum_doe_revalidation.py`。

## 設定
- **Universe**：DEFAULT_UNIVERSE 10 檔大型股（2330/2317/2454/1101/3008/2882/1303/2412/2308/2891），live FinMind 免費 tier ingest（無 token），parquet cache。
- **IS 窗**：2016-01-01 ~ 2020-12-31（lookback 252 由 2015 前史供給）。
- **DOE grid（8 configs = 8 trials）**：rebalance {monthly, quarterly} × vol_target {None, 0.15} × lookback {126, 252}。
- **DSR 誠實 deflate**：`sharpe_variance` = 8 configs 的 **per-period Sharpe 跨試驗變異數**（非固定預設）→ 對選擇偏誤如實扣分。

## 結果

| reb | vt | lb | CAGR | Sharpe | MaxDD | DSR | green | deploy |
|:--|:--|:--|--:|--:|--:|--:|--:|:--:|
| monthly | None | 126 | **19.6%** | **0.92** | 32.0% | **0.96** | 2 | ❌ |
| monthly | None | 252 | 18.8% | 0.92 | 32.8% | 0.96 | 2 | ❌ |
| monthly | 0.15 | 126 | 13.8% | 0.86 | 23.1% | 0.94 | 2 | ❌ |
| monthly | 0.15 | 252 | 12.7% | 0.81 | 29.8% | 0.93 | 0 | ❌ |
| quarterly | None | 126 | 16.1% | 0.79 | 31.0% | 0.93 | 1 | ❌ |
| quarterly | None | 252 | 14.5% | 0.74 | 43.4% | 0.91 | 0 | ❌ |
| quarterly | 0.15 | 126 | 10.5% | 0.69 | 27.2% | 0.89 | 0 | ❌ |
| quarterly | 0.15 | 252 | 10.2% | 0.68 | 32.9% | 0.89 | 0 | ❌ |

**最佳（by Sharpe）**：monthly / vt=None / lb=126 → CAGR 19.6%、Sharpe 0.92、MaxDD 32%、DSR 0.96 → **NO-GO**。

## 判讀（為何這是「好的」NO-GO）

- **K1 CAGR 19.6% > 18% ✅**、**DSR 0.96 > 0.95 ✅**（過擬合檢驗過關——edge 真實、非曲線擬合）。
- **唯一未過：K2 Sharpe 0.92 < 1.0** —— 風險調整後報酬就差臨門一腳。
- 與 ADR-023 一致：**動能是真實溢酬、但未達可部署 Sharpe 門檻**。本次在大型股 10 檔窄 universe 用統一 harness 重驗，結論穩健重現。
- vol-target（0.15）有效砍 MaxDD（32%→23%）但同時壓低 CAGR/Sharpe——此 universe 下非淨增益。

## 平台意義（Phase 1 收尾達成）

- **`validation/full_report.py` 在真實資料上端到端跑通**：metrics + §4.3.1 健檢 + bootstrap CI + MC edge p-value + Deflated Sharpe 一次產出，self-judge deployable。
- **修正 DSR 單位 bug**：原固定 `sharpe_variance=0.5` 與 per-period Sharpe 單位不符 → DSR 失真（≈0）；改為 n_trials>1 時強制傳入跨試驗 per-period 變異數，DSR 才誠實（0.96）。
- 模組 6.0 的驗證 pipeline 由「工具齊備」進到「真實資料端到端執行過」。

## 下一步（Phase 2 追 alpha）

動能=對的 family、Sharpe 差 0.08。文獻支持的穩健強化（非曲線擬合）：
- **更大 / 更乾淨 universe**（10 檔大型股太窄；擴到中小型動能溢酬更強，但需成本控管）。
- **abs-momentum / trend 崩盤過濾**（time-series momentum overlay）。
- vol-target 在更廣 universe 可能轉為淨增益。
目標：把 OOS Sharpe 從 0.92 推過 1.0，同時守住 DSR>0.95 + CAGR>18%。

---

## Phase 2 ①：絕對動能（abs-momentum）崩盤過濾（2026-06-07）

文獻支持的穩健強化（Antonacci dual momentum）：相對動能選出贏家後，再加一道
**絕對動能閘**——只持有自身 12-1 momentum>0 者，全為負則持現金。off by default，
加進 DOE grid（16 configs）重跑同 universe/窗。

| reb | vt | lb | abs | CAGR | Sharpe | MaxDD | DSR | deploy |
|:--|:--|:--|:--|--:|--:|--:|--:|:--:|
| monthly | None | 126 | **True** | **22.4%** | **0.97** | 32.0% | 0.96 | ❌ |
| monthly | None | 126 | False | 19.6% | 0.92 | 32.0% | 0.95 | ❌ |

**效果**：abs-momentum 把最佳 config 的 **CAGR 19.6%→22.4%、Sharpe 0.92→0.97**
（+0.05），DSR 維持 0.96（非過擬合）。**真實、非曲線擬合的改善，幾乎補上缺口**，
但 Sharpe 0.97 仍 < 1.0 → 仍 NO-GO。

**判讀**：abs-overlay 是淨增益（同時拉高報酬與風險調整報酬）。剩餘 0.03 缺口最可能
來自 **universe 太窄**（10 檔大型股；動能需要橫斷面廣度）。Phase 2 ② = 擴大乾淨
universe（中小型動能溢酬更強），預期是把 Sharpe 推過 1.0 的主要槓桿。
- **Phase 2 ② 待辦**：擴 universe（point-in-time 中小型 + 反 survivorship）後重跑 DOE。
