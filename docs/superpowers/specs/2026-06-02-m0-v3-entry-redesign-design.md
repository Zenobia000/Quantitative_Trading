# v3 進場重設設計 spec — 放寬四層進場 + 最小 exit 搭配

> **狀態：** 設計定稿 / 待 Sprint 4-6 v0.1 實作
> **日期：** 2026-06-02
> **觸發：** [[ADR-017]] M2 IS gate FAIL → 回 M0 重設進場
> **前置：** `docs/superpowers/specs/2026-06-02-m0-entry-redesign-scope.md`（證據包）
> **決策授權：** 使用者授權「站在操盤手角度代為決策」，經四交易視角壓測收斂
> **相關：** `strategy/v2.md` §2.4 / §2.5、ADR-016（gate KPI）、16 WBS §5

---

## 0. 一句話定調

四層共振策略**進場過嚴**（5 年 14 次進場、勝率 50%、在市場 3.9%、平均持有 3.4 bar），於雙 IS 窗口皆無 edge。v3 **放寬現有四層進場（保留四層 hypothesis）+ 搭配最小 exit 鬆綁**，方法=**參數化分級放寬 + 一組操盤手先驗預設**。本 spec 是可直接落檔的定稿，含 layer_policy、exit 決策、凍結清單、防自欺成功判準。

**核心紀律（反過擬合 + 反發散）：v0.1 只跑一組先驗預設、不在雙窗口 IS sweep；進場數是參與度非 edge；雙窗口 IS 非 OOS；綠燈只代表『值得進 OOS』非『有 edge』。**

---

## 1. Architecture — 放寬發生在哪一層

scoring.py（`compute_scores`，四層分數）**完全不動**——v3 是放寬**進場 gate**，不重寫 scoring。改動集中在：

| 層 | 檔案 | 改動 |
|:--|:--|:--|
| Config | `config/strategy_config.py` | 新增 6 欄位（4 進場旋鈕 + 2 固定守門），附 v2 預設 |
| 進場 gate | `strategies/four_layer_resonance/signals.py` `_evaluate_priority` `buy_sig`(L306-313) | 五重 AND → 必含層+可選結構 + confirm + cooldown + 負向 veto |
| 出場（最小搭配） | 同上 `flameout`(states L51) / `exit_sig`(L271) | flameout momentum 觸發加 2-bar 確認窗；硬停損不動 |
| preset | config | v2/v3 兩組預設；v2 regression test 釘死 baseline 14 次進場 |

**為何改 gate 不改 scoring：** ADR-017 已證根因在進場 hypothesis 的 gate 收斂（`structure==2` + `prev_total<5` + 五重 AND），非分數計算。scoring 不動使放寬可追溯、可關閉、可對照。

---

## 2. 根因錨定（壓測校正）

scope §2.4 證據包，經 code 實證校正後的**真正收斂主力**：

- `state_strong_buy`（signals.py L52-58）用 `>=1` 非 `==2`，已含 `total>=5` → 188 天。
- 進場僅 14 次的收斂主力是 `buy_sig`（L306-313）的三道 transition gate：**`structure_score==2`**（箱型完美突破）AND **`prev_total<5`**（單日首次站上）AND `edge_ok`。
- **抱不住**：`state_flameout` 464 天 ≫ strong_buy 188 天，`flameout=(momentum_score==-1) OR (close<box_lower)` 單一動能層回落即出 → 平均持有 3.4 bar。

> **校正紀錄（壓測發現）：** 提案文字把「四層全 AND」講成進場稀主因，但實證上 `structure==2` + `prev_total<5` 才是收斂主力。v3 放寬目標已對準這兩道閘（structure 2→1、first_cross True→False），非空放四層計數。

---

## 3. layer_policy 決策 — 必含層 + 可選層（非純計數、非加權）

**放行充要條件（硬不變式）：**

```
momentum_score >= 1                                  # 必含:動能(強制守門,不豁免)
AND structure_score >= 1                             # 必含:結構(close>=box_mid)
AND (direction_score >= 1 OR chip_score >= 1)        # 必含:機構共識至少一邊背書
AND total_score >= 5                                 # 算術品質地板(凍結)
AND edge_ok                                          # 成本/波動地板(凍結)
AND NOT (direction_score==-1 OR chip_score==-1)      # 負向 veto hard floor
```

`entry_min_layers=3` 作為**冗餘的 N-of-4 計數上限門**（與必含層 AND 並存，且 IS 讀片記錄 N-of-4 命中分布）。

**理由（實證支撐，駁回原始對等 N-of-4 純計數）：**

