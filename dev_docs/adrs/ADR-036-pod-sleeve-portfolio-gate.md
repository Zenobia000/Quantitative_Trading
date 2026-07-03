# ADR-036: Pod/Sleeve 多策略架構 — 組合級審判庭判決 + 規則式資本配置

- **狀態**: Accepted（2026-07-03）
- **關聯**: [ADR-022](./ADR-022-fleet-architecture.md)（艦隊）、[ADR-025](./ADR-025-two-stage-validation-gate-and-paper-promotion.md)（SizingGate）、[ADR-030](./ADR-030-truth-gate-judgement-fix.md)（DSR 單位修正）、[ADR-033](./ADR-033-paper-watch-tier.md)（觀察艙）

## 1. 背景與問題

### 1.1 0.9 Sharpe 牆是單策略的，產品目標應該是組合級的

一年來每個 edge family 都撞同一面牆：momentum NO-GO、inst_flow DSR 0.908、reversal 全滅。審判庭判的是**單策略 standalone DSR ≥ 0.95**，但華爾街多策略機構不靠單一英雄策略獲利——靠的是**多個中等 Sharpe、低互相關艙位的分散紅利**：兩個互相關 0.3 的 Sharpe 0.85 艙位，等權組合 Sharpe ≈ 1.1。現行審判庭無法看見這種價值：一個對艦隊正交、standalone DSR 0.91 的候選，和一個與艦隊相關 0.9、DSR 0.91 的候選，判決完全相同（PAPER_WATCH）——但前者對組合的邊際貢獻遠大於後者。

### 1.2 配置層「設計了但零接線」

ADR-025 的 `compute_position_size`（max_weight × conviction × diversification × capacity）與 `fleet_correlation` 已實作並有測試，但**零生產呼叫者**（2026-07-02 審查缺陷）。缺的不是數學，是「誰在什麼時機呼叫、輸出去哪裡」的政策層。

### 1.3 多維度再平衡的兩個嵌套迴圈

使用者的理想形狀：資料卡 → 單策略評估 → 多策略組合（類主動 ETF 季度再平衡：股票汰弱留強 × 策略汰弱留強）。**內圈**（股票層）panel 策略每期 rebalance 本來就在做；**外圈**（策略層資本配置與淘汰）完全不存在。

## 2. 考量的選項

### 選項一：中央化 Alpha 混合（AQR / Two Sigma 式）
策略降格為 alpha（只輸出橫斷面分數、不擁有部位），單一最佳化器合成一個組合，「汰弱」= 權重連續衰減。
**否決**：需要大量同質正交 alpha + Barra 級因子風險模型才有意義；本平台策略異質（four_layer 事件驅動輸出的是事件不是分數，混不進去）、數量 1~3、無 netting 紅利；審判庭的離散判決語意（REAL/PAPER_WATCH/REJECTED）與連續權重衰減語意衝突。

### 選項二：只做組合級指標展示，不改判決
在 GUI 加「組合 Sharpe 模擬」但審判庭照舊。
**否決**：不改變決策就不改變行為——掃 edge family 的目標函數仍是「找英雄」，正交候選仍會被 standalone 門檻殺掉，牆還在。

### 選項三（★採納）：Pod/Sleeve 制 + 組合級判決作為額外證據軸
策略是獨立艙位（sleeve），各自擁有資本配額；審判庭增加**組合級評估**（候選 + 既有艦隊的合成組合走同一套 DSR 機器）；資本配置用 ADR-025 SizingGate 規則式給付，慢速（季度）+ hysteresis + pod 式回撤停損。

## 3. 決策

### 3.1 架構選型：Pod/Sleeve 制
- 策略 = 艙位：獨立資本配額、獨立 P&L 歸因、離散進出艙事件
- 進艙路徑不變：審判庭 REAL → 真資本；PAPER_WATCH → 零資本觀察（ADR-033）
- 本 ADR 只加「組合級證據軸 + 配置政策」，**不放寬任何既有門檻**（standalone REAL 仍需 DSR ≥ 0.95）

### 3.2 組合級判決（portfolio gate）— 證據軸，非後門
`validation/portfolio_gate.py`：
- `combine_returns(sleeves, weights)`：日報酬按日期 inner-join 對齊後加權合成（v1 預設等權）
- 合成序列走**同一條 DSR 數學**（`deflated_sharpe_from_returns`，即 ADR-030 修正後的 per-period 單位路徑，由 truth_gate 的 `_deflated_sharpe` 升格為 `validation/dsr.py` 公開函式——單一真相源，兩處共用）
- `n_trials` 取**候選的** trials 數（艦隊成員已各自通過驗證，其 trials 已在各自判決中通縮過；合成組合的自由度來自候選）
- **判決語意**：組合級結果是**額外證據軸**，記錄於判決 metrics（`portfolio_dsr` / `correlation_to_fleet` / `standalone_dsr`），供晉升決策參考。v1 **不自動改寫** standalone verdict——「正交紅利能否折抵 standalone 缺口」的轉換規則，等第一個真實案例出現再以 ADR 補充（防止在零樣本下設計後門）

### 3.3 資本配置政策（外圈，季度）
- 權重 = `compute_position_size(SizingInput(oos_sharpe, correlation_to_fleet, capacity))`（ADR-025 首個生產呼叫者）
- **Hysteresis**：新舊權重相對變化 < 20% 不動作——防止追著近期 Sharpe 搬資本（街上教訓：那是在策略層高買低賣）
- **Pod 式停損**：`apply_stop_outs`——艙位 live 回撤超過閾值（預設 15%）→ 配額歸零、退回審判庭重驗。離散、殘酷、規則式
- 權重總和不強制歸一：餘額即現金（pod 制的自然語意）

### 3.4 v1 邊界（誠實聲明）
- 艦隊現況 = 1 個零資本觀察艙候選 → 組合級判決在庫存 ≥ 2 前是**建好待用的機器**；不為此阻擋工廠產能主線（掃 edge family）
- run sidecar 無日期索引 → CLI 的跨 run 合成 v1 用**同窗口位置對齊**（長度不符即拒絕），日期化 sidecar 列後續項
- 跨艙風險聚合（heat 加總）、per-sleeve P&L 歸因（orders 表 `strategy_id` migration）為第二艙位前置，不入本 ADR 範圍

## 4. 後果

**正面**：掃 edge 的目標函數從「找英雄」變「找正交」——DSR 0.90-0.95 帶低相關的候選從「邊緣」變「潛在組合資產」，搜尋空間變大；SizingGate 缺陷關閉；配置決策可測試、可審計（純函式）。
**負面/風險**：組合級 DSR 的統計詮釋比 standalone 弱（艦隊固定的條件性），已以「證據軸非判決」語意圍住；hysteresis/停損閾值是先驗設定，待 live 資料校準。
**遺留**：組合級判決自動化進晉升管線的轉換規則（等真實案例）、sidecar 日期化、`strategy_id` migration。
