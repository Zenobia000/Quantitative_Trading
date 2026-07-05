# ADR-R01: backtest_platform 重定位為第 2 層 research_validation service（採 Option B 而非綠地重建）

> 狀態: Accepted | 日期: 2026-07-05 | 決策者: refactor 任務

## 背景

Golden `16_wbs` 宣稱「乾淨新建」（greenfield，M1–M6），並標示當前進度僅「M0 文件 baseline」。但實況相反：163 檔的 `backtest_platform` package 已是可運作、80% 覆蓋、UI 已接的**第 2 層 Research & Validation** 平台（run ledger、evaluation profiles、DSR/PBO/WFA gates、DOE/truth-gate workflows、五個策略、TargetPortfolio sizing），另加真實且 load-bearing 的第 3–7 層 bleed（paper daemon、risk gate、monitoring、Discord alerts）。

## 決策

採 **Option B**：保留既有已測試/已打包的 `backtest_platform` 作為 `services/research_validation` 的 seed，用 **import fitness function 鎖住第 2 層邊界**，逐叢集抽離越層碼；**不**綠地重寫到全新 `quant_platform/` 樹。

## 理由（Linus 實用主義）

- Theory (greenfield) loses to practice：重寫等於數月工作，且會 break userspace（after-close paper daemon、frontend、CI），近期產品價值為零。
- 本 session 用最低風險換取最大 golden 對齊：刪死碼 + 鎖邊界 + 抽第 3 層 governance。
- 大型物理搬移（monorepo、per-service clean-arch 拆分）在邊界被命名並用 fitness function 鎖住後是**機械式**工作，延後到 M1–M2，並在綠色 fitness wall 之後執行。

## 後果

- 所有模組須標示所屬 golden 層。
- `backtest_platform` import path 短期維持可用；物理搬移分波、一 service 一 PR。
- 補 golden ADR-002（backtest_platform 僅屬 Research）的可執行落地路徑。
- 覆蓋 [18_refactor_wbs](../18_refactor_wbs.md) 全波次。