1. **L2⊂L3 非獨立**：`chip_total` 公式（scoring.py L80-88）含 `foreign_buy + trust_buy`（L2 的兩輸入原封進 L3），2330 Pearson=0.615。等票計數把同一筆法人資訊**雙重計入**，v2.md §2.1.1「四獨立力量→70%勝率」對這兩層失效。故把 dir/chip 當「機構共識至少一邊」而非兩張獨立票。
2. **大型股掩蓋稀釋風險**：實測 2330 上 3-of-4 唯一會放掉的就是 structure（dir/chip 幾乎不單獨失效）→「必含 dir/chip」在大型股**零成本**、在中小型 universe **才真正擋住假突破**（丟 chip 反事實單 fwd5 -6.9% / fwd10 -12.6%）。**這是 v0.1 IS 必須納中小型股、不能只看 2330 的根本理由。**
3. **不採加權**：加權引入連續權重自由度，過擬合懷疑論者明確反對 v0.1 增旋鈕。若 v0.2 採加權，dir+chip 合計權重不得等於兩個獨立層。

---

## 4. 參數表（v2 預設重現 baseline / v3 先驗值）

| 參數 | v2 預設 | v3 值（v0.1 先驗） | sweep 範圍（OOS only） | 理由 |
|:--|:--|:--|:--|:--|
| `entry_min_layers` | 4 | 3 | v0.2 {2,3,4}；2 須附警告 | 3-of-4=多數共振最小誠實定義（容一層落後、不容兩層同失效）。實際放行由必含層決定，此為冗餘上限+記錄。2 背叛 hypothesis。 |
| `entry_min_structure` | 2 | 1（close≥box_mid） | v0.2 + `entry_structure_mode` | structure≥1=站在箱體上半未轉弱，有先驗交易意義；==2 瞬時條件過嚴。structure==0 永遠排除。 |
| `entry_first_cross_only` | True | False | v0.2 {True,False} | `prev_total<5` 是 ADR-017 證實的收斂主力之一。放行持續站上解除 transition 偏誤，須配 confirm+cooldown 防 churn。 |
| `entry_confirm_days` | 1 | 2 | v0.3 {1,2,3} | 探針實證 confirm=2 在 2020-2024 +0.69%、有過濾單日插針先驗。K=1 是 transition 偏誤最大端點，最不該當預設。 |
| `entry_cooldown_bars`（守門，**固定不 sweep**） | 0 | 3 | v0.3 {0,2,3,5}；v0.1/v0.2 固定 | first_cross=False+confirm=2+單日 flameout 仍可能反覆進出磨成本。固定常識值控自由度。structure==2 突破新箱頂豁免。 |
| `exit_flameout_confirm_bars`（exit 搭配，**固定不 sweep**） | 1 | 2 | v0.3 {1,2}；v0.1 固定 | 464≫188 抱不住根因。給 momentum 熄火一個確認 bar，否則增量單在正常回檔被單根黑K洗掉。box_lower 硬停損不動。 |

---

## 5. entry / exit pseudocode

```python
# ── 進場 gate (v0.1 單一先驗預設) ──
def v3_buy_signal(row, prev_rows, cfg, position, cooldown_state):
    if position.in_position:
        return False

    # 0. re-entry cooldown (固定 3, 突破新箱頂豁免)
    if cooldown_state.bars_since_exit < cfg.entry_cooldown_bars:
        if not (row.structure_score == 2 and row.close > prev_rows[-1].box_upper):
            return False

    # 1. 必含層不變式
    if not (row.momentum_score >= 1 and row.structure_score >= 1
            and (row.direction_score >= 1 or row.chip_score >= 1)):
        return False

    # 2. 負向 veto hard floor
    if row.direction_score == -1 or row.chip_score == -1:
        return False

    # 3. 冗餘 N-of-4 計數上限門
    layers_hit = sum(s >= 1 for s in [row.structure_score, row.direction_score,
                                      row.chip_score, row.momentum_score])
    if layers_hit < cfg.entry_min_layers:           # =3
        return False

    # 4. 算術品質地板 (凍結)
    if row.total_score < cfg.strong_buy_threshold:  # >=5
        return False

    # 5. confirm_days 持續站穩 (first_cross_only=False, confirm=2)
    if not all(prev_rows[-k].structure_score >= 1
               for k in range(1, cfg.entry_confirm_days)):
        return False

    # 6. edge_ok 成本/波動地板 (凍結, 實測 ~1.27%)
    return bool(row.edge_ok)

# ── 出場:最小 exit 搭配 (與進場同 commit) ──
def v3_flameout_exit(row, prev_row, cfg, position):
    if not position.in_position:
        return False
    if row.close < row.box_lower or row.close < row.risk_swing_low:
        return True                                  # 硬停損(優先,不動)
    if row.momentum_score == -1 and prev_row.momentum_score == -1:
        return True                                  # flameout(2-bar 確認)
    return False
```

---

## 6. 強制守門（非參數）

1. **momentum_score≥1 強制守門**：必含層/N-of-4 皆不豁免動能。逆動能進場是已知賠錢路徑（四 lens 一致）。
2. **必含層不變式**：structure+momentum 必到（型態本質）、dir/chip 至少一邊（機構共識）。擋中小型單一主力假突破。
3. **edge_ok 凍結**：`volatility_rate >= cost_round_rate + min_edge_rate`，v0.1 不放鬆、不升級。
4. **total≥5 算術地板凍結**：明文凍結 threshold，防偷放第二個旋鈕。
5. **負向 veto hard floor**：dir==-1 OR chip==-1 即不進，不被任何總分蓋過。
6. **box_lower 硬停損絕不放寬**：`close<box_lower OR close<risk_swing_low` 即時、不受 cost 濾網、優先於 buy（SIGNAL_PRIORITY）。exit 最小鬆綁只動 flameout 確認窗。
7. **re-entry cooldown=3**：防 churn 漏成本，突破新箱頂豁免。
8. **凍結清單**（v0.1 全程不動）：`strong_buy_threshold=5`、`min_edge_rate=0.006`、`warning_threshold=2`、`add_score_threshold=6`、`box_period=60`、`chip_strong_threshold=0.10`、所有 cost/tp 參數。**只允許動 4 進場旋鈕 + 2 固定守門。**
9. **向後相容 regression test**：v2 預設精確重現 baseline 14 次進場，CI 釘死。

---

## 7. exit 決策 — 為何納入最小搭配且不違反 ADR-017

**決策：納入 v3 範圍、為必要項。** flameout 的 momentum 觸發 1→2 bar 確認（`exit_flameout_confirm_bars=2`，固定不 sweep）；box_lower/risk_swing_low 硬停損完全不動。不碰其餘 exit。

**為何不違反 ADR-017「出場校準單獨無效」：**

| ADR-017 否決的 | 本次做的 |
|:--|:--|
| v2 過嚴進場**不變**下、**單獨**調 flameout，最佳 ~0.4% CAGR | 進場放寬（必含層+structure≥1+first_cross=False+confirm=2，預期 30-80 筆）**搭配** exit 最小鬆綁 |
| 進場 14 次樣本不足，出場再調也無從兌現 | 進場放寬後樣本足，flameout 確認窗讓增量單有機會奔跑 |

四 lens 一致論證「只放寬進場不動 flameout = 半套」：464≫188、3.4 bar、放寬增量單會被 hair-trigger flameout 在 3 bar 內洗掉，製造「>40 筆但平均持有仍 3 bar、勝率仍 coin-flip」假成功。

**誠實邊界：** v0.1 同批必輸出 `flameout=1`（原始）對照組，證明改善來自搭配而非單側。若 flameout=2 單獨拉長持有但不改善跨窗一致性，回退並承認 exit 鬆綁無效（避免重蹈 ADR-017 自欺）。

---

## 8. 成本基準校正（壓測發現的 doc/code drift）

實測（以 code `strategy_config.py` L37-56 為真相源）：

- `cost_buy_rate ≈ 0.186%`、`cost_sell_rate ≈ 0.486%`、**`cost_round_rate ≈ 0.671%`**、**`edge_ok 門檻 ≈ 1.27%`**。
- v2.md §2.5.1（L760）寫 `cost_round 1.07%`（含 0.2%×2 buffer）、line 777 寫「1.3%」。**三處不一致**：code **無** 0.002 buffer。

**決定：** v0.1 在 spec 明記 code 實測值為單一真相源，並開 doc-sync 修正 v2.md §2.5.1 與 line 777。是否把 0.002 buffer 補進 code（→ edge 門檻升至 ~1.67%）交使用者決定，但 v0.1 至少消除三方不一致並單一記錄。中小型 universe slip buffer 上調（v2.md L766 自承 0.5%）留 v0.2。

> **為何 load-bearing：** 壓測 edge 門檻若算錯 ~0.4%，在 30-80 筆上放大成顯著歸因偏差；違反 MEMORY「用 ground-truth 核對」。

---

## 9. 測試策略

1. **regression（CRITICAL）**：v2 預設精確重現 baseline 14 次進場 + 47/1216 在市場 bars，CI 釘死。
2. **單元**：必含層不變式、負向 veto、cooldown 豁免、confirm_days 邊界、flameout 2-bar 確認，各別 truth-table 測試。
3. **雙窗口 IS（人工讀，非自動 gate）**：2015-2020 / 2020-2024，標的 = 2330 + 2-3 檔中小型成分股（1101/1303/2308/2317/2891/3008/2412，已有 broker_chips+institutional parquet）。同批輸出 flameout=1 對照組。
4. **凍結驗證**：測試確認 v0.1 run 未動凍結清單任一欄。

---

## 10. 文件同步（code-doc-sync 觸發表）

| 觸發 | 必動 docs |
|:--|:--|
| signals.py / config 進場+exit 邏輯改 | v2.md §2.4（開 v3 並存對照，非整段重寫）、§2.5.1 成本校正 |
| 新 StrategyConfig 欄位 | 21 資料契約、09 依賴、v2.md §6.1.1 參數表 |
| 進場 hypothesis 重設 + exit 最小搭配決策 | 新增 ADR、ADR-017 cross-ref、02 PRD 決策沿革表、INDEX ADR 表計數 |
| 風控/熔斷（flameout 確認窗、負向 veto、cooldown） | 24 風控規格、13 安全清單 |
| Sprint milestone | **16 WBS §5 R9（單一狀態真相源，永遠更新進度欄）** |

---

## 11. 成功標準（v0.1 exit gate — 誠實版）

**硬性 PASS（全過才算「值得進 v0.2 OOS」，綠燈≠有 edge）：**

1. v2 預設重現 baseline 14 次（regression 綠）。
2. **跨雙窗口符號一致**：CAGR/Sharpe 符號相同且差距不誇張（非一窗正一窗深負）。
3. **進出場成對**：同批輸出 flameout=1 對照組，改善來自搭配非單側。
4. **邊際單品質不劣化**：邊際單勝率 ≥ baseline -5pp；profit factor 不降；每筆扣成本淨利 >0 且 > min_edge_rate。
5. **操盤手體檢**：平均持有 ≥6 bar（從 3.4 拉長）；structure==1 中段進場占比 <30%；churn 率 <20%。

**明文禁令：**
- 進場數 >40 **嚴禁**當 PASS/成功指標，只當樣本健全性下限（30-80 筆/股/5年區間）。筆數只決定樣本夠不夠統計。
- v0.1 **禁止 sweep**：不好看時不得偷調 threshold/min_edge_rate 救筆數。
- 雙窗口綠燈零 edge 證據力：只代表「值得進 v0.2 OOS」，絕不據此進 M3/上實盤。

**誠實退場：** 雙窗口符號不一致 / 邊際單劣化 / 中小型 universe 也無一致正期望 → 問題在 hypothesis 不在進場閘，回 M0 換 edge 來源（候選 D 或重訂 edge），不續鬆閘自欺。

---

## 12. 開放風險

1. **edge_ok 凍結可能誤殺低波動箱型突破起點**（波段 lens）→ IS 讀片監控「被 edge_ok 擋下的 structure==2 突破單」數量，v0.2 決定是否補當根實波幅。
2. **portfolio 同日多檔群聚**（風控 lens）→ v0.1 逐股讀片，若見群聚，v0.2 進 portfolio 前優先補 heat cap / max_concurrent。
3. **2330 大型股 L3 退化為常數**（chip 0.10 在 2330 上 93% 恆真，籌碼 lens）→ 中小型 universe 須 v0.2 重校 chip_strong_threshold。
4. **6+ 護欄可能把進場壓回 ~14 筆**（風控 lens）→ 護欄分「硬地板（必留）/ 可調冷卻（v0.3 校準）」兩級，先用寬鬆值確認進場數上到 30-80 再收緊。
5. **中小型 universe 本身仍無 alpha** → 放寬解進場稀、解不了標的無 alpha（籌碼 lens + ADR-017）；退場觸發即回 M0。
6. **doc/code 成本 buffer 歸屬未定**（§8）→ 0.002 buffer 是否進 code 須使用者拍板，否則 edge 門檻持續模糊。

7. **confirm_days=2 視窗邊界 / warmup**：`prev_rows` 連續站穩判定須明確處理 `box_period=60` warmup 的 NaN bars 與序列邊界，否則 `first_cross_only=False + confirm=2` 在 warmup 邊界可能未定義行為。實作以單元測試釘死邊界（前 60 bar、序列首尾）。
8. **flameout 確認窗實作層級**：2-bar 確認須在 **signal 層**（用 `prev_momentum_score`）實作，**不改** `compute_states` 的 `state_flameout` 單 bar 語意——`state_flameout` 被 `warning` 等其他邏輯依賴，改其語意會污染下游。event-driven engine `evaluate_bar` 已有 `prev_momentum_score` 欄位可直接用。

---

> **設計 skill Phase 1 產物**｜分支 `feat/m0-v3-entry-redesign`｜四交易視角壓測（波段動能 / 籌碼法人 / 風控部位 / 過擬合懷疑論者）收斂｜待使用者 review → Phase 2 寫實作計畫。

